import aiosqlite

from api.config import settings


class ImageStore:
    """
    Stores raw image bytes alongside their ChromaDB chunk IDs so they can be
    retrieved at query time and passed to the vision model.
    """

    def __init__(self) -> None:
        self._path = settings.sqlite_path

    async def init(self) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS images (
                    id      TEXT PRIMARY KEY,
                    doc_id  TEXT NOT NULL,
                    page    INTEGER NOT NULL,
                    data    BLOB NOT NULL
                )
                """
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_img_doc ON images(doc_id)"
            )
            await db.commit()

    async def add_images(self, images: list[dict]) -> None:
        """Each dict must have: id, doc_id, page, data (bytes)."""
        if not images:
            return
        async with aiosqlite.connect(self._path) as db:
            await db.executemany(
                "INSERT OR REPLACE INTO images(id, doc_id, page, data) VALUES(?,?,?,?)",
                [(img["id"], img["doc_id"], img["page"], img["data"]) for img in images],
            )
            await db.commit()

    async def get_by_ids(self, ids: list[str]) -> dict[str, bytes]:
        """Returns {chunk_id: image_bytes} for the given IDs."""
        if not ids:
            return {}
        placeholders = ",".join("?" * len(ids))
        async with aiosqlite.connect(self._path) as db:
            async with db.execute(
                f"SELECT id, data FROM images WHERE id IN ({placeholders})", ids
            ) as cursor:
                rows = await cursor.fetchall()
        return {r[0]: bytes(r[1]) for r in rows}

    async def delete_by_doc_id(self, doc_id: str) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute("DELETE FROM images WHERE doc_id = ?", (doc_id,))
            await db.commit()
