"""
Tests for Worker Role.

Based on SPEC_角色.md §Worker
"""

import pytest

from fih_emergence.roles.worker import Worker, create_worker
from fih_emergence.state import create_initial_state


class TestWorkerBasic:
    """测试 Worker 基本功能"""

    def setup_method(self):
        self.worker = Worker("worker_p")

    @pytest.mark.asyncio
    async def test_worker_generate_insight(self):
        """生成 Insight 基本测试"""
        state = create_initial_state("s1", "test")
        state["facts"] = [
            {"id": "F1", "content": "经济增长放缓", "source": "human", "confidence": 0.9},
        ]
        state["hints"] = [
            {"id": "H1", "content": "关注消费", "source": "human", "weight": 0.5},
        ]
        state["intents"] = [
            {"id": "I1", "content": "验证消费降级", "type": "待验证"},
        ]
        intent = {"id": "I1", "content": "验证消费降级", "type": "待验证"}

        result = await self.worker.generate_insight(state, intent)

        assert "insight" in result
        assert "self_confidence" in result
        assert "prompt" in result

    def test_worker_id(self):
        """Worker ID 正确"""
        assert self.worker.worker_id == "worker_p"

    def test_worker_type(self):
        """Worker 类型正确"""
        assert self.worker.worker_type == "正方"

    def test_create_worker(self):
        """工厂函数测试"""
        worker = create_worker("worker_n")

        assert worker.worker_id == "worker_n"


class TestWorkerSelfConfidence:
    """测试 Worker 置信度计算"""

    def setup_method(self):
        self.worker = Worker("worker_p")

    def test_calculate_self_confidence_with_facts_and_concept(self):
        """有 Fact 支撑 + 引入新概念"""
        confidence = self.worker.calculate_self_confidence(
            insight="新观点",
            supporting_facts=["F1", "F2"],
            has_new_concept=True,
        )

        assert confidence == 90.0  # 50 + 20 + 20

    def test_calculate_self_confidence_without_facts(self):
        """无 Fact 支撑"""
        confidence = self.worker.calculate_self_confidence(
            insight="无根据观点",
            supporting_facts=[],
            has_new_concept=False,
        )

        assert confidence == 0.0  # 50 - 30 - 20

    def test_calculate_self_confidence_partial(self):
        """部分支撑：50 + 20 (有Fact) - 20 (无新概念) = 50"""
        confidence = self.worker.calculate_self_confidence(
            insight="部分支撑",
            supporting_facts=["F1"],
            has_new_concept=False,
        )

        assert confidence == 50.0

    def test_calculate_self_confidence_bounds(self):
        """置信度边界"""
        # 最小: 50 - 30 - 20 = 0
        confidence = self.worker.calculate_self_confidence(
            insight="",
            supporting_facts=[],
            has_new_concept=False,
        )
        assert confidence == 0.0

        # 最大: 50 + 20 + 20 = 90 (不是100)
        confidence = self.worker.calculate_self_confidence(
            insight="有支撑有新概念",
            supporting_facts=["F1", "F2", "F3"],
            has_new_concept=True,
        )
        assert confidence == 90.0


class TestWorkerRebuttal:
    """测试 Worker 反驳"""

    def setup_method(self):
        self.worker = Worker("worker_p")

    @pytest.mark.asyncio
    async def test_rebuttal_basic(self):
        """反驳基本测试"""
        state = create_initial_state("s1", "test")

        result = await self.worker.rebuttal(
            state,
            previous_insight="原观点",
            confidence=60.0,
            opponent_insight="对手观点",
        )

        assert "rebuttal" in result or "insight" in result
        assert "prompt" in result


class TestWorkerDualWorker:
    """测试双 Worker 模式"""

    def setup_method(self):
        self.worker_p = Worker("worker_p")
        self.worker_n = Worker("worker_n")

    def test_worker_p_identity(self):
        """Worker_P 身份"""
        assert self.worker_p.worker_id == "worker_p"
        assert self.worker_p.worker_type == "正方"

    def test_worker_n_identity(self):
        """Worker_N 身份"""
        assert self.worker_n.worker_id == "worker_n"
        assert self.worker_n.worker_type == "反方"

    def test_workers_have_different_ids(self):
        """两个 Worker ID 不同"""
        assert self.worker_p.worker_id != self.worker_n.worker_id

    def test_invalid_worker_id(self):
        """无效 Worker ID"""
        with pytest.raises(ValueError):
            Worker("invalid_worker")
