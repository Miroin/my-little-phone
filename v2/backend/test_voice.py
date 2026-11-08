import os
from pathlib import Path

db_path = Path(__file__).parent / "data" / "test-voice.db"
if db_path.exists():
    db_path.unlink()
os.environ["MLP_DATABASE_PATH"] = str(db_path)

from app import main
from app.voice import install_voice_schema, voice_text

assert voice_text("[[voice]] 晚点想用声音哄你睡觉") == (True, "晚点想用声音哄你睡觉")
assert voice_text("【voice】我在呢") == (True, "我在呢")
assert voice_text("普通文字") == (False, "普通文字")
with main.db() as connection:
    install_voice_schema(connection)
    assert connection.execute("SELECT name FROM sqlite_master WHERE name='audio_assets'").fetchone()

print("voice message schema test passed")
