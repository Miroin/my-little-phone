import json
import os
from pathlib import Path

db_path = Path(__file__).parent / "data" / "test-import.db"
os.environ["MLP_DATABASE_PATH"] = str(db_path)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
sample = [{
    "id": "conversation-1",
    "title": "地铁里陪伴",
    "create_time": 1700000000,
    "update_time": 1700000100,
    "current_node": "a2",
    "mapping": {
        "a1": {"id": "a1", "parent": None, "message": {"id": "m1", "author": {"role": "user"}, "create_time": 1700000000, "content": {"parts": ["我在坐地铁，有点无聊。"]}}},
        "a2": {"id": "a2", "parent": "a1", "message": {"id": "m2", "author": {"role": "assistant"}, "create_time": 1700000005, "content": {"parts": ["那我陪你。坐到哪一站了？"]}}},
    },
}]
payload = json.dumps(sample, ensure_ascii=False).encode("utf-8")

response = client.post("/api/history-imports/chatgpt", files={"file": ("conversations.json", payload, "application/json")})
assert response.status_code == 201, response.text
batch = response.json()
assert batch["conversation_count"] == 1
assert batch["message_count"] == 2
assert batch["status"] == "previewed"
assert batch["duplicate"] is False

again = client.post("/api/history-imports/chatgpt", files={"file": ("conversations.json", payload, "application/json")})
assert again.status_code == 201
assert again.json()["id"] == batch["id"]
assert again.json()["duplicate"] is True

conversations = client.get(f"/api/history-imports/{batch['id']}/conversations").json()
assert conversations["total"] == 1
conversation_id = conversations["items"][0]["id"]
messages = client.get(f"/api/history-imports/conversations/{conversation_id}/messages").json()
assert [item["speaker"] for item in messages["items"]] == ["user", "assistant"]
assert messages["items"][1]["text"] == "那我陪你。坐到哪一站了？"
print("history import smoke test passed")
