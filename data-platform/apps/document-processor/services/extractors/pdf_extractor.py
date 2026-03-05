import fitz  # PyMuPDF

from .base import BaseExtractor, ExtractedContent, PageContent, TableContent


class PdfExtractor(BaseExtractor):
    def extract(self, file_bytes: bytes) -> ExtractedContent:
        pages: list[PageContent] = []
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]

                # --- Tables (PyMuPDF >= 1.23) ---
                tables: list[TableContent] = []
                table_bboxes = []
                for tab in page.find_tables():
                    raw = tab.extract()
                    if not raw:
                        continue
                    clean = [[str(cell) if cell else "" for cell in row] for row in raw]
                    if not any(any(c.strip() for c in row) for row in clean):
                        continue
                    headers = clean[0]
                    rows = clean[1:]
                    tables.append(
                        TableContent(page=page_num + 1, headers=headers, rows=rows)
                    )
                    table_bboxes.append(tab.bbox)

                # --- Text (skip table regions to avoid duplication) ---
                blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, ...)
                text_parts: list[str] = []
                for block in blocks:
                    bx0, by0, bx1, by1, block_text = block[:5]
                    if not block_text.strip():
                        continue
                    in_table = any(
                        bx0 >= tx0 - 2 and by0 >= ty0 - 2 and bx1 <= tx1 + 2 and by1 <= ty1 + 2
                        for tx0, ty0, tx1, ty1 in table_bboxes
                    )
                    if not in_table:
                        text_parts.append(block_text.strip())
                text = "\n\n".join(text_parts)

                # --- Images ---
                image_blobs: list[bytes] = []
                for img_info in page.get_images(full=True):
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    image_blobs.append(base_image["image"])

                pages.append(
                    PageContent(
                        page=page_num + 1,
                        text=text,
                        images=image_blobs,
                        tables=tables,
                    )
                )
        finally:
            doc.close()
        return ExtractedContent(pages=pages, file_type="pdf")
