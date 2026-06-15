"""
NetworkSearchTool v2 - 网络搜索工具

基于百度千帆 AI 搜索 API
流程: API拉取50条 → 权威度排序 → 返回Top 3原文

用法:
    tool = NetworkSearchTool(api_key="bce-v3/...")
    results = await tool.search("AI agents 2024 trends")
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger("fih.network_search")

# 默认配置
DEFAULT_FETCH_TOP_K = 50        # API 拉取数量
DEFAULT_RETURN_TOP_K = 3        # 过滤后返回数量
DEFAULT_TIMEOUT = 30
DEFAULT_CACHE_SIZE = 100
DEFAULT_CACHE_TTL = 3600        # 1小时
BAIDU_SEARCH_API = "https://qianfan.baidubce.com/v2/ai_search/web_search"

# 权威度评分规则
AUTHORITY_RULES = [
    # (匹配模式, 分数, 说明)
    (["stats.gov.cn", "www.stats.gov.cn"], 10, "国家统计局"),
    (["gov.cn"], 10, "政府网站"),
    (["edu.cn"], 9, "教育机构"),
    (["news.cn", "xinhuanet.com", "cctv.com", "people.com.cn"], 8, "官方媒体"),
    (["std.gov.cn", "nmpa.gov.cn", "mof.gov.cn"], 8, "标准/监管机构"),
    (["caixin.com", "cls.cn", "yicai.com"], 6, "财经媒体"),
    (["36kr.com", "jiemian.com", "thepaper.cn"], 5, "科技/综合媒体"),
    (["zhihu.com", "weixin.qq.com", "zhuanlan.zhihu.com"], 4, "自媒体/问答"),
]
DEFAULT_AUTHORITY_SCORE = 3
NO_DOMAIN_SCORE = 1

# 默认高权威站点（Auditor 搜索时自动添加）
DEFAULT_AUTHORITY_SITES = [
    "stats.gov.cn",
    "news.cn",
    "xinhuanet.com",
    "gov.cn",
    "edu.cn",
]


@dataclass
class SearchResult:
    """搜索结果"""
    title: str
    url: str
    content: str           # 摘要内容（原文，不压缩）
    domain: str = ""       # 域名
    authority: int = 0     # 权威度评分 1-10
    publish_time: str = "" # 发布时间


class NetworkSearchTool:
    """网络搜索工具 v2 (百度千帆 + 权威度过滤)"""

    def __init__(
        self,
        fetch_top_k: int = DEFAULT_FETCH_TOP_K,
        return_top_k: int = DEFAULT_RETURN_TOP_K,
        timeout: int = DEFAULT_TIMEOUT,
        cache_size: int = DEFAULT_CACHE_SIZE,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        api_key: str = None,
    ):
        self.fetch_top_k = fetch_top_k
        self.return_top_k = return_top_k
        self.timeout = timeout
        self._max_cache_size = cache_size
        self._cache_ttl = cache_ttl
        # 缓存格式: {query: (results, timestamp)}
        self._search_cache: dict[str, tuple[list[SearchResult], float]] = {}

        # API Key: 从环境变量或参数获取
        self._api_key = api_key or os.environ.get("BAIDU_API_KEY", "")
        if not self._api_key:
            logger.warning("未设置 BAIDU_API_KEY 环境变量")

    async def search(
        self,
        query: str,
        site_filter: Optional[list[str]] = None,
        time_range: Optional[tuple[str, str]] = None,
    ) -> list[SearchResult]:
        """
        执行网络搜索

        Args:
            query: 搜索关键词
            site_filter: 指定站点列表（如 ["stats.gov.cn", "news.cn"]）
            time_range: 时间范围 ("2026-01-01", "2026-06-01")

        Returns:
            权威度排序后的 Top return_top_k 条结果
        """
        if not query or not query.strip():
            logger.warning("搜索关键词为空，跳过")
            return []

        query = query.strip()

        # 检查缓存
        cache_key = f"{query}|{site_filter}|{time_range}"
        if cache_key in self._search_cache:
            cached_results, timestamp = self._search_cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                logger.info(f"使用缓存: {query}")
                return cached_results
            else:
                del self._search_cache[cache_key]

        try:
            # 1. 百度 API 拉取 50 条
            raw_results = await self._baidu_search(query, site_filter, time_range)
            if not raw_results:
                logger.warning(f"百度搜索无结果: {query}")
                return []

            # 2. 权威度评分 + 排序
            for r in raw_results:
                r.authority = self._authority_score(r.domain or self._extract_domain(r.url))

            raw_results.sort(key=lambda r: r.authority, reverse=True)

            # 3. 取 Top N
            results = raw_results[:self.return_top_k]

            # 缓存
            self._search_cache[cache_key] = (results, time.time())
            if len(self._search_cache) > self._max_cache_size:
                oldest_key = min(self._search_cache.keys(),
                                key=lambda k: self._search_cache[k][1])
                del self._search_cache[oldest_key]

            logger.info(
                f"搜索完成: {query}, "
                f"拉取{len(raw_results)}条 → 权威度排序 → 返回{len(results)}条"
            )
            return results

        except Exception as e:
            logger.error(f"搜索失败: {query}, error: {e}")
            return []

    async def _baidu_search(
        self,
        query: str,
        site_filter: Optional[list[str]] = None,
        time_range: Optional[tuple[str, str]] = None,
    ) -> list[SearchResult]:
        """
        百度千帆 AI 搜索 API

        Args:
            query: 搜索关键词
            site_filter: 站点过滤列表
            time_range: 时间范围 (start, end)
        """
        import requests

        if not self._api_key:
            logger.warning("未配置百度 API Key")
            return []

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "messages": [{"content": query, "role": "user"}],
            "search_source": "baidu_search_v2",
            "resource_type_filter": [{"type": "web", "top_k": self.fetch_top_k}],
        }

        # 构建搜索过滤条件
        search_filter = {}

        if site_filter:
            search_filter["match"] = {"site": site_filter}

        if time_range:
            start, end = time_range
            search_filter["range"] = {
                "page_time": {
                    "gte": start,
                    "lte": end,
                }
            }

        if search_filter:
            data["search_filter"] = search_filter

        results = []

        try:
            resp = requests.post(
                BAIDU_SEARCH_API,
                headers=headers,
                json=data,
                timeout=self.timeout,
            )

            if resp.status_code != 200:
                logger.warning(f"百度搜索请求失败: {resp.status_code}, {resp.text[:200]}")
                return []

            result = resp.json()
            references = result.get("references", [])

            for ref in references:
                title = ref.get("title", "")
                ref_url = ref.get("url", "")
                content = ref.get("content", "") or ref.get("snippet", "")
                publish_time = ref.get("date", "") or ref.get("page_time", "")

                if ref_url:
                    domain = self._extract_domain(ref_url)
                    authority = self._authority_score(domain)
                    results.append(SearchResult(
                        title=title,
                        url=ref_url,
                        content=content[:500] if content else "[无摘要]",
                        domain=domain,
                        authority=authority,
                        publish_time=publish_time,
                    ))

        except requests.Timeout:
            logger.warning(f"百度搜索请求超时: {query}")
        except Exception as e:
            logger.error(f"百度搜索请求异常: {e}")

        return results

    # ========== 权威度评分 ==========

    @staticmethod
    def _extract_domain(url: str) -> str:
        """从 URL 提取域名"""
        if not url:
            return ""
        try:
            # 无 scheme 时 urlparse 无法正确解析，补上 //
            if "://" not in url:
                url = "//" + url
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return ""

    @staticmethod
    def _authority_score(domain: str) -> int:
        """
        域名权威度评分

        规则:
          gov.cn          → 10
          edu.cn          → 9
          stats.gov.cn    → 10
          官媒(news.cn等) → 8
          财经媒体        → 6
          科技/综合       → 5
          自媒体/问答     → 4
          其他            → 3
          无域名          → 1
        """
        if not domain:
            return NO_DOMAIN_SCORE

        domain_lower = domain.lower()

        for patterns, score, _label in AUTHORITY_RULES:
            for pat in patterns:
                if domain_lower == pat or domain_lower.endswith("." + pat):
                    return score

        return DEFAULT_AUTHORITY_SCORE

    # ========== 缓存 ==========

    def clear_cache(self):
        """清空缓存"""
        self._search_cache.clear()
        logger.info("搜索缓存已清空")

    # ========== 辅助方法 ==========

    @staticmethod
    def needs_search(text: str, keywords: Optional[list[str]] = None) -> bool:
        """
        判断文本是否需要搜索验证
        """
        if not text or not text.strip():
            return False

        if keywords is None:
            keywords = [
                "最新", "2024", "2025", "2026", "趋势", "市场", "报告",
                "数据", "统计", "增长", "下降",
            ]

        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in keywords)

    @staticmethod
    def extract_search_queries(text: str) -> list[str]:
        """
        从文本中提取可搜索的关键词（只取1个最关键的）
        """
        import re

        queries = []

        year_patterns = [
            r'(202[4-9])\s*(?:年|的)?\s*(\w+)',
            r'(\w+)\s*(?:202[4-9]|年|趋势)',
        ]

        for pattern in year_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    query = " ".join(match)
                else:
                    query = match
                if len(query) > 3:
                    queries.append(query)

        if not queries and len(text) > 5:
            queries = [text[:50]]

        return queries[:1]


async def main():
    """测试"""
    api_key = os.environ.get("BAIDU_API_KEY", "")
    tool = NetworkSearchTool(api_key=api_key)

    query = "湖南产业 2026年一季度GDP"
    print(f"搜索: {query}")

    results = await tool.search(
        query,
        site_filter=["stats.gov.cn", "news.cn", "gov.cn"],
    )
    print(f"\n结果: {len(results)} 条\n")

    for i, r in enumerate(results, 1):
        print(f"{i}. [{r.authority}] {r.title}")
        print(f"   URL: {r.url}")
        print(f"   域名: {r.domain}")
        print(f"   内容: {r.content[:150]}...")
        print()


if __name__ == "__main__":
    asyncio.run(main())
