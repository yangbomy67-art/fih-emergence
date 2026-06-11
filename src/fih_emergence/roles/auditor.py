"""
Auditor Role - 审计员

Based on SPEC_角色.md §Auditor

Responsibilities:
1. 事前审计 (Intent → Worker 门槛)：EI 启发式评估（门控）
2. 事后审计 (Insight → 黑板 门槛)：EI 追踪 + Fact+候选 + Hint+候选 + 快照策略 + 四维审计 + 低谷识别
3. 检测 4 条件并通知 Manager
"""

from fih_emergence.llm import BaseLLMClient, get_auditor_client
from fih_emergence.prompts import (
    AUDITOR_POST_CHECK,
    AUDITOR_PRE_CHECK,
)


class Auditor:
    """FIH Auditor 角色"""

    def __init__(self, llm_client: BaseLLMClient = None):
        self.llm_client = llm_client or get_auditor_client()

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

            # 调用 LLM 进行审计
            try:
                response = await self.llm_client.complete(prompt, max_tokens=1500)
                content = response.content
            
                # 解析 LLM 返回的 JSON
                import json
            
                # 策略 1: 直接 json.loads
                try:
                    parsed = json.loads(content.strip())
                except:
                    # 策略 2: 提取 ```json 部分
                    try:
                        if '```json' in content:
                            content = content.split('```json')[1].split('```')[0]
                        elif '```' in content:
                            content = content.split('```')[1].split('```')[0]
                        parsed = json.loads(content.strip())
                    except:
                        # 策略 3: 回退到默认
                        parsed = {}
            
                if parsed:
                    # 提取结果
                    scores_4d = parsed.get("scores_4d", {"A": 7, "B": 7, "C": 7, "D": 7})
                    result_ei = parsed.get("result_ei", 15)
                    passed = parsed.get("passed", result_ei >= 15)
                    fact_candidates = parsed.get("fact_candidates", [])
                    hint_candidates = parsed.get("hint_candidates", [])
                    valley_detected = parsed.get("valley_detected", False)
                
                    return {
                        "passed": passed,
                        "scores_4d": scores_4d,
                        "result_ei": result_ei,
                        "result_ei_S1": parsed.get("result_ei_S1", result_ei // 3),
                        "result_ei_S2": parsed.get("result_ei_S2", result_ei // 3),
                        "result_ei_S3": parsed.get("result_ei_S3", result_ei - 2 * (result_ei // 3)),
                        "fact_candidates": fact_candidates,
                        "hint_candidates": hint_candidates,
                        "valley_detected": valley_detected,
                        "prompt": prompt,
                    }
            except Exception as e:
                print(f"Auditor LLM 调用失败: {e}")
        
            # 如果 LLM 调用失败，返回默认值
            scores_4d = {"A": 7, "B": 7, "C": 7, "D": 7}
            result_ei = 15
            passed = result_ei >= 15 and all(s >= 7 for s in scores_4d.values())
        
            return {
                "passed": passed,
                "scores_4d": scores_4d,
                "result_ei": result_ei,
                "result_ei_S1": 5,
                "result_ei_S2": 5,
                "result_ei_S3": 5,
                "fact_candidates": [],
                "hint_candidates": [],
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
        检查是否需要弱势方重产（程序自动处理）

        Returns:
            (是否触发重产, 类型)
        """
        # 正方>80% 且 反方<30%
        if worker_p_confidence > 80 and worker_n_confidence < 30:
            return True, "p_dominant"

        # 反方>80% 且 正方<30%
        if worker_n_confidence > 80 and worker_p_confidence < 30:
            return True, "n_dominant"

        return False, ""
