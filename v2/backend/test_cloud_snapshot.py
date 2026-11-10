import sqlite3
import shutil
from pathlib import Path

from app.cloud_snapshot import build_archive, extract_archive


test_root = Path(__file__).parent / "data"
source = test_root / "test-cloud-source"
restored = test_root / "test-cloud-restored"
for folder in (source, restored):
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
try:
    database = source / "little-phone.db"
    audio = source / "audio"
    media = source / "media"
    audio.mkdir()
    media.mkdir()
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE sample(id TEXT PRIMARY KEY,value TEXT)")
        connection.execute("INSERT INTO sample VALUES('one','保留下来')")
    (audio / "voice.mp3").write_bytes(b"ID3-voice")
    (media / "photo.png").write_bytes(b"PNG-photo")

    raw = build_archive(database, audio, media)
    restored_database = restored / "little-phone.db"
    restored_audio = restored / "audio"
    restored_media = restored / "media"
    extract_archive(raw, restored_database, restored_audio, restored_media)

    with sqlite3.connect(restored_database) as connection:
        assert connection.execute("SELECT value FROM sample WHERE id='one'").fetchone()[0] == "保留下来"
    assert (restored_audio / "voice.mp3").read_bytes() == b"ID3-voice"
    assert (restored_media / "photo.png").read_bytes() == b"PNG-photo"
finally:
    shutil.rmtree(source, ignore_errors=True)
    shutil.rmtree(restored, ignore_errors=True)

print("cloud snapshot archive test passed")
