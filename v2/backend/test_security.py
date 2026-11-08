import os
from pathlib import Path

db_path = Path(__file__).parent / "data" / "test-security.db"
if db_path.exists():
    db_path.unlink()
os.environ["MLP_DATABASE_PATH"] = str(db_path)
os.environ["MLP_ACCESS_TOKEN"] = "private-test-token"
os.environ["SCHEDULER_TOKEN"] = "scheduler-test-token"

from fastapi.testclient import TestClient
from app import main

client = TestClient(main.app)
assert client.get("/health").status_code == 200
assert client.get("/api/session").status_code == 401
assert client.get("/api/session", headers={"X-MLP-Access-Token": "wrong"}).status_code == 401
assert client.get("/api/session", headers={"X-MLP-Access-Token": "private-test-token"}).status_code == 200
assert client.get("/api/profiles", headers={"Authorization": "Bearer private-test-token"}).status_code == 200
assert client.get("/api/profiles", headers={"X-Scheduler-Token": "scheduler-test-token"}).status_code == 200
print("private API security test passed")
