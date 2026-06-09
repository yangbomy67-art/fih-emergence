"""
FIH State - Global state definition for the multi-agent collaboration system.

Based on SPEC_DataStructures.md
"""

from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class Fact(BaseModel):
    """Fact: 硬边界 / 已验证真值。只读。"""
    id: str
    content: str
    source: str  # 来源：worker_audit / human_gate
    confidence: float = Field(ge=0, le=1)
    created_at: str


class Hint(BaseModel):
    """Hint: 环境原始输入"""
    id: str
    content: str
    source: str  # 来源：human_gate / system
    weight: float = Field(default=0.5, ge=0, le=1)
    created_at: str


class Intent(BaseModel):
    """Intent: 当前轮次自主声明的假设或方向"""
    id: str
    content: str
    type: Literal["待验证", "待探索", "待决策"]  # 三类 Intent
    supporting_facts: list[str] = Field(default_factory=list)  # 支撑 Fact IDs
    ei_score: float | None = None


class WorkerSubmission(BaseModel):
    """Worker 产出"""
    worker_id: str  # "worker_p" or "worker_n"
    insight: str
    next_intent_suggestions: list[str] = Field(default_factory=list)
    self_confidence: float = Field(ge=0, le=100)


class AuditResult(BaseModel):
    """Auditor 审计结果"""
    passed: bool
    scores_4d: dict[str, float] = Field(default_factory=dict)  # A/B/C/D
    result_ei: float | None = None
    fact_candidates: list[Fact] = Field(default_factory=list)
    hint_candidates: list[Hint] = Field(default_factory=list)
    valley_detected: bool = False
    valley_report: dict | None = None
    reason: str | None = None


class FIHState(TypedDict, total=False):
    """
    FIH 多智能体协作系统全局状态

    存储原则:
    - 累积字段 (追加): valley_signals, facts, hints, ei_tracking, human_intervention_log
    - 覆盖字段 (最新值): no_fact_rounds, consecutive_same_output, current_round
    """

    # =======================
    # 任务信息
    # =======================
    task_description: str
    mode: str  # 固定 "FULL"
    session_id: str
    current_round: int  # 当前轮次 (1, 2, 3, ...)
    max_iterations: int  # 最大轮次限制 (默认 20)

    # =======================
    # 黑板 (Facts/Hints/Intents)
    # =======================
    facts: list[dict]  # 已验证事实
    hints: list[dict]  # 环境输入
    intents: list[dict]  # 候选Intent列表 (每轮替换)

    # =======================
    # Worker 竞争结果 (固定2个 Worker，正反对抗)
    # =======================
    worker_submissions: list  # [Worker_P提交, Worker_N提交]
    worker_count: int  # 固定 2

    # =======================
    # Auditor 审计结果
    # =======================
    audit_result: dict | None  # 完整审计结果

    # =======================
    # Fact+ 执行状态
    # =======================
    fact_plus_executed: bool  # 本轮是否执行了 Fact+ 升格
    hints_promoted_to_facts: list  # 本轮从 Hint 升格为 Fact 的列表

    # =======================
    # Manager 决策结果
    # =======================
    winner_intent: dict | None  # 本轮胜出Intent
    next_intent_candidates: list  # 下一轮候选 Intent
    intent_ei_scores: list  # 每个候选的 intent EI 分数

    # =======================
    # 低谷检测 (累积存储)
    # =======================
    valley_detected: bool
    valley_signals: list  # 滑动窗口保留最近5轮
    valley_operation: str | None

    # =======================
    # Fact 冲突检测
    # =======================
    fact_conflicts: list[dict]  # 含 resolved 标记

    # =======================
    # 人工介入
    # =======================
    needs_human: bool  # 是否需要人工介入
    human_intervention_reason: str  # 介入原因
    human_input: dict | None  # 人工输入
    human_action_taken: str | None  # 最终执行的人工操作

    # =======================
    # 历史计数器
    # =======================
    no_fact_rounds: int  # 连续无 Fact+ 轮次
    consecutive_same_output: int  # 连续产出完全相同的轮次

    # =======================
    # 产出整合
    # =======================
    main_text_parts: list
    appendix_parts: list
    final_output: str | None

    # =======================
    # 控制标志
    # =======================
    task_complete: bool
    is_first_round: bool  # 是否首轮
    task_boundary_status: str  # "open" | "closed"


def create_initial_state(
    session_id: str,
    task_description: str,
    max_iterations: int = 20,
) -> FIHState:
    """创建初始状态"""
    return {
        "task_description": task_description,
        "mode": "FULL",
        "session_id": session_id,
        "current_round": 1,
        "max_iterations": max_iterations,
        "facts": [],
        "hints": [],
        "intents": [],
        "worker_submissions": [],
        "worker_count": 2,
        "audit_result": None,
        "fact_plus_executed": False,
        "hints_promoted_to_facts": [],
        "winner_intent": None,
        "next_intent_candidates": [],
        "intent_ei_scores": [],
        "valley_detected": False,
        "valley_signals": [],
        "valley_operation": None,
        "fact_conflicts": [],
        "needs_human": False,
        "human_intervention_reason": "",
        "human_input": None,
        "human_action_taken": None,
        "no_fact_rounds": 0,
        "consecutive_same_output": 0,
        "main_text_parts": [],
        "appendix_parts": [],
        "final_output": None,
        "task_complete": False,
        "is_first_round": True,
        "task_boundary_status": "open",
    }
