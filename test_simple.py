"""
简化测试：验证 LLM 集成工作正常
"""

import asyncio
import os

# 直接从环境变量读取，不重新赋值
API_KEY = os.environ.get("LLM_API_KEY", "") or os.getenv("LLM_API_KEY", "")
API_URL = os.environ.get("LLM_API_URL", "") or os.getenv("LLM_API_URL", "")

from fih_emergence.llm import get_manager_client, get_proposer_client, get_worker_client, get_auditor_client


async def simple_test():
    print("=" * 50)
    print("FIH Emergence - 简化测试")
    print("=" * 50)
    
    print(f"\n[环境变量]")
    print(f"  LLM_API_KEY: {API_KEY[:15]}...")
    print(f"  LLM_API_URL: {API_URL}")
    
    # ===== 测试 Manager =====
    print("\n[1] Manager 测试...")
    manager = get_manager_client()
    response = await manager.complete("用一句话介绍你的角色")
    print(f"  → {response.content[:100]}")
    
    # ===== 测试 Proposer =====
    print("\n[2] Proposer 测试...")
    proposer = get_proposer_client()
    response = await proposer.complete("列出3种经济增长因素")
    print(f"  → {response.content[:150]}...")
    
    # ===== 测试 Worker =====
    print("\n[3] Worker 测试...")
    worker = get_worker_client()
    response = await worker.complete("分析消费降级对经济的影响")
    print(f"  → {response.content[:150]}...")
    
    # ===== 测试 Auditor =====
    print("\n[4] Auditor 测试...")
    auditor = get_auditor_client()
    response = await auditor.complete("评估这个观点：经济需要转型")
    print(f"  → {response.content[:150]}...")
    
    print("\n" + "=" * 50)
    print("✅ 所有角色 LLM 调用测试通过!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(simple_test())