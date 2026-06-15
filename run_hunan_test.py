#!/usr/bin/env python3
"""FIH Emergence 测试运行脚本 - 湖南产业全方位调查"""

import asyncio
import json
import os
import sys

# 加载 .env
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, "src")

from fih_emergence.graph import run_session


async def main():
    session_id = "hunan-industry-survey"
    topic = "湖南产业全方位调查"
    initial_facts = [
        "2026年一季度湖南GDP 13,156.10亿元、同比增长3.0%",
        "湖南GDP增速为中部六省最低、全国倒数第二",
    ]
    max_iterations = 5

    print(f"=== FIH Emergence 测试 ===")
    print(f"主题: {topic}")
    print(f"初始 Facts: {len(initial_facts)} 条")
    print(f"最大轮次: {max_iterations}")
    print(f"=========================\n")

    result = await run_session(
        session_id=session_id,
        task_description=topic,
        initial_facts=initial_facts,
        max_iterations=max_iterations,
    )

    # 输出摘要
    print("\n=== 运行结果 ===")
    print(f"最终轮次: {result.get('current_round')}")
    print(f"任务完成: {result.get('task_complete')}")
    print(f"Facts 数量: {len(result.get('facts', []))}")
    print(f"Hints 数量: {len(result.get('hints', []))}")
    print(f"涌现检测: {result.get('emergence_detected')}")
    print(f"低谷检测: {result.get('valley_detected')}")

    # 写入结果文件
    results_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(results_dir, exist_ok=True)
    
    result_path = os.path.join(results_dir, f"{session_id}.json")
    # 序列化（排除不可JSON化的字段）
    serializable = {k: v for k, v in result.items() if k != "rounds_history"}
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n结果已写入: {result_path}")

    # rounds_history 也保存
    history_path = os.path.join(results_dir, f"{session_id}_history.json")
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(result.get("rounds_history", []), f, ensure_ascii=False, indent=2, default=str)
    print(f"轮次历史已写入: {history_path}")

    # Markdown 报告路径
    md_path = os.path.join(results_dir, f"{session_id}.md")
    if os.path.exists(md_path):
        print(f"Markdown 报告已生成: {md_path}")
    else:
        print("Markdown 报告未生成")


if __name__ == "__main__":
    asyncio.run(main())
