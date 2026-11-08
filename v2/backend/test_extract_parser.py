from app.memory_extract import parse_candidate_payload

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
print("memory extraction parser test passed")
