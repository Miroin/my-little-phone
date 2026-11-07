from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("MLP_DATABASE_PATH", ROOT / "data" / "little-phone.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="小手叽 v2 API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("MLP_ALLOWED_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MemoryLayer = Literal["personality", "relationship", "user", "event", "feeling", "plan", "sample"]
MemoryStatus = Literal["candidate", "active", "archived", "superseded", "deleted"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


def content_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,speaker TEXT NOT NULL,kind TEXT NOT NULL,text TEXT NOT NULL,created_at TEXT NOT NULL,call_id TEXT);
        CREATE TABLE IF NOT EXISTS memories(id TEXT PRIMARY KEY,category TEXT NOT NULL,text TEXT NOT NULL,created_at TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY,direction TEXT NOT NULL,status TEXT NOT NULL,started_at TEXT NOT NULL,ended_at TEXT,duration_seconds INTEGER NOT NULL DEFAULT 0,turns_json TEXT NOT NULL DEFAULT '[]');

        CREATE TABLE IF NOT EXISTS memory_items(
            id TEXT PRIMARY KEY, layer TEXT NOT NULL, content TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'candidate', importance REAL NOT NULL DEFAULT 5,
            valence REAL, arousal REAL, confidence REAL NOT NULL DEFAULT 0.5,
            occurred_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_reinforced_at TEXT,
            source_type TEXT NOT NULL DEFAULT 'manual', source_id TEXT, source_hash TEXT NOT NULL,
            tags_json TEXT NOT NULL DEFAULT '[]', embedding_status TEXT NOT NULL DEFAULT 'pending'
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_source_hash ON memory_items(layer,source_hash) WHERE status!='deleted';
        CREATE INDEX IF NOT EXISTS idx_memory_lookup ON memory_items(status,layer,importance,updated_at);

        CREATE TABLE IF NOT EXISTS memory_evidence(
            id TEXT PRIMARY KEY, memory_id TEXT NOT NULL REFERENCES memory_items(id) ON DELETE CASCADE,
            conversation_id TEXT, message_start_id TEXT, message_end_id TEXT,
            raw_text TEXT NOT NULL, sha256 TEXT NOT NULL, created_at TEXT NOT NULL,
            UNIQUE(memory_id,sha256)
        );
        CREATE TABLE IF NOT EXISTS memory_jobs(
            id TEXT PRIMARY KEY, job_type TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
            cursor TEXT, attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_memory_jobs_status ON memory_jobs(status,updated_at);
        CREATE TABLE IF NOT EXISTS memory_feedback(
            id TEXT PRIMARY KEY, message_id TEXT NOT NULL, scene TEXT NOT NULL DEFAULT 'unknown',
            verdict TEXT NOT NULL, reason TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS memory_usage(
            message_id TEXT NOT NULL, memory_id TEXT NOT NULL REFERENCES memory_items(id),
            rank INTEGER NOT NULL, score REAL NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(message_id,memory_id)
        );
        """
    )
    return connection


class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class MemoryCreate(BaseModel):
    layer: MemoryLayer
    content: str = Field(min_length=1, max_length=12000)
    summary: str = Field(default="", max_length=2000)
    status: MemoryStatus = "candidate"
    importance: float = Field(default=5, ge=0, le=10)
    valence: float | None = Field(default=None, ge=-1, le=1)
    arousal: float | None = Field(default=None, ge=0, le=1)
    confidence: float = Field(default=0.5, ge=0, le=1)
    occurred_at: str | None = None
    source_type: str = Field(default="manual", max_length=80)
    source_id: str | None = Field(default=None, max_length=200)
    tags: list[str] = Field(default_factory=list, max_length=30)
    evidence: str | None = Field(default=None, max_length=50000)


class MemoryStatusUpdate(BaseModel):
    status: MemoryStatus


class MemoryJobCreate(BaseModel):
    job_type: Literal["import", "extract", "embed", "merge", "backup"]
    payload: dict = Field(default_factory=dict)


class FeedbackCreate(BaseModel):
    message_id: str
    scene: str = Field(default="unknown", max_length=80)
    verdict: Literal["like", "dislike"]
    reason: str = Field(default="", max_length=1000)


def message_dict(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "speaker": row["speaker"], "kind": row["kind"], "text": row["text"], "createdAt": row["created_at"], "callId": row["call_id"]}


def memory_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "layer": row["layer"], "content": row["content"], "summary": row["summary"],
        "status": row["status"], "importance": row["importance"], "valence": row["valence"],
        "arousal": row["arousal"], "confidence": row["confidence"], "occurredAt": row["occurred_at"],
        "createdAt": row["created_at"], "updatedAt": row["updated_at"],
        "lastReinforcedAt": row["last_reinforced_at"], "sourceType": row["source_type"],
        "sourceId": row["source_id"], "sourceHash": row["source_hash"],
        "tags": json.loads(row["tags_json"] or "[]"), "embeddingStatus": row["embedding_status"],
    }


def query_terms(value: str) -> set[str]:
    lowered = value.lower()
    latin = re.findall(r"[a-z0-9_]+", lowered)
    chinese = re.findall(r"[\u4e00-\u9fff]", lowered)
    pairs = ["".join(chinese[index:index + 2]) for index in range(max(0, len(chinese) - 1))]
    return {term for term in [*latin, *chinese, *pairs] if term.strip()}


def retrieve_memories(connection: sqlite3.Connection, query: str, limit: int = 8) -> list[tuple[sqlite3.Row, float]]:
    terms = query_terms(query)
    rows = connection.execute(
        "SELECT * FROM memory_items WHERE status='active' ORDER BY importance DESC,COALESCE(last_reinforced_at,occurred_at,created_at) DESC LIMIT 250"
    ).fetchall()
    scored: list[tuple[sqlite3.Row, float]] = []
    for row in rows:
        haystack = " ".join((row["content"], row["summary"], row["tags_json"])).lower()
        overlap = sum(1 for term in terms if term in haystack)
        layer_bonus = 2.5 if row["layer"] in {"personality", "relationship"} else 0
        score = overlap * 4 + float(row["importance"]) * 0.55 + float(row["confidence"]) + layer_bonus
        if overlap or row["layer"] in {"personality", "relationship"}:
            scored.append((row, score))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:limit]


@app.get("/health")
def health() -> dict:
    with db() as connection:
        memory_count = connection.execute("SELECT COUNT(*) FROM memory_items WHERE status!='deleted'").fetchone()[0]
    return {"ok": True, "database": DB_PATH.name, "modelConfigured": bool(os.getenv("DEEPSEEK_API_KEY")), "memorySchema": 2, "memoryCount": memory_count}


@app.get("/api/messages")
def messages() -> list[dict]:
    with db() as connection:
        return [message_dict(row) for row in connection.execute("SELECT * FROM messages ORDER BY created_at ASC LIMIT 500")]


@app.get("/api/memories")
def memories(status: MemoryStatus | None = None, layer: MemoryLayer | None = None, limit: int = Query(default=100, ge=1, le=500)) -> list[dict]:
    clauses = ["status!='deleted'"]
    values: list[object] = []
    if status:
        clauses.append("status=?")
        values.append(status)
    if layer:
        clauses.append("layer=?")
        values.append(layer)
    values.append(limit)
    with db() as connection:
        rows = connection.execute(f"SELECT * FROM memory_items WHERE {' AND '.join(clauses)} ORDER BY updated_at DESC LIMIT ?", values).fetchall()
    return [memory_dict(row) for row in rows]


@app.post("/api/memories", status_code=201)
def create_memory(body: MemoryCreate) -> dict:
    timestamp, memory_id = now(), new_id()
    normalized, digest = body.content.strip(), content_hash(body.content.strip())
    try:
        with db() as connection:
            connection.execute(
                "INSERT INTO memory_items(id,layer,content,summary,status,importance,valence,arousal,confidence,occurred_at,created_at,updated_at,source_type,source_id,source_hash,tags_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (memory_id, body.layer, normalized, body.summary.strip(), body.status, body.importance, body.valence, body.arousal, body.confidence, body.occurred_at, timestamp, timestamp, body.source_type, body.source_id, digest, json.dumps(body.tags, ensure_ascii=False)),
            )
            if body.evidence:
                raw = body.evidence.strip()
                connection.execute("INSERT INTO memory_evidence VALUES(?,?,?,?,?,?,?,?)", (new_id(), memory_id, body.source_id, None, None, raw, content_hash(raw), timestamp))
            row = connection.execute("SELECT * FROM memory_items WHERE id=?", (memory_id,)).fetchone()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="相同内容已经存在于这一记忆层") from exc
    return memory_dict(row)


@app.patch("/api/memories/{memory_id}/status")
def update_memory_status(memory_id: str, body: MemoryStatusUpdate) -> dict:
    with db() as connection:
        cursor = connection.execute("UPDATE memory_items SET status=?,updated_at=? WHERE id=?", (body.status, now(), memory_id))
        if not cursor.rowcount:
            raise HTTPException(status_code=404, detail="没有找到这条记忆")
        row = connection.execute("SELECT * FROM memory_items WHERE id=?", (memory_id,)).fetchone()
    return memory_dict(row)


@app.get("/api/memories/{memory_id}/evidence")
def memory_evidence(memory_id: str) -> list[dict]:
    with db() as connection:
        if not connection.execute("SELECT 1 FROM memory_items WHERE id=?", (memory_id,)).fetchone():
            raise HTTPException(status_code=404, detail="没有找到这条记忆")
        rows = connection.execute("SELECT * FROM memory_evidence WHERE memory_id=? ORDER BY created_at", (memory_id,)).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/memory-search")
def memory_search(q: str = Query(min_length=1, max_length=1000), limit: int = Query(default=8, ge=1, le=30)) -> list[dict]:
    with db() as connection:
        results = retrieve_memories(connection, q, limit)
    return [{**memory_dict(row), "score": round(score, 3), "retrieval": "keyword-fallback"} for row, score in results]


@app.post("/api/memory-jobs", status_code=201)
def create_memory_job(body: MemoryJobCreate) -> dict:
    job_id, timestamp = new_id(), now()
    with db() as connection:
        connection.execute("INSERT INTO memory_jobs VALUES(?,?,?,?,?,?,?,?,?)", (job_id, body.job_type, "pending", None, 0, None, json.dumps(body.payload, ensure_ascii=False), timestamp, timestamp))
        row = connection.execute("SELECT * FROM memory_jobs WHERE id=?", (job_id,)).fetchone()
    return dict(row)


@app.get("/api/memory-jobs/{job_id}")
def get_memory_job(job_id: str) -> dict:
    with db() as connection:
        row = connection.execute("SELECT * FROM memory_jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="没有找到这个记忆任务")
    return dict(row)


@app.post("/api/memory-feedback", status_code=201)
def create_feedback(body: FeedbackCreate) -> dict:
    feedback_id, timestamp = new_id(), now()
    with db() as connection:
        connection.execute("INSERT INTO memory_feedback VALUES(?,?,?,?,?,?)", (feedback_id, body.message_id, body.scene, body.verdict, body.reason.strip(), timestamp))
    return {"id": feedback_id, **body.model_dump(), "createdAt": timestamp}


@app.post("/api/chat")
async def chat(body: ChatRequest) -> dict:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="服务端尚未配置 DeepSeek API Key")
    user = {"id": new_id(), "speaker": "user", "kind": "text", "text": body.text.strip(), "createdAt": now(), "callId": None}
    with db() as connection:
        connection.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)", (user["id"], user["speaker"], user["kind"], user["text"], user["createdAt"], None))
        recent = list(connection.execute("SELECT speaker,text FROM messages ORDER BY created_at DESC LIMIT 24"))[::-1]
        selected = retrieve_memories(connection, user["text"], 8)
        legacy = [] if selected else connection.execute("SELECT category,text FROM memories WHERE active=1 ORDER BY created_at DESC LIMIT 8").fetchall()

    system = "你是沈砚。你与陈钰是长期恋人。自然承接聊天与记忆，先理解情绪再回应；有自己的生活和判断，但不靠犟嘴证明独立。相关资料是事实线索，不是必须复述的台词。"
    if selected:
        system += "\n本轮相关资料：\n" + "\n".join(f"- [{row['layer']}] {row['summary'] or row['content']}" for row, _ in selected)
    elif legacy:
        system += "\n旧版长期记忆：\n" + "\n".join(f"- [{item['category']}] {item['text']}" for item in legacy)
    payload = {
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "messages": [{"role": "system", "content": system}, *[{"role": "assistant" if item["speaker"] == "assistant" else "user", "content": item["text"]} for item in recent]],
        "temperature": 0.8,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions"), headers={"Authorization": f"Bearer {api_key}"}, json=payload)
    if response.is_error:
        raise HTTPException(status_code=502, detail="模型服务暂时不可用")
    answer = response.json()["choices"][0]["message"]["content"].strip()
    assistant = {"id": new_id(), "speaker": "assistant", "kind": "text", "text": answer, "createdAt": now(), "callId": None}
    with db() as connection:
        connection.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)", (assistant["id"], assistant["speaker"], assistant["kind"], assistant["text"], assistant["createdAt"], None))
        for rank, (row, score) in enumerate(selected, start=1):
            connection.execute("INSERT INTO memory_usage VALUES(?,?,?,?,?)", (assistant["id"], row["id"], rank, score, now()))
    return {"user": user, "assistant": assistant, "memoryIds": [row["id"] for row, _ in selected]}
