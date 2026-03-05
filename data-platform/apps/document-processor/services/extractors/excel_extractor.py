import io

import pandas as pd

from .base import BaseExtractor, ExtractedContent, PageContent, TableContent


class ExcelExtractor(BaseExtractor):
    def extract(self, file_bytes: bytes) -> ExtractedContent:
        pages: list[PageContent] = []
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        for idx, sheet_name in enumerate(xl.sheet_names, start=1):
            df = xl.parse(sheet_name)
            df = df.dropna(how="all").fillna("")

            headers = [str(c) for c in df.columns.tolist()]
            rows = [[str(v) for v in row] for row in df.values.tolist()]

            table = TableContent(
                page=idx,
                headers=headers,
                rows=rows,
                caption=f"Sheet: {sheet_name}",
            )
            # Keep a brief text summary too (for full-document context search)
            text = f"Sheet: {sheet_name}\n{df.to_string(index=False)}"
            pages.append(PageContent(page=idx, text=text, tables=[table]))

        return ExtractedContent(pages=pages, file_type="excel")
