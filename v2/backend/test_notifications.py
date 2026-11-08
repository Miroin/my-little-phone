import json
import os
from pathlib import Path

key_path = Path(__file__).parent / "data" / "test-vapid.json"
key_path.unlink(missing_ok=True)
os.environ.pop("VAPID_PUBLIC_KEY", None)
os.environ.pop("VAPID_PRIVATE_KEY", None)
os.environ["MLP_VAPID_PATH"] = str(key_path)

from app.notifications import vapid_config

vapid_config.cache_clear()
public_key, private_key = vapid_config()
assert len(public_key) == 87
assert private_key.startswith("-----BEGIN PRIVATE KEY-----")
assert key_path.is_file()
saved = json.loads(key_path.read_text(encoding="utf-8"))
vapid_config.cache_clear()
assert vapid_config() == (saved["publicKey"], saved["privateKey"])
print("persistent web push key test passed")
