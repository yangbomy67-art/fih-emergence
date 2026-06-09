"""
Human Gate - 人工网关客户端

Based on SPEC_角色.md §Human Gate

Architecture:
- 双形态：CLI + Hermes Skill
- 通信：HTTP API ↔ FIH Backend Service
- 方案：不依赖 Hermes，FIH 后端独立运行
"""

import asyncio
import json
from typing import Optional
import aiohttp


class HumanGateClient:
    """Human Gate 客户端"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id: Optional[str] = None

    async def start(self, topic: str, facts: list[str] = None, hints: list[str] = None) -> dict:
        """
        开始任务（Round 1）

        Args:
            topic: 任务主题
            facts: 初始 Facts
            hints: 初始 Hints
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/start",
                json={
                    "topic": topic,
                    "facts": facts or [],
                    "hints": hints or [],
                },
            ) as resp:
                data = await resp.json()
                if data.get("status") == "started":
                    self.session_id = data.get("session_id")
                return data

    async def status(self) -> dict:
        """查看状态"""
        if not self.session_id:
            return {"error": "No active session"}

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/status") as resp:
                return await resp.json()

    async def interrupt(self, operation: str, content: str = None) -> dict:
        """
        人工介入操作

        Args:
            operation: 操作类型 (fact+/fact-/hint+/修正intent/强制继续/强制完成/低谷穿越/回退)
            content: 操作内容
        """
        if not self.session_id:
            return {"error": "No active session"}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/interrupt",
                json={
                    "operation": operation,
                    "content": content,
                },
            ) as resp:
                return await resp.json()

    async def stop(self) -> dict:
        """强制终止任务"""
        if not self.session_id:
            return {"error": "No active session"}

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/stop") as resp:
                return await resp.json()

    async def force_complete(self) -> dict:
        """强制完成（输出最终成果）"""
        if not self.session_id:
            return {"error": "No active session"}

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/force-complete") as resp:
                return await resp.json()

    async def rollback(self, round_num: int) -> dict:
        """回退到第 N 轮"""
        if not self.session_id:
            return {"error": "No active session"}

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/rollback/{round_num}") as resp:
                return await resp.json()

    async def close(self):
        """关闭会话"""
        self.session_id = None


# =======================
# CLI 入口
# =======================

async def main():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="FIH Human Gate CLI")
    parser.add_argument("--url", default="http://localhost:8000", help="FIH Backend URL")
    parser.add_argument("command", choices=["start", "status", "interrupt", "stop", "force-complete", "rollback"])
    parser.add_argument("--topic", help="任务主题 (start)")
    parser.add_argument("--facts", nargs="*", help="初始 Facts")
    parser.add_argument("--hints", nargs="*", help="初始 Hints")
    parser.add_argument("--operation", help="操作类型 (interrupt)")
    parser.add_argument("--content", help="操作内容")
    parser.add_argument("--round", type=int, help="回退轮次 (rollback)")

    args = parser.parse_args()

    client = HumanGateClient(args.url)

    try:
        if args.command == "start":
            result = await client.start(args.topic, args.facts, args.hints)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == "status":
            result = await client.status()
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == "interrupt":
            result = await client.interrupt(args.operation, args.content)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == "stop":
            result = await client.stop()
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == "force-complete":
            result = await client.force_complete()
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == "rollback":
            result = await client.rollback(args.round)
            print(json.dumps(result, indent=2, ensure_ascii=False))

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())