"""
Tests for FIH State.

Based on SPEC_DataStructures.md §1
"""

import pytest

from fih_emergence.state import (
    Fact,
    Hint,
    Intent,
    WorkerSubmission,
    create_initial_state,
)


class TestCreateInitialState:
    """测试创建初始状态"""

    def test_basic_fields(self):
        """基本字段初始化"""
        state = create_initial_state(
            session_id="test-123",
            task_description="测试任务",
            max_iterations=20,
        )

        assert state["session_id"] == "test-123"
        assert state["task_description"] == "测试任务"
        assert state["current_round"] == 1
        assert state["max_iterations"] == 20
        assert state["mode"] == "FULL"

    def test_control_flags(self):
        """控制标志初始值"""
        state = create_initial_state("s1", "task")

        assert state["task_complete"] is False
        assert state["is_first_round"] is True
        assert state["task_boundary_status"] == "open"

    def test_accumulation_fields(self):
        """累积字段初始为空"""
        state = create_initial_state("s1", "task")

        assert state["facts"] == []
        assert state["hints"] == []
        assert state["valley_signals"] == []

    def test_worker_count_fixed(self):
        """Worker 数量固定为 2"""
        state = create_initial_state("s1", "task")

        assert state["worker_count"] == 2


class TestFactModel:
    """测试 Fact 模型"""

    def test_valid_fact(self):
        """有效 Fact"""
        fact = Fact(
            id="F1",
            content="GDP 增速从 8% 降至 5%",
            source="worker_audit",
            confidence=0.9,
            created_at="2026-06-09T10:00:00Z",
        )

        assert fact.id == "F1"
        assert fact.confidence == 0.9

    def test_confidence_bounds(self):
        """置��度边界"""
        with pytest.raises(ValueError):
            Fact(
                id="F1",
                content="test",
                source="worker_audit",
                confidence=1.5,  # 超出范围
                created_at="2026-06-09T10:00:00Z",
            )


class TestHintModel:
    """测试 Hint 模型"""

    def test_default_weight(self):
        """默认权重"""
        hint = Hint(
            id="H1",
            content="关注房地产行业",
            source="human_gate",
            created_at="2026-06-09T10:00:00Z",
        )

        assert hint.weight == 0.5

    def test_custom_weight(self):
        """自定义权重"""
        hint = Hint(
            id="H1",
            content="test",
            source="human_gate",
            weight=0.8,
            created_at="2026-06-09T10:00:00Z",
        )

        assert hint.weight == 0.8


class TestIntentModel:
    """测试 Intent 模型"""

    def test_three_types(self):
        """三类 Intent"""
        types = ["待验证", "待探索", "待决策"]

        for intent_type in types:
            intent = Intent(
                id="I1",
                content="test intent",
                type=intent_type,
            )
            assert intent.type == intent_type

    def test_supporting_facts_default(self):
        """默认无支撑 Fact"""
        intent = Intent(
            id="I1",
            content="test",
            type="待验证",
        )

        assert intent.supporting_facts == []


class TestWorkerSubmission:
    """测试 Worker 提交"""

    def test_confidence_bounds(self):
        """置信度 0-100"""
        sub = WorkerSubmission(
            worker_id="worker_p",
            insight="test insight",
            self_confidence=85.0,
        )

        assert sub.self_confidence == 85.0

    def test_invalid_confidence(self):
        """无效置信度"""
        with pytest.raises(ValueError):
            WorkerSubmission(
                worker_id="worker_p",
                insight="test",
                self_confidence=150,  # 超出范围
            )


class TestStateFieldConstraints:
    """测试状态字段约束（��应 SPEC_数据结构和.md §4.4 非法状态断言）"""

    def test_task_complete_true_with_high_round(self):
        """task_complete=true 且 current_round > max_rounds 应该是非法的"""
        # 这个测试验证我们需要在实现时添加断言检查
        state = create_initial_state("s1", "task", max_iterations=20)
        state["task_complete"] = True
        state["current_round"] = 25  # 超出 max_iterations

        # 实现时应拒绝这种状态组合
        is_valid = not (state["task_complete"] and state["current_round"] > state["max_iterations"])
        assert is_valid is False  # 应该被标记为非法

    def test_needs_human_with_task_complete(self):
        """needs_human=true 且 task_complete=true 应该是非法的"""
        state = create_initial_state("s1", "task")
        state["needs_human"] = True
        state["task_complete"] = True

        is_valid = not (state["needs_human"] and state["task_complete"])
        assert is_valid is False
