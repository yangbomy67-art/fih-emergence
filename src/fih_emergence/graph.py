"""
LangGraph Workflow - 工作流编排（多轮版）

基于 SPEC_流程.md §完整流程（九步）
支持多轮循环
"""

import asyncio
from typing import List
from langgraph.graph import END, StateGraph

from fih_emergence.state import FIHState, create_initial_state
from fih_emergence.roles.proposer import Proposer
from fih_emergence.roles.manager import Manager
from fih_emergence.roles.worker import Worker
from fih_emergence.roles.auditor import Auditor


# 全局角色实例
_proposer = None
_manager = None
_auditor = None
_worker_p = None
_worker_n = None


def get_proposer() -> Proposer:
    global _proposer
    if _proposer is None:
        _proposer = Proposer()
    return _proposer


def get_manager() -> Manager:
    global _manager
    if _manager is None:
        _manager = Manager()
    return _manager


def get_auditor() -> Auditor:
    global _auditor
    if _auditor is None:
        _auditor = Auditor()
    return _auditor


def get_worker_p() -> Worker:
    global _worker_p
    if _worker_p is None:
        _worker_p = Worker("worker_p")
    return _worker_p


def get_worker_n() -> Worker:
    global _worker_n
    if _worker_n is None:
        _worker_n = Worker("worker_n")
    return _worker_n


def node_manager_start(state: FIHState) -> FIHState:
    """Manager: 发布主题"""
    return state


async def node_proposer_generate(state: FIHState) -> FIHState:
    """Proposer: 生成 Intent"""
    proposer = get_proposer()
    result = await proposer.generate_intents(state)
    state["intents"] = result.get("intents", [])
    return state


async def node_auditor_pre(state: FIHState) -> FIHState:
    """Auditor: 事前审计"""
    return state


async def node_worker_p(state: FIHState) -> FIHState:
    """Worker_P: 产出 Insight"""
    worker = get_worker_p()
    intents = state.get("intents", [])
    intent = intents[0] if intents else {"id": "I1", "content": "默认"}
    
    result = await worker.generate_insight(state=state, intent=intent)
    
    submissions = state.get("worker_submissions", [])
    submissions.append({
        "worker_id": "worker_p",
        "insight": result.get("insight", ""),
        "self_confidence": result.get("self_confidence", 75.0),
    })
    state["worker_submissions"] = submissions
    return state


async def node_worker_n(state: FIHState) -> FIHState:
    """Worker_N: 产出 Insight"""
    worker = get_worker_n()
    intents = state.get("intents", [])
    intent = intents[0] if intents else {"id": "I1", "content": "默认"}
    
    result = await worker.generate_insight(state=state, intent=intent)
    
    submissions = state.get("worker_submissions", [])
    submissions.append({
        "worker_id": "worker_n",
        "insight": result.get("insight", ""),
        "self_confidence": result.get("self_confidence", 70.0),
    })
    state["worker_submissions"] = submissions
    return state


async def node_auditor_post(state: FIHState) -> FIHState:
    """Auditor: 事后审计 + 低谷检测 + 置信度异常检测"""
    auditor = get_auditor()
    submissions = state.get("worker_submissions", [])
    
    # 收集双方的置信度
    pro_confidence = 0.0
    con_confidence = 0.0
    
    if submissions:
        for sub in submissions:
            worker_id = sub.get("worker_id", "")
            conf = sub.get("self_confidence", 0.0)
            if worker_id == "worker_p":
                pro_confidence = conf
            elif worker_id == "worker_n":
                con_confidence = conf
        
        # 审计第一个 submission
        sub = submissions[0]
        result = await auditor.post_audit_insight(
            worker_id=sub.get("worker_id", "unknown"),
            insight=sub.get("insight", ""),
            facts=state.get("facts", []),
        )
        state["audit_result"] = result
    else:
        result = {}
    
    # === 置信度异常检测（弱势方重产）===
    need_rebuttal = False
    rebuttal_type = ""
    
    if pro_confidence > 0 or con_confidence > 0:
        need_rebuttal, rebuttal_type = auditor.check_confidence_anomaly(
            pro_confidence, con_confidence
        )
    
    state["pro_confidence"] = pro_confidence
    state["con_confidence"] = con_confidence
    state["need_rebuttal"] = need_rebuttal
    state["rebuttal_type"] = rebuttal_type
    
    # === 低谷检测 ===
    current_round = state.get("current_round", 1)
    
    # 检查本轮是否产生新 Fact+
    new_facts_this_round = result.get("fact_candidates", []) if submissions else []
    has_new_fact = len(new_facts_this_round) > 0
    
    # 检查 EI 分数
    ei_score = result.get("result_ei", 0) if submissions else 0
    
    # 更新低谷信号
    valley_signals = state.get("valley_signals", [])
    valley_signals.append({
        "round": current_round,
        "has_new_fact": has_new_fact,
        "ei_score": ei_score,
    })
    # 保留最近 5 轮
    valley_signals = valley_signals[-5:]
    state["valley_signals"] = valley_signals
    
    # 计算连续无新 Fact 轮次
    no_fact_rounds = 0
    for sig in reversed(valley_signals):
        if not sig.get("has_new_fact", False):
            no_fact_rounds += 1
        else:
            break
    state["no_fact_rounds"] = no_fact_rounds
    
    # === 产出重复检测 ===
    # 连续 2 轮产出相同 → 人工介入
    duplicate_detected = False
    duplicate_operation = "none"
    
    # 获取本轮产出
    current_insights = [s.get("insight", "")[:100] for s in submissions]  # 取前100字符比较
    
    if len(current_insights) > 0 and len(valley_signals) >= 2:
        # 检查上一轮的产出
        prev_round = None
        for sig in reversed(valley_signals[:-1]):
            if "insight" in sig:
                prev_round = sig
                break
        
        if prev_round and "insight" in prev_round:
            prev_insight = prev_round.get("insight", "")[:100]
            curr_insight = current_insights[0] if current_insights else ""
            
            if prev_insight and curr_insight and prev_insight == curr_insight:
                duplicate_detected = True
                duplicate_operation = "force_human_intervention"
    
    state["duplicate_detected"] = duplicate_detected
    state["duplicate_operation"] = duplicate_operation
    
    # === Fact 冲突检��� ===
    # 黑板中 Fact 存在矛盾 → 人工介入
    fact_conflict_detected = False
    
    facts = state.get("facts", [])
    if len(facts) >= 2:
        # 简化：检查是否有矛盾的关键词（如"增长"vs"下降"同时出现）
        conflict_indicators = [
            ("增长", "下降"), ("增加", "减少"), ("上升", "下跌"),
            ("正面", "负面"), ("好", "坏"), ("盈利", "亏损"),
        ]
        content_all = " ".join(str(f) for f in facts).lower()
        for pos, neg in conflict_indicators:
            if pos in content_all and neg in content_all:
                fact_conflict_detected = True
                break
    
    state["fact_conflict_detected"] = fact_conflict_detected
    
    # 低谷类型判断
    valley_detected = False
    valley_type = ""
    valley_operation = "none"
    
    if no_fact_rounds >= 4:
        # 连续 4+ 轮无 Fact+ → 低谷穿越失败，触发人工介入
        valley_detected = True
        valley_type = "no_fact"
        valley_operation = "force_human_intervention"
    elif no_fact_rounds >= 3:
        # 连续 3 轮无 Fact+ → 尝试低谷穿越
        valley_detected = True
        valley_type = "no_fact"
        valley_operation = "valley_traverse"
    elif len(valley_signals) >= 3:
        # 检查 EI 持续低下
        recent_ei = [s.get("ei_score", 0) for s in valley_signals[-3:]]
        if all(ei < 10 for ei in recent_ei):
            valley_detected = True
            valley_type = "ei_low"
            # EI 持续低，尝试多样化
            valley_operation = "diversify_intent"
    
    # === 涌现成功检测 ===
    # 连续 2 轮 EI >= 15 → 任务完成
    emergence_detected = False
    emergence_operation = "none"
    
    if ei_score >= 15 and len(valley_signals) >= 2:
        # 检查前一轮是否也 >= 15
        prev_ei = valley_signals[-2].get("ei_score", 0) if len(valley_signals) >= 2 else 0
        if prev_ei >= 15:
            emergence_detected = True
            emergence_operation = "emergence_success"
    
    state["emergence_detected"] = emergence_detected
    state["emergence_operation"] = emergence_operation
    
    state["valley_detected"] = valley_detected
    state["valley_type"] = valley_type
    state["valley_operation"] = valley_operation
    
    return state


def create_graph() -> StateGraph:
    """创建工作流（单轮）"""
    graph = StateGraph(FIHState)

    graph.add_node("manager", node_manager_start)
    graph.add_node("proposer", node_proposer_generate)
    graph.add_node("auditor_pre", node_auditor_pre)
    graph.add_node("worker_p", node_worker_p)
    graph.add_node("worker_n", node_worker_n)
    graph.add_node("auditor_post", node_auditor_post)

    graph.set_entry_point("manager")
    graph.add_edge("manager", "proposer")
    graph.add_edge("proposer", "auditor_pre")
    graph.add_edge("auditor_pre", "worker_p")
    graph.add_edge("worker_p", "worker_n")
    graph.add_edge("worker_n", "auditor_post")
    graph.add_edge("auditor_post", END)

    return graph


def compile_graph():
    return create_graph().compile()


workflow = compile_graph()


async def run_session(
    session_id: str,
    task_description: str,
    initial_facts: list[str] = None,
    initial_hints: list[str] = None,
    max_iterations: int = 20,
) -> dict:
    """运行多轮会话（含终止条件和低谷穿越）"""
    # 初始化数据库
    from fih_emergence.database import init_db, create_session, update_session
    await init_db()
    
    # 创建会话
    await create_session(
        session_id=session_id,
        task_description=task_description,
        max_iterations=max_iterations,
    )
    
    # 创建初始状态并设置任务为 running
    state = create_initial_state(
        session_id=session_id,
        task_description=task_description,
        max_iterations=max_iterations,
    )
    await update_session(session_id, task_status="running")
    
    for round_num in range(1, max_iterations + 1):
        # 设置当前轮次
        state["current_round"] = round_num
        state["worker_submissions"] = []
        
        # 执行一轮工作流
        state = await workflow.ainvoke(state)
        
        print(f"Round {round_num}: valley_detected={state.get('valley_detected')}, operation={state.get('valley_operation')}")
        
        # === 检查终止条件 ===
        valley_detected = state.get("valley_detected", False)
        valley_operation = state.get("valley_operation", "none")
        
        # 终止条件 1: 达到 max_rounds
        if round_num >= max_iterations:
            print(f"  → 达到最大轮数 {max_iterations}，终止")
            await update_session(session_id, task_status="completed")
            break
        
        # 终止条件 2: 低谷穿越失败后，触发人工介入
        if valley_detected and valley_operation == "force_human_intervention":
            state["needs_human"] = True
            state["human_intervention_reason"] = f"低谷穿越失败 (valley_type={state.get('valley_type')})"
            print(f"  → 低谷穿越失败，触发人工介入: {state['human_intervention_reason']}")
            await update_session(session_id, task_status="paused", human_intervention_reason=state["human_intervention_reason"])
            break
        
        # 终止条件 3: 涌现成功（连续 2 轮 EI >= 15）
        emergence_detected = state.get("emergence_detected", False)
        emergence_operation = state.get("emergence_operation", "none")
        if emergence_detected and emergence_operation == "emergence_success":
            print(f"  → 涌现成功！连续 2 轮 EI >= 15，任务完成")
            state["task_complete"] = True
            state["task_boundary_status"] = "closed"
            await update_session(session_id, task_status="completed")
            break
        
        # 低谷穿越尝试：产出停滞后首次触发，继续下一轮
        if valley_detected and valley_operation == "valley_traverse":
            print(f"  → 检测到产出停滞，尝试低谷穿越（继续下一轮）")
            # 继续下一轮，让 Proposer 生成多样化 Intent
        
        # 低谷穿越：EI 持续低，尝试多���化（继续下一轮）
        if valley_detected and valley_operation == "diversify_intent":
            print(f"  → 检测到 EI 持续低，尝试低谷穿越（继续）")
        
        # === 弱势方重产处理 ===
        need_rebuttal = state.get("need_rebuttal", False)
        rebuttal_type = state.get("rebuttal_type", "")
        if need_rebuttal:
            print(f"  → 置信度异常检测: {rebuttal_type}，弱势方重产")
            state["rebuttal_triggered"] = True
        
        # === 产出重复检测 ===
        duplicate_detected = state.get("duplicate_detected", False)
        duplicate_operation = state.get("duplicate_operation", "none")
        if duplicate_detected and duplicate_operation == "force_human_intervention":
            state["needs_human"] = True
            state["human_intervention_reason"] = "连续 2 轮产出相同"
            print(f"  → 产出重复，触发人工介入")
            await update_session(session_id, task_status="paused", human_intervention_reason="连续 2 轮产出相同")
            break
        
        # === Fact 冲突检测 ===
        fact_conflict_detected = state.get("fact_conflict_detected", False)
        if fact_conflict_detected:
            state["needs_human"] = True
            state["human_intervention_reason"] = "Fact 存在矛盾"
            print(f"  → Fact 冲突，触发人工介入")
            # 设置为 paused 状态，等待人工介入
            await update_session(session_id, task_status="paused", human_intervention_reason="Fact 存在矛盾")
            break
        
        # === 保存到数据库 ===
        from fih_emergence.database import update_session
        import json
        await update_session(
            session_id,
            current_round=round_num,
            task_status="running",
            facts=json.dumps(state.get("facts", [])),
            hints=json.dumps(state.get("hints", [])),
            intents=json.dumps(state.get("intents", [])),
        )
    
    # 全部完成后标记
    state["task_complete"] = True
    state["task_boundary_status"] = "closed"
    
    # 保存最终状态
    from fih_emergence.database import update_session
    import json
    await update_session(
        session_id,
        current_round=state.get("current_round", 1),
        task_status="completed",
        facts=json.dumps(state.get("facts", [])),
        hints=json.dumps(state.get("hints", [])),
        intents=json.dumps(state.get("intents", [])),
    )
    return state