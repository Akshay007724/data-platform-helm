import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from api.config import settings
from services.chunker import chunk_table, chunk_text
from services.document_store import DocumentStore
from services.embedder import Embedder
from services.extractors.base import ExtractedContent, PageContent
from services.extractors.excel_extractor import ExcelExtractor
from services.extractors.glm_ocr_extractor import GlmOcrExtractor
from services.extractors.pdf_extractor import PdfExtractor
from services.extractors.word_extractor import WordExtractor
from services.vector_store import VectorStore

logger = logging.getLogger(__name__)

_PDF_EXTRACTOR = PdfExtractor()
_OFFICE_EXTRACTORS = {
    "xlsx": ExcelExtractor(),
    "xls": ExcelExtractor(),
    "docx": WordExtractor(),
    "doc": WordExtractor(),
}
_IMAGE_TYPES = {"jpg", "jpeg", "png", "tiff", "tif", "bmp", "webp"}

# Shared lazy-loaded GLM-OCR instance (model downloaded on first use)
_glm_ocr = GlmOcrExtractor()


def _detect_file_type(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


class DocumentProcessor:
    def __init__(
        self,
        document_store: DocumentStore,
        vector_store: VectorStore,
        embedder: Embedder,
        chunk_store=None,
        hybrid_search=None,
    ) -> None:
        self._doc_store = document_store
        self._vec_store = vector_store
        self._embedder = embedder
        self._chunk_store = chunk_store
        self._hybrid_search = hybrid_search
        self._executor = ThreadPoolExecutor(max_workers=settings.max_workers)

    async def process(self, doc_id: str, filename: str, file_bytes: bytes) -> None:
        file_type = _detect_file_type(filename)
        supported = {"pdf"} | set(_OFFICE_EXTRACTORS) | _IMAGE_TYPES
        if file_type not in supported:
            await self._doc_store.update_status(
                doc_id, "error", error_message=f"Unsupported file type: {file_type}"
            )
            return

        await self._doc_store.update_status(doc_id, "processing")
        try:
            loop = asyncio.get_running_loop()

            # ── 1. Extract ────────────────────────────────────────────────
            # Routing:
            #   • Office files  → dedicated extractor (fast, lossless)
            #   • Image files   → GLM-OCR directly
            #   • PDF (digital) → PdfExtractor; if avg chars/page < threshold
            #                     it's a scanned PDF → re-extract with GLM-OCR
            if file_type in _OFFICE_EXTRACTORS:
                extracted: ExtractedContent = await loop.run_in_executor(
                    self._executor, partial(_OFFICE_EXTRACTORS[file_type].extract, file_bytes)
                )
            elif file_type in _IMAGE_TYPES:
                logger.info("Image upload (%s) — routing to GLM-OCR", file_type)
                extracted = await loop.run_in_executor(
                    self._executor, partial(_glm_ocr.extract_image, file_bytes)
                )
            else:  # pdf
                digital = await loop.run_in_executor(
                    self._executor, partial(_PDF_EXTRACTOR.extract, file_bytes)
                )
                total_chars = sum(len(p.text) for p in digital.pages)
                avg_chars = total_chars / max(len(digital.pages), 1)
                if avg_chars >= settings.ocr_scanned_threshold:
                    logger.info("Digital PDF (avg %.0f chars/page) — using text layer", avg_chars)
                    extracted = digital
                else:
                    logger.info(
                        "Scanned PDF detected (avg %.0f chars/page < threshold %d) "
                        "— re-extracting with GLM-OCR",
                        avg_chars, settings.ocr_scanned_threshold,
                    )
                    extracted = await loop.run_in_executor(
                        self._executor, partial(_glm_ocr.extract, file_bytes)
                    )

            # ── 2. Chunk all pages + tables in parallel ───────────────────
            async def chunk_page(page: PageContent) -> tuple[PageContent, list[str], list[str]]:
                text_chunks = await loop.run_in_executor(
                    self._executor, partial(chunk_text, page.text)
                )
                table_chunks: list[str] = []
                for table in page.tables:
                    tcs = await loop.run_in_executor(
                        self._executor, partial(chunk_table, table)
                    )
                    table_chunks.extend(tcs)
                return page, text_chunks, table_chunks

            page_results = await asyncio.gather(*[chunk_page(p) for p in extracted.pages])

            # ── 3. Collect indexable items ────────────────────────────────
            # text_items: (page, text, chunk_type)
            text_items: list[tuple[int, str, str]] = []
            # image_items: (page, img_bytes, caption)
            image_items: list[tuple[int, bytes, str]] = []

            for page, text_chunks, table_chunks in page_results:
                for c in text_chunks:
                    text_items.append((page.page, c, "text"))
                for c in table_chunks:
                    text_items.append((page.page, c, "table"))
                for img_bytes in page.images:
                    caption = f"Image from page {page.page}"
                    image_items.append((page.page, img_bytes, caption))

            # ── 4. Batch-embed ALL text + captions in one model.encode() ──
            all_index_texts = (
                [t for _, t, _ in text_items]
                + [cap for _, _, cap in image_items]
            )
            if all_index_texts:
                all_vectors = await loop.run_in_executor(
                    self._executor, partial(self._embedder.embed_texts, all_index_texts)
                )
                text_vectors = all_vectors[: len(text_items)]
                caption_vectors = all_vectors[len(text_items):]
            else:
                text_vectors, caption_vectors = [], []

            # ── 5. ONE batch upsert for text + table chunks ───────────────
            if text_items:
                text_chunk_ids = [str(uuid.uuid4()) for _ in text_items]
                await self._vec_store.upsert_batch([
                    {
                        "id": chunk_id,
                        "vector": vec,
                        "document": text,
                        "metadata": {"type": ctype, "doc_id": doc_id, "page": page},
                    }
                    for chunk_id, (page, text, ctype), vec in zip(text_chunk_ids, text_items, text_vectors)
                ])
                if self._chunk_store is not None:
                    await self._chunk_store.add_chunks([
                        {"id": chunk_id, "doc_id": doc_id, "text": text, "page": page, "type": ctype}
                        for chunk_id, (page, text, ctype) in zip(text_chunk_ids, text_items)
                    ])

            # ── 6. Embed images in parallel, ONE batch upsert ─────────────
            if image_items:
                img_vectors = await asyncio.gather(*[
                    loop.run_in_executor(
                        self._executor, partial(self._embedder.embed_image, img_bytes)
                    )
                    for _, img_bytes, _ in image_items
                ])
                await self._vec_store.upsert_batch([
                    {
                        "vector": cap_vec,
                        "document": caption,
                        "metadata": {"type": "image", "doc_id": doc_id, "page": page},
                    }
                    for (page, _, caption), cap_vec in zip(image_items, caption_vectors)
                ])

            if self._hybrid_search is not None:
                self._hybrid_search.mark_dirty()

            total = len(text_items) + len(image_items)
            await self._doc_store.update_status(doc_id, "ready", chunk_count=total)
            logger.info("Processed %s: %d chunks (%d text/table, %d image)",
                        filename, total, len(text_items), len(image_items))

        except Exception:
            logger.exception("Failed to process %s", filename)
            await self._doc_store.update_status(doc_id, "error",
                                                error_message="Processing failed — check logs")
