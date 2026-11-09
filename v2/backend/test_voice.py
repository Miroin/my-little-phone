import os
from pathlib import Path
from fastapi.testclient import TestClient

db_path = Path(__file__).parent / "data" / "test-voice.db"
if db_path.exists():
    db_path.unlink()
os.environ["MLP_DATABASE_PATH"] = str(db_path)

from app import main
from app import voice as voice_module
from app.voice import install_voice_schema, voice_text

assert voice_text("[[voice]] 晚点想用声音哄你睡觉") == (True, "晚点想用声音哄你睡觉")
assert voice_text("【voice】我在呢") == (True, "我在呢")
assert voice_text("普通文字") == (False, "普通文字")
with main.db() as connection:
    install_voice_schema(connection)
    assert connection.execute("SELECT name FROM sqlite_master WHERE name='audio_assets'").fetchone()
    connection.execute("INSERT INTO calls(id,direction,status,started_at,ended_at,duration_seconds,turns_json,answered_at) VALUES(?,?,?,?,?,?,?,?)", ("call", "outgoing", "active", main.now(), None, 0, "[]", main.now()))
    connection.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)", ("call-message", "assistant", "text", "喂，听得见吗？", main.now(), "call"))

async def fake_synthesize(text: str):
    assert text == "喂，听得见吗？"
    return b"ID3-test-audio", 720

voice_module._minimax_synthesize = fake_synthesize
client = TestClient(main.app)
generated = client.post("/api/voice/messages/call-message")
assert generated.status_code == 200
assert generated.json()["duration_ms"] == 720
reused = client.post("/api/voice/messages/call-message")
assert reused.status_code == 200
assert reused.json()["id"] == generated.json()["id"]
with main.db() as connection:
    assert connection.execute("SELECT COUNT(*) FROM audio_assets WHERE message_id='call-message'").fetchone()[0] == 1

print("voice message schema test passed")
