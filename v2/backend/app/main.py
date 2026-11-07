from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("MLP_DATABASE_PATH", ROOT / "data" / "little-phone.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="小手叽 v2 API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("MLP_ALLOWED_ORIGINS", "http://localhost:5173").split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,speaker TEXT NOT NULL,kind TEXT NOT NULL,text TEXT NOT NULL,created_at TEXT NOT NULL,call_id TEXT);
    CREATE TABLE IF NOT EXISTS memories(id TEXT PRIMARY KEY,category TEXT NOT NULL,text TEXT NOT NULL,created_at TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY,direction TEXT NOT NULL,status TEXT NOT NULL,started_at TEXT NOT NULL,ended_at TEXT,duration_seconds INTEGER NOT NULL DEFAULT 0,turns_json TEXT NOT NULL DEFAULT '[]');
    """)
    return connection


class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


def message_dict(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "speaker": row["speaker"], "kind": row["kind"], "text": row["text"], "createdAt": row["created_at"], "callId": row["call_id"]}


@app.get("/health")
def health() -> dict:
    return {"ok": True, "database": str(DB_PATH.name), "modelConfigured": bool(os.getenv("DEEPSEEK_API_KEY"))}


@app.get("/api/messages")
def messages() -> list[dict]:
    with db() as connection:
        return [message_dict(row) for row in connection.execute("SELECT * FROM messages ORDER BY created_at ASC LIMIT 500")]


@app.post("/api/chat")
async def chat(body: ChatRequest) -> dict:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="服务端尚未配置 DeepSeek API Key")

    user = {"id": str(uuid.uuid4()), "speaker": "user", "kind": "text", "text": body.text.strip(), "createdAt": now(), "callId": None}
    with db() as connection:
        connection.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)", (user["id"], user["speaker"], user["kind"], user["text"], user["createdAt"], None))
        recent = list(connection.execute("SELECT speaker,text FROM messages ORDER BY created_at DESC LIMIT 24"))[::-1]
        memories = list(connection.execute("SELECT category,text FROM memories WHERE active=1 ORDER BY created_at DESC LIMIT 20"))

    system = "你是沈砚。你与陈钰是长期恋人。自然承接聊天与记忆，先理解情绪再回应；有自己的生活和判断，但不靠犟嘴证明独立。"
    if memories:
        system += "\n相关长期记忆：\n" + "\n".join(f"- [{item['category']}] {item['text']}" for item in memories)
    payload = {"model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"), "messages": [{"role": "system", "content": system}, *[{"role": "assistant" if item["speaker"] == "assistant" else "user", "content": item["text"]} for item in recent]], "temperature": 0.8, "stream": False}
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions"), headers={"Authorization": f"Bearer {api_key}"}, json=payload)
    if response.is_error:
        raise HTTPException(status_code=502, detail="模型服务暂时不可用")
    answer = response.json()["choices"][0]["message"]["content"].strip()
    assistant = {"id": str(uuid.uuid4()), "speaker": "assistant", "kind": "text", "text": answer, "createdAt": now(), "callId": None}
    with db() as connection:
        connection.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)", (assistant["id"], assistant["speaker"], assistant["kind"], assistant["text"], assistant["createdAt"], None))
    return {"user": user, "assistant": assistant}

