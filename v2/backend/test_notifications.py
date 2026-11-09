import json
import os
from pathlib import Path
from fastapi.testclient import TestClient

key_path = Path(__file__).parent / "data" / "test-vapid.json"
key_path.unlink(missing_ok=True)
os.environ.pop("VAPID_PUBLIC_KEY", None)
os.environ.pop("VAPID_PRIVATE_KEY", None)
os.environ["MLP_VAPID_PATH"] = str(key_path)
db_path = Path(__file__).parent / "data" / "test-notifications.db"
db_path.unlink(missing_ok=True)
os.environ["MLP_DATABASE_PATH"] = str(db_path)

from app.notifications import vapid_config

vapid_config.cache_clear()
public_key, private_key = vapid_config()
assert len(public_key) == 87
assert private_key.startswith("-----BEGIN PRIVATE KEY-----")
assert key_path.is_file()
saved = json.loads(key_path.read_text(encoding="utf-8"))
vapid_config.cache_clear()
assert vapid_config() == (saved["publicKey"], saved["privateKey"])

from app import main
client = TestClient(main.app)
with main.db() as connection:
    connection.execute(
        "INSERT INTO push_subscriptions VALUES(?,?,?,?,?,?)",
        ("https://push.example/device", "p" * 40, "a" * 12, 1, main.now(), main.now()),
    )
    connection.execute(
        "INSERT INTO notification_outbox VALUES(?,?,?,?,?,?,?,?,?,?)",
        ("failed-job", "message", "沈砚", "想你了", "/v2-preview/", "failed", 1, "temporary", main.now(), main.now()),
    )
status = client.get("/api/notifications/status")
assert status.status_code == 200
assert status.json()["activeSubscriptions"] == 1
assert status.json()["counts"]["failed"] == 1
retried = client.post("/api/notifications/retry-failed")
assert retried.status_code == 200
assert retried.json()["queued"] == 1
assert client.get("/api/notifications/status").json()["counts"]["pending"] == 1
print("persistent web push key test passed")
