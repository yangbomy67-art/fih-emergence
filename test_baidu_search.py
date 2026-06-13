#!/usr/bin/env python3
"""联调测试: 百度搜索 API"""
import asyncio
import os
import sys

# 设置百度 API Key
os.environ["BAIDU_API_KEY"] = "BAIDU_API_KEY_FROM_ENV"

sys.path.insert(0, 'src')

from fih_emergence.graph import run_session

async def main():
    print("=== 联调测试: 百度搜索 API ===")
    print()
    
    result = await run_session(
        session_id='test-baidu-v2',
        task_description='湖南产业全方位调查',
        initial_facts=[
            '2026年一季度湖南GDP 13,156.10亿元、同比增长3.0%，湖南GDP增速为中部六省最低、全国倒数第二'
        ],
        max_iterations=2
    )
    
    print()
    print("=== 运行完成 ===")
    print(f"完成状态: {result.get('status')}")
    print(f"最终轮次: {result.get('current_round')}")
    print(f"EI: {result.get('final_ei')}")
    
    # 保存结果
    with open('results/test-baidu-search.md', 'w') as f:
        f.write(f"# 联调测试结果\n\n")
        f.write(f"状态: {result.get('status')}\n\n")
        f.write(f"轮次: {result.get('current_round')}\n\n")
        f.write(f"EI: {result.get('final_ei')}\n\n")
        f.write("## 黑板内容\n\n")
        for fact in result.get('blackboard', {}).get('facts', []):
            f.write(f"- {fact}\n")

if __name__ == "__main__":
    asyncio.run(main())