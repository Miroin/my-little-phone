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
assert {"memory_evidence", "memory_feedback", "memory_items", "memory_jobs", "memory_usage"}.issubset(tables)

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
assert main.cosine_similarity(main.ngrams("周末一起吃火锅"), main.ngrams("约好周末去吃火锅")) > 0.4
updated = main.update_memory(created["id"], main.MemoryUpdate(
    layer="relationship", content="陈钰难过时先陪她，不急着讲道理", summary="难过时先陪伴",
    importance=9.5, confidence=0.9, tags=["安慰", "陪伴"],
))
assert updated["summary"] == "难过时先陪伴"
reinforced = main.reinforce_memory(created["id"])
assert abs(reinforced["confidence"] - 0.95) < 0.0001
archived = main.update_memory_status(created["id"], main.MemoryStatusUpdate(status="archived"))
assert archived["status"] == "archived"
deleted = main.delete_memory(created["id"])
assert deleted["deleted"] is True
with main.db() as connection:
    assert connection.execute("SELECT 1 FROM memory_items WHERE id=?", (created["id"],)).fetchone() is None
    assert connection.execute("SELECT 1 FROM memory_evidence WHERE memory_id=?", (created["id"],)).fetchone() is None
assert main.health()["memorySchema"] == 2
print("memory smoke test passed")
