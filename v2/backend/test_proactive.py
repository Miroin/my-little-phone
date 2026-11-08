import os
from pathlib import Path

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

print("proactive companion test passed")
