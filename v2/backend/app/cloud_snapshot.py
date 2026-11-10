from __future__ import annotations

import io
import os
import sqlite3
import uuid
import zipfile
from pathlib import Path

import httpx


def configured() -> bool:
    return bool(os.getenv("SUPABASE_URL", "").strip() and os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip())


def _settings() -> tuple[str, str, str, str]:
    base = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    bucket = os.getenv("MLP_SNAPSHOT_BUCKET", "mlp-backups").strip() or "mlp-backups"
    name = os.getenv("MLP_SNAPSHOT_OBJECT", "latest.zip").strip() or "latest.zip"
    return base, key, bucket, name


def _headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}", "apikey": key}


def build_archive(database: Path, audio_dir: Path, media_dir: Path) -> bytes:
    buffer = io.BytesIO()
    safe_database = database.parent / f".snapshot-{uuid.uuid4().hex}.db"
    try:
        if database.exists():
            source = sqlite3.connect(database)
            target = sqlite3.connect(safe_database)
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            if safe_database.exists():
                archive.write(safe_database, "little-phone.db")
            for folder, prefix in ((audio_dir, "audio"), (media_dir, "media")):
                if folder.exists():
                    for path in folder.rglob("*"):
                        if path.is_file():
                            archive.write(path, f"{prefix}/{path.relative_to(folder).as_posix()}")
    finally:
        safe_database.unlink(missing_ok=True)
    return buffer.getvalue()


def extract_archive(raw: bytes, database: Path, audio_dir: Path, media_dir: Path) -> None:
    roots = {"little-phone.db": database, "audio": audio_dir, "media": media_dir}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for info in archive.infolist():
            parts = Path(info.filename).parts
            if not parts or info.is_dir() or ".." in parts:
                continue
            if parts[0] == "little-phone.db" and len(parts) == 1:
                target = database
            elif parts[0] in ("audio", "media") and len(parts) > 1:
                target = roots[parts[0]].joinpath(*parts[1:])
            else:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))


def restore_if_available(database: Path, audio_dir: Path, media_dir: Path) -> bool:
    if not configured() or database.exists():
        return False
    base, key, bucket, name = _settings()
    response = httpx.get(f"{base}/storage/v1/object/{bucket}/{name}", headers=_headers(key), timeout=45.0)
    if response.status_code in (400, 404):
        return False
    response.raise_for_status()
    extract_archive(response.content, database, audio_dir, media_dir)
    return database.exists()


def upload(database: Path, audio_dir: Path, media_dir: Path) -> dict[str, int | str | bool]:
    if not configured():
        return {"configured": False, "uploaded": 0}
    base, key, bucket, name = _settings()
    headers = _headers(key)
    bucket_response = httpx.get(f"{base}/storage/v1/bucket/{bucket}", headers=headers, timeout=30.0)
    if bucket_response.status_code in (400, 404):
        bucket_response = httpx.post(
            f"{base}/storage/v1/bucket",
            headers={**headers, "Content-Type": "application/json"},
            json={"id": bucket, "name": bucket, "public": False, "file_size_limit": 536870912},
            timeout=30.0,
        )
    bucket_response.raise_for_status()
    raw = build_archive(database, audio_dir, media_dir)
    response = httpx.post(
        f"{base}/storage/v1/object/{bucket}/{name}",
        headers={**headers, "Content-Type": "application/zip", "x-upsert": "true"},
        content=raw,
        timeout=120.0,
    )
    response.raise_for_status()
    return {"configured": True, "uploaded": len(raw), "bucket": bucket, "object": name}
