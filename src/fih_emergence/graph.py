"""
LangGraph Workflow - 工作流编排（简化版）

基于 SPEC_流程.md §完整流程（九步）
Flow: Manager → Proposer → Auditor → Workers (P/N) → Auditor → END
"""

from langgraph.graph import END, StateGraph

from fih_emergence.state import FIHState, create_initial_state


def node_manager_start(state: FIHState) -> FIHState:
    """Manager: 发布主题（Round 1）"""
    state["current_round"] = 1
    return state


def node_proposer_generate(state: FIHState) -> FIHState:
    """Proposer: 多草稿生成"""
    state["intents"] = [{"id": "I1", "content": "Generated Intent", "type": "待探索"}]
    return state


def node_auditor_pre(state: FIHState) -> FIHState:
    """Auditor: 事前审计"""
    return state


def node_worker_p(state: FIHState) -> FIHState:
    """Worker_P: 产出 Insight"""
    submissions = state.get("worker_submissions", [])
    submissions.append({
        "worker_id": "worker_p",
        "insight": "Positive insight from Worker P",
        "self_confidence": 75.0,
    })
    state["worker_submissions"] = submissions
    return state


def node_worker_n(state: FIHState) -> FIHState:
    """Worker_N: 产出 Insight"""
    submissions = state.get("worker_submissions", [])
    submissions.append({
        "worker_id": "worker_n",
        "insight": "Negative insight from Worker N",
        "self_confidence": 70.0,
    })
    state["worker_submissions"] = submissions
    return state


def node_auditor_post(state: FIHState) -> FIHState:
    """Auditor: 事后审计"""
    state["audit_result"] = {"passed": True, "result_ei": 12.0}
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