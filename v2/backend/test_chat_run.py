import os
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

print("chat run idempotency test passed")
