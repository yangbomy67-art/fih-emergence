"""
验证 LLM 配置脚本
"""

import asyncio
import os

# 优先使用环境变量，如果被污染则使用备用
API_KEY = os.getenv("FIH_API_KEY", "") or os.getenv("LLM_API_KEY", "")
API_URL = os.getenv("LLM_API_URL", "")

# 检测是否有效
if not API_KEY or len(API_KEY) < 20:
    # 使用备用 Key（仅用于测试）
    API_KEY = "sk-sp-***"

if not API_URL:
    API_URL = "https://aigw-gzgy2.cucloud.cn:8443/v1"

print(f"API Key: {API_KEY[:15]}...")
print(f"API URL: {API_URL}")

# 测试
from fih_emergence.llm import create_llm_client

async def test():
    client = create_llm_client(
        provider='custom',
        api_key=API_KEY,
        base_url=API_URL,
        model='MiniMax-M2.5'
    )
    resp = await client.complete("hi")
    if "[API Error" in resp.content:
        print(f"❌ 失败: {resp.content[:80]}")
    else:
        print(f"✅ 响应: {resp.content[:80]}...")

asyncio.run(test())
print("\n🎉 测试完成!")
