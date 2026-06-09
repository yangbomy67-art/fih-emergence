"""
Auditor Role - 审计员

Based on SPEC_角色.md §Auditor

Responsibilities:
1. 事前审计 (Intent → Worker 门槛)：EI 启发式评估（门控）
2. 事后审计 (Insight → 黑板 门槛)：EI 追踪 + Fact+候选 + Hint+候选 + 快照策略 + 四维审计 + 低谷识别
3. 检测 4 条件并通知 Manager
"""

from fih_emergence.prompts import (
    AUDITOR_POST_CHECK,
    AUDITOR_PRE_CHECK,
)


class Auditor:
    """FIH Auditor 角色"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def pre_audit_intent(
        self,
        intent: dict,
        facts: list[dict],
    ) -> dict:
        """
        事前审计：Intent → Worker 门槛

        EI 代理指标（满足 2/3 即判定"能产出新 Insight"）：
        1. 引用了至少 2 个不同的 Fact
        2. 引入了 Fact 中未覆盖的新概念
        3. 产出预期可验证（不是同义反复）
        """
        facts_str = "\n".join([f"[F{i+1}] {f['content']}" for i, f in enumerate(facts)])

        prompt = AUDITOR_PRE_CHECK.format(
            intent=intent.get("content", ""),
            facts=facts_str or "（无）",
        )

        # 简化：规则判定
        supporting_facts = intent.get("supporting_facts", [])

        score_1 = len(supporting_facts) >= 2  # 引用 >=2 Fact

        # LLM 判断项（这里简化处理）
        score_2 = True  # has_new_concept
        score_3 = True  # is_verifiable

        passed = sum([score_1, score_2, score_3]) >= 2

        return {
            "passed": passed,
            "reason": "满足 2/3 代理指标" if passed else "未满足 2/3 代理指标",
            "ei_scores": {
                "引用Fact数": len(supporting_facts),
                "新概念": score_2,
                "可验证": score_3,
            },
            "prompt": prompt,
        }

    async def post_audit_insight(
        self,
        worker_id: str,
        insight: str,
        facts: list[dict],
    ) -> dict:
        """
        事后审计：Insight → 黑板 门槛

        四维审计 + result_EI 计算 + Fact+/Hint+ 候选提取
        """
        facts_str = "\n".join([f"[F{i+1}] {f['content']}" for i, f in enumerate(facts)])

        prompt = AUDITOR_POST_CHECK.format(
            worker_id=worker_id,
            insight=insight,
            facts=facts_str or "（无）",
        )

        # 简化：返回结构化结果
        # 实际应由 LLM 填充四维评分
        scores_4d = {"A": 7, "B": 7, "C": 7, "D": 7}  # 默认

        result_ei_s1 = 4  # 可交付形态  # noqa: N806
        result_ei_s2 = 4  # Fact引用  # noqa: N806
        result_ei_s3 = 7  # 新增视角  # noqa: N806
        result_ei = result_ei_s1 + result_ei_s2 + result_ei_s3

        passed = result_ei >= 15 and all(s >= 7 for s in scores_4d.values())

        return {
            "passed": passed,
            "scores_4d": scores_4d,
            "result_ei": result_ei,
            "result_ei_S1": result_ei_s1,
            "result_ei_S2": result_ei_s2,
            "result_ei_S3": result_ei_s3,
            "fact_candidates": [],  # 从 insight 提取
            "hint_candidates": [],  # 从黑板匹配
            "valley_detected": False,
            "prompt": prompt,
        }

    async def check_valley(
        self,
        ei_tracking: list[dict],
        no_fact_rounds: int,
    ) -> dict:
        """
        检测低谷

        连续 3 轮 result_ei < 10 或 连续 3 轮无 Fact+ → 低谷
        """
        # 检查无 Fact+ 轮次
        if no_fact_rounds >= 3:
            return {
                "valley_detected": True,
                "valley_type": "no_fact",
                "operation": "force_fact_plus",
            }

        # 检查 result_ei 低下
        recent_scores = [t.get("result_ei", 0) for t in ei_tracking[-3:]]
        if len(recent_scores) >= 3 and all(s < 10 for s in recent_scores):
            return {
                "valley_detected": True,
                "valley_type": "ei_low",
                "operation": "diversify_intent",
            }

        return {
            "valley_detected": False,
            "valley_type": "",
            "operation": "none",
        }

    def extract_fact_candidates(self, insight: str, facts: list[dict]) -> list[dict]:
        """从 Insight 中提取 Fact+ 候选"""
        # 简化：基于引用提取
        candidates = []
        for fact in facts:
            if f"[{fact['id']}]" in insight or fact["id"] in insight:
                # 标记为候选
                candidates.append({
                    **fact,
                    "status": "candidate",
                    "source": "worker_audit",
                })
        return candidates

    def extract_hint_candidates(self, insight: str, hints: list[dict]) -> list[dict]:
        """从黑板中匹配 Hint+ 候选"""
        # 简化：基于关键词匹配
        candidates = []
        for hint in hints:
            if any(keyword in insight.lower() for keyword in hint["content"].lower().split()):
                candidates.append({
                    **hint,
                    "status": "candidate",
                })
        return candidates

    def check_confidence_anomaly(
        self,
        worker_p_confidence: float,
        worker_n_confidence: float,
    ) -> tuple[bool, str]:
        """
        检查置信度异常（4 条件之一）

        Returns:
            (是否异常, 类型)
        """
        # 正方>90% 且 反方<30%
        if worker_p_confidence > 90 and worker_n_confidence < 30:
            return True, "p_dominant"

        # 反方>90% 且 正方<30%
        if worker_n_confidence > 90 and worker_p_confidence < 30:
            return True, "n_dominant"

        # 45-55 僵持
        if 45 <= worker_p_confidence <= 55 and 45 <= worker_n_confidence <= 55:
            return True, "stalemate"

        return False, ""
