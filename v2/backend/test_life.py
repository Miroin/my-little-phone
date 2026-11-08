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
print("shared life test passed")
