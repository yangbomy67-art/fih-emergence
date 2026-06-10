"""
Worker Role - 工作者

Based on SPEC_角色.md §Worker

Responsibilities:
1. 双 Worker 模式（正方/反方），每个 Worker 内嵌正/反、判三方对抗
2. Phase A: Worker 内部三方对抗（生成 → 自反驳 → 自判断 → self_confidence）
3. Phase B: Auditor 检查双 Worker 信心，若差距大则弱势方重产
"""

from fih_emergence.llm import BaseLLMClient, get_worker_client
from fih_emergence.prompts import WORKER_REBUTTAL, WORKER_SELF_DEBATE
from fih_emergence.state import FIHState


class Worker:
    """FIH Worker 角色"""

    WORKER_P = "worker_p"
    WORKER_N = "worker_n"

    def __init__(self, worker_id: str, llm_client: BaseLLMClient = None):
        if worker_id not in (self.WORKER_P, self.WORKER_N):
            raise ValueError(f"Invalid worker_id: {worker_id}")
        self.worker_id = worker_id
        self.worker_type = "正方" if worker_id == self.WORKER_P else "反方"
        self.llm_client = llm_client or get_worker_client(worker_id)

    async def generate_insight(
        self,
        state: FIHState,
        intent: dict,
    ) -> dict:
        """
        Worker 内部三方对抗：生成初稿 → 自反驳 → 自判断

        Args:
            state: 当前状态
            intent: 当前处理的 Intent
        """
        facts = state.get("facts", [])
        hints = state.get("hints", [])

        facts_str = "\n".join([f"[F{i+1}] {f['content']}" for i, f in enumerate(facts)])
        hints_str = "\n".join([f"[H{i+1}] {h['content']}" for i, h in enumerate(hints)])

        prompt = WORKER_SELF_DEBATE.format(
            worker_type=self.worker_type,
            intent=intent.get("content", ""),
            facts=facts_str or "（无）",
            hints=hints_str or "（无）",
        )

        # 调用 LLM
        response = await self.llm_client.complete(prompt)
        content = response.content
        
        # 解析 JSON 格式
        # 策略 1: 先尝试整体 json.loads()
        import json
        try:
            parsed = json.loads(content.strip())
            if isinstance(parsed, dict):
                insight = parsed.get("insight", content[:200])
                confidence = parsed.get("self_confidence", 75.0)
                suggestions = parsed.get("next_intent_suggestions", [])
                return {
                    "insight": insight,
                    "self_confidence": confidence,
                    "action": "generate_insight",
                    "citations": suggestions,
                }
        except:
            pass
        
        # 策略 2: 尝试 ```json 提取
        try:
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]
            
            parsed = json.loads(content.strip())
            
            if isinstance(parsed, dict):
                insight = parsed.get("insight", content[:200])
                confidence = parsed.get("self_confidence", 75.0)
                suggestions = parsed.get("next_intent_suggestions", [])
                return {
                    "insight": insight,
                    "self_confidence": confidence,
                    "action": "generate_insight",
                    "citations": suggestions,
                }
        except:
            pass
        
        # 策略 3: 解析失败，保存 raw_content
        return {
            "insight": content[:500],
            "self_confidence": 50.0,
            "action": "generate_insight",
            "citations": [],
            "_raw_content": content,
            "_parse_status": "failed",
        }

        return {
            "prompt": prompt,
            "worker_id": self.worker_id,
            "insight": insight,
            "self_confidence": confidence,
            "next_intent_suggestions": suggestions,
        }

    async def rebuttal(
        self,
        state: FIHState,
        previous_insight: str,
        confidence: float,
        opponent_insight: str,
    ) -> dict:
        """
        弱势方重新产出，注入对抗性 Hint

        Args:
            previous_insight: 上一轮产出
            confidence: 上一轮置信度
            opponent_insight: 对手产出
        """
        prompt = WORKER_REBUTTAL.format(
            previous_insight=previous_insight,
            confidence=confidence,
            opponent_insight=opponent_insight,
        )

        return {
            "prompt": prompt,
            "worker_id": self.worker_id,
            "insight": "",
            "self_confidence": 0.0,
        }

    def calculate_self_confidence(
        self,
        insight: str,
        supporting_facts: list[str],
        has_new_concept: bool,
    ) -> float:
        """
        计算 self_confidence（可由 LLM 评估或规则计算）

        Args:
            insight: 推理结论
            supporting_facts: 支撑 Facts
            has_new_concept: 是否引入新概念
        """
        # 简化规则：
        # - 有 Fact 支撑 +20%
        # - 引入新概念 +20%
        # - 无 Fact 支撑 -30%
        # - 同义反复 -40%

        base = 50.0

        if supporting_facts:
            base += 20
        else:
            base -= 30

        if has_new_concept:
            base += 20
        else:
            base -= 20

        # 限制范围
        return max(0, min(100, base))


# 工厂函数
def create_worker(worker_id: str, llm_client=None) -> Worker:
    """创建 Worker 实例"""
    return Worker(worker_id, llm_client)
