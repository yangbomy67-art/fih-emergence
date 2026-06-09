"""
Proposer Role - 提议者

Based on SPEC_角色.md §PROPOSER

Responsibilities:
1. 多草稿生成：基于当前 Facts + Hints，生成 N=2-4 个候选 Intent
2. 发布/更新 Intent：发布到黑板供 Manager 确认
3. 缺失补足（被动响应）：仅当 Manager 判定缺失时补生成
"""

from fih_emergence.state import FIHState
from fih_emergence.prompts import PROPOSER_GENERATE, PROPOSER_SUPPLEMENT


class Proposer:
    """FIH Proposer 角色"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def generate_intents(self, state: FIHState) -> dict:
        """
        生成候选 Intent

        Returns:
            {"intents": [...], "prompt": "..."}
        """
        facts = state.get("facts", [])
        hints = state.get("hints", [])

        facts_str = "\n".join([f"- {f['content']}" for f in facts]) or "（无）"
        hints_str = "\n".join([f"- {h['content']}" for h in hints]) or "（无）"

        prompt = PROPOSER_GENERATE.format(
            facts=facts_str,
            hints=hints_str,
        )

        return {
            "prompt": prompt,
            "intents": [],  # 由 LLM 填充
        }

    async def supplement_intents(
        self,
        state: FIHState,
        missing_type: str,
        details: str,
    ) -> dict:
        """
        补充生成（Manager 判定缺失后）

        Args:
            missing_type: 缺失类型
            details: 详情
        """
        prompt = PROPOSER_SUPPLEMENT.format(
            missing_type=missing_type,
            details=details,
        )

        return {
            "prompt": prompt,
            "intents": [],
        }

    def check_intent_quality(self, intents: list[dict]) -> tuple[bool, str]:
        """
        检查 Intent 候选质量（供 Manager 调用）

        Returns:
            (是否合格, 问题描述)
        """
        if len(intents) < 2:
            return False, "候选 Intent 数量不足（需要 2-4 个）"

        # 检查三类 Intent 是否覆盖
        types_present = set(i.get("type") for i in intents)
        required_types = {"待验证", "待探索", "待决策"}

        if not required_types.issubset(types_present):
            missing = required_types - types_present
            return False, f"缺少 Intent 类型: {missing}"

        # 检查是否有支撑 Fact
        for intent in intents:
            if not intent.get("supporting_facts"):
                return False, f"Intent {intent.get('id')} 缺少支撑 Fact"

        return True, ""

    def calculate_diversity(self, intents: list[dict]) -> float:
        """
        计算候选 Intent 之间的差异度

        Returns:
            差异度 (0-1)，越高表示越多样
        """
        if len(intents) < 2:
            return 0.0

        # 简化的差异度计算：基于类型分布
        types = [i.get("type") for i in intents]
        type_diversity = len(set(types)) / 3

        return type_diversity