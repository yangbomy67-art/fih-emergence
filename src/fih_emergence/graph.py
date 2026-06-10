"""
LangGraph Workflow - 工作流编排（LLM版）

基于 SPEC_流程.md §完整流程（九步）
Flow: Manager → Proposer → Auditor → Workers (P/N) → Auditor → END
"""

import asyncio
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
    """Manager: 发布主题（Round 1）"""
    state["current_round"] = 1
    task = state.get("task_description", "")
    # 可调用 Manager 发布主题
    return state


async def node_proposer_generate(state: FIHState) -> FIHState:
    """Proposer: 多草稿生成"""
    proposer = get_proposer()
    result = await proposer.generate_intents(state)
    state["intents"] = result.get("intents", [])
    return state


async def node_auditor_pre(state: FIHState) -> FIHState:
    """Auditor: 事前审计"""
    # 简化：不做过滤，直接通过
    return state


async def node_worker_p(state: FIHState) -> FIHState:
    """Worker_P: 产出 Insight"""
    worker = get_worker_p()
    intents = state.get("intents", [])
    intent = intents[0] if intents else {"id": "I1", "content": "默认 Intent"}
    
    result = await worker.generate_insight(
        state=state,
        intent=intent,
    )
    
    submissions = state.get("worker_submissions", [])
    submissions.append({
        "worker_id": "worker_p",
        "insight": result.get("insight", ""),
        "self_confidence": result.get("self_confidence", 75.0),
        "next_intent_suggestions": result.get("next_intent_suggestions", []),
    })
    state["worker_submissions"] = submissions
    return state


async def node_worker_n(state: FIHState) -> FIHState:
    """Worker_N: 产出 Insight"""
    worker = get_worker_n()
    intents = state.get("intents", [])
    intent = intents[0] if intents else {"id": "I1", "content": "默认 Intent"}
    
    result = await worker.generate_insight(
        state=state,
        intent=intent,
    )
    
    submissions = state.get("worker_submissions", [])
    submissions.append({
        "worker_id": "worker_n",
        "insight": result.get("insight", ""),
        "self_confidence": result.get("self_confidence", 70.0),
        "next_intent_suggestions": result.get("next_intent_suggestions", []),
    })
    state["worker_submissions"] = submissions
    return state


async def node_auditor_post(state: FIHState) -> FIHState:
    """Auditor: 事后审计"""
    auditor = get_auditor()
    submissions = state.get("worker_submissions", [])
    
    # 简化：只审计第一个 submission
    if submissions:
        sub = submissions[0]
        result = await auditor.post_audit_insight(
            worker_id=sub.get("worker_id", "unknown"),
            insight=sub.get("insight", ""),
            facts=state.get("facts", []),
        )
        state["audit_result"] = result
    
    # 检查是否完成（简化：总是完成）
    state["task_complete"] = True
    return state


def create_graph() -> StateGraph:
    """创建 LangGraph 工作流（线性）"""
    graph = StateGraph(FIHState)

    # 添加节点
    graph.add_node("manager", node_manager_start)
    graph.add_node("proposer", node_proposer_generate)
    graph.add_node("auditor_pre", node_auditor_pre)
    graph.add_node("worker_p", node_worker_p)
    graph.add_node("worker_n", node_worker_n)
    graph.add_node("auditor_post", node_auditor_post)

    # 设置入口
    graph.set_entry_point("manager")

    # 线性流程
    graph.add_edge("manager", "proposer")
    graph.add_edge("proposer", "auditor_pre")
    graph.add_edge("auditor_pre", "worker_p")
    graph.add_edge("worker_p", "worker_n")
    graph.add_edge("worker_n", "auditor_post")
    graph.add_edge("auditor_post", END)

    return graph


def compile_graph():
    """编译工作流"""
    return create_graph().compile()


workflow = compile_graph()


async def run_session(
    session_id: str,
    task_description: str,
    initial_facts: list[str] = None,
    initial_hints: list[str] = None,
    max_iterations: int = 20,
) -> dict:
    """运行完整会话"""
    initial_state = create_initial_state(
        session_id=session_id,
        task_description=task_description,
        max_iterations=max_iterations,
    )
    
    final_state = await workflow.ainvoke(initial_state)
    return final_state