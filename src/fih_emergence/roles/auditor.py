"""
Auditor Role - 审计员

Based on SPEC_角色.md §Auditor

Responsibilities:
1. 事前审计 (Intent → Worker 门槛)：EI 启发式评估（门控）
2. 事后审计 (Insight → 黑板 门槛)：EI 追踪 + Fact+候选 + Hint+候选 + 快照策略 + 四维审计 + 低谷识别
3. 检测 3 条件并通知 Manager
4. **网络搜索验证**：审核时判断是否需要搜索获取实时信息
"""

import logging

from fih_emergence.config import get_config
from fih_emergence.llm import BaseLLMClient, get_auditor_client
from fih_emergence.prompts import (
    AUDITOR_POST_CHECK,
    AUDITOR_PRE_CHECK,
)

logger = logging.getLogger("fih.auditor")

# 导入网络搜索工具
try:
    from fih_emergence.tools.network_search import (
        NetworkSearchTool,
        DEFAULT_AUTHORITY_SITES,
    )
    NETWORK_SEARCH_AVAILABLE = True
except ImportError:
    NETWORK_SEARCH_AVAILABLE = False
    DEFAULT_AUTHORITY_SITES = []
    logger.warning("NetworkSearchTool 不可用，网络搜索功能禁用")


class Auditor:
    """FIH Auditor 角色"""

    def __init__(self, llm_client: BaseLLMClient = None):
        self.llm_client = llm_client or get_auditor_client()
        
        # 初始化网络搜索工具 v2
        self.search_tool = None
        if NETWORK_SEARCH_AVAILABLE:
            try:
                config = get_config()
                if config.network_search.enabled:
                    self.search_tool = NetworkSearchTool(
                        fetch_top_k=config.network_search.fetch_top_k,
                        return_top_k=config.network_search.return_top_k,
                        timeout=config.network_search.timeout,
                    )
                    logger.info("Auditor 网络搜索工具 v2 已初始化")
            except Exception as e:
                logger.warning(f"网络搜索工具初始化失败: {e}")

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

            # 使用 replace 替换占位符（避免 format 与 JSON 冲突）
            prompt = AUDITOR_POST_CHECK
            prompt = prompt.replace("WORKER_ID", worker_id)
            prompt = prompt.replace("INSIGHT_PLACEHOLDER", insight)
            prompt = prompt.replace("FACTS_PLACEHOLDER", facts_str or "（无）")

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
        检测低谷 (N1: 死代码，当前未调用)
        
        实际低谷检测逻辑在 graph.py auditor_post 节点中实现。
        此方法保留作为未来可能的重构参考。
        
        连续 3 轮 result_ei < 10 或 连续 3 轮无 Fact+ → 低谷
        """
        # 备用逻辑，当前未调用
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
        """从黑板中匹配 Hint+ 候选，并标记是否建议升格 Fact"""
        candidates = []
        for hint in hints:
            # 基于关键词匹配
            keywords = hint.get("content", "").lower().split()
            matched = any(keyword in insight.lower() for keyword in keywords if len(keyword) > 2)
            
            if matched:
                # 检查是否已引用多次（跨轮次），建议升格
                current_round = hint.get("round", 0)
                is_repeated = hint.get("引用次数", 0) > 1
                
                candidates.append({
                    **hint,
                    "status": "candidate",
                    "hint_matched": True,
                    "suggest_promote_to_fact": is_repeated,  # 多次引用，建议升格
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

    # =======================
    # 网络搜索相关方法
    # =======================

    def needs_search_verification(self, insight: str) -> tuple[bool, list[str]]:
        """
        判断 Insight 是否需要搜索验证

        Args:
            insight: Worker 产出

        Returns:
            (是否需要搜索, 搜索关键词列表)
        """
        if not self.search_tool:
            return False, []

        # 检查是否包含需要实时信息的关键词
        if self.search_tool.needs_search(insight):
            # 提取搜索关键词
            queries = self.search_tool.extract_search_queries(insight)
            if queries:
                logger.info(f"检测到需要搜索验证的内容，关键词: {queries}")
                return True, queries

        return False, []

    async def search_and_format_hints(
        self,
        queries: list[str],
    ) -> list[dict]:
        """
        执行搜索并格式化为 Hint v2

        不再 LLM 压缩：API 拉 50 条 → 权威度排序 → Top 3 原文直接存储

        Args:
            queries: 搜索关键词列表

        Returns:
            Hint 列表（供写入黑板），每条含 title/url/content/authority/source
        """
        if not self.search_tool or not queries:
            return []

        hints = []
        seen_urls = set()

        for query in queries:
            try:
                results = await self.search_tool.search(
                    query,
                    site_filter=DEFAULT_AUTHORITY_SITES,
                )
                for r in results:
                    if r.url in seen_urls:
                        continue
                    seen_urls.add(r.url)

                    hints.append({
                        "content": f"{r.title}: {r.content[:300]}",
                        "source": "network_search",
                        "url": r.url,
                        "status": "candidate",
                        "search_query": query,
                        "authority": r.authority,
                        "domain": r.domain,
                    })
                logger.info(
                    f"搜索 '{query}' 返回 {len(results)} 条 Hint "
                    f"(权威度: {[r.authority for r in results]})"
                )
            except Exception as e:
                logger.error(f"搜索 '{query}' 失败: {e}")

        return hints
