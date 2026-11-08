import os
from pathlib import Path

db_path = Path(__file__).parent / "data" / "test-memory.db"
if db_path.exists():
    db_path.unlink()
os.environ["MLP_DATABASE_PATH"] = str(db_path)

from app import main

connection = main.db()
tables = [row[0] for row in connection.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'memory_%' ORDER BY name"
)]
connection.close()
assert tables == ["memory_evidence", "memory_feedback", "memory_items", "memory_jobs", "memory_usage"]

created = main.create_memory(main.MemoryCreate(
    layer="relationship",
    content="陈钰难过时先陪伴，不急着讲道理",
    status="active",
    importance=9,
    evidence="真实聊天片段",
))
assert created["layer"] == "relationship"
assert main.memory_search("难过的时候陪陪我", 8)[0]["id"] == created["id"]
assert len(main.memory_evidence(created["id"])) == 1
assert main.health()["memorySchema"] == 2
print("memory smoke test passed")
