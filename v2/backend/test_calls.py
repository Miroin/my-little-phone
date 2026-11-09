import os
import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

db_path = Path(__file__).parent / "data" / "test-calls.db"
if db_path.exists():
    db_path.unlink()
os.environ["MLP_DATABASE_PATH"] = str(db_path)

from app import main

call = main.start_call(main.CallStart(direction="incoming"))
main.add_call_turn(call["id"], main.CallTurnCreate(speaker="assistant", text="喂，想你了。"))
main.add_call_turn(call["id"], main.CallTurnCreate(speaker="user", text="我也想你。"))
ended = main.end_call(call["id"], main.CallEnd(status="answered"))
assert ended["status"] == "answered"
assert len(ended["turns"]) == 2
assert main.list_calls(50)[0]["direction"] == "incoming"
with main.db() as connection:
    call_messages = connection.execute("SELECT * FROM messages WHERE call_id=? ORDER BY created_at", (call["id"],)).fetchall()
assert [row["speaker"] for row in call_messages[:2]] == ["assistant", "user"]
assert call_messages[-1]["kind"] == "call_event"

# 主动来电只从接听时开始计时，不把响铃等待算进去。
ringing_id = main.new_id()
ring_started = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
with main.db() as connection:
    connection.execute(
        "INSERT INTO calls(id,direction,status,started_at,ended_at,duration_seconds,turns_json,answered_at) VALUES(?,?,?,?,?,?,?,?)",
        (ringing_id, "incoming", "ringing", ring_started, None, 0, "[]", None),
    )
    connection.execute(
        "INSERT INTO proactive_events VALUES(?,?,?,?,?,?,?,?,?)",
        (main.new_id(), "call", "sent", "想她", "刚忙完，想听听你的声音。", None, ringing_id, ring_started, None),
    )
answered = main.answer_call(ringing_id)
assert answered["answeredAt"] is not None
assert answered["turns"][-1]["text"] == "刚忙完，想听听你的声音。"
assert answered["turns"][-1]["messageId"]
with main.db() as connection:
    connection.execute("UPDATE calls SET answered_at=? WHERE id=?", ((datetime.now(timezone.utc) - timedelta(seconds=65)).isoformat(), ringing_id))
ended_ringing = main.end_call(ringing_id, main.CallEnd(status="answered"))
assert 64 <= ended_ringing["durationSeconds"] <= 66

# 拒接来电会结束对应主动事件，不能永久挡住之后的主动联系。
declined_id = main.new_id()
with main.db() as connection:
    connection.execute(
        "INSERT INTO calls(id,direction,status,started_at,ended_at,duration_seconds,turns_json,answered_at) VALUES(?,?,?,?,?,?,?,?)",
        (declined_id, "incoming", "ringing", main.now(), None, 0, "[]", None),
    )
    connection.execute(
        "INSERT INTO proactive_events VALUES(?,?,?,?,?,?,?,?,?)",
        (main.new_id(), "call", "sent", "想她", "想听听你的声音。", None, declined_id, main.now(), None),
    )
declined = main.end_call(declined_id, main.CallEnd(status="declined"))
assert declined["status"] == "declined"
with main.db() as connection:
    event_status = connection.execute("SELECT status FROM proactive_events WHERE call_id=?", (declined_id,)).fetchone()[0]
assert event_status == "declined"

# 挂断后只生成待确认候选；重复请求复用同一结果，不重复写入。
class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": json.dumps({"candidates": [{
            "layer": "relationship",
            "summary": "两人在电话里自然表达想念",
            "evidence": "沈砚：喂，想你了。\n陈钰：我也想你。",
            "confidence": 0.92,
        }]}, ensure_ascii=False)}}]}


class FakeClient:
    def __init__(self, **_kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def post(self, *_args, **_kwargs):
        return FakeResponse()


real_client = main.httpx.AsyncClient
os.environ["DEEPSEEK_API_KEY"] = "test-key"
main.httpx.AsyncClient = FakeClient
try:
    extracted = asyncio.run(main.extract_call_memories(call["id"]))
    assert extracted["created"] == 1
    assert extracted["items"][0]["status"] == "candidate"
    cached = asyncio.run(main.extract_call_memories(call["id"]))
    assert cached["cached"] is True
    assert cached["created"] == 0
    assert len(cached["items"]) == 1
    with main.db() as connection:
        evidence = connection.execute(
            "SELECT raw_text FROM memory_evidence WHERE memory_id=?", (extracted["items"][0]["id"],),
        ).fetchone()
    assert "想你" in evidence["raw_text"]
finally:
    main.httpx.AsyncClient = real_client

print("call continuity test passed")
