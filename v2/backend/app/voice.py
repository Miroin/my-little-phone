from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import FileResponse


VOICE_MARKER = re.compile(r"^\s*(?:\[voice\]|\[\[voice\]\]|【voice】)\s*", re.IGNORECASE)


def voice_text(value: str) -> tuple[bool, str]:
    matched = bool(VOICE_MARKER.match(value))
    return matched, VOICE_MARKER.sub("", value, count=1).strip()


def install_voice_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """CREATE TABLE IF NOT EXISTS audio_assets(
        id TEXT PRIMARY KEY,message_id TEXT NOT NULL UNIQUE,path TEXT NOT NULL,mime_type TEXT NOT NULL,
        duration_ms INTEGER NOT NULL DEFAULT 0,transcript TEXT NOT NULL,status TEXT NOT NULL,
        error TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)"""
    )


async def _minimax_synthesize(text: str) -> tuple[bytes, int]:
    try:
        import websockets
    except ImportError as exc:
        raise RuntimeError("服务端缺少 WebSocket 语音依赖") from exc
    api_key = os.getenv("MINIMAX_API_KEY")
    voice_id = os.getenv("MINIMAX_VOICE_ID")
    if not api_key or not voice_id:
        raise RuntimeError("服务端尚未配置 MiniMax API Key 或音色 ID")
    url = os.getenv("MINIMAX_T2A_WS_URL", "wss://api.minimax.io/ws/v1/t2a_v2")
    audio = bytearray()
    duration_ms = 0
    async with websockets.connect(url, additional_headers={"Authorization": f"Bearer {api_key}"}, open_timeout=20, close_timeout=10) as ws:
        connected = json.loads(await ws.recv())
        if connected.get("event") != "connected_success":
            raise RuntimeError("MiniMax 语音连接失败")
        await ws.send(json.dumps({
            "event": "task_start", "model": os.getenv("MINIMAX_SPEECH_MODEL", "speech-2.8-turbo"),
            "language_boost": "Chinese",
            "voice_setting": {"voice_id": voice_id, "speed": float(os.getenv("MINIMAX_VOICE_SPEED", "0.92")), "vol": 1, "pitch": int(os.getenv("MINIMAX_VOICE_PITCH", "0")), "english_normalization": False},
            "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
        }, ensure_ascii=False))
        started = json.loads(await ws.recv())
        if started.get("event") != "task_started":
            raise RuntimeError("MiniMax 语音任务启动失败")
        await ws.send(json.dumps({"event": "task_continue", "text": text}, ensure_ascii=False))
        while True:
            packet = json.loads(await ws.recv())
            if packet.get("event") == "task_failed":
                raise RuntimeError(packet.get("base_resp", {}).get("status_msg") or "MiniMax 语音生成失败")
            chunk = packet.get("data", {}).get("audio")
            if chunk:
                audio.extend(bytes.fromhex(chunk))
            info = packet.get("extra_info") or {}
            duration_ms = max(duration_ms, int(info.get("audio_length") or 0))
            if packet.get("is_final"):
                break
        await ws.send(json.dumps({"event": "task_finish"}))
    if not audio:
        raise RuntimeError("MiniMax 没有返回音频")
    return bytes(audio), duration_ms


def build_router(db_factory: Callable[[], sqlite3.Connection], now: Callable[[], str], new_id: Callable[[], str], root: Path) -> APIRouter:
    router = APIRouter(prefix="/api/voice", tags=["voice"])
    audio_dir = Path(os.getenv("MLP_AUDIO_PATH", root / "data" / "audio"))

    @router.post("/messages/{message_id}")
    async def synthesize_message(message_id: str, retry: bool = Query(default=False)) -> dict:
        with db_factory() as connection:
            install_voice_schema(connection)
            existing = connection.execute("SELECT * FROM audio_assets WHERE message_id=?", (message_id,)).fetchone()
            if existing:
                if existing["status"] == "ready":
                    return {**dict(existing), "audioUrl": f"/api/voice/assets/{existing['id']}/audio"}
                if existing["status"] == "generating":
                    raise HTTPException(status_code=409, detail="这条语音正在生成，请稍后刷新")
                if not retry:
                    raise HTTPException(status_code=409, detail="上次语音生成失败，需要手动重试")
            message = connection.execute("SELECT * FROM messages WHERE id=? AND speaker='assistant'", (message_id,)).fetchone()
            if not message:
                raise HTTPException(status_code=404, detail="没有找到沈砚的这条消息")
            marked, transcript = voice_text(message["text"])
            if not marked and not message["call_id"]:
                raise HTTPException(status_code=409, detail="这条回复没有选择发送语音")
            asset_id, timestamp = (existing["id"] if existing else new_id()), now()
            audio_dir.mkdir(parents=True, exist_ok=True)
            path = Path(existing["path"]) if existing else audio_dir / f"{asset_id}.mp3"
            if existing:
                claimed = connection.execute(
                    "UPDATE audio_assets SET status='generating',error=NULL,updated_at=? WHERE id=? AND status='failed'",
                    (timestamp, asset_id),
                )
                if not claimed.rowcount:
                    raise HTTPException(status_code=409, detail="这条语音正在由另一个请求处理")
            else:
                try:
                    connection.execute(
                        "INSERT INTO audio_assets VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (asset_id, message_id, str(path), "audio/mpeg", 0, transcript, "generating", None, timestamp, timestamp),
                    )
                except sqlite3.IntegrityError as exc:
                    raise HTTPException(status_code=409, detail="这条语音正在由另一个请求处理") from exc
        try:
            audio, duration_ms = await _minimax_synthesize(transcript)
            path.write_bytes(audio)
            with db_factory() as connection:
                connection.execute("UPDATE messages SET kind='voice',text=? WHERE id=?", (transcript, message_id))
                connection.execute("UPDATE audio_assets SET duration_ms=?,status='ready',updated_at=? WHERE id=?", (duration_ms, now(), asset_id))
                row = connection.execute("SELECT * FROM audio_assets WHERE id=?", (asset_id,)).fetchone()
            return {**dict(row), "audioUrl": f"/api/voice/assets/{asset_id}/audio"}
        except Exception as exc:
            with db_factory() as connection:
                connection.execute("UPDATE audio_assets SET status='failed',error=?,updated_at=? WHERE id=?", (str(exc)[:500], now(), asset_id))
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @router.post("/pending")
    async def synthesize_pending(
        limit: int = Query(default=3, ge=1, le=10),
        x_scheduler_token: str | None = Header(default=None),
    ) -> dict:
        """Prepare proactive voice notes before their notification is delivered."""
        expected = os.getenv("SCHEDULER_TOKEN", "").strip()
        if not expected or x_scheduler_token != expected:
            raise HTTPException(status_code=401, detail="调度凭证无效")
        if not os.getenv("MINIMAX_API_KEY", "").strip() or not os.getenv("MINIMAX_VOICE_ID", "").strip():
            return {"found": 0, "ready": 0, "failed": 0, "errors": [], "skipped": "MiniMax 尚未配置"}
        with db_factory() as connection:
            install_voice_schema(connection)
            rows = connection.execute(
                """SELECT m.id FROM messages m JOIN proactive_events p ON p.message_id=m.id
                LEFT JOIN audio_assets a ON a.message_id=m.id
                WHERE p.event_type='voice' AND p.status='sent' AND m.speaker='assistant' AND a.id IS NULL AND
                (LOWER(LTRIM(m.text)) LIKE '[voice]%' OR LOWER(LTRIM(m.text)) LIKE '[[voice]]%' OR LTRIM(m.text) LIKE '【voice】%')
                ORDER BY m.created_at LIMIT ?""", (limit,),
            ).fetchall()
        ready = failed = 0
        errors: list[str] = []
        for row in rows:
            try:
                await synthesize_message(row["id"])
                ready += 1
            except HTTPException as exc:
                failed += 1
                errors.append(str(exc.detail)[:200])
        return {"found": len(rows), "ready": ready, "failed": failed, "errors": errors}

    @router.get("/messages/{message_id}")
    def message_audio(message_id: str) -> dict:
        with db_factory() as connection:
            install_voice_schema(connection)
            row = connection.execute("SELECT * FROM audio_assets WHERE message_id=?", (message_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="这条消息没有语音")
        return {**dict(row), "audioUrl": f"/api/voice/assets/{row['id']}/audio" if row["status"] == "ready" else None}

    @router.get("/assets/{asset_id}/audio")
    def audio_file(asset_id: str) -> FileResponse:
        with db_factory() as connection:
            install_voice_schema(connection)
            row = connection.execute("SELECT * FROM audio_assets WHERE id=? AND status='ready'", (asset_id,)).fetchone()
        if not row or not Path(row["path"]).is_file():
            raise HTTPException(status_code=404, detail="语音文件不存在")
        return FileResponse(row["path"], media_type=row["mime_type"], filename=f"voice-{asset_id}.mp3")

    return router
