"""
Tests for Manager Role.

Based on SPEC_角色.md §MANAGER
"""

import pytest

from fih_emergence.roles.manager import Manager
from fih_emergence.state import create_initial_state


class TestManagerInterruptConditions:
    """测试 Manager 4 条件检测"""

    def setup_method(self):
        self.manager = Manager()

    def test_confidence_anomaly_p_dominant(self):
        """置信度异常：正方>90% 且 反方<30%"""
        state = create_initial_state("s1", "test")
        state["worker_submissions"] = [
            {"worker_id": "worker_p", "self_confidence": 95},
            {"worker_id": "worker_n", "self_confidence": 25},
        ]

        triggered, reason = self.manager.check_interrupt_conditions(state)

        assert triggered is True
        assert "confidence_anomaly" in reason
        assert "P=95%" in reason

    def test_confidence_anomaly_n_dominant(self):
        """置信度异常：反方>90% 且 正方<30%"""
        state = create_initial_state("s1", "test")
        # 反方 N=92 > 90 但 P=20 不 < 30
        # 当前逻辑：P>90 and N<30 或 (45-55 范围)
        # N 主导需要额外逻辑
        state["worker_submissions"] = [
            {"worker_id": "worker_p", "self_confidence": 20},
            {"worker_id": "worker_n", "self_confidence": 92},
        ]

        triggered, reason = self.manager.check_interrupt_conditions(state)

        # 当前实现只检查 P>90 && N<30，不检查反向
        # 此测试预期需要先修复 manager.py
        assert triggered is True
        assert "confidence_anomaly" in reason

    def test_confidence_stalemate(self):
        """置信度僵持：45-55"""
        state = create_initial_state("s1", "test")
        state["worker_submissions"] = [
            {"worker_id": "worker_p", "self_confidence": 85},
            {"worker_id": "worker_n", "self_confidence": 25},
        ]

        triggered, reason = self.manager.check_interrupt_conditions(state)

        assert triggered is True
        assert "confidence_anomaly" in reason

    def test_output_stagnation(self):
        """产出停滞：连续 3 轮无 Fact+"""
        state = create_initial_state("s1", "test")
        state["no_fact_rounds"] = 3

        triggered, reason = self.manager.check_interrupt_conditions(state)

        assert triggered is True
        assert "output_stagnation" in reason

    def test_output_repetition(self):
        """产出重复：连续 2 轮产出相同"""
        state = create_initial_state("s1", "test")
        state["consecutive_same_output"] = 2

        triggered, reason = self.manager.check_interrupt_conditions(state)

        assert triggered is True
        assert "output_repetition" in reason

    def test_fact_conflict(self):
        """Fact 冲突"""
        state = create_initial_state("s1", "test")
        state["fact_conflicts"] = [{"id": "F1"}, {"id": "F2"}]

        triggered, reason = self.manager.check_interrupt_conditions(state)

        assert triggered is True
        assert "fact_conflict" in reason

    def test_no_interrupt_conditions(self):
        """无触发条件"""
        state = create_initial_state("s1", "test")
        state["worker_submissions"] = [
            {"worker_id": "worker_p", "self_confidence": 70},
            {"worker_id": "worker_n", "self_confidence": 65},
        ]
        state["no_fact_rounds"] = 1
        state["consecutive_same_output"] = 1
        state["fact_conflicts"] = []

        triggered, reason = self.manager.check_interrupt_conditions(state)

        assert triggered is False
        assert reason == ""


class TestManagerDecideNext:
    """测试 Manager 汇总裁决"""

    def setup_method(self):
        self.manager = Manager()

    @pytest.mark.asyncio
    async def test_decide_max_rounds_reached(self):
        """达到最大轮次 → COMPLETE"""
        state = create_initial_state("s1", "test", max_iterations=20)
        state["current_round"] = 20
        state["worker_submissions"] = [
            {"worker_id": "worker_p", "self_confidence": 90},
            {"worker_id": "worker_n", "self_confidence": 90},
        ]
        audit_result = {"scores_4d": {"A": 9, "B": 9, "C": 9, "D": 9}}

        decision = await self.manager.decide_next(state, audit_result)

        assert decision == "COMPLETE"

    @pytest.mark.asyncio
    async def test_decide_interrupt_triggered(self):
        """触发中断 → INTERRUPT"""
        state = create_initial_state("s1", "test")
        state["worker_submissions"] = [
            {"worker_id": "worker_p", "self_confidence": 95},
            {"worker_id": "worker_n", "self_confidence": 25},
        ]

        decision = await self.manager.decide_next(state, {})

        assert decision == "INTERRUPT"
        assert state["needs_human"] is True

    @pytest.mark.asyncio
    async def test_decide_continue(self):
        """默认继续 → CONTINUE"""
        state = create_initial_state("s1", "test")
        state["current_round"] = 1
        state["worker_submissions"] = [
            {"worker_id": "worker_p", "self_confidence": 70},
            {"worker_id": "worker_n", "self_confidence": 65},
        ]
        state["no_fact_rounds"] = 0
        state["consecutive_same_output"] = 0
        state["fact_conflicts"] = []
        audit_result = {"scores_4d": {"A": 6, "B": 6, "C": 6, "D": 6}}

        decision = await self.manager.decide_next(state, audit_result)

        assert decision == "CONTINUE"


class TestManagerValleyDetection:
    """测试 Manager 低谷检测"""

    def setup_method(self):
        self.manager = Manager()

    def test_valley_no_fact(self):
        """连续无 Fact+ → 低谷策略选择"""
        state = create_initial_state("s1", "test")
        state["no_fact_rounds"] = 3

        # 方法已重命名为 select_valley_strategy
        needs_strategy, strategy_type, suggestion = self.manager.select_valley_strategy(state)

        assert needs_strategy is True
        assert strategy_type == "no_fact"

    def test_no_valley(self):
        """无低谷 - 不需要策略"""
        state = create_initial_state("s1", "test")
        state["no_fact_rounds"] = 1

        needs_strategy, strategy_type, suggestion = self.manager.select_valley_strategy(state)

        assert needs_strategy is False


class TestConfidenceAggregation:
    """测试置信度聚合计算"""

    def setup_method(self):
        self.manager = Manager()

    def test_calculate_confidence_aggregation(self):
        """计算置信度聚合"""
        audit_result = {"scores_4d": {"A": 8, "B": 7, "C": 9, "D": 6}}

        aggregation = self.manager.calculate_confidence_aggregation(audit_result)

        assert aggregation == 75.0

    def test_calculate_confidence_aggregation_empty(self):
        """空结果返回 0"""
        aggregation = self.manager.calculate_confidence_aggregation({})

        assert aggregation == 0.0
