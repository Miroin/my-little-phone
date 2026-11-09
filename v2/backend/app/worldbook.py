from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Callable

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


class WorldbookInput(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=30000)
    keywords: list[str] = Field(default_factory=list, max_length=100)
    enabled: bool = True


def install_worldbook_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """CREATE TABLE IF NOT EXISTS worldbook_entries(
        id TEXT PRIMARY KEY,title TEXT NOT NULL,content TEXT NOT NULL,keywords_json TEXT NOT NULL DEFAULT '[]',
        enabled INTEGER NOT NULL DEFAULT 1,content_hash TEXT NOT NULL UNIQUE,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_worldbook_enabled ON worldbook_entries(enabled,updated_at);"""
    )


def _digest(title: str, content: str) -> str:
    return hashlib.sha256(f"{title.strip()}\n{content.strip()}".encode("utf-8")).hexdigest()


def entry_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "title": row["title"], "content": row["content"],
        "keywords": json.loads(row["keywords_json"] or "[]"), "enabled": bool(row["enabled"]),
        "createdAt": row["created_at"], "updatedAt": row["updated_at"],
    }


def worldbook_prompt(connection: sqlite3.Connection, query: str, limit: int = 8) -> list[str]:
    install_worldbook_schema(connection)
    normalized = query.casefold()
    matches: list[tuple[sqlite3.Row, int]] = []
    for row in connection.execute("SELECT * FROM worldbook_entries WHERE enabled=1 ORDER BY updated_at DESC"):
        keywords = [str(value).strip().casefold() for value in json.loads(row["keywords_json"] or "[]") if str(value).strip()]
        score = 1 if not keywords else sum(3 for keyword in keywords if keyword in normalized)
        if row["title"].casefold() in normalized:
            score += 2
        if score:
            matches.append((row, score))
    matches.sort(key=lambda item: (item[1], item[0]["updated_at"]), reverse=True)
    return [f"[世界书/{row['title']}] {row['content']}" for row, _ in matches[:limit]]


def build_router(db_factory: Callable[[], sqlite3.Connection], now: Callable[[], str], new_id: Callable[[], str]) -> APIRouter:
    router = APIRouter(prefix="/api/worldbook", tags=["worldbook"])

    @router.get("")
    def list_entries() -> list[dict]:
        with db_factory() as connection:
            install_worldbook_schema(connection)
            rows = connection.execute("SELECT * FROM worldbook_entries ORDER BY updated_at DESC").fetchall()
        return [entry_dict(row) for row in rows]

    @router.post("", status_code=201)
    def create_entry(body: WorldbookInput) -> dict:
        entry_id, timestamp = new_id(), now()
        keywords = [value.strip() for value in body.keywords if value.strip()][:100]
        try:
            with db_factory() as connection:
                install_worldbook_schema(connection)
                connection.execute(
                    "INSERT INTO worldbook_entries VALUES(?,?,?,?,?,?,?,?)",
                    (entry_id, body.title.strip(), body.content.strip(), json.dumps(keywords, ensure_ascii=False),
                     body.enabled, _digest(body.title, body.content), timestamp, timestamp),
                )
                row = connection.execute("SELECT * FROM worldbook_entries WHERE id=?", (entry_id,)).fetchone()
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="相同的世界书条目已经存在") from exc
        return entry_dict(row)

    @router.put("/{entry_id}")
    def update_entry(entry_id: str, body: WorldbookInput) -> dict:
        keywords = [value.strip() for value in body.keywords if value.strip()][:100]
        try:
            with db_factory() as connection:
                cursor = connection.execute(
                    """UPDATE worldbook_entries SET title=?,content=?,keywords_json=?,enabled=?,content_hash=?,updated_at=?
                    WHERE id=?""",
                    (body.title.strip(), body.content.strip(), json.dumps(keywords, ensure_ascii=False), body.enabled,
                     _digest(body.title, body.content), now(), entry_id),
                )
                if not cursor.rowcount:
                    raise HTTPException(status_code=404, detail="没有找到世界书条目")
                row = connection.execute("SELECT * FROM worldbook_entries WHERE id=?", (entry_id,)).fetchone()
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="修改后与现有世界书条目重复") from exc
        return entry_dict(row)

    @router.delete("/{entry_id}")
    def delete_entry(entry_id: str) -> dict:
        with db_factory() as connection:
            cursor = connection.execute("DELETE FROM worldbook_entries WHERE id=?", (entry_id,))
        if not cursor.rowcount:
            raise HTTPException(status_code=404, detail="没有找到世界书条目")
        return {"deleted": True, "id": entry_id}

    return router
