import logging
import os
from datetime import datetime, timezone

import aiosqlite

from api.config import settings

logger = logging.getLogger(__name__)

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    chunk_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DocumentStore:
    def __init__(self) -> None:
        self._path = settings.sqlite_path

    async def init(self) -> None:
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        async with aiosqlite.connect(self._path) as db:
            await db.execute(CREATE_TABLE)
            await db.commit()
        logger.info("DocumentStore initialised at %s", self._path)

    async def create(self, doc_id: str, filename: str, file_type: str) -> dict:
        now = _now()
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "INSERT INTO documents (id, filename, file_type, status, chunk_count, created_at, updated_at)"
                " VALUES (?, ?, ?, 'pending', 0, ?, ?)",
                (doc_id, filename, file_type, now, now),
            )
            await db.commit()
        return await self.get(doc_id)

    async def update_status(
        self,
        doc_id: str,
        status: str,
        chunk_count: int | None = None,
        error_message: str | None = None,
    ) -> None:
        now = _now()
        async with aiosqlite.connect(self._path) as db:
            if chunk_count is not None:
                await db.execute(
                    "UPDATE documents SET status=?, chunk_count=?, error_message=?, updated_at=? WHERE id=?",
                    (status, chunk_count, error_message, now, doc_id),
                )
            else:
                await db.execute(
                    "UPDATE documents SET status=?, error_message=?, updated_at=? WHERE id=?",
                    (status, error_message, now, doc_id),
                )
            await db.commit()

    async def get(self, doc_id: str) -> dict | None:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM documents WHERE id=?", (doc_id,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def list_all(self) -> list[dict]:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM documents ORDER BY created_at DESC"
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def delete(self, doc_id: str) -> bool:
        async with aiosqlite.connect(self._path) as db:
            cur = await db.execute("DELETE FROM documents WHERE id=?", (doc_id,))
            await db.commit()
            return cur.rowcount > 0
