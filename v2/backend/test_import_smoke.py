import json
import os
from pathlib import Path

db_path = Path(__file__).parent / "data" / "test-import.db"
if db_path.exists():
    db_path.unlink()
os.environ["MLP_DATABASE_PATH"] = str(db_path)

from fastapi.testclient import TestClient
from app.chat_import import _opposite_polarity, _similarity
from app.main import app

assert _similarity("陈钰喜欢香菜", "陈钰不喜欢香菜") >= 0.5
assert _opposite_polarity("陈钰喜欢香菜", "陈钰不喜欢香菜") is True

client = TestClient(app)
sample = [{
    "id": "conversation-1",
    "title": "地铁里陪伴",
    "create_time": 1700000000,
    "update_time": 1700000100,
    "current_node": "a4",
    "mapping": {
        "a1": {"id": "a1", "parent": None, "message": {"id": "m1", "author": {"role": "user"}, "create_time": 1700000000, "content": {"parts": ["我在坐地铁，有点无聊。"]}}},
        "a2": {"id": "a2", "parent": "a1", "message": {"id": "m2", "author": {"role": "assistant"}, "create_time": 1700000005, "content": {"parts": ["那我陪你。坐到哪一站了？"]}}},
        "a3": {"id": "a3", "parent": "a2", "message": {"id": "m3", "author": {"role": "user"}, "create_time": 1700000010, "content": {"parts": ["我喜欢下雨天，也喜欢你陪我坐地铁。"]}}},
        "a4": {"id": "a4", "parent": "a3", "message": {"id": "m4", "author": {"role": "assistant"}, "create_time": 1700000015, "content": {"parts": ["记住了。下次下雨，我来陪你。"]}}},
    },
}]
payload = json.dumps(sample, ensure_ascii=False).encode("utf-8")

response = client.post("/api/history-imports/chatgpt", files={"file": ("conversations.json", payload, "application/json")})
assert response.status_code == 201, response.text
batch = response.json()
assert batch["conversation_count"] == 1
assert batch["message_count"] == 4
assert batch["status"] == "previewed"
assert batch["duplicate"] is False

again = client.post("/api/history-imports/chatgpt", files={"file": ("conversations.json", payload, "application/json")})
assert again.status_code == 201
assert again.json()["id"] == batch["id"]
assert again.json()["duplicate"] is True

job = client.post(f"/api/history-imports/{batch['id']}/extraction-jobs")
assert job.status_code == 201, job.text
job_id = job.json()["id"]
paused = client.patch(f"/api/history-imports/{batch['id']}/extraction-jobs/{job_id}", json={"action": "pause"})
assert paused.json()["status"] == "paused"
resumed = client.patch(f"/api/history-imports/{batch['id']}/extraction-jobs/{job_id}", json={"action": "resume"})
assert resumed.json()["status"] == "ready"
assert client.get(f"/api/history-imports/{batch['id']}/extraction-jobs/{job_id}").json()["total"] == 1

conversations = client.get(f"/api/history-imports/{batch['id']}/conversations").json()
assert conversations["total"] == 1
conversation_id = conversations["items"][0]["id"]
messages = client.get(f"/api/history-imports/conversations/{conversation_id}/messages").json()
assert [item["speaker"] for item in messages["items"]] == ["user", "assistant", "user", "assistant"]
assert messages["items"][1]["text"] == "那我陪你。坐到哪一站了？"

local = client.post(f"/api/history-imports/{batch['id']}/local-candidates")
assert local.status_code == 200, local.text
assert local.json()["counts"]["user"] == 1
candidates = client.get(f"/api/history-imports/{batch['id']}/candidates?limit=20").json()
assert candidates["total"] == 1
candidate_id = candidates["items"][0]["id"]
updated = client.patch(f"/api/history-imports/{batch['id']}/candidates/{candidate_id}", json={"layer": "user", "summary": "陈钰喜欢下雨天，也喜欢沈砚陪她坐地铁"})
assert updated.status_code == 200, updated.text
assert updated.json()["summary"].startswith("陈钰喜欢")
analyzed = client.post(f"/api/history-imports/{batch['id']}/candidates/analyze")
assert analyzed.status_code == 200, analyzed.text
before_report = client.get(f"/api/history-imports/{batch['id']}/integrity-report").json()
assert before_report["safeToBackup"] is False
accepted = client.post(f"/api/history-imports/{batch['id']}/candidates/accept", json={"ids": [candidate_id]})
assert accepted.json()["accepted"] == 1
assert client.get("/api/memories?status=active").json()[0]["sourceType"] == "history-local"
report = client.get(f"/api/history-imports/{batch['id']}/integrity-report").json()
assert report["safeToBackup"] is True
assert report["checks"]["acceptedMemoriesTraceable"] is True
print("history import smoke test passed")
