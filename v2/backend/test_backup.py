import json
import os
from pathlib import Path

db_path = Path(__file__).parent / "data" / "test-backup.db"
audio_dir = Path(__file__).parent / "data" / "test-backup-audio"
media_dir = Path(__file__).parent / "data" / "test-backup-media"
if db_path.exists():
    db_path.unlink()
os.environ["MLP_DATABASE_PATH"] = str(db_path)
os.environ["MLP_AUDIO_PATH"] = str(audio_dir)
os.environ["MLP_MEDIA_PATH"] = str(media_dir)

from fastapi.testclient import TestClient
from app import main

client = TestClient(main.app)
main.create_memory(main.MemoryCreate(layer="relationship", content="难过时先陪伴", status="active", importance=9))
client.put("/api/profiles/shenyan", json={"display_name": "沈砚", "categories": {"relationship": "陈钰的恋人"}})
client.post("/api/life/notes", json={"kind": "home", "title": "周末", "content": "一起吃火锅"})
photo = client.post("/api/life/media", files={"file": ("photo.png", b"fake-png-data", "image/png")}, data={"title": "合照"})
assert photo.status_code == 201

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

# 在全新空数据库中恢复，扩展表和相册文件也不能丢失。
db_path.unlink()
fresh_preview = client.post("/api/backups/restore-preview", files={"file": ("backup.json", exported.content, "application/json")})
assert fresh_preview.status_code == 201, fresh_preview.text
fresh_confirmed = client.post("/api/backups/restore-confirm", json={"token": fresh_preview.json()["token"], "mode": "merge"})
assert fresh_confirmed.status_code == 200, fresh_confirmed.text
assert fresh_confirmed.json()["inserted"]["character_profiles"] == 2
assert fresh_confirmed.json()["inserted"]["life_notes"] == 1
assert fresh_confirmed.json()["inserted"]["media_assets"] == 1
assert client.get("/api/profiles").json()[0]["categories"]["relationship"] == "陈钰的恋人"
assert len(client.get("/api/life/media").json()) == 1

print("backup validation test passed")
