from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Callable, Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

LifeKind = Literal["home", "music", "schedule"]


class LifeNoteCreate(BaseModel):
    kind: LifeKind
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(default="", max_length=8000)


def install_life_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """CREATE TABLE IF NOT EXISTS life_notes(
        id TEXT PRIMARY KEY,kind TEXT NOT NULL,title TEXT NOT NULL,content TEXT NOT NULL,
        created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS media_assets(
        id TEXT PRIMARY KEY,kind TEXT NOT NULL,title TEXT NOT NULL,path TEXT NOT NULL,mime_type TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_life_kind ON life_notes(kind,created_at);
        CREATE INDEX IF NOT EXISTS idx_media_kind ON media_assets(kind,created_at);
        """
    )


def build_router(db_factory: Callable[[], sqlite3.Connection], now: Callable[[], str], new_id: Callable[[], str]) -> APIRouter:
    router = APIRouter(prefix="/api/life", tags=["shared-life"])
    media_dir = Path(os.getenv("MLP_MEDIA_PATH", Path(__file__).resolve().parents[1] / "data" / "media"))

    @router.get("/notes")
    def notes(kind: LifeKind | None = None) -> list[dict]:
        with db_factory() as connection:
            install_life_schema(connection)
            rows = connection.execute("SELECT * FROM life_notes WHERE kind=? ORDER BY created_at DESC", (kind,)).fetchall() if kind else connection.execute("SELECT * FROM life_notes ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]

    @router.post("/notes", status_code=201)
    def add_note(body: LifeNoteCreate) -> dict:
        item_id, timestamp = new_id(), now()
        with db_factory() as connection:
            install_life_schema(connection)
            connection.execute("INSERT INTO life_notes VALUES(?,?,?,?,?,?)", (item_id, body.kind, body.title.strip(), body.content.strip(), timestamp, timestamp))
            row = connection.execute("SELECT * FROM life_notes WHERE id=?", (item_id,)).fetchone()
        return dict(row)

    @router.delete("/notes/{item_id}")
    def delete_note(item_id: str) -> dict:
        with db_factory() as connection:
            install_life_schema(connection)
            cursor = connection.execute("DELETE FROM life_notes WHERE id=?", (item_id,))
        if not cursor.rowcount:
            raise HTTPException(status_code=404, detail="没有找到这条内容")
        return {"deleted": True}

    @router.get("/media")
    def media() -> list[dict]:
        with db_factory() as connection:
            install_life_schema(connection)
            rows = connection.execute("SELECT * FROM media_assets ORDER BY created_at DESC LIMIT 300").fetchall()
        return [{**dict(row), "url": f"/api/life/media/{row['id']}/file"} for row in rows]

    @router.post("/media", status_code=201)
    async def upload_media(file: UploadFile = File(...), title: str = Form(default="")) -> dict:
        if not (file.content_type or "").startswith("image/"):
            raise HTTPException(status_code=400, detail="相册目前只接受图片")
        raw = await file.read(12 * 1024 * 1024 + 1)
        await file.close()
        if len(raw) > 12 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="单张图片不能超过 12MB")
        extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}.get(file.content_type or "", ".img")
        asset_id, timestamp = new_id(), now()
        media_dir.mkdir(parents=True, exist_ok=True)
        path = media_dir / f"{asset_id}{extension}"
        path.write_bytes(raw)
        with db_factory() as connection:
            install_life_schema(connection)
            connection.execute("INSERT INTO media_assets VALUES(?,?,?,?,?,?,?)", (asset_id, "image", title.strip()[:120] or (file.filename or "照片")[:120], str(path), file.content_type, len(raw), timestamp))
            row = connection.execute("SELECT * FROM media_assets WHERE id=?", (asset_id,)).fetchone()
        return {**dict(row), "url": f"/api/life/media/{asset_id}/file"}

    @router.get("/media/{asset_id}/file")
    def media_file(asset_id: str) -> FileResponse:
        with db_factory() as connection:
            install_life_schema(connection)
            row = connection.execute("SELECT * FROM media_assets WHERE id=?", (asset_id,)).fetchone()
        if not row or not Path(row["path"]).is_file():
            raise HTTPException(status_code=404, detail="图片不存在")
        return FileResponse(row["path"], media_type=row["mime_type"])

    @router.delete("/media/{asset_id}")
    def delete_media(asset_id: str) -> dict:
        with db_factory() as connection:
            install_life_schema(connection)
            row = connection.execute("SELECT * FROM media_assets WHERE id=?", (asset_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="图片不存在")
            connection.execute("DELETE FROM media_assets WHERE id=?", (asset_id,))
        Path(row["path"]).unlink(missing_ok=True)
        return {"deleted": True}

    return router
