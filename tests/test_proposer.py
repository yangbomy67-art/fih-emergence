"""
Tests for Proposer Role.

Based on SPEC_角色.md §PROPOSER
"""

import pytest

from fih_emergence.roles.proposer import Proposer
from fih_emergence.state import create_initial_state


class TestProposerGenerateIntents:
    """测试 Proposer 多草稿生成"""

    def setup_method(self):
        self.proposer = Proposer()

    @pytest.mark.asyncio
    async def test_generate_intents_basic(self):
        """基本生成测试"""
        state = create_initial_state("s1", "test")
        state["facts"] = [
            {"id": "F1", "content": "经济增长放缓", "source": "human", "confidence": 0.9},
            {"id": "F2", "content": "消费降级趋势", "source": "human", "confidence": 0.8},
        ]
        state["hints"] = [
            {"id": "H1", "content": "关注年轻群体", "source": "human", "weight": 0.5},
        ]

        result = await self.proposer.generate_intents(state)

        assert "intents" in result
        assert "prompt" in result

    @pytest.mark.asyncio
    async def test_generate_intents_empty_facts(self):
        """空 Facts 时生成降级处理"""
        state = create_initial_state("s1", "test")
        state["facts"] = []

        result = await self.proposer.generate_intents(state)

        assert "intents" in result
        assert "prompt" in result


class TestProposerSupplementIntents:
    """测试 Proposer 缺失补足"""

    def setup_method(self):
        self.proposer = Proposer()

    @pytest.mark.asyncio
    async def test_supplement_intents(self):
        """补充缺失 Intent"""
        state = create_initial_state("s1", "test")

        result = await self.proposer.supplement_intents(
            state, missing_type="待决策", details="需要决策类 Intent"
        )

        assert "intents" in result
        assert "prompt" in result


class TestProposerIntentQuality:
    """测试 Proposer Intent ��量检查"""

    def setup_method(self):
        self.proposer = Proposer()

    def test_check_intent_quality_valid(self):
        """有效 Intent 列表"""
        intents = [
            {"id": "I1", "content": "验证 X", "type": "待验证", "supporting_facts": ["F1"]},
            {"id": "I2", "content": "探索 Y", "type": "待探索", "supporting_facts": ["F1"]},
            {"id": "I3", "content": "决策 Z", "type": "待决策", "supporting_facts": ["F1"]},
        ]

        is_valid, reason = self.proposer.check_intent_quality(intents)

        assert is_valid is True
        assert reason == ""

    def test_check_intent_quality_insufficient_count(self):
        """数量不足"""
        intents = [
            {"id": "I1", "content": "验证 X", "type": "待验证", "supporting_facts": ["F1"]},
        ]

        is_valid, reason = self.proposer.check_intent_quality(intents)

        assert is_valid is False
        assert "数量不足" in reason

    def test_check_intent_quality_missing_type(self):
        """缺少类型"""
        intents = [
            {"id": "I1", "content": "验证 X", "type": "待验证", "supporting_facts": ["F1"]},
            {"id": "I2", "content": "验证 Y", "type": "待验证", "supporting_facts": ["F1"]},
        ]

        is_valid, reason = self.proposer.check_intent_quality(intents)

        assert is_valid is False
        assert "缺少 Intent 类型" in reason


class TestProposerDiversity:
    """测试 Proposer 多样性评估"""

    def setup_method(self):
        self.proposer = Proposer()

    def test_calculate_diversity_full(self):
        """完全多样性"""
        intents = [
            {"type": "待验证"},
            {"type": "待探索"},
            {"type": "待决策"},
        ]

        diversity = self.proposer.calculate_diversity(intents)

        assert diversity == 1.0

    def test_calculate_diversity_partial(self):
        """部分多样性"""
        intents = [
            {"type": "待验证"},
            {"type": "待验证"},
            {"type": "待探索"},
        ]

        diversity = self.proposer.calculate_diversity(intents)

        assert diversity == 2 / 3

    def test_calculate_diversity_empty(self):
        """空列表"""
        diversity = self.proposer.calculate_diversity([])

        assert diversity == 0.0
