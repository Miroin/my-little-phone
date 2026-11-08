import json
import os
from pathlib import Path

db_path = Path(__file__).parent / "data" / "test-backup.db"
if db_path.exists():
    db_path.unlink()
os.environ["MLP_DATABASE_PATH"] = str(db_path)

from fastapi.testclient import TestClient
from app import main

client = TestClient(main.app)
main.create_memory(main.MemoryCreate(layer="relationship", content="难过时先陪伴", status="active", importance=9))

exported = client.get("/api/backups/export")
assert exported.status_code == 200
envelope = exported.json()
assert envelope["format"] == "my-little-phone-v2-backup"
assert len(envelope["checksum"]) == 64
assert len(envelope["payload"]["tables"]["memory_items"]) == 1

preview = client.post("/api/backups/restore-preview", files={"file": ("backup.json", exported.content, "application/json")})
assert preview.status_code == 201, preview.text
assert preview.json()["counts"]["memory_items"] == 1
confirmed = client.post("/api/backups/restore-confirm", json={"token": preview.json()["token"], "mode": "merge"})
assert confirmed.status_code == 200, confirmed.text
assert confirmed.json()["inserted"]["memory_items"] == 0

tampered = json.loads(exported.content)
tampered["payload"]["tables"]["memory_items"][0]["content"] = "被篡改"
invalid = client.post("/api/backups/restore-preview", files={"file": ("bad.json", json.dumps(tampered).encode(), "application/json")})
assert invalid.status_code == 400

print("backup validation test passed")
