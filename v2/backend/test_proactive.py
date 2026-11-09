import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi.testclient import TestClient

db_path = Path(__file__).parent / "data" / "test-proactive.db"
if db_path.exists():
    db_path.unlink()
os.environ["MLP_DATABASE_PATH"] = str(db_path)

from app import main
from app.proactive import CompanionSettings, _inside_dnd, _parse_decision

assert _inside_dnd("01:00", "00:30", "08:30") is True
assert _inside_dnd("23:30", "23:00", "07:00") is True
assert _inside_dnd("12:00", "23:00", "07:00") is False
assert _parse_decision('{"action":"message","text":"刚忙完，想找你待会儿。","reason":"想她"}')["action"] == "message"
assert _parse_decision('{"action":"voice","text":"想听你说句话。","reason":"突然想你"}')["action"] == "voice"
settings = main.app.routes
from app.proactive import install_proactive_schema
with main.db() as connection:
    install_proactive_schema(connection, main.now)
    row = connection.execute("SELECT * FROM companion_settings WHERE id=1").fetchone()
assert row["enabled"] == 1

os.environ["SCHEDULER_TOKEN"] = "scheduler-test"
old_call = main.new_id()
old_started = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
with main.db() as connection:
    connection.execute("UPDATE companion_settings SET dnd_enabled=0 WHERE id=1")
    connection.execute(
        "INSERT INTO calls(id,direction,status,started_at,ended_at,duration_seconds,turns_json,answered_at) VALUES(?,?,?,?,?,?,?,?)",
        (old_call, "incoming", "ringing", old_started, None, 0, "[]", None),
    )
    connection.execute(
        "INSERT INTO proactive_events VALUES(?,?,?,?,?,?,?,?,?)",
        (main.new_id(), "call", "sent", "想她", "想听听你的声音。", None, old_call, old_started, None),
    )
expired = TestClient(main.app).post("/api/companion/tick", headers={"X-Scheduler-Token": "scheduler-test"})
assert expired.status_code == 200
assert expired.json()["expiredCalls"] == 1
with main.db() as connection:
    assert connection.execute("SELECT status FROM calls WHERE id=?", (old_call,)).fetchone()[0] == "missed"
    assert connection.execute("SELECT status FROM proactive_events WHERE call_id=?", (old_call,)).fetchone()[0] == "missed"
    assert connection.execute("SELECT text FROM messages WHERE call_id=?", (old_call,)).fetchone()[0] == "未接来电"

print("proactive companion test passed")
