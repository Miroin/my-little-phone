import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

db_path = Path(__file__).parent / "data" / "test-recent-memory.db"
db_path.unlink(missing_ok=True)
os.environ["MLP_DATABASE_PATH"] = str(db_path)
os.environ["DEEPSEEK_API_KEY"] = "test-key"

from app import main


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": json.dumps({"candidates": [{
            "layer": "plan",
            "summary": "两人约好周末一起吃火锅",
            "evidence": "陈钰：周末一起吃火锅吧。\n沈砚：好，我来订位置。",
            "confidence": 0.94,
        }]}, ensure_ascii=False)}}]}


class FakeClient:
    calls = 0

    def __init__(self, **_kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def post(self, *_args, **_kwargs):
        FakeClient.calls += 1
        return FakeResponse()


base = datetime.now(timezone.utc) - timedelta(minutes=30)
turns = [
    ("user", "周末一起吃火锅吧。"),
    ("assistant", "好，我来订位置。"),
    ("user", "记得不要放蒜。"),
    ("assistant", "记住了，会单独备注。"),
]
with main.db() as connection:
    for index, (speaker, text) in enumerate(turns):
        connection.execute(
            "INSERT INTO messages VALUES(?,?,?,?,?,?)",
            (f"recent-{index}", speaker, "text", text, (base + timedelta(seconds=index)).isoformat(), None),
        )

real_client = main.httpx.AsyncClient
main.httpx.AsyncClient = FakeClient
try:
    result = asyncio.run(main.extract_recent_chat_memories())
    assert result["processed"] == 4
    assert result["created"] == 1
    assert result["items"][0]["status"] == "candidate"
    second = asyncio.run(main.extract_recent_chat_memories())
    assert second["processed"] == 0
    assert FakeClient.calls == 1
    with main.db() as connection:
        evidence = connection.execute(
            "SELECT raw_text FROM memory_evidence WHERE memory_id=?", (result["items"][0]["id"],),
        ).fetchone()
        job = connection.execute("SELECT status,cursor FROM memory_jobs WHERE id='recent-chat-memory'").fetchone()
    assert "火锅" in evidence["raw_text"]
    assert job["status"] == "done"
    assert json.loads(job["cursor"])["id"] == "recent-3"
finally:
    main.httpx.AsyncClient = real_client

print("recent chat memory extraction test passed")
