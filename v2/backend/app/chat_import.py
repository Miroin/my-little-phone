from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, File, HTTPException, Query, UploadFile


def _timestamp(value: object) -> str | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value), timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _message_text(message: dict) -> str:
    content = message.get("content") or {}
    parts = content.get("parts") or []
    text_parts: list[str] = []
    for part in parts:
        if isinstance(part, str):
            text_parts.append(part)
        elif isinstance(part, dict) and isinstance(part.get("text"), str):
            text_parts.append(part["text"])
    return "\n".join(item.strip() for item in text_parts if item.strip()).strip()


def _conversation_messages(conversation: dict) -> list[dict]:
    mapping = conversation.get("mapping") or {}
    if not isinstance(mapping, dict):
        return []
    ordered: list[dict] = []
    current = conversation.get("current_node")
    visited: set[str] = set()
    while current and current not in visited:
        visited.add(current)
        node = mapping.get(current) or {}
        message = node.get("message")
        if isinstance(message, dict):
            ordered.append(message)
        current = node.get("parent")
    if ordered:
        ordered.reverse()
    else:
        ordered = [node["message"] for node in mapping.values() if isinstance(node, dict) and isinstance(node.get("message"), dict)]
        ordered.sort(key=lambda item: item.get("create_time") or 0)
    result: list[dict] = []
    for message in ordered:
        role = ((message.get("author") or {}).get("role") or "").lower()
        if role not in {"user", "assistant"}:
            continue
        text = _message_text(message)
        if not text:
            continue
        result.append({
            "source_id": str(message.get("id") or ""),
            "speaker": role,
            "text": text,
            "created_at": _timestamp(message.get("create_time")),
        })
    return result


def install_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS import_batches(
            id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_sha256 TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            conversation_count INTEGER NOT NULL DEFAULT 0,
            message_count INTEGER NOT NULL DEFAULT 0,
            cursor INTEGER NOT NULL DEFAULT 0,
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS imported_conversations(
            id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL REFERENCES import_batches(id) ON DELETE CASCADE,
            source_id TEXT,
            title TEXT NOT NULL,
            created_at TEXT,
            updated_at TEXT,
            message_count INTEGER NOT NULL DEFAULT 0,
            UNIQUE(batch_id,source_id)
        );
        CREATE INDEX IF NOT EXISTS idx_imported_conversations_batch ON imported_conversations(batch_id,created_at);
        CREATE TABLE IF NOT EXISTS imported_messages(
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL REFERENCES imported_conversations(id) ON DELETE CASCADE,
            source_id TEXT,
            speaker TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT,
            ordinal INTEGER NOT NULL,
            text_sha256 TEXT NOT NULL,
            UNIQUE(conversation_id,ordinal)
        );
        CREATE INDEX IF NOT EXISTS idx_imported_messages_conversation ON imported_messages(conversation_id,ordinal);
        """
    )


def build_router(
    db_factory: Callable[[], sqlite3.Connection],
    now: Callable[[], str],
    new_id: Callable[[], str],
) -> APIRouter:
    router = APIRouter(prefix="/api/history-imports", tags=["history-imports"])

    @router.post("/chatgpt", status_code=201)
    async def import_chatgpt(file: UploadFile = File(...)) -> dict:
        filename = file.filename or "conversations.json"
        if not filename.lower().endswith(".json"):
            raise HTTPException(status_code=400, detail="请选择 ChatGPT 导出的 conversations.json")
        digest = hashlib.sha256()
        size = 0
        max_bytes = 250 * 1024 * 1024
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(prefix="mlp-import-", suffix=".json", delete=False) as temp:
                temp_path = Path(temp.name)
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_bytes:
                        raise HTTPException(status_code=413, detail="聊天文件超过 250MB，请分批导入")
                    digest.update(chunk)
                    temp.write(chunk)
            file_hash = digest.hexdigest()
            existing_batch: dict | None = None
            with db_factory() as connection:
                install_schema(connection)
                existing = connection.execute("SELECT * FROM import_batches WHERE file_sha256=?", (file_hash,)).fetchone()
                if existing and existing["status"] == "previewed":
                    return {**dict(existing), "duplicate": True}
                if existing:
                    existing_batch = dict(existing)

            try:
                raw = json.loads(temp_path.read_text(encoding="utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=400, detail="无法读取这个 JSON 文件，请确认它来自 ChatGPT 数据导出") from exc
            if not isinstance(raw, list):
                raise HTTPException(status_code=400, detail="文件结构不是 ChatGPT conversations.json")

            batch_id = existing_batch["id"] if existing_batch else new_id()
            timestamp = now()
            start_cursor = int(existing_batch["cursor"] or 0) if existing_batch else 0
            conversation_count = int(existing_batch["conversation_count"] or 0) if existing_batch else 0
            message_count = int(existing_batch["message_count"] or 0) if existing_batch else 0
            with db_factory() as connection:
                install_schema(connection)
                if existing_batch:
                    connection.execute("UPDATE import_batches SET status='reading',error=NULL,updated_at=? WHERE id=?", (timestamp, batch_id))
                else:
                    connection.execute(
                        "INSERT INTO import_batches VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (batch_id, "chatgpt", filename, file_hash, "reading", 0, 0, 0, None, timestamp, timestamp),
                    )
                for index, conversation in enumerate(raw):
                    if index < start_cursor:
                        continue
                    if not isinstance(conversation, dict):
                        continue
                    messages = _conversation_messages(conversation)
                    if not messages:
                        continue
                    conversation_id = new_id()
                    source_id = str(conversation.get("id") or f"conversation-{index}")
                    connection.execute(
                        "INSERT OR IGNORE INTO imported_conversations VALUES(?,?,?,?,?,?,?)",
                        (conversation_id, batch_id, source_id, str(conversation.get("title") or "未命名对话"), _timestamp(conversation.get("create_time")), _timestamp(conversation.get("update_time")), len(messages)),
                    )
                    for ordinal, message in enumerate(messages):
                        connection.execute(
                            "INSERT INTO imported_messages VALUES(?,?,?,?,?,?,?,?)",
                            (new_id(), conversation_id, message["source_id"], message["speaker"], message["text"], message["created_at"], ordinal, hashlib.sha256(message["text"].encode("utf-8")).hexdigest()),
                        )
                    conversation_count += 1
                    message_count += len(messages)
                    if conversation_count % 50 == 0:
                        connection.execute("UPDATE import_batches SET cursor=?,conversation_count=?,message_count=?,updated_at=? WHERE id=?", (index + 1, conversation_count, message_count, now(), batch_id))
                        connection.commit()
                connection.execute(
                    "UPDATE import_batches SET status='previewed',cursor=?,conversation_count=?,message_count=?,updated_at=? WHERE id=?",
                    (len(raw), conversation_count, message_count, now(), batch_id),
                )
                row = connection.execute("SELECT * FROM import_batches WHERE id=?", (batch_id,)).fetchone()
            return {**dict(row), "duplicate": False, "resumed": bool(existing_batch)}
        finally:
            await file.close()
            if temp_path:
                temp_path.unlink(missing_ok=True)

    @router.get("")
    def list_imports(limit: int = Query(default=20, ge=1, le=100)) -> list[dict]:
        with db_factory() as connection:
            install_schema(connection)
            rows = connection.execute("SELECT * FROM import_batches ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    @router.get("/{batch_id}")
    def get_import(batch_id: str) -> dict:
        with db_factory() as connection:
            install_schema(connection)
            row = connection.execute("SELECT * FROM import_batches WHERE id=?", (batch_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="没有找到这个导入批次")
        return dict(row)

    @router.get("/{batch_id}/conversations")
    def list_conversations(batch_id: str, offset: int = Query(default=0, ge=0), limit: int = Query(default=30, ge=1, le=100)) -> dict:
        with db_factory() as connection:
            install_schema(connection)
            total = connection.execute("SELECT COUNT(*) FROM imported_conversations WHERE batch_id=?", (batch_id,)).fetchone()[0]
            rows = connection.execute(
                "SELECT * FROM imported_conversations WHERE batch_id=? ORDER BY COALESCE(created_at,'') DESC LIMIT ? OFFSET ?",
                (batch_id, limit, offset),
            ).fetchall()
        return {"total": total, "offset": offset, "limit": limit, "items": [dict(row) for row in rows]}

    @router.get("/conversations/{conversation_id}/messages")
    def conversation_messages(conversation_id: str, offset: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=500)) -> dict:
        with db_factory() as connection:
            install_schema(connection)
            total = connection.execute("SELECT COUNT(*) FROM imported_messages WHERE conversation_id=?", (conversation_id,)).fetchone()[0]
            rows = connection.execute(
                "SELECT * FROM imported_messages WHERE conversation_id=? ORDER BY ordinal LIMIT ? OFFSET ?",
                (conversation_id, limit, offset),
            ).fetchall()
        return {"total": total, "offset": offset, "limit": limit, "items": [dict(row) for row in rows]}

    return router
