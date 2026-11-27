from __future__ import annotations

import os
from typing import Any, Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


SKILL_VERSION = "0.0.3"
BASE_URL = "https://a.y.qq.com"


class QQMusicRequest(BaseModel):
    action: Literal["search", "daily", "radio", "charts", "chart_detail", "playlist", "report"]
    keyword: str = Field(default="", max_length=100)
    item_id: int | None = None
    page: int = Field(default=0, ge=0, le=20)
    period: Literal["d", "w", "m"] = "m"


def build_router() -> APIRouter:
    router = APIRouter(prefix="/api/qqmusic", tags=["qqmusic"])

    @router.get("/status")
    def status() -> dict[str, bool]:
        return {"configured": bool(os.getenv("QQMUSIC_API_KEY", "").strip())}

    @router.post("/query")
    async def query(body: QQMusicRequest) -> dict[str, Any]:
        api_key = os.getenv("QQMUSIC_API_KEY", "").strip()
        if not api_key:
            raise HTTPException(status_code=503, detail="尚未配置 QQ 音乐 API Key")

        path: str
        params: dict[str, Any]
        if body.action == "search":
            if not body.keyword.strip():
                raise HTTPException(status_code=422, detail="请输入歌名或歌手")
            path, params = "/discover/search", {"keyword": body.keyword.strip(), "type": "0", "page": body.page}
        elif body.action == "daily":
            path, params = "/discover/daily-mix", {}
        elif body.action == "radio":
            path, params = "/discover/radio", {}
        elif body.action == "charts":
            path, params = "/charts", {}
        elif body.action == "chart_detail":
            if body.item_id is None:
                raise HTTPException(status_code=422, detail="缺少榜单编号")
            path, params = "/charts/detail", {"topId": body.item_id, "page": body.page}
        elif body.action == "playlist":
            if body.item_id is None:
                raise HTTPException(status_code=422, detail="缺少歌单编号")
            path, params = "/playlists/detail", {"dissId": body.item_id, "page": body.page}
        else:
            path, params = "/me/report", {"timeKey": body.period}

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(25, connect=10)) as client:
                response = await client.post(
                    f"{BASE_URL}{path}",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"params": params, "comm": {"skill_version": SKILL_VERSION}},
                )
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status_code=502, detail="QQ 音乐暂时无法连接") from exc
        if response.is_error or payload.get("ret") not in (None, 0) or payload.get("sub_ret") not in (None, 0):
            message = payload.get("msg") or "QQ 音乐请求失败，请检查 Key"
            raise HTTPException(status_code=502, detail=message)
        return payload

    return router
