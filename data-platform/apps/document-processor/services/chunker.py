import re

from api.config import settings
from services.extractors.base import TableContent

# Lines shorter than this that end with no period are treated as headings
_HEADING_MAX_LEN = 120
_HEADING_RE = re.compile(r"^(\d+[\.\)]|\#{1,4}|[A-Z][A-Z\s]{3,}$)")


def _is_heading(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > _HEADING_MAX_LEN:
        return False
    return bool(_HEADING_RE.match(line)) or (line.isupper() and len(line.split()) <= 8)


def chunk_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    """
    Paragraph-aware chunker. Splits on blank lines, keeps headings attached
    to their following paragraph, falls back to sentence splitting for oversized blocks.
    """
    chunk_size = chunk_size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap

    if not text.strip():
        return []

    # Split into blocks on blank lines
    raw_blocks = re.split(r"\n{2,}", text)
    blocks: list[str] = [b.strip() for b in raw_blocks if b.strip()]

    # Attach headings to the next block so they never float alone
    merged: list[str] = []
    i = 0
    while i < len(blocks):
        if _is_heading(blocks[i]) and i + 1 < len(blocks):
            merged.append(f"{blocks[i]}\n{blocks[i + 1]}")
            i += 2
        else:
            merged.append(blocks[i])
            i += 1

    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    def _flush() -> str:
        return "\n\n".join(current_parts)

    for block in merged:
        # Block fits in current chunk
        if current_len + len(block) + 2 <= chunk_size:
            current_parts.append(block)
            current_len += len(block) + 2
        else:
            if current_parts:
                chunks.append(_flush())
                # Overlap: carry the tail of the last part
                tail = current_parts[-1][-overlap:] if overlap else ""
                current_parts = [tail] if tail else []
                current_len = len(tail)

            # Block larger than chunk_size → sentence-level split
            if len(block) > chunk_size:
                sentences = re.split(r"(?<=[.!?])\s+", block)
                for sent in sentences:
                    if current_len + len(sent) + 1 <= chunk_size:
                        current_parts.append(sent)
                        current_len += len(sent) + 1
                    else:
                        if current_parts:
                            chunks.append(_flush())
                            tail = current_parts[-1][-overlap:] if overlap else ""
                            current_parts = [tail] if tail else []
                            current_len = len(tail)
                        current_parts.append(sent)
                        current_len = len(sent)
            else:
                current_parts.append(block)
                current_len += len(block) + 2

    if current_parts:
        chunks.append(_flush())

    return [c.strip() for c in chunks if c.strip()]


def chunk_table(table: TableContent) -> list[str]:
    """
    Generate multiple chunk representations of a table:
      1. Full table as pipe-delimited text (context chunk)
      2. One chunk per row with header:value pairs
      3. One chunk per column with all values
    """
    chunks: list[str] = []
    headers = [h.strip() for h in table.headers]

    # 1. Full table — header row + all data rows
    def _row_str(row: list[str]) -> str:
        return " | ".join(c.strip() for c in row)

    all_rows = ([headers] if headers else []) + table.rows
    full_text = "\n".join(_row_str(r) for r in all_rows if any(c.strip() for c in r))
    if table.caption:
        full_text = f"{table.caption}\n{full_text}"
    if full_text.strip():
        chunks.append(full_text.strip())

    # 2. Row-level chunks: "Col1: val | Col2: val | ..."
    for row in table.rows:
        if not any(c.strip() for c in row):
            continue
        if headers:
            pairs = [
                f"{h}: {v.strip()}"
                for h, v in zip(headers, row)
                if v.strip()
            ]
            row_text = " | ".join(pairs)
        else:
            row_text = " | ".join(c.strip() for c in row if c.strip())
        if row_text:
            prefix = f"{table.caption} — " if table.caption else ""
            chunks.append(f"{prefix}{row_text}")

    # 3. Column-level chunks: "ColumnName: v1, v2, v3"
    if headers:
        for col_idx, header in enumerate(headers):
            if not header:
                continue
            values = [
                row[col_idx].strip()
                for row in table.rows
                if col_idx < len(row) and row[col_idx].strip()
            ]
            if values:
                prefix = f"{table.caption} — " if table.caption else ""
                chunks.append(f"{prefix}{header}: {', '.join(values)}")

    return [c for c in chunks if c.strip()]
