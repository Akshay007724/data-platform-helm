import base64
import io
import logging

import fitz  # PyMuPDF
import torch
from PIL import Image

from .base import BaseExtractor, ExtractedContent, PageContent

logger = logging.getLogger(__name__)

_MODEL_ID = "zai-org/GLM-OCR"
_OCR_PROMPT = "Text Recognition:"


class GlmOcrExtractor(BaseExtractor):
    """
    OCR extractor powered by GLM-OCR (zai-org/GLM-OCR, 0.9B).

    The model is loaded lazily on first use so it does not consume memory
    when all uploaded documents are digital (text-layer) PDFs.
    """

    def __init__(self) -> None:
        self._processor = None
        self._model = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._model is not None:
            return
        logger.info("Loading GLM-OCR model: %s", _MODEL_ID)
        from transformers import AutoProcessor, GlmOcrForConditionalGeneration  # noqa: PLC0415

        self._processor = AutoProcessor.from_pretrained(_MODEL_ID)
        self._model = GlmOcrForConditionalGeneration.from_pretrained(
            _MODEL_ID,
            dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            device_map="auto",
        )
        logger.info("GLM-OCR model loaded")

    def _ocr_pil(self, pil_image: Image.Image) -> str:
        """Run GLM-OCR on a single PIL image and return the extracted text."""
        self._load()

        # Encode the image as a data URL so the processor handles it in-memory
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        data_url = f"data:image/png;base64,{b64}"

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "url": data_url},
                    {"type": "text", "text": _OCR_PROMPT},
                ],
            }
        ]
        inputs = self._processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self._model.device)

        output = self._model.generate(**inputs, max_new_tokens=2048)
        # Decode only the newly generated tokens (skip the prompt)
        prompt_len = inputs["input_ids"].shape[1]
        return self._processor.decode(output[0][prompt_len:], skip_special_tokens=True).strip()

    # ------------------------------------------------------------------
    # Public extraction API
    # ------------------------------------------------------------------

    def extract(self, file_bytes: bytes) -> ExtractedContent:
        """
        Extract text from a scanned PDF by rendering each page to a 150 DPI
        image and running GLM-OCR on it.
        """
        pages: list[PageContent] = []
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                # Render at 150 DPI (matrix scale = 150/72 ≈ 2.08×)
                mat = fitz.Matrix(150 / 72, 150 / 72)
                pix = page.get_pixmap(matrix=mat)
                pil = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                text = self._ocr_pil(pil)
                logger.debug("GLM-OCR page %d: %d chars extracted", page_num + 1, len(text))
                pages.append(PageContent(page=page_num + 1, text=text))
        finally:
            doc.close()
        return ExtractedContent(pages=pages, file_type="pdf")

    def extract_image(self, file_bytes: bytes) -> ExtractedContent:
        """Extract text from a raw image file (jpg, png, tiff, etc.)."""
        pil = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        text = self._ocr_pil(pil)
        return ExtractedContent(
            pages=[PageContent(page=1, text=text)],
            file_type="image",
        )
