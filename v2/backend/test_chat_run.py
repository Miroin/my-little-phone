import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

db_path = Path(__file__).parent / "data" / "test-chat-run.db"
if db_path.exists():
    db_path.unlink()
os.environ["MLP_DATABASE_PATH"] = str(db_path)

from app import main

body = main.ChatRequest(text="我今天有点难过，只想让你陪陪我", request_id="fixed-request-001")
user, _, selected, payload, run_id, cached = main.prepare_chat(body)
assert run_id == "fixed-request-001"
assert cached == ""
assert payload["stream"] is True
assert "先具体接住感受" in payload["messages"][0]["content"]

assistant = main.finish_chat(run_id, "嗯，不讲道理。你靠过来，我陪你待着。", selected)
same_user, _, _, same_payload, _, cached = main.prepare_chat(body)
assert same_user["id"] == user["id"]
assert same_payload is None
assert cached == assistant["text"]

with main.db() as connection:
    assert connection.execute("SELECT COUNT(*) FROM messages WHERE speaker='user'").fetchone()[0] == 1
    assert connection.execute("SELECT status FROM chat_runs WHERE id=?", (run_id,)).fetchone()[0] == "complete"

# 消息接口从最新一页开始，并能继续向前读取，不再卡在固定 500 条。
base = datetime(2030, 1, 1, tzinfo=timezone.utc)
with main.db() as connection:
    for index in range(120):
        connection.execute(
            "INSERT INTO messages VALUES(?,?,?,?,?,?)",
            (f"history-{index:03d}", "user", "text", f"历史消息 {index}", (base + timedelta(seconds=index)).isoformat(), None),
        )
recent = main.messages(limit=100, offset=0)
older = main.messages(limit=100, offset=100)
assert recent[0]["id"] == "history-020"
assert recent[-1]["id"] == "history-119"
assert {item["id"] for item in recent}.isdisjoint({item["id"] for item in older})
assert any(item["id"] == user["id"] for item in older)

print("chat run idempotency test passed")
