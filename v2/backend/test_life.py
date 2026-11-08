import os
from pathlib import Path

db_path = Path(__file__).parent / "data" / "test-life.db"
if db_path.exists():
    db_path.unlink()
os.environ["MLP_DATABASE_PATH"] = str(db_path)

from fastapi.testclient import TestClient
from app import main

client = TestClient(main.app)
created = client.post("/api/life/notes", json={"kind": "home", "title": "周末火锅", "content": "一起买菜。"})
assert created.status_code == 201
items = client.get("/api/life/notes?kind=home").json()
assert len(items) == 1 and items[0]["title"] == "周末火锅"
schedule = client.post("/api/life/notes", json={"kind": "schedule", "title": "周六约会", "content": "下午去看电影。"})
assert schedule.status_code == 201
assert client.get("/api/life/notes?kind=schedule").json()[0]["title"] == "周六约会"
assert client.delete(f"/api/life/notes/{schedule.json()['id']}").status_code == 200
assert client.get("/api/life/notes?kind=schedule").json() == []
print("shared life test passed")
