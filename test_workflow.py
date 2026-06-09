"""
快速测试脚本：运行完整工作流一轮

用途：验证各角色 + LLM 集成是否正常工作
"""

import asyncio
import os

# 设置 API Key
os.environ["LLM_API_KEY"] = os.getenv("LLM_API_KEY", "***")

from fih_emergence.config import get_config, reload_config
from fih_emergence.roles import Manager, Proposer, Worker, Auditor
from fih_emergence.state import create_initial_state


async def run_round_1():
    """运行 Round 1"""
    print("=" * 50)
    print("FIH Emergence - Round 1 测试")
    print("=" * 50)
    
    # 加载配置
    config = reload_config("config.yaml")
    print(f"\n[配置] max_rounds: {config.task.max_rounds}")
    
    # 创建初始状态
    topic = "分析中国经济增长趋势"
    state = create_initial_state("test-session", topic)
    state["facts"] = [
        {"id": "F1", "content": "2024年GDP增长5%", "source": "human", "confidence": 0.9},
        {"id": "F2", "content": "消费增速放缓至3%", "source": "human", "confidence": 0.85},
    ]
    state["hints"] = [
        {"id": "H1", "content": "关注年轻人消费观变化", "source": "human", "weight": 0.6},
    ]
    
    print(f"\n[主题] {topic}")
    print(f"[Facts] {len(state['facts'])} 条")
    print(f"[Hints] {len(state['hints'])} 条")
    
    # ===== 步骤1: Manager 发布主题 =====
    print("\n[Step 1] Manager 发布主题...")
    manager = Manager()
    state = await manager.initiate_round(state, topic, ["2024年GDP增长5%"], ["消费增速放缓"])
    print(f"  → 状态更新完成")
    
    # ===== 步骤2: Proposer 生成 Intent =====
    print("\n[Step 2] Proposer 生成 Intent 候选...")
    proposer = Proposer()
    result = await proposer.generate_intents(state)
    intents = result.get("intents", [])
    print(f"  → 生成 {len(intents)} 个 Intent 候选")
    state["intents"] = intents
    
    # ===== 步骤3: Auditor 事前审计 =====
    print("\n[Step 3] Auditor 事前审计...")
    auditor = Auditor()
    if intents:
        intent = intents[0]
        audit_result = await auditor.pre_audit_intent(intent, state["facts"])
        print(f"  → 审计结果: passed={audit_result['passed']}")
    
    # ===== 步骤4: Worker_P 产出 Insight =====
    print("\n[Step 4] Worker_P 产出 Insight...")
    worker_p = Worker("worker_p")
    if intents:
        result_p = await worker_p.generate_insight(state, intents[0])
        print(f"  → self_confidence: {result_p.get('self_confidence', 0):.1f}%")
        state["worker_submissions"] = state.get("worker_submissions", [])
        state["worker_submissions"].append({
            "worker_id": "worker_p",
            "insight": result_p.get("insight", ""),
            "self_confidence": result_p.get("self_confidence", 0),
        })
    
    # ===== 步骤5: Worker_N 产出 Insight =====
    print("\n[Step 5] Worker_N 产出 Insight...")
    worker_n = Worker("worker_n")
    if intents:
        result_n = await worker_n.generate_insight(state, intents[0])
        print(f"  → self_confidence: {result_n.get('self_confidence', 0):.1f}%")
        state["worker_submissions"].append({
            "worker_id": "worker_n",
            "insight": result_n.get("insight", ""),
            "self_confidence": result_n.get("self_confidence", 0),
        })
    
    # ===== 步骤6: Auditor 事后审计 =====
    print("\n[Step 6] Auditor 事后审计...")
    if state["worker_submissions"]:
        for sub in state["worker_submissions"]:
            post_result = await auditor.post_audit_insight(
                sub["worker_id"],
                sub.get("insight", "测试Insight"),
                state["facts"]
            )
            print(f"  → {sub['worker_id']}: result_ei={post_result['result_ei']}, passed={post_result['passed']}")
    
    # ===== 步骤7: Manager 汇总裁决 =====
    print("\n[Step 7] Manager 汇总裁决...")
    decision = await manager.decide_next(state)
    print(f"  → 决策: {decision.get('next_action', 'UNKNOWN')}")
    print(f"  → 下一轮: {decision.get('next_round', 1)}")
    
    # ===== 步骤8: 检查 4 条件 =====
    print("\n[Step 8] Manager 检查 4 条件...")
    triggered, reason = manager.check_interrupt_conditions(state)
    print(f"  → 触发中断: {triggered}, 原因: {reason or '无'}")
    
    print("\n" + "=" * 50)
    print("Round 1 完成!")
    print("=" * 50)
    
    return state


if __name__ == "__main__":
    asyncio.run(run_round_1())