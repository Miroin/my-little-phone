from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from typing import Callable

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


ALLOWED_LAYERS = {"relationship", "user", "event", "feeling", "plan", "sample"}


class ExtractionAction(BaseModel):
    action: str


def install_extraction_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS extraction_runs(
            conversation_id TEXT PRIMARY KEY,status TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,
            candidate_count INTEGER NOT NULL DEFAULT 0,last_error TEXT,updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS extraction_jobs(
            id TEXT PRIMARY KEY,batch_id TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'ready',
            total INTEGER NOT NULL DEFAULT 0,processed INTEGER NOT NULL DEFAULT 0,
            failed INTEGER NOT NULL DEFAULT 0,created INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_extraction_jobs_batch ON extraction_jobs(batch_id,status,updated_at);
        CREATE TABLE IF NOT EXISTS extraction_chunks(
            conversation_id TEXT NOT NULL,chunk_index INTEGER NOT NULL,start_ordinal INTEGER NOT NULL,
            end_ordinal INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'pending',attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,updated_at TEXT NOT NULL,
            PRIMARY KEY(conversation_id,chunk_index)
        );
        CREATE INDEX IF NOT EXISTS idx_extraction_chunks_status ON extraction_chunks(status,conversation_id,chunk_index);
        """
    )


def populate_extraction_chunks(connection: sqlite3.Connection, batch_id: str, timestamp: str, chunk_size: int = 20) -> int:
    conversations = connection.execute(
        "SELECT id,message_count FROM imported_conversations WHERE batch_id=?", (batch_id,),
    ).fetchall()
    for conversation in conversations:
        count = conversation["message_count"] or connection.execute(
            "SELECT COUNT(*) FROM imported_messages WHERE conversation_id=?", (conversation["id"],),
        ).fetchone()[0]
        for index, start in enumerate(range(0, count, chunk_size)):
            connection.execute(
                "INSERT OR IGNORE INTO extraction_chunks VALUES(?,?,?,?, 'pending',0,NULL,?)",
                (conversation["id"], index, start, min(count - 1, start + chunk_size - 1), timestamp),
            )
    return connection.execute(
        """SELECT COUNT(*) FROM extraction_chunks WHERE conversation_id IN
        (SELECT id FROM imported_conversations WHERE batch_id=?)""", (batch_id,),
    ).fetchone()[0]


def queued_conversations(connection: sqlite3.Connection, batch_id: str, limit: int) -> list[sqlite3.Row]:
    return connection.execute(
        """SELECT c.*,x.chunk_index,x.start_ordinal,x.end_ordinal FROM extraction_chunks x
        JOIN imported_conversations c ON c.id=x.conversation_id
        WHERE c.batch_id=? AND x.status IN ('pending','retry')
        ORDER BY COALESCE(c.created_at,'') ASC,x.chunk_index ASC LIMIT ?""",
        (batch_id, limit),
    ).fetchall()


def extraction_queue_counts(connection: sqlite3.Connection, batch_id: str) -> tuple[int, int]:
    remaining = connection.execute(
        """SELECT COUNT(*) FROM extraction_chunks WHERE status IN ('pending','retry') AND conversation_id IN
        (SELECT id FROM imported_conversations WHERE batch_id=?)""", (batch_id,),
    ).fetchone()[0]
    failed = connection.execute(
        """SELECT COUNT(*) FROM extraction_chunks WHERE status='failed' AND conversation_id IN
        (SELECT id FROM imported_conversations WHERE batch_id=?)""", (batch_id,),
    ).fetchone()[0]
    return remaining, failed


def parse_candidate_payload(text: str) -> list[dict]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    payload = json.loads(cleaned)
    items = payload.get("candidates", []) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise ValueError("candidates must be a list")
    result: list[dict] = []
    for item in items:
        if not isinstance(item, dict) or item.get("layer") not in ALLOWED_LAYERS:
            continue
        summary = str(item.get("summary") or "").strip()
        evidence = str(item.get("evidence") or "").strip()
        if not summary or not evidence:
            continue
        result.append({
            "layer": item["layer"],
            "summary": summary[:500],
            "evidence": evidence[:6000],
            "confidence": max(0.0, min(1.0, float(item.get("confidence", 0.65)))),
        })
    return result[:12]


def extraction_prompt(title: str, messages: list[sqlite3.Row]) -> str:
    transcript = "\n".join(f"{'陈钰' if row['speaker']=='user' else '沈砚'}：{row['text']}" for row in messages)
    return f"""从真实聊天中提取值得长期保留的记忆候选。不要总结整段对话，不要编造，不要把普通寒暄当记忆。

分类只能使用：
- relationship：双方如何相处、稳定关系默契
- user：陈钰明确表达的长期偏好、习惯或边界
- event：真实发生的共同经历
- feeling：一次经历留下的自然感受，不是固定台词
- plan：尚未完成或需要追踪的约定
- sample：能代表沈砚在特定场景如何回应的真实对话样本

返回严格 JSON：{{"candidates":[{{"layer":"event","summary":"简洁事实","evidence":"原文证据","confidence":0.8}}]}}
找不到值得保留的内容就返回 {{"candidates":[]}}。

会话标题：{title}
聊天原文：
{transcript[:50000]}"""


def build_router(db_factory: Callable[[], sqlite3.Connection], now: Callable[[], str], new_id: Callable[[], str]) -> APIRouter:
    router = APIRouter(prefix="/api/history-imports", tags=["memory-extraction"])

    @router.post("/{batch_id}/extraction-jobs", status_code=201)
    def create_extraction_job(batch_id: str) -> dict:
        with db_factory() as connection:
            install_extraction_schema(connection)
            if not connection.execute("SELECT 1 FROM import_batches WHERE id=? AND status='previewed'", (batch_id,)).fetchone():
                raise HTTPException(status_code=404, detail="没有找到已读取完成的历史聊天")
            timestamp = now()
            total = populate_extraction_chunks(connection, batch_id, timestamp)
            existing = connection.execute(
                "SELECT * FROM extraction_jobs WHERE batch_id=? AND status IN ('ready','running','paused','needs_retry') ORDER BY created_at DESC LIMIT 1", (batch_id,)
            ).fetchone()
            if existing:
                connection.execute("UPDATE extraction_jobs SET total=?,updated_at=? WHERE id=?", (total, timestamp, existing["id"]))
                return dict(connection.execute("SELECT * FROM extraction_jobs WHERE id=?", (existing["id"],)).fetchone())
            remaining, failed = extraction_queue_counts(connection, batch_id)
            completed = max(0, total - remaining - failed)
            status = "needs_retry" if failed and not remaining else ("complete" if total and completed == total else "ready")
            job_id = new_id()
            connection.execute(
                "INSERT INTO extraction_jobs VALUES(?,?,?,?,?,?,?,?,?,?)",
                (job_id, batch_id, status, total, completed, failed, 0, None, timestamp, timestamp),
            )
            row = connection.execute("SELECT * FROM extraction_jobs WHERE id=?", (job_id,)).fetchone()
        return dict(row)

    @router.get("/{batch_id}/extraction-jobs/{job_id}")
    def get_extraction_job(batch_id: str, job_id: str) -> dict:
        with db_factory() as connection:
            install_extraction_schema(connection)
            row = connection.execute("SELECT * FROM extraction_jobs WHERE id=? AND batch_id=?", (job_id, batch_id)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="没有找到这个精提取任务")
        return dict(row)

    @router.patch("/{batch_id}/extraction-jobs/{job_id}")
    def control_extraction_job(batch_id: str, job_id: str, body: ExtractionAction) -> dict:
        if body.action not in {"pause", "resume", "retry"}:
            raise HTTPException(status_code=400, detail="不支持的任务操作")
        target = "paused" if body.action == "pause" else "ready"
        with db_factory() as connection:
            install_extraction_schema(connection)
            cursor = connection.execute(
                "UPDATE extraction_jobs SET status=?,last_error=NULL,updated_at=? WHERE id=? AND batch_id=? AND status!='complete'",
                (target, now(), job_id, batch_id),
            )
            if not cursor.rowcount:
                raise HTTPException(status_code=404, detail="任务不存在或已经完成")
            if body.action == "retry":
                connection.execute(
                    "UPDATE extraction_runs SET status='retry' WHERE status='failed' AND conversation_id IN (SELECT id FROM imported_conversations WHERE batch_id=?)",
                    (batch_id,),
                )
                connection.execute(
                    """UPDATE extraction_chunks SET status='retry',last_error=NULL,updated_at=? WHERE status='failed'
                    AND conversation_id IN (SELECT id FROM imported_conversations WHERE batch_id=?)""",
                    (now(), batch_id),
                )
            row = connection.execute("SELECT * FROM extraction_jobs WHERE id=?", (job_id,)).fetchone()
        return dict(row)

    @router.post("/{batch_id}/deepseek-candidates")
    async def extract_candidates(batch_id: str, max_conversations: int = Query(default=3, ge=1, le=10), job_id: str | None = None) -> dict:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise HTTPException(status_code=503, detail="服务端尚未配置 DeepSeek API Key")
        with db_factory() as connection:
            install_extraction_schema(connection)
            populate_extraction_chunks(connection, batch_id, now())
            if job_id:
                job = connection.execute("SELECT * FROM extraction_jobs WHERE id=? AND batch_id=?", (job_id, batch_id)).fetchone()
                if not job:
                    raise HTTPException(status_code=404, detail="没有找到这个精提取任务")
                if job["status"] == "paused":
                    return {"processed": 0, "created": 0, "failed": 0, "paused": True, "complete": False, "job": dict(job)}
                if job["status"] == "complete":
                    return {"processed": 0, "created": 0, "failed": 0, "complete": True, "job": dict(job)}
                connection.execute("UPDATE extraction_jobs SET status='running',updated_at=? WHERE id=?", (now(), job_id))
            conversations = queued_conversations(connection, batch_id, max_conversations)
        if not conversations:
            result = {"processed": 0, "created": 0, "complete": True}
            if job_id:
                with db_factory() as connection:
                    _, failed_total = extraction_queue_counts(connection, batch_id)
                    final_status = "needs_retry" if failed_total else "complete"
                    connection.execute("UPDATE extraction_jobs SET status=?,updated_at=? WHERE id=?", (final_status, now(), job_id))
                    result["job"] = dict(connection.execute("SELECT * FROM extraction_jobs WHERE id=?", (job_id,)).fetchone())
                    result["complete"] = final_status == "complete"
            return result

        processed = 0
        created = 0
        errors: list[str] = []
        async with httpx.AsyncClient(timeout=90) as client:
            for conversation in conversations:
                if job_id:
                    with db_factory() as connection:
                        current_status = connection.execute("SELECT status FROM extraction_jobs WHERE id=?", (job_id,)).fetchone()
                    if not current_status or current_status["status"] == "paused":
                        break
                with db_factory() as connection:
                    messages = connection.execute(
                        """SELECT * FROM imported_messages WHERE conversation_id=? AND ordinal BETWEEN ? AND ?
                        ORDER BY ordinal""",
                        (conversation["id"], conversation["start_ordinal"], conversation["end_ordinal"]),
                    ).fetchall()
                try:
                    response = await client.post(
                        os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions"),
                        headers={"Authorization": f"Bearer {api_key}"},
                        json={
                            "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                            "messages": [{"role": "user", "content": extraction_prompt(conversation["title"], messages)}],
                            "temperature": 0.15,
                            "response_format": {"type": "json_object"},
                            "stream": False,
                        },
                    )
                    response.raise_for_status()
                    items = parse_candidate_payload(response.json()["choices"][0]["message"]["content"])
                    with db_factory() as connection:
                        first_message = messages[0]["id"] if messages else ""
                        for item in items:
                            digest = hashlib.sha256(f"{item['layer']}\n{item['summary']}".encode("utf-8")).hexdigest()
                            cursor = connection.execute(
                                "INSERT OR IGNORE INTO memory_candidates VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                                (new_id(), batch_id, conversation["id"], first_message, item["layer"], item["summary"], item["evidence"], item["confidence"], "pending", digest, now()),
                            )
                            created += cursor.rowcount
                        connection.execute(
                            """UPDATE extraction_chunks SET status='done',attempts=attempts+1,last_error=NULL,updated_at=?
                            WHERE conversation_id=? AND chunk_index=?""",
                            (now(), conversation["id"], conversation["chunk_index"]),
                        )
                        unfinished = connection.execute(
                            "SELECT COUNT(*) FROM extraction_chunks WHERE conversation_id=? AND status!='done'", (conversation["id"],),
                        ).fetchone()[0]
                        candidate_count = connection.execute(
                            "SELECT COUNT(*) FROM memory_candidates WHERE conversation_id=?", (conversation["id"],),
                        ).fetchone()[0]
                        run_status = "done" if unfinished == 0 else "running"
                        connection.execute(
                            """INSERT INTO extraction_runs VALUES(?,?,?,?,?,?) ON CONFLICT(conversation_id) DO UPDATE SET
                            status=excluded.status,attempts=extraction_runs.attempts+1,candidate_count=excluded.candidate_count,
                            last_error=NULL,updated_at=excluded.updated_at""",
                            (conversation["id"], run_status, 1, candidate_count, None, now()),
                        )
                    processed += 1
                except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError) as exc:
                    label = f"{conversation['title']}（第 {conversation['chunk_index'] + 1} 段）"
                    errors.append(label)
                    with db_factory() as connection:
                        connection.execute(
                            """UPDATE extraction_chunks SET status='failed',attempts=attempts+1,last_error=?,updated_at=?
                            WHERE conversation_id=? AND chunk_index=?""",
                            (str(exc)[:500], now(), conversation["id"], conversation["chunk_index"]),
                        )
                        connection.execute(
                            "INSERT INTO extraction_runs VALUES(?,?,?,?,?,?) ON CONFLICT(conversation_id) DO UPDATE SET status='failed',attempts=extraction_runs.attempts+1,last_error=excluded.last_error,updated_at=excluded.updated_at",
                            (conversation["id"], "failed", 1, 0, str(exc)[:500], now()),
                        )
        complete = len(conversations) < max_conversations
        result = {"processed": processed, "created": created, "failed": len(errors), "failedTitles": errors, "complete": complete}
        if job_id:
            with db_factory() as connection:
                remaining, failed_total = extraction_queue_counts(connection, batch_id)
                status = ("needs_retry" if failed_total else "complete") if remaining == 0 else "ready"
                connection.execute(
                    """UPDATE extraction_jobs SET status=?,processed=processed+?,failed=?,created=created+?,
                    last_error=?,updated_at=? WHERE id=?""",
                    (status, processed, failed_total, created, (", ".join(errors[:3]) or None), now(), job_id),
                )
                result["complete"] = status == "complete"
                result["job"] = dict(connection.execute("SELECT * FROM extraction_jobs WHERE id=?", (job_id,)).fetchone())
        return result

    return router
