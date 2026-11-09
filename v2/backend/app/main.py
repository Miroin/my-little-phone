from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from .chat_import import build_router as build_chat_import_router, install_schema as install_import_schema
from .backup import build_router as build_backup_router
from .memory_extract import build_router as build_memory_extract_router, install_extraction_schema
from .persona import build_system_prompt, detect_scene
from .voice import build_router as build_voice_router, install_voice_schema
from .proactive import build_router as build_proactive_router, install_proactive_schema
from .notifications import build_router as build_notification_router, install_notification_schema
from .profiles import build_router as build_profile_router, install_profile_schema, profile_prompt
from .life import build_router as build_life_router, install_life_schema

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


@app.middleware("http")
async def require_private_access(request: Request, call_next):
    """Protect personal data and paid endpoints when a service token is configured."""
    expected = os.getenv("MLP_ACCESS_TOKEN", "").strip()
    if expected and request.url.path.startswith("/api/") and request.method != "OPTIONS":
        scheduler = os.getenv("SCHEDULER_TOKEN", "").strip()
        scheduler_ok = bool(scheduler and hmac.compare_digest(request.headers.get("X-Scheduler-Token", ""), scheduler))
        supplied = request.headers.get("X-MLP-Access-Token", "")
        bearer = request.headers.get("Authorization", "")
        if bearer.lower().startswith("bearer "):
            supplied = bearer[7:].strip()
        if not scheduler_ok and not hmac.compare_digest(supplied, expected):
            return Response(
                content=json.dumps({"detail": "需要小手叽服务访问口令"}, ensure_ascii=False),
                status_code=401,
                media_type="application/json",
            )
    return await call_next(request)

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
        CREATE TABLE IF NOT EXISTS chat_runs(
            id TEXT PRIMARY KEY, user_message_id TEXT NOT NULL, assistant_message_id TEXT,
            status TEXT NOT NULL DEFAULT 'pending', scene TEXT NOT NULL DEFAULT 'daily',
            memory_ids_json TEXT NOT NULL DEFAULT '[]', error TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );

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
    call_columns = {row[1] for row in connection.execute("PRAGMA table_info(calls)")}
    if "answered_at" not in call_columns:
        connection.execute("ALTER TABLE calls ADD COLUMN answered_at TEXT")
        connection.execute("UPDATE calls SET answered_at=started_at WHERE status IN ('active','answered')")
    install_import_schema(connection)
    install_extraction_schema(connection)
    install_voice_schema(connection)
    install_proactive_schema(connection, now, seed=False)
    install_notification_schema(connection)
    install_profile_schema(connection, now, seed=False)
    install_life_schema(connection)
    return connection


app.include_router(build_chat_import_router(db, now, new_id))
app.include_router(build_memory_extract_router(db, now, new_id))
app.include_router(build_backup_router(db, now, new_id))
app.include_router(build_voice_router(db, now, new_id, ROOT))
app.include_router(build_proactive_router(db, now, new_id))
app.include_router(build_notification_router(db, now, new_id))
app.include_router(build_profile_router(db, now))
app.include_router(build_life_router(db, now, new_id))


class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    request_id: str | None = Field(default=None, min_length=8, max_length=100)


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


class MemoryUpdate(BaseModel):
    layer: MemoryLayer
    content: str = Field(min_length=1, max_length=12000)
    summary: str = Field(default="", max_length=2000)
    importance: float = Field(default=5, ge=0, le=10)
    confidence: float = Field(default=0.5, ge=0, le=1)
    tags: list[str] = Field(default_factory=list, max_length=30)


class MemoryJobCreate(BaseModel):
    job_type: Literal["import", "extract", "embed", "merge", "backup"]
    payload: dict = Field(default_factory=dict)


class FeedbackCreate(BaseModel):
    message_id: str
    scene: str = Field(default="unknown", max_length=80)
    verdict: Literal["like", "dislike"]
    reason: str = Field(default="", max_length=1000)


class CallStart(BaseModel):
    direction: Literal["incoming", "outgoing"] = "outgoing"


class CallTurnCreate(BaseModel):
    speaker: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=4000)


class CallEnd(BaseModel):
    status: Literal["answered", "missed", "declined"] = "answered"


class CallReply(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


def message_dict(row: sqlite3.Row) -> dict:
    result = {"id": row["id"], "speaker": row["speaker"], "kind": row["kind"], "text": row["text"], "createdAt": row["created_at"], "callId": row["call_id"]}
    keys = row.keys()
    if "audio_id" in keys and row["audio_id"]:
        result.update({"audioUrl": f"/api/voice/assets/{row['audio_id']}/audio", "durationMs": row["duration_ms"], "voiceStatus": row["voice_status"]})
    return result


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


def call_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "direction": row["direction"], "status": row["status"],
        "startedAt": row["started_at"], "answeredAt": row["answered_at"], "endedAt": row["ended_at"],
        "durationSeconds": row["duration_seconds"], "turns": json.loads(row["turns_json"] or "[]"),
    }


def query_terms(value: str) -> set[str]:
    lowered = value.lower()
    latin = re.findall(r"[a-z0-9_]+", lowered)
    chinese = re.findall(r"[\u4e00-\u9fff]", lowered)
    pairs = ["".join(chinese[index:index + 2]) for index in range(max(0, len(chinese) - 1))]
    return {term for term in [*latin, *chinese, *pairs] if term.strip()}


def ngrams(value: str, size: int = 2) -> dict[str, int]:
    compact = re.sub(r"\s+", "", value.lower())
    grams: dict[str, int] = {}
    for index in range(max(0, len(compact) - size + 1)):
        gram = compact[index:index + size]
        grams[gram] = grams.get(gram, 0) + 1
    return grams


def cosine_similarity(left: dict[str, int], right: dict[str, int]) -> float:
    if not left or not right:
        return 0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0


def retrieve_memories(connection: sqlite3.Connection, query: str, limit: int = 8) -> list[tuple[sqlite3.Row, float]]:
    terms = query_terms(query)
    query_grams = ngrams(query)
    rows = connection.execute(
        "SELECT * FROM memory_items WHERE status='active' ORDER BY importance DESC,COALESCE(last_reinforced_at,occurred_at,created_at) DESC LIMIT 250"
    ).fetchall()
    scored: list[tuple[sqlite3.Row, float]] = []
    for row in rows:
        haystack = " ".join((row["content"], row["summary"], row["tags_json"])).lower()
        overlap = sum(1 for term in terms if term in haystack)
        semantic = cosine_similarity(query_grams, ngrams(haystack))
        layer_bonus = 2.5 if row["layer"] in {"personality", "relationship"} else 0
        score = overlap * 3.2 + semantic * 9 + float(row["importance"]) * 0.55 + float(row["confidence"]) + layer_bonus
        if overlap or semantic >= 0.12 or row["layer"] in {"personality", "relationship"}:
            scored.append((row, score))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:limit]


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def prepare_chat(body: ChatRequest) -> tuple[dict, list[sqlite3.Row], list[tuple[sqlite3.Row, float]], object, str, str]:
    run_id = body.request_id or new_id()
    with db() as connection:
        existing = connection.execute("SELECT * FROM chat_runs WHERE id=?", (run_id,)).fetchone()
        if existing and existing["status"] == "complete" and existing["assistant_message_id"]:
            user_row = connection.execute("SELECT * FROM messages WHERE id=?", (existing["user_message_id"],)).fetchone()
            assistant_row = connection.execute("SELECT * FROM messages WHERE id=?", (existing["assistant_message_id"],)).fetchone()
            return message_dict(user_row), [], [], None, run_id, message_dict(assistant_row)["text"]
        if existing:
            user_row = connection.execute("SELECT * FROM messages WHERE id=?", (existing["user_message_id"],)).fetchone()
            user = message_dict(user_row)
        else:
            user = {"id": new_id(), "speaker": "user", "kind": "text", "text": body.text.strip(), "createdAt": now(), "callId": None}
            scene = detect_scene(user["text"])
            connection.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)", (user["id"], "user", "text", user["text"], user["createdAt"], None))
            install_proactive_schema(connection, now)
            connection.execute("UPDATE proactive_events SET status='answered',answered_at=? WHERE status='sent' AND answered_at IS NULL", (user["createdAt"],))
            connection.execute(
                "INSERT INTO chat_runs(id,user_message_id,status,scene,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                (run_id, user["id"], "pending", scene.name, user["createdAt"], user["createdAt"]),
            )
        recent = list(connection.execute("SELECT speaker,text FROM messages ORDER BY created_at DESC LIMIT 24"))[::-1]
        selected = retrieve_memories(connection, user["text"], 8)
        profiles = profile_prompt(connection, now)
        legacy = [] if selected else connection.execute("SELECT category,text FROM memories WHERE active=1 ORDER BY created_at DESC LIMIT 8").fetchall()
    prompt_memories = [f"[{row['layer']}] {row['summary'] or row['content']}" for row, _ in selected]
    if not prompt_memories:
        prompt_memories = [f"[旧版/{item['category']}] {item['text']}" for item in legacy]
    prompt_memories = [*profiles, *prompt_memories]
    scene = detect_scene(user["text"])
    payload = {
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "messages": [{"role": "system", "content": build_system_prompt(scene, prompt_memories)}, *[
            {"role": "assistant" if item["speaker"] == "assistant" else "user", "content": item["text"]} for item in recent
        ]],
        "temperature": 0.8,
        "stream": True,
    }
    with db() as connection:
        connection.execute(
            "UPDATE chat_runs SET status='streaming',scene=?,memory_ids_json=?,error=NULL,updated_at=? WHERE id=?",
            (scene.name, json.dumps([row["id"] for row, _ in selected]), now(), run_id),
        )
    return user, recent, selected, payload, run_id, ""


def finish_chat(run_id: str, answer: str, selected: list[tuple[sqlite3.Row, float]]) -> dict:
    assistant = {"id": new_id(), "speaker": "assistant", "kind": "text", "text": answer.strip(), "createdAt": now(), "callId": None}
    with db() as connection:
        connection.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)", (assistant["id"], "assistant", "text", assistant["text"], assistant["createdAt"], None))
        connection.execute("UPDATE chat_runs SET assistant_message_id=?,status='complete',updated_at=? WHERE id=?", (assistant["id"], now(), run_id))
        for rank, (row, score) in enumerate(selected, start=1):
            connection.execute("INSERT OR IGNORE INTO memory_usage VALUES(?,?,?,?,?)", (assistant["id"], row["id"], rank, score, now()))
    return assistant


@app.get("/health")
def health() -> dict:
    with db() as connection:
        memory_count = connection.execute("SELECT COUNT(*) FROM memory_items WHERE status!='deleted'").fetchone()[0]
    return {"ok": True, "database": DB_PATH.name, "modelConfigured": bool(os.getenv("DEEPSEEK_API_KEY")), "memorySchema": 2, "memoryCount": memory_count}


@app.get("/api/session")
def private_session() -> dict:
    return {"ok": True, "authenticated": True}


@app.get("/api/messages")
def messages() -> list[dict]:
    with db() as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS audio_assets(
        id TEXT PRIMARY KEY,message_id TEXT NOT NULL UNIQUE,path TEXT NOT NULL,mime_type TEXT NOT NULL,
        duration_ms INTEGER NOT NULL DEFAULT 0,transcript TEXT NOT NULL,status TEXT NOT NULL,error TEXT,
        created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""")
        rows = connection.execute(
            """SELECT m.*,a.id audio_id,a.duration_ms,a.status voice_status FROM messages m
            LEFT JOIN audio_assets a ON a.message_id=m.id ORDER BY m.created_at ASC LIMIT 500"""
        ).fetchall()
        return [message_dict(row) for row in rows]


@app.get("/api/memories")
def memories(status: MemoryStatus | None = None, layer: MemoryLayer | None = None, limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> list[dict]:
    clauses = ["status!='deleted'"]
    values: list[object] = []
    if status:
        clauses.append("status=?")
        values.append(status)
    if layer:
        clauses.append("layer=?")
        values.append(layer)
    values.extend((limit, offset))
    with db() as connection:
        rows = connection.execute(f"SELECT * FROM memory_items WHERE {' AND '.join(clauses)} ORDER BY updated_at DESC LIMIT ? OFFSET ?", values).fetchall()
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


@app.put("/api/memories/{memory_id}")
def update_memory(memory_id: str, body: MemoryUpdate) -> dict:
    normalized, timestamp = body.content.strip(), now()
    try:
        with db() as connection:
            cursor = connection.execute(
                """UPDATE memory_items SET layer=?,content=?,summary=?,importance=?,confidence=?,tags_json=?,
                source_hash=?,updated_at=? WHERE id=? AND status!='deleted'""",
                (body.layer, normalized, body.summary.strip(), body.importance, body.confidence,
                 json.dumps(body.tags, ensure_ascii=False), content_hash(normalized), timestamp, memory_id),
            )
            if not cursor.rowcount:
                raise HTTPException(status_code=404, detail="没有找到这条记忆")
            row = connection.execute("SELECT * FROM memory_items WHERE id=?", (memory_id,)).fetchone()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="修改后的内容与现有记忆重复") from exc
    return memory_dict(row)


@app.post("/api/memories/{memory_id}/reinforce")
def reinforce_memory(memory_id: str) -> dict:
    timestamp = now()
    with db() as connection:
        cursor = connection.execute(
            "UPDATE memory_items SET last_reinforced_at=?,confidence=MIN(1,confidence+0.05),updated_at=? WHERE id=? AND status='active'",
            (timestamp, timestamp, memory_id),
        )
        if not cursor.rowcount:
            raise HTTPException(status_code=404, detail="只有正在使用的记忆可以加强")
        row = connection.execute("SELECT * FROM memory_items WHERE id=?", (memory_id,)).fetchone()
    return memory_dict(row)


@app.get("/api/memories/{memory_id}/evidence")
def memory_evidence(memory_id: str) -> list[dict]:
    with db() as connection:
        if not connection.execute("SELECT 1 FROM memory_items WHERE id=?", (memory_id,)).fetchone():
            raise HTTPException(status_code=404, detail="没有找到这条记忆")
        rows = connection.execute("SELECT * FROM memory_evidence WHERE memory_id=? ORDER BY created_at", (memory_id,)).fetchall()
    return [dict(row) for row in rows]


@app.delete("/api/memories/{memory_id}")
def delete_memory(memory_id: str) -> dict:
    """Permanently remove one user-selected memory and its derived references."""
    with db() as connection:
        if not connection.execute("SELECT 1 FROM memory_items WHERE id=?", (memory_id,)).fetchone():
            raise HTTPException(status_code=404, detail="没有找到这条记忆")
        connection.execute("DELETE FROM memory_usage WHERE memory_id=?", (memory_id,))
        connection.execute("DELETE FROM memory_evidence WHERE memory_id=?", (memory_id,))
        connection.execute("DELETE FROM memory_items WHERE id=?", (memory_id,))
    return {"deleted": True, "id": memory_id}


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
        delta = 0.03 if body.verdict == "like" else -0.03
        connection.execute(
            """UPDATE memory_items SET confidence=MAX(0,MIN(1,confidence+?)),updated_at=?
            WHERE layer IN ('sample','relationship') AND id IN (SELECT memory_id FROM memory_usage WHERE message_id=?)""",
            (delta, timestamp, body.message_id),
        )
    return {"id": feedback_id, **body.model_dump(), "createdAt": timestamp}


@app.get("/api/calls")
def list_calls(limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    with db() as connection:
        rows = connection.execute("SELECT * FROM calls ORDER BY started_at DESC LIMIT ?", (limit,)).fetchall()
    return [call_dict(row) for row in rows]


@app.post("/api/calls", status_code=201)
def start_call(body: CallStart) -> dict:
    call_id, timestamp = new_id(), now()
    with db() as connection:
        connection.execute("INSERT INTO calls(id,direction,status,started_at,ended_at,duration_seconds,turns_json,answered_at) VALUES(?,?,?,?,?,?,?,?)", (call_id, body.direction, "active", timestamp, None, 0, "[]", timestamp))
    return {"id": call_id, "direction": body.direction, "status": "active", "startedAt": timestamp, "answeredAt": timestamp, "durationSeconds": 0, "turns": []}


@app.post("/api/calls/{call_id}/turns", status_code=201)
def add_call_turn(call_id: str, body: CallTurnCreate) -> dict:
    timestamp, message_id = now(), new_id()
    turn = {"speaker": body.speaker, "text": body.text.strip(), "createdAt": timestamp, "messageId": message_id}
    with db() as connection:
        row = connection.execute("SELECT * FROM calls WHERE id=? AND status='active'", (call_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="通话不存在或已经结束")
        turns = json.loads(row["turns_json"] or "[]")
        turns.append(turn)
        connection.execute("UPDATE calls SET turns_json=? WHERE id=?", (json.dumps(turns, ensure_ascii=False), call_id))
        connection.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)", (message_id, body.speaker, "text", turn["text"], timestamp, call_id))
    return turn


@app.post("/api/calls/{call_id}/answer")
def answer_call(call_id: str) -> dict:
    answered = now()
    with db() as connection:
        cursor = connection.execute("UPDATE calls SET status='active',answered_at=? WHERE id=? AND status='ringing'", (answered, call_id))
        if not cursor.rowcount:
            raise HTTPException(status_code=404, detail="来电不存在或已经处理")
        connection.execute("UPDATE proactive_events SET status='answered',answered_at=? WHERE call_id=?", (now(), call_id))
        row = connection.execute("SELECT * FROM calls WHERE id=?", (call_id,)).fetchone()
    return call_dict(row)


@app.post("/api/calls/{call_id}/end")
def end_call(call_id: str, body: CallEnd) -> dict:
    ended = datetime.now(timezone.utc)
    with db() as connection:
        row = connection.execute("SELECT * FROM calls WHERE id=?", (call_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="没有找到这次通话")
        if row["status"] not in {"active", "ringing"}:
            return call_dict(row)
        if row["status"] == "ringing" and body.status == "answered":
            raise HTTPException(status_code=409, detail="请先接听来电")
        connected_at = datetime.fromisoformat(row["answered_at"] or row["started_at"])
        duration = max(0, int((ended - connected_at).total_seconds())) if body.status == "answered" else 0
        connection.execute("UPDATE calls SET status=?,ended_at=?,duration_seconds=? WHERE id=?", (body.status, ended.isoformat(), duration, call_id))
        label = "通话" if body.status == "answered" else ("未接来电" if body.status == "missed" else "已拒绝来电")
        event_text = f"{label} · {duration // 60:02d}:{duration % 60:02d}" if duration else label
        connection.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)", (new_id(), "assistant", "call_event", event_text, ended.isoformat(), call_id))
        updated = connection.execute("SELECT * FROM calls WHERE id=?", (call_id,)).fetchone()
    return call_dict(updated)


@app.post("/api/calls/{call_id}/reply")
async def reply_in_call(call_id: str, body: CallReply) -> dict:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="服务端尚未配置 DeepSeek API Key")
    user_turn = add_call_turn(call_id, CallTurnCreate(speaker="user", text=body.text))
    with db() as connection:
        call = connection.execute("SELECT * FROM calls WHERE id=? AND status='active'", (call_id,)).fetchone()
        if not call:
            raise HTTPException(status_code=404, detail="通话已经结束")
        turns = json.loads(call["turns_json"] or "[]")[-20:]
        selected = retrieve_memories(connection, body.text, 7)
        profiles = profile_prompt(connection, now)
    memories = [*profiles, *[f"[{row['layer']}] {row['summary'] or row['content']}" for row, _ in selected]]
    scene = detect_scene(body.text)
    system = build_system_prompt(scene, memories) + "\n你们正在实时语音通话。说得自然、短一些，像真的电话口语；不要写动作括号、旁白、标签或舞台说明。"
    payload = {
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "messages": [{"role": "system", "content": system}, *[
            {"role": "assistant" if item["speaker"] == "assistant" else "user", "content": item["text"]} for item in turns
        ]],
        "temperature": 0.82,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions"),
            headers={"Authorization": f"Bearer {api_key}"}, json=payload,
        )
    if response.is_error:
        raise HTTPException(status_code=502, detail="通话回复暂时中断")
    try:
        answer = response.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise HTTPException(status_code=502, detail="通话回复格式错误") from exc
    assistant_turn = add_call_turn(call_id, CallTurnCreate(speaker="assistant", text=answer))
    return {"user": user_turn, "assistant": assistant_turn, "memoryIds": [row["id"] for row, _ in selected]}


@app.post("/api/chat/stream")
async def chat_stream(body: ChatRequest, request: Request) -> StreamingResponse:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="服务端尚未配置 DeepSeek API Key")
    user, _, selected, payload, run_id, cached_answer = prepare_chat(body)

    async def generate():
        completed = False
        try:
            yield sse("meta", {"requestId": run_id, "user": user, "memoryIds": [row["id"] for row, _ in selected]})
            if cached_answer:
                with db() as connection:
                    run = connection.execute("SELECT assistant_message_id,scene FROM chat_runs WHERE id=?", (run_id,)).fetchone()
                    assistant = message_dict(connection.execute("SELECT * FROM messages WHERE id=?", (run["assistant_message_id"],)).fetchone())
                yield sse("delta", {"text": cached_answer})
                yield sse("done", {"assistant": assistant, "scene": run["scene"]})
                return
            answer = ""
            async with httpx.AsyncClient(timeout=httpx.Timeout(90, connect=15)) as client:
                async with client.stream(
                    "POST",
                    os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions"),
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                ) as response:
                    if response.is_error:
                        await response.aread()
                        raise RuntimeError(f"model_http_{response.status_code}")
                    async for line in response.aiter_lines():
                        if await request.is_disconnected():
                            return
                        if not line.startswith("data:"):
                            continue
                        raw = line[5:].strip()
                        if raw == "[DONE]":
                            break
                        try:
                            chunk = json.loads(raw)["choices"][0]["delta"].get("content", "")
                        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
                            continue
                        if chunk:
                            answer += chunk
                            yield sse("delta", {"text": chunk})
            if not answer.strip():
                raise RuntimeError("empty_model_response")
            assistant = finish_chat(run_id, answer, selected)
            completed = True
            yield sse("done", {"assistant": assistant, "scene": detect_scene(user["text"]).name})
        except Exception:
            with db() as connection:
                connection.execute("UPDATE chat_runs SET status='failed',error=?,updated_at=? WHERE id=?", ("模型服务暂时不可用", now(), run_id))
            yield sse("error", {"message": "回复中断了，可以原样重试，不会重复保存消息。"})
        finally:
            if not completed and not cached_answer:
                with db() as connection:
                    connection.execute("UPDATE chat_runs SET status=CASE WHEN status='failed' THEN status ELSE 'interrupted' END,updated_at=? WHERE id=?", (now(), run_id))

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


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
        profiles = profile_prompt(connection, now)
        legacy = [] if selected else connection.execute("SELECT category,text FROM memories WHERE active=1 ORDER BY created_at DESC LIMIT 8").fetchall()

    prompt_memories: list[str] = []
    if selected:
        prompt_memories = [f"[{row['layer']}] {row['summary'] or row['content']}" for row, _ in selected]
    elif legacy:
        prompt_memories = [f"[旧版/{item['category']}] {item['text']}" for item in legacy]
    prompt_memories = [*profiles, *prompt_memories]
    scene = detect_scene(user["text"])
    system = build_system_prompt(scene, prompt_memories)
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
    return {"user": user, "assistant": assistant, "memoryIds": [row["id"] for row, _ in selected], "scene": scene.name}
