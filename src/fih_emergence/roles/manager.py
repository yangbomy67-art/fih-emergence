"""
Manager Role - 管理者

Based on SPEC_角色.md §MANAGER

Responsibilities:
1. 发布主题（含 Fact/Hint/Intent）
2. Intent 确认：EI 启发式评估 + 低谷识别 + Next Intent 建议
3. 汇总裁决：审核 fact_candidates、hint_candidates，执行低谷穿越策略
4. 唯一与 Human Gate 通信的接口
"""

from fih_emergence.llm import BaseLLMClient, get_manager_client
from fih_emergence.prompts import (
    MANAGER_INITIATE,
)
from fih_emergence.state import FIHState


class Manager:
    """FIH Manager 角色"""

    def __init__(self, llm_client: BaseLLMClient = None):
        # 如果没有提供 LLM 客户端，自动创建
        self.llm_client = llm_client or get_manager_client()

    async def initiate_round(
        self,
        state: FIHState,
        topic: str,
        initial_facts: list[str] = None,
        initial_hints: list[str] = None,
    ) -> dict:
        """
        Round 1: 初始化并发布主题

        Args:
            state: 当前状态
            topic: 任务主题
            initial_facts: 初始 Facts
            initial_hints: 初始 Hints
        """
        facts = initial_facts or []
        hints = initial_hints or []

        # 更新黑板
        state["facts"] = [{"id": f"F{i+1}", "content": f, "source": "human_gate"}
                          for i, f in enumerate(facts)]
        state["hints"] = [{"id": f"H{i+1}", "content": h, "source": "human_gate"}
                          for i, h in enumerate(hints)]
        state["task_description"] = topic
        state["is_first_round"] = False

        # 生成 Intent 确认prompt
        prompt = MANAGER_INITIATE.format(
            task_description=topic,
            current_round=state["current_round"],
            max_iterations=state["max_iterations"],
            facts=facts,
            hints=hints,
            intents="（待 Proposer 生成）",
        )

        return {
            "prompt": prompt,
            "state": state,
        }

    def check_interrupt_conditions(self, state: FIHState) -> tuple[bool, str]:
        """
        检查 4 条件是否触发

        Returns:
            (是否触发, 原因)
        """
        # 条件1: 置信度异常（单方面主导）
        if len(state.get("worker_submissions", [])) >= 2:
            submissions = state["worker_submissions"]
            p_conf = submissions[0].get("self_confidence", 0)
            n_conf = submissions[1].get("self_confidence", 0)

            # 正方主导: P>80% 且 N<30%
            if p_conf > 80 and n_conf < 30:
                return True, f"confidence_anomaly: P={p_conf}%, N={n_conf}%"
            # 反方主导: N>80% 且 P<30%
            if n_conf > 80 and p_conf < 30:
                return True, f"confidence_anomaly: P={p_conf}%, N={n_conf}%"

        # 条件2: 产出停滞（连续无 Fact+）
        if state.get("no_fact_rounds", 0) >= 3:
            return True, "output_stagnation: 连续3轮无Fact+"

        # 条件3: 产出重复
        if state.get("consecutive_same_output", 0) >= 2:
            return True, "output_repetition: 连续2轮产出相同"

        # 条件4: Fact 冲突
        if state.get("fact_conflicts"):
            return True, f"fact_conflict: {state['fact_conflicts']}"

        return False, ""

    async def decide_next(
        self,
        state: FIHState,
        audit_result: dict,
    ) -> str:
        """
        汇总裁决：决定下一步

        Returns:
            "CONTINUE" | "COMPLETE" | "INTERRUPT"
        """
        # 检查是否触发中断
        interrupt_triggered, reason = self.check_interrupt_conditions(state)
        if interrupt_triggered:
            state["needs_human"] = True
            state["human_intervention_reason"] = reason
            return "INTERRUPT"

        # 检查终止条件
        # 条件1: 达到最大轮次
        if state["current_round"] >= state["max_iterations"]:
            return "COMPLETE"

        # 条件2: 置信度聚合 > 85%
        if audit_result and "scores_4d" in audit_result:
            scores = audit_result["scores_4d"]
            total = sum(scores.values())
            confidence_agg = (total / (4 * 10)) * 100
            if confidence_agg > 85:
                return "COMPLETE"

        # 条件3: task_complete 由外部设置（force_complete）

        return "CONTINUE"

    def calculate_confidence_aggregation(self, audit_result: dict) -> float:
        """计算置信度聚合"""
        if not audit_result or "scores_4d" not in audit_result:
            return 0.0

        scores = audit_result["scores_4d"]
        total = sum(scores.values())
        return (total / (4 * 10)) * 100

    def detect_valley(self, state: FIHState) -> tuple[bool, str, str]:
        """
        检测低谷

        Returns:
            (是否检测到低谷, 低谷类型, 建议操作)
        """
        # 检查连续无 Fact+ 轮次
        if state.get("no_fact_rounds", 0) >= 3:
            return True, "no_fact", "force_fact_plus"

        # 检查 result_ei 连续低下（需要 ei_tracking）

        return False, "", ""

    def execute_valley_crossing(self, state: FIHState, valley_type: str) -> dict:
        """
        执行低谷穿越

        Args:
            state: 当前状态
            valley_type: low_ei / no_fact

        Returns:
            穿越策略
        """
        if valley_type == "no_fact":
            return {
                "operation": "force_fact_plus",
                "suggestion": "强制人工介入，要求 Fact+"
            }
        elif valley_type == "low_ei":
            return {
                "operation": "diversify_intent",
                "suggestion": "引导 Proposer 生成不同方向的 Intent"
            }

        return {"operation": "none"}
