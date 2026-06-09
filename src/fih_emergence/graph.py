"""
LangGraph Workflow - 工作流编排

Based on SPEC_流程.md §完整流程（九步）

Flow:
  Manager → Proposer → Auditor → Workers (P/N) → Auditor → Manager (循环)
"""

from typing import Literal

from langgraph.graph import END, StateGraph
from langgraph.types import Command

from fih_emergence.state import FIHState, create_initial_state

# =======================
# Node Definitions
# =======================

def node_manager_start(state: FIHState) -> FIHState:
    """Manager: 发布主题（Round 1）"""
    # 由外部调用 initiate_round 填充
    return state


def node_proposer_generate(state: FIHState) -> FIHState:
    """Proposer: 多草稿生成"""
    # 调用 Proposer.generate_intents
    state["intents"] = []  # 待填充
    return state


def node_auditor_pre(state: FIHState) -> FIHState:
    """Auditor: 事前审计（Intent → Worker 门槛）"""
    # 调用 Auditor.pre_audit_intent
    return state


def node_worker_p(state: FIHState) -> FIHState:
    """Worker_P: 产出 Insight"""
    state["worker_submissions"] = state.get("worker_submissions", [])
    return state


def node_worker_n(state: FIHState) -> FIHState:
    """Worker_N: 产出 Insight"""
    state["worker_submissions"] = state.get("worker_submissions", [])
    return state


def node_auditor_post(state: FIHState) -> FIHState:
    """Auditor: 事后审计（Insight → 黑板 门槛）"""
    # 调用 Auditor.post_audit_insight
    state["audit_result"] = {}  # 待填充
    return state


def node_manager_decide(state: FIHState) -> Command[Literal["proposer", "__end__", "interrupt"]]:
    """
    Manager: 汇总裁决

    Returns:
        Command 决定下一步
    """
    # 调用 Manager.decide_next
    decision = state.get("_decision", "CONTINUE")

    if decision == "COMPLETE":
        state["task_complete"] = True
        state["task_boundary_status"] = "closed"
        return Command(goto=END)

    if decision == "INTERRUPT":
        return Command(goto="interrupt")

    # CONTINUE: 进入下一轮
    state["current_round"] += 1
    return Command(goto="proposer")


def node_manager_check_interrupt(state: FIHState) -> Command[Literal["interrupt", "worker_p"]]:
    """Manager: 检查是否触发中断"""
    # 调用 Manager.check_interrupt_conditions
    needs_interrupt = state.get("_needs_interrupt", False)

    if needs_interrupt:
        state["needs_human"] = True
        return Command(goto="interrupt")

    return Command(goto="worker_p")


def node_interrupt(state: FIHState) -> FIHState:
    """人工介入节点（LangGraph interrupt）"""
    # 这里会触发 interrupt，等待 Human Gate 响应
    state["needs_human"] = True
    return state


def node_manager_resume(state: FIHState) -> FIHState:
    """Manager: Resume 后恢复执行"""
    # Human Gate 响应后恢复
    state["needs_human"] = False
    return state


# =======================
# Graph Definition
# =======================

def create_graph() -> StateGraph:
    """创建 LangGraph 工作流"""
    graph = StateGraph(FIHState)

    # 添加节点
    graph.add_node("manager_start", node_manager_start)
    graph.add_node("proposer", node_proposer_generate)
    graph.add_node("auditor_pre", node_auditor_pre)
    graph.add_node("worker_p", node_worker_p)
    graph.add_node("worker_n", node_worker_n)
    graph.add_node("auditor_post", node_auditor_post)
    graph.add_node("manager_decide", node_manager_decide)
    graph.add_node("manager_check_interrupt", node_manager_check_interrupt)
    graph.add_node("interrupt", node_interrupt)
    graph.add_node("manager_resume", node_manager_resume)

    # 设置入口
    graph.set_entry_point("manager_start")

    # 定义边
    graph.add_edge("manager_start", "proposer")
    graph.add_edge("proposer", "auditor_pre")
    graph.add_edge("auditor_pre", "manager_check_interrupt")

    # 条件边：检查中断
    graph.add_conditional_edges(
        "manager_check_interrupt",
        node_manager_check_interrupt,
        {
            "interrupt": "interrupt",
            "worker_p": "worker_p",
        },
    )

    # 并行执行 Worker
    graph.add_edge("worker_p", "worker_n")
    graph.add_edge("worker_n", "auditor_post")

    # Manager 汇总裁决（循环）
    graph.add_edge("auditor_post", "manager_decide")

    # 条件边：决定下一步
    graph.add_conditional_edges(
        "manager_decide",
        node_manager_decide,
        {
            "proposer": "proposer",  # 继续下一轮
            "__end__": END,          # 完成任务
            "interrupt": "interrupt",  # 人工介入
        },
    )

    # 中断后恢复
    graph.add_edge("interrupt", "manager_resume")
    graph.add_edge("manager_resume", "proposer")

    return graph


# =======================
# Compile
# =======================

def compile_graph():
    """编译工作流"""
    graph = create_graph()
    return graph.compile()


# 全局编译后的图
workflow = compile_graph()


# =======================
# Entry Points
# =======================

async def run_session(
    session_id: str,
    task_description: str,
    initial_facts: list[str] = None,
    initial_hints: list[str] = None,
    max_iterations: int = 20,
) -> dict:
    """
    运行完整会话

    Args:
        session_id: 会话 ID
        task_description: 任务描述
        initial_facts: 初始 Facts
        initial_hints: 初始 Hints
        max_iterations: 最大轮次

    Returns:
        最终状态
    """
    # 创建初始状态
    initial_state = create_initial_state(
        session_id=session_id,
        task_description=task_description,
        max_iterations=max_iterations,
    )

    # 填充初始 Fact/Hint
    if initial_facts:
        initial_state["facts"] = [
            {"id": f"F{i+1}", "content": f, "source": "human_gate", "confidence": 1.0}
            for i, f in enumerate(initial_facts)
        ]
    if initial_hints:
        initial_state["hints"] = [
            {"id": f"H{i+1}", "content": h, "source": "human_gate", "weight": 0.5}
            for i, h in enumerate(initial_hints)
        ]

    # 运行工作流
    final_state = await workflow.ainvoke(initial_state)

    return final_state


async def resume_session(state: FIHState, human_input: dict) -> dict:
    """
    恢复中断的会话

    Args:
        state: 中断时的状态
        human_input: Human Gate 的输入

    Returns:
        恢复后的状态
    """
    # 更新状态中的 Human Input
    state["human_input"] = human_input
    state["human_action_taken"] = human_input.get("action")

    # 恢复执行
    # 注意：实际实现需要使用 graph.invoke(resume={...})
    # 这里简化处理
    state["needs_human"] = False

    # 继续执行
    final_state = await workflow.ainvoke(state)

    return final_state
