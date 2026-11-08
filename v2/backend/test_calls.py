import os
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

print("call continuity test passed")
