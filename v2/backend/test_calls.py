import os
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
answered = main.answer_call(ringing_id)
assert answered["answeredAt"] is not None
with main.db() as connection:
    connection.execute("UPDATE calls SET answered_at=? WHERE id=?", ((datetime.now(timezone.utc) - timedelta(seconds=65)).isoformat(), ringing_id))
ended_ringing = main.end_call(ringing_id, main.CallEnd(status="answered"))
assert 64 <= ended_ringing["durationSeconds"] <= 66

print("call continuity test passed")
