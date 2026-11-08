from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, HTTPException
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
    async def synthesize_message(message_id: str) -> dict:
        with db_factory() as connection:
            install_voice_schema(connection)
            existing = connection.execute("SELECT * FROM audio_assets WHERE message_id=? AND status='ready'", (message_id,)).fetchone()
            if existing:
                return {**dict(existing), "audioUrl": f"/api/voice/assets/{existing['id']}/audio"}
            message = connection.execute("SELECT * FROM messages WHERE id=? AND speaker='assistant'", (message_id,)).fetchone()
            if not message:
                raise HTTPException(status_code=404, detail="没有找到沈砚的这条消息")
            marked, transcript = voice_text(message["text"])
            if not marked:
                raise HTTPException(status_code=409, detail="这条回复没有选择发送语音")
            asset_id, timestamp = new_id(), now()
            audio_dir.mkdir(parents=True, exist_ok=True)
            path = audio_dir / f"{asset_id}.mp3"
            connection.execute(
                "INSERT OR REPLACE INTO audio_assets VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (asset_id, message_id, str(path), "audio/mpeg", 0, transcript, "generating", None, timestamp, timestamp),
            )
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
