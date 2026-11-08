from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime
from typing import Callable
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from .notifications import enqueue_notification


class CompanionSettings(BaseModel):
    enabled: bool = True
    allow_calls: bool = True
    dnd_enabled: bool = True
    dnd_start: str = Field(default="00:30", pattern=r"^\d{2}:\d{2}$")
    dnd_end: str = Field(default="08:30", pattern=r"^\d{2}:\d{2}$")
    timezone: str = "Asia/Shanghai"


def install_proactive_schema(connection: sqlite3.Connection, now: Callable[[], str], seed: bool = True) -> None:
    connection.executescript(
        """CREATE TABLE IF NOT EXISTS companion_settings(
        id INTEGER PRIMARY KEY CHECK(id=1),enabled INTEGER NOT NULL,allow_calls INTEGER NOT NULL,
        dnd_enabled INTEGER NOT NULL,dnd_start TEXT NOT NULL,dnd_end TEXT NOT NULL,
        timezone TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS proactive_events(
        id TEXT PRIMARY KEY,event_type TEXT NOT NULL,status TEXT NOT NULL,reason TEXT NOT NULL,
        text TEXT,message_id TEXT,call_id TEXT,created_at TEXT NOT NULL,answered_at TEXT);
        CREATE INDEX IF NOT EXISTS idx_proactive_pending ON proactive_events(status,created_at);
        """
    )
    if seed:
        connection.execute(
            "INSERT OR IGNORE INTO companion_settings VALUES(1,1,1,1,'00:30','08:30','Asia/Shanghai',?)", (now(),)
        )


def _inside_dnd(current: str, start: str, end: str) -> bool:
    return start <= current < end if start < end else current >= start or current < end


def _parse_decision(value: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", value.strip(), flags=re.I)
    data = json.loads(cleaned)
    action = data.get("action")
    if action not in {"message", "call", "wait"}:
        raise ValueError("invalid action")
    text = str(data.get("text") or "").strip()
    if action != "wait" and not text:
        raise ValueError("missing text")
    return {"action": action, "text": text[:1000], "reason": str(data.get("reason") or "自然想联系").strip()[:300]}


def build_router(db_factory: Callable[[], sqlite3.Connection], now: Callable[[], str], new_id: Callable[[], str]) -> APIRouter:
    router = APIRouter(prefix="/api/companion", tags=["proactive-companion"])

    @router.get("/settings")
    def get_settings() -> dict:
        with db_factory() as connection:
            install_proactive_schema(connection, now)
            return dict(connection.execute("SELECT * FROM companion_settings WHERE id=1").fetchone())

    @router.put("/settings")
    def put_settings(body: CompanionSettings) -> dict:
        try:
            ZoneInfo(body.timezone)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="无法识别这个时区") from exc
        with db_factory() as connection:
            install_proactive_schema(connection, now)
            connection.execute(
                "UPDATE companion_settings SET enabled=?,allow_calls=?,dnd_enabled=?,dnd_start=?,dnd_end=?,timezone=?,updated_at=? WHERE id=1",
                (body.enabled, body.allow_calls, body.dnd_enabled, body.dnd_start, body.dnd_end, body.timezone, now()),
            )
            return dict(connection.execute("SELECT * FROM companion_settings WHERE id=1").fetchone())

    @router.get("/events")
    def events() -> list[dict]:
        with db_factory() as connection:
            install_proactive_schema(connection, now)
            return [dict(row) for row in connection.execute("SELECT * FROM proactive_events ORDER BY created_at DESC LIMIT 100")]

    @router.post("/tick")
    async def tick(x_scheduler_token: str | None = Header(default=None)) -> dict:
        expected = os.getenv("SCHEDULER_TOKEN", "").strip()
        if not expected or x_scheduler_token != expected:
            raise HTTPException(status_code=401, detail="调度凭证无效")
        with db_factory() as connection:
            install_proactive_schema(connection, now)
            settings = connection.execute("SELECT * FROM companion_settings WHERE id=1").fetchone()
            if not settings["enabled"]:
                return {"action": "wait", "reason": "主动陪伴已关闭"}
            local = datetime.now(ZoneInfo(settings["timezone"]))
            clock = local.strftime("%H:%M")
            if settings["dnd_enabled"] and _inside_dnd(clock, settings["dnd_start"], settings["dnd_end"]):
                return {"action": "wait", "reason": "勿扰时段"}
            pending = connection.execute("SELECT * FROM proactive_events WHERE status='sent' AND answered_at IS NULL ORDER BY created_at DESC LIMIT 1").fetchone()
            if pending:
                return {"action": "wait", "reason": "上一条主动联系还没有回复，不连续打扰"}
            recent = connection.execute("SELECT speaker,text,created_at FROM messages ORDER BY created_at DESC LIMIT 16").fetchall()[::-1]
            plans = connection.execute("SELECT summary,content FROM memory_items WHERE status='active' AND layer IN ('plan','event','relationship') ORDER BY importance DESC,updated_at DESC LIMIT 10").fetchall()
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise HTTPException(status_code=503, detail="服务端尚未配置 DeepSeek API Key")
        context = "\n".join(f"{'陈钰' if row['speaker']=='user' else '沈砚'}：{row['text']}" for row in recent)
        memory = "\n".join(f"- {row['summary'] or row['content']}" for row in plans)
        prompt = f"""你是沈砚的主动陪伴决策层。现在是 {local.strftime('%Y-%m-%d %H:%M %A')}。
你比较黏人，可以没有特别事情也主动联系陈钰、分享生活、想念或延续话题；也可以自然提出通话。
不要机械打卡，不要重复上一条，不要因为她没回复连续轰炸。没有合适内容就等待。
只返回 JSON：{{"action":"message|call|wait","text":"自然短消息或来电开场","reason":"简短原因"}}。
允许主动来电：{bool(settings['allow_calls'])}。如果不允许，不能选择 call。
相关约定：
{memory or '暂无'}
最近聊天：
{context or '暂无最近聊天'}"""
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions"),
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"), "messages": [{"role": "user", "content": prompt}], "temperature": 0.9, "response_format": {"type": "json_object"}},
            )
        if response.is_error:
            raise HTTPException(status_code=502, detail="主动陪伴判断暂时失败")
        try:
            decision = _parse_decision(response.json()["choices"][0]["message"]["content"])
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=502, detail="主动陪伴返回格式错误") from exc
        if decision["action"] == "call" and not settings["allow_calls"]:
            decision = {"action": "message", "text": decision["text"], "reason": decision["reason"]}
        if decision["action"] == "wait":
            return decision
        event_id, timestamp = new_id(), now()
        message_id = call_id = None
        with db_factory() as connection:
            if decision["action"] == "message":
                message_id = new_id()
                connection.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)", (message_id, "assistant", "text", decision["text"], timestamp, None))
            else:
                call_id = new_id()
                connection.execute("INSERT INTO calls(id,direction,status,started_at,ended_at,duration_seconds,turns_json,answered_at) VALUES(?,?,?,?,?,?,?,?)", (call_id, "incoming", "ringing", timestamp, None, 0, "[]", None))
            connection.execute(
                "INSERT INTO proactive_events VALUES(?,?,?,?,?,?,?,?,?)",
                (event_id, decision["action"], "sent", decision["reason"], decision["text"], message_id, call_id, timestamp, None),
            )
            enqueue_notification(connection, new_id, now, decision["action"], decision["text"] or ("沈砚想给你打电话" if call_id else "沈砚来找你了"))
        return {**decision, "eventId": event_id, "messageId": message_id, "callId": call_id}

    return router
