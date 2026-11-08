import sqlite3

from app.chat_import import install_schema
from app.memory_extract import extraction_queue_counts, install_extraction_schema, parse_candidate_payload, queued_conversations

payload = """```json
{"candidates":[
  {"layer":"relationship","summary":"难过时先陪伴","evidence":"陈钰：我不想讲道理。沈砚：嗯，不讲了。","confidence":0.92},
  {"layer":"unknown","summary":"应被忽略","evidence":"无","confidence":1}
]}
```"""

items = parse_candidate_payload(payload)
assert len(items) == 1
assert items[0]["layer"] == "relationship"
assert items[0]["confidence"] == 0.92
assert parse_candidate_payload('{"candidates":[]}') == []

connection = sqlite3.connect(":memory:")
connection.row_factory = sqlite3.Row
install_schema(connection)
install_extraction_schema(connection)
connection.execute("INSERT INTO import_batches VALUES(?,?,?,?,?,?,?,?,?,?,?)", ("b", "chatgpt", "x.json", "sha", "previewed", 4, 0, 0, None, "now", "now"))
for index in range(4):
    connection.execute("INSERT INTO imported_conversations VALUES(?,?,?,?,?,?,?)", (f"c{index}", "b", f"s{index}", f"会话{index}", f"2026-01-0{index+1}", None, 0))
connection.execute("INSERT INTO extraction_runs VALUES(?,?,?,?,?,?)", ("c1", "done", 1, 1, None, "now"))
connection.execute("INSERT INTO extraction_runs VALUES(?,?,?,?,?,?)", ("c2", "failed", 1, 0, "500", "now"))
connection.execute("INSERT INTO extraction_runs VALUES(?,?,?,?,?,?)", ("c3", "retry", 1, 0, None, "now"))
assert [row["id"] for row in queued_conversations(connection, "b", 10)] == ["c0", "c3"]
assert extraction_queue_counts(connection, "b") == (2, 1)
print("memory extraction parser test passed")
