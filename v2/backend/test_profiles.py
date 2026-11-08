import os
from pathlib import Path

db_path = Path(__file__).parent / "data" / "test-profiles.db"
if db_path.exists():
    db_path.unlink()
os.environ["MLP_DATABASE_PATH"] = str(db_path)

from app import main
from app.profiles import profile_prompt
from fastapi.testclient import TestClient

client = TestClient(main.app)
profiles = client.get("/api/profiles").json()
assert {item["subject"] for item in profiles} == {"shenyan", "user"}
saved = client.put("/api/profiles/shenyan", json={"display_name": "沈砚", "categories": {"personality": "温和、宠溺，有自己的生活。", "relationship": "陈钰的恋人。"}}).json()
assert saved["categories"]["personality"].startswith("温和")
with main.db() as connection:
    prompt = profile_prompt(connection, main.now)
assert any("温和、宠溺" in item for item in prompt)
print("profile prompt test passed")
