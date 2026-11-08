from __future__ import annotations

import json
import os
import sqlite3
from typing import Callable

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=20, max_length=1000)
    auth: str = Field(min_length=8, max_length=500)


class PushSubscription(BaseModel):
    endpoint: str = Field(min_length=20, max_length=3000)
    keys: PushKeys


def install_notification_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """CREATE TABLE IF NOT EXISTS push_subscriptions(
        endpoint TEXT PRIMARY KEY,p256dh TEXT NOT NULL,auth TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS notification_outbox(
        id TEXT PRIMARY KEY,event_type TEXT NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,url TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',attempts INTEGER NOT NULL DEFAULT 0,last_error TEXT,
        created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_notification_pending ON notification_outbox(status,created_at);
        """
    )


def enqueue_notification(
    connection: sqlite3.Connection,
    new_id: Callable[[], str],
    now: Callable[[], str],
    event_type: str,
    body: str,
    url: str = "/v2-preview/",
) -> str:
    install_notification_schema(connection)
    notification_id, timestamp = new_id(), now()
    connection.execute(
        "INSERT INTO notification_outbox VALUES(?,?,?,?,?,'pending',0,NULL,?,?)",
        (notification_id, event_type, "沈砚", body[:500], url, timestamp, timestamp),
    )
    return notification_id


def build_router(db_factory: Callable[[], sqlite3.Connection], now: Callable[[], str], new_id: Callable[[], str]) -> APIRouter:
    router = APIRouter(prefix="/api/notifications", tags=["notifications"])

    @router.get("/vapid-public-key")
    def public_key() -> dict:
        value = os.getenv("VAPID_PUBLIC_KEY", "").strip()
        if not value:
            raise HTTPException(status_code=503, detail="推送服务尚未配置 VAPID 公钥")
        return {"publicKey": value}

    @router.post("/subscribe", status_code=201)
    def subscribe(body: PushSubscription) -> dict:
        timestamp = now()
        with db_factory() as connection:
            install_notification_schema(connection)
            connection.execute(
                """INSERT INTO push_subscriptions VALUES(?,?,?,1,?,?)
                ON CONFLICT(endpoint) DO UPDATE SET p256dh=excluded.p256dh,auth=excluded.auth,active=1,updated_at=excluded.updated_at""",
                (body.endpoint, body.keys.p256dh, body.keys.auth, timestamp, timestamp),
            )
        return {"subscribed": True}

    @router.delete("/subscribe")
    def unsubscribe(body: PushSubscription) -> dict:
        with db_factory() as connection:
            install_notification_schema(connection)
            connection.execute("UPDATE push_subscriptions SET active=0,updated_at=? WHERE endpoint=?", (now(), body.endpoint))
        return {"subscribed": False}

    @router.post("/dispatch")
    def dispatch(x_scheduler_token: str | None = Header(default=None)) -> dict:
        expected = os.getenv("SCHEDULER_TOKEN", "").strip()
        if not expected or x_scheduler_token != expected:
            raise HTTPException(status_code=401, detail="调度凭证无效")
        private_key, subject = os.getenv("VAPID_PRIVATE_KEY", "").strip(), os.getenv("VAPID_SUBJECT", "mailto:owner@example.com").strip()
        if not private_key:
            raise HTTPException(status_code=503, detail="推送服务尚未配置 VAPID 私钥")
        try:
            from pywebpush import WebPushException, webpush
        except ImportError as exc:
            raise HTTPException(status_code=503, detail="服务端尚未安装 Web Push 依赖") from exc
        sent = failed = 0
        with db_factory() as connection:
            install_notification_schema(connection)
            jobs = connection.execute("SELECT * FROM notification_outbox WHERE status='pending' ORDER BY created_at LIMIT 20").fetchall()
            subscriptions = connection.execute("SELECT * FROM push_subscriptions WHERE active=1").fetchall()
            for job in jobs:
                payload = json.dumps({"title": job["title"], "body": job["body"], "url": job["url"], "type": job["event_type"]}, ensure_ascii=False)
                errors: list[str] = []
                for subscription in subscriptions:
                    try:
                        webpush(
                            subscription_info={"endpoint": subscription["endpoint"], "keys": {"p256dh": subscription["p256dh"], "auth": subscription["auth"]}},
                            data=payload,
                            vapid_private_key=private_key,
                            vapid_claims={"sub": subject},
                            timeout=20,
                        )
                        sent += 1
                    except WebPushException as exc:
                        errors.append(str(exc)[:500])
                        if getattr(exc, "response", None) is not None and exc.response.status_code in {404, 410}:
                            connection.execute("UPDATE push_subscriptions SET active=0,updated_at=? WHERE endpoint=?", (now(), subscription["endpoint"]))
                status = "sent" if subscriptions and not errors else ("pending" if not subscriptions else "failed")
                connection.execute(
                    "UPDATE notification_outbox SET status=?,attempts=attempts+1,last_error=?,updated_at=? WHERE id=?",
                    (status, "; ".join(errors) or ("没有有效订阅" if not subscriptions else None), now(), job["id"]),
                )
                failed += len(errors)
        return {"jobs": len(jobs), "sent": sent, "failed": failed}

    return router
