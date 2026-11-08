from __future__ import annotations

import json
import sqlite3
from typing import Callable, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

ProfileSubject = Literal["shenyan", "user"]
PROFILE_CATEGORIES = ("identity", "appearance", "personality", "relationship", "habits", "life")


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=40)
    categories: dict[str, str]


def install_profile_schema(connection: sqlite3.Connection, now: Callable[[], str], seed: bool = True) -> None:
    connection.execute(
        """CREATE TABLE IF NOT EXISTS character_profiles(
        subject TEXT PRIMARY KEY,display_name TEXT NOT NULL,categories_json TEXT NOT NULL,updated_at TEXT NOT NULL)"""
    )
    if seed:
        empty = json.dumps({key: "" for key in PROFILE_CATEGORIES}, ensure_ascii=False)
        connection.execute("INSERT OR IGNORE INTO character_profiles VALUES('shenyan','沈砚',?,?)", (empty, now()))
        connection.execute("INSERT OR IGNORE INTO character_profiles VALUES('user','陈钰',?,?)", (empty, now()))


def profile_dict(row: sqlite3.Row) -> dict:
    return {"subject": row["subject"], "displayName": row["display_name"], "categories": json.loads(row["categories_json"]), "updatedAt": row["updated_at"]}


def profile_prompt(connection: sqlite3.Connection, now: Callable[[], str]) -> list[str]:
    install_profile_schema(connection, now)
    output: list[str] = []
    labels = {"identity": "身份基础", "appearance": "外貌形象", "personality": "性格内核", "relationship": "关系相处", "habits": "习惯偏好", "life": "生活背景"}
    for row in connection.execute("SELECT * FROM character_profiles ORDER BY subject"):
        name, categories = row["display_name"], json.loads(row["categories_json"])
        for key in PROFILE_CATEGORIES:
            value = str(categories.get(key) or "").strip()
            if value:
                output.append(f"[档案/{name}/{labels[key]}] {value}")
    return output


def build_router(db_factory: Callable[[], sqlite3.Connection], now: Callable[[], str]) -> APIRouter:
    router = APIRouter(prefix="/api/profiles", tags=["profiles"])

    @router.get("")
    def list_profiles() -> list[dict]:
        with db_factory() as connection:
            install_profile_schema(connection, now)
            return [profile_dict(row) for row in connection.execute("SELECT * FROM character_profiles ORDER BY subject")]

    @router.put("/{subject}")
    def update_profile(subject: ProfileSubject, body: ProfileUpdate) -> dict:
        unknown = set(body.categories) - set(PROFILE_CATEGORIES)
        if unknown:
            raise HTTPException(status_code=400, detail=f"未知档案分类：{', '.join(sorted(unknown))}")
        categories = {key: str(body.categories.get(key) or "").strip()[:3000] for key in PROFILE_CATEGORIES}
        with db_factory() as connection:
            install_profile_schema(connection, now)
            connection.execute(
                "UPDATE character_profiles SET display_name=?,categories_json=?,updated_at=? WHERE subject=?",
                (body.display_name.strip(), json.dumps(categories, ensure_ascii=False), now(), subject),
            )
            row = connection.execute("SELECT * FROM character_profiles WHERE subject=?", (subject,)).fetchone()
        return profile_dict(row)

    return router
