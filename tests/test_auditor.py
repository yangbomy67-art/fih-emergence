"""
Tests for Auditor Role.

Based on SPEC_角色.md §Auditor
"""

import pytest

from fih_emergence.roles.auditor import Auditor


class TestAuditorPreAudit:
    """测试 Auditor 事前审计"""

    def setup_method(self):
        self.auditor = Auditor()

    @pytest.mark.asyncio
    async def test_pre_audit_intent_basic(self):
        """事前审计基本测试"""
        intent = {"id": "I1", "content": "验证消费降级", "type": "待验证", "supporting_facts": ["F1", "F2"]}
        facts = [{"id": "F1", "content": "经济增长放缓", "source": "human", "confidence": 0.9}]

        result = await self.auditor.pre_audit_intent(intent, facts)

        assert "passed" in result
        assert "prompt" in result


class TestAuditorPostAudit:
    """测试 Auditor 事后审计"""

    def setup_method(self):
        self.auditor = Auditor()

    @pytest.mark.asyncio
    async def test_post_audit_insight_basic(self):
        """事后审计基本测试"""
        facts = [{"id": "F1", "content": "经济增长放缓", "source": "human", "confidence": 0.9}]
        insight = "通过分析数据，消费确实呈下降趋势"

        result = await self.auditor.post_audit_insight("worker_p", insight, facts)

        assert "passed" in result
        assert "result_ei" in result
        assert "scores_4d" in result


class TestAuditorValleyDetection:
    """测试 Auditor 低谷检测"""

    def setup_method(self):
        self.auditor = Auditor()

    @pytest.mark.asyncio
    async def test_check_valley_no_facts(self):
        """无 Fact+ 产出"""
        result = await self.auditor.check_valley(ei_tracking=[], no_fact_rounds=3)

        assert result["valley_detected"] is True
        assert result["valley_type"] == "no_fact"

    @pytest.mark.asyncio
    async def test_check_valley_no_issues(self):
        """无低谷"""
        result = await self.auditor.check_valley(ei_tracking=[], no_fact_rounds=1)

        assert result["valley_detected"] is False


class TestAuditorConfidenceAnomaly:
    """测试 Auditor 置信度异常检测"""

    def setup_method(self):
        self.auditor = Auditor()

    def test_check_confidence_anomaly_p_dominant(self):
        """置信度异常：正方主导"""
        triggered, condition = self.auditor.check_confidence_anomaly(95, 25)

        assert triggered is True
        assert condition == "p_dominant"

    def test_check_confidence_anomaly_n_dominant(self):
        """置信度异常：反方主导"""
        triggered, condition = self.auditor.check_confidence_anomaly(25, 95)

        assert triggered is True
        assert condition == "n_dominant"

    def test_check_confidence_dominance(self):
        """置信度悬殊 - 弱势方重产 (已删除45-55僵持)"""
        # P强N弱: P>80%, N<30%
        triggered, condition = self.auditor.check_confidence_anomaly(85, 25)
        assert triggered is True
        assert condition == "p_dominant"
        
        # N强P弱: N>80%, P<30%
        triggered, condition = self.auditor.check_confidence_anomaly(25, 85)
        assert triggered is True
        assert condition == "n_dominant"

    def test_check_no_anomaly(self):
        """无异常"""
        triggered, condition = self.auditor.check_confidence_anomaly(70, 65)

        assert triggered is False
        assert condition == ""


class TestAuditorCandidateExtraction:
    """测试 Auditor 候选提取"""

    def setup_method(self):
        self.auditor = Auditor()

    def test_extract_fact_candidates(self):
        """提取 Fact+ 候选"""
        insight = "基于 [F1] 和 [F2] 的分析"
        facts = [
            {"id": "F1", "content": "经济增长放缓", "source": "human"},
            {"id": "F2", "content": "消费下降", "source": "human"},
        ]

        candidates = self.auditor.extract_fact_candidates(insight, facts)

        assert len(candidates) == 2

    def test_extract_hint_candidates(self):
        """提取 Hint+ 候选"""
        insight = "需要关注年轻群体的消费行为"
        hints = [
            {"id": "H1", "content": "年轻群体", "source": "human"},
            {"id": "H2", "content": "消费行为", "source": "human"},
        ]

        candidates = self.auditor.extract_hint_candidates(insight, hints)

        assert len(candidates) == 2
