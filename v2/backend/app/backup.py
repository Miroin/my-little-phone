from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from pydantic import BaseModel


BACKUP_TABLES = (
    "messages", "memories", "calls", "memory_items", "memory_evidence", "memory_jobs",
    "memory_feedback", "memory_usage", "import_batches", "imported_conversations",
    "imported_messages", "memory_candidates", "memory_candidate_conflicts",
    "extraction_runs", "extraction_jobs", "extraction_chunks", "chat_runs", "audio_assets", "character_profiles",
    "companion_settings", "proactive_events",
    "life_notes", "media_assets", "worldbook_entries",
)
BACKUP_MAX_BYTES = max(1, int(os.getenv("MLP_BACKUP_MAX_MB", "512"))) * 1024 * 1024


class RestoreConfirm(BaseModel):
    token: str
    mode: str = "merge"


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def install_restore_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """CREATE TABLE IF NOT EXISTS restore_sessions(
        id TEXT PRIMARY KEY,checksum TEXT NOT NULL,payload_json TEXT NOT NULL,status TEXT NOT NULL,
        created_at TEXT NOT NULL,updated_at TEXT NOT NULL)"""
    )


def build_router(db_factory: Callable[[], sqlite3.Connection], now: Callable[[], str], new_id: Callable[[], str]) -> APIRouter:
    router = APIRouter(prefix="/api/backups", tags=["backups"])

    @router.get("/export")
    def export_backup() -> Response:
        payload: dict[str, object] = {"schemaVersion": 1, "exportedAt": now(), "tables": {}}
        with db_factory() as connection:
            existing = _tables(connection)
            for table in BACKUP_TABLES:
                if table in existing:
                    payload["tables"][table] = [dict(row) for row in connection.execute(f"SELECT * FROM {table}").fetchall()]
            audio_files: dict[str, str] = {}
            if "audio_assets" in existing:
                for row in connection.execute("SELECT id,path FROM audio_assets WHERE status='ready'"):
                    path = Path(row["path"])
                    if path.is_file():
                        audio_files[row["id"]] = base64.b64encode(path.read_bytes()).decode("ascii")
            payload["audioFiles"] = audio_files
            media_files: dict[str, str] = {}
            if "media_assets" in existing:
                for row in connection.execute("SELECT id,path FROM media_assets"):
                    path = Path(row["path"])
                    if path.is_file():
                        media_files[row["id"]] = base64.b64encode(path.read_bytes()).decode("ascii")
            payload["mediaFiles"] = media_files
        checksum = hashlib.sha256(_canonical(payload)).hexdigest()
        envelope = {"format": "my-little-phone-v2-backup", "checksum": checksum, "payload": payload}
        filename = f"my-little-phone-v2-{now()[:10]}.json"
        return Response(
            content=json.dumps(envelope, ensure_ascii=False, indent=2), media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"', "X-Backup-Checksum": checksum},
        )

    @router.post("/restore-preview", status_code=201)
    async def preview_restore(file: UploadFile = File(...)) -> dict:
        raw = await file.read(BACKUP_MAX_BYTES + 1)
        await file.close()
        if len(raw) > BACKUP_MAX_BYTES:
            raise HTTPException(status_code=413, detail=f"备份文件超过 {BACKUP_MAX_BYTES // 1024 // 1024}MB")
        try:
            envelope = json.loads(raw.decode("utf-8-sig"))
            payload = envelope["payload"]
            checksum = envelope["checksum"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise HTTPException(status_code=400, detail="这不是有效的小手叽 v2 备份") from exc
        if envelope.get("format") != "my-little-phone-v2-backup" or payload.get("schemaVersion") != 1:
            raise HTTPException(status_code=400, detail="备份格式或版本不受支持")
        actual = hashlib.sha256(_canonical(payload)).hexdigest()
        if actual != checksum:
            raise HTTPException(status_code=400, detail="备份校验失败，文件可能不完整")
        incoming = payload.get("tables")
        if not isinstance(incoming, dict) or any(name not in BACKUP_TABLES for name in incoming):
            raise HTTPException(status_code=400, detail="备份包含未知数据表")
        token, timestamp = new_id(), now()
        with db_factory() as connection:
            install_restore_schema(connection)
            connection.execute("INSERT INTO restore_sessions VALUES(?,?,?,?,?,?)", (token, checksum, json.dumps(payload, ensure_ascii=False), "previewed", timestamp, timestamp))
        return {
            "token": token, "checksum": checksum, "exportedAt": payload.get("exportedAt"),
            "counts": {name: len(rows) for name, rows in incoming.items() if isinstance(rows, list)},
            "mode": "merge-only", "warning": "确认后只补充缺失数据，不覆盖现有记录。",
        }

    @router.post("/restore-confirm")
    def confirm_restore(body: RestoreConfirm) -> dict:
        if body.mode != "merge":
            raise HTTPException(status_code=400, detail="当前只允许安全合并恢复")
        inserted: dict[str, int] = {}
        with db_factory() as connection:
            install_restore_schema(connection)
            session = connection.execute("SELECT * FROM restore_sessions WHERE id=? AND status='previewed'", (body.token,)).fetchone()
            if not session:
                raise HTTPException(status_code=404, detail="恢复预览不存在或已经使用")
            payload = json.loads(session["payload_json"])
            audio_dir = Path(os.getenv("MLP_AUDIO_PATH", Path(__file__).resolve().parents[1] / "data" / "audio"))
            media_dir = Path(os.getenv("MLP_MEDIA_PATH", Path(__file__).resolve().parents[1] / "data" / "media"))
            audio_dir.mkdir(parents=True, exist_ok=True)
            media_dir.mkdir(parents=True, exist_ok=True)
            existing = _tables(connection)
            for table in BACKUP_TABLES:
                rows = payload.get("tables", {}).get(table, [])
                if table not in existing or not isinstance(rows, list) or not rows:
                    inserted[table] = 0
                    continue
                allowed = [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
                count = 0
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    if table == "audio_assets":
                        row = {**row, "path": str(audio_dir / f"{row['id']}.mp3")}
                    elif table == "media_assets":
                        extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}.get(row.get("mime_type"), ".img")
                        row = {**row, "path": str(media_dir / f"{row['id']}{extension}")}
                    columns = [name for name in allowed if name in row]
                    if not columns:
                        continue
                    placeholders = ",".join("?" for _ in columns)
                    cursor = connection.execute(
                        f"INSERT OR IGNORE INTO {table}({','.join(columns)}) VALUES({placeholders})", [row[name] for name in columns]
                    )
                    count += cursor.rowcount
                inserted[table] = count
            for asset_id, encoded in payload.get("audioFiles", {}).items():
                target = audio_dir / f"{asset_id}.mp3"
                if not target.exists():
                    try:
                        target.write_bytes(base64.b64decode(encoded, validate=True))
                    except (ValueError, TypeError) as exc:
                        raise HTTPException(status_code=400, detail="备份中的语音文件损坏") from exc
            media_rows = {row.get("id"): row for row in payload.get("tables", {}).get("media_assets", []) if isinstance(row, dict)}
            for asset_id, encoded in payload.get("mediaFiles", {}).items():
                row = media_rows.get(asset_id, {})
                extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}.get(row.get("mime_type"), ".img")
                target = media_dir / f"{asset_id}{extension}"
                if not target.exists():
                    try:
                        target.write_bytes(base64.b64decode(encoded, validate=True))
                    except (ValueError, TypeError) as exc:
                        raise HTTPException(status_code=400, detail="备份中的相册文件损坏") from exc
            connection.execute("UPDATE restore_sessions SET status='merged',updated_at=? WHERE id=?", (now(), body.token))
        return {"restored": True, "mode": "merge", "inserted": inserted, "checksum": session["checksum"]}

    return router
