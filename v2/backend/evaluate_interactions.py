"""固定互动回归集。只有显式运行时才调用模型，不影响正常服务。"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.persona import build_system_prompt, detect_scene

ROOT = Path(__file__).parent


async def main() -> None:
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("请只在安全环境变量中设置 DEEPSEEK_API_KEY")
    cases = json.loads((ROOT / "interaction_cases.json").read_text(encoding="utf-8"))
    results = []
    async with httpx.AsyncClient(timeout=90) as client:
        for case in cases:
            scene = detect_scene(case["input"])
            response = await client.post(
                os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions"),
                headers={"Authorization": f"Bearer {key}"},
                json={"model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"), "temperature": 0.2, "messages": [
                    {"role": "system", "content": build_system_prompt(scene, [])}, {"role": "user", "content": case["input"]}
                ]},
            )
            response.raise_for_status()
            answer = response.json()["choices"][0]["message"]["content"]
            results.append({**case, "detectedScene": scene.name, "answer": answer})
        judge = await client.post(
            os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions"),
            headers={"Authorization": f"Bearer {key}"},
            json={"model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"), "temperature": 0, "response_format": {"type": "json_object"}, "messages": [{"role": "user", "content": """你是严格的角色互动回归评审。逐项结合 must/avoid 评估回答，给 naturalness、intimacy、emotion、consistency、nonMechanical、notOverCompliant、notArgumentative 七项 0-10 分，并给一句 issue。只返回 JSON：{\"scores\":[{\"id\":\"A\",\"naturalness\":0,...,\"issue\":\"\"}],\"overall\":0}。数据：\n""" + json.dumps(results, ensure_ascii=False)}]},
        )
        judge.raise_for_status()
        scores = json.loads(judge.json()["choices"][0]["message"]["content"])
    report = {"createdAt": datetime.now(timezone.utc).isoformat(), "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"), "results": results, "evaluation": scores}
    path = ROOT / "data" / "interaction-evaluation-latest.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    asyncio.run(main())
