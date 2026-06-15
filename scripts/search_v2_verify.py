"""搜索 v2 实搜验证 - API Key 从环境变量读取"""
import asyncio, os, sys
sys.path.insert(0, "/home/bo/fih-emergence/src")

from fih_emergence.tools.network_search import NetworkSearchTool

async def main():
    api_key = os.environ["BAIDU_API_KEY"]
    tool = NetworkSearchTool(api_key=api_key)
    queries = [
        "2026年一季度中国GDP增速 产业结构",
        "中国新能源汽车 2026 销量 市场渗透率",
        "AI大模型 2026 最新进展",
    ]
    for q in queries:
        print(f"查询: {q}")
        print("-" * 50)
        r = await tool.search(q, site_filter=["stats.gov.cn", "news.cn", "gov.cn", "edu.cn"])
        
        v1 = f"{r[0].title}: {r[0].content[:200]}" if r else "(无)"
        
        print(f"v2 结果: {len(r)} 条")
        for i, x in enumerate(r, 1):
            print(f"  [{i}] 权威度:{x.authority} {x.domain}")
            print(f"       {x.title[:60]}")
        print(f"v1 模拟: {v1[:100]}...")
        print(f"提升: {len(r)}源 vs 1源, {sum(len(x.content) for x in r)}字 vs ~200字")
        print()

asyncio.run(main())
