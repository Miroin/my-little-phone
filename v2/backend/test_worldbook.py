import os
from pathlib import Path

db_path = Path(__file__).parent / "data" / "test-worldbook.db"
if db_path.exists():
    db_path.unlink()
os.environ["MLP_DATABASE_PATH"] = str(db_path)

from app import main
from app.worldbook import worldbook_prompt
from fastapi.testclient import TestClient

client = TestClient(main.app)

global_entry = client.post("/api/worldbook", json={
    "title": "固定背景", "content": "两个人住在临江公寓。", "keywords": [], "enabled": True,
})
assert global_entry.status_code == 201

cafe = client.post("/api/worldbook", json={
    "title": "常去的咖啡店", "content": "店名是暮色，靠窗的位置最安静。", "keywords": ["咖啡", "暮色"], "enabled": True,
})
assert cafe.status_code == 201
cafe_entry = cafe.json()

hidden = client.post("/api/worldbook", json={
    "title": "停用条目", "content": "不应进入提示词。", "keywords": ["咖啡"], "enabled": False,
})
assert hidden.status_code == 201

with main.db() as connection:
    prompt = worldbook_prompt(connection, "想去喝咖啡")
joined = "\n".join(prompt)
assert "临江公寓" in joined
assert "暮色" in joined
assert "不应进入提示词" not in joined

updated = client.put(f"/api/worldbook/{cafe_entry['id']}", json={
    "title": "常去的咖啡店", "content": "暮色咖啡店周二休息。", "keywords": ["咖啡"], "enabled": False,
})
assert updated.status_code == 200
with main.db() as connection:
    assert "暮色咖啡店周二休息" not in "\n".join(worldbook_prompt(connection, "喝咖啡"))

duplicate = client.post("/api/worldbook", json={
    "title": "固定背景", "content": "两个人住在临江公寓。", "keywords": [], "enabled": True,
})
assert duplicate.status_code == 409
assert client.delete(f"/api/worldbook/{cafe_entry['id']}").status_code == 200
assert len(client.get("/api/worldbook").json()) == 2
print("worldbook CRUD and retrieval test passed")
