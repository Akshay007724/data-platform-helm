import logging
import os

import aiosqlite

from api.config import settings

logger = logging.getLogger(__name__)

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    text TEXT NOT NULL,
    page INTEGER,
    type TEXT
)
"""


class ChunkStore:
    def __init__(self) -> None:
        self._path = settings.sqlite_path

    async def init(self) -> None:
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        async with aiosqlite.connect(self._path) as db:
            await db.execute(CREATE_TABLE)
            await db.commit()
        logger.info("ChunkStore initialised at %s", self._path)

    async def add_chunks(self, chunks: list[dict]) -> None:
        """Insert or replace chunks. Each chunk: {id, doc_id, text, page, type}"""
        if not chunks:
            return
        async with aiosqlite.connect(self._path) as db:
            await db.executemany(
                "INSERT OR REPLACE INTO chunks (id, doc_id, text, page, type) VALUES (?, ?, ?, ?, ?)",
                [(c["id"], c["doc_id"], c["text"], c.get("page"), c.get("type")) for c in chunks],
            )
            await db.commit()

    async def get_all(self) -> list[dict]:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT id, doc_id, text, page, type FROM chunks") as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def get_by_ids(self, ids: list[str]) -> list[dict]:
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                f"SELECT id, doc_id, text, page, type FROM chunks WHERE id IN ({placeholders})",
                ids,
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def delete_by_doc_id(self, doc_id: str) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
            await db.commit()
