"""
NetworkSearchTool - 网络搜索工具

基于百度智能搜索 API + 本地 trafilatura 提取

用法:
    tool = NetworkSearchTool(api_key="bce-v3/...")
    results = await tool.search("AI agents 2024 trends")
"""

import asyncio
import logging
import os
import time
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("fih.network_search")

# 默认配置
DEFAULT_MAX_RESULTS = 3
DEFAULT_TIMEOUT = 30
DEFAULT_CACHE_SIZE = 100
DEFAULT_CACHE_TTL = 3600  # 1小时
BAIDU_SEARCH_API = "https://qianfan.baidubce.com/v2/ai_search/web_search"


@dataclass
class SearchResult:
    """搜索结果"""
    title: str
    url: str
    content: str  # 提取的网页内容摘要


class NetworkSearchTool:
    """网络搜索工具 (百度智能搜索 API + 本地 trafilatura)"""

    def __init__(
        self,
        max_results: int = DEFAULT_MAX_RESULTS,
        timeout: int = DEFAULT_TIMEOUT,
        cache_size: int = DEFAULT_CACHE_SIZE,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        api_key: str = None,
    ):
        self.max_results = max_results
        self.timeout = timeout
        self._max_cache_size = cache_size
        self._cache_ttl = cache_ttl
        # 缓存格式: {query: (results, timestamp)}
        self._search_cache: dict[str, tuple[list[SearchResult], float]] = {}
        
        # API Key: 从环境变量或参数获取
        self._api_key = api_key or os.environ.get("BAIDU_API_KEY", "")
        if not self._api_key:
            logger.warning("未设置 BAIDU_API_KEY 环境变量")

    async def search(self, query: str) -> list[SearchResult]:
        """
        执行网络搜索

        Args:
            query: 搜索关键词

        Returns:
            搜索结果列表
        """
        if not query or not query.strip():
            logger.warning("搜索关键词为空，跳过")
            return []

        query = query.strip()

        # 检查缓存（有 TTL）
        if query in self._search_cache:
            cached_results, timestamp = self._search_cache[query]
            if time.time() - timestamp < self._cache_ttl:
                logger.info(f"使用缓存: {query}")
                return cached_results
            else:
                # 缓存过期，删除
                del self._search_cache[query]

        try:
            # 1. 百度搜索 API 获取 URLs 和内容摘要
            results = await self._baidu_search(query)
            if not results:
                logger.warning(f"百度搜索无结果: {query}")
                return []

            # 缓存结果（带时间戳）
            self._search_cache[query] = (results, time.time())
            # LRU 清理：如果缓存超过大小限制，删除最老的
            if len(self._search_cache) > self._max_cache_size:
                oldest_key = min(self._search_cache.keys(), 
                                key=lambda k: self._search_cache[k][1])
                del self._search_cache[oldest_key]
            
            logger.info(f"搜索完成: {query}, 获取 {len(results)} 条结果")

            return results

        except Exception as e:
            logger.error(f"搜索失败: {query}, error: {e}")
            return []

    async def _baidu_search(self, query: str) -> list[SearchResult]:
        """
        百度智能搜索 API - 直接返回标题+URL+摘要
        """
        import requests
        
        if not self._api_key:
            logger.warning("未配置百度 API Key")
            return []

        url = BAIDU_SEARCH_API
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messages": [
                {"content": query, "role": "user"}
            ],
            "search_source": "baidu_search_v2",
            "resource_type_filter": [{"type": "web", "top_k": self.max_results}],
        }

        results = []
        
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=self.timeout)
            
            if resp.status_code != 200:
                logger.warning(f"百度搜索请求失败: {resp.status_code}")
                return []

            result = resp.json()
            references = result.get("references", [])
            
            for ref in references[:self.max_results]:
                title = ref.get("title", "")
                ref_url = ref.get("url", "")
                content = ref.get("content", "") or ref.get("snippet", "")
                
                if ref_url:
                    results.append(SearchResult(
                        title=title,
                        url=ref_url,
                        content=content[:500] if content else "[无摘要]"
                    ))

        except requests.Timeout:
            logger.warning(f"百度搜索请求超时: {query}")
        except Exception as e:
            logger.error(f"百度搜索请求异常: {e}")

        return results

    def clear_cache(self):
        """清空缓存"""
        self._search_cache.clear()
        logger.info("搜索缓存已清空")

    def needs_search(self, text: str, keywords: list[str] = None) -> bool:
        """
        判断文本是否需要搜索验证

        Args:
            text: 待检查文本
            keywords: 触发搜索的关键词（默认内置）

        Returns:
            是否需要搜索
        """
        if not text or not text.strip():
            return False
        
        if keywords is None:
            # 默认关键词
            keywords = [
                "最新", "2024", "2025", "2026", "趋势", "市场", "报告",
                "数据", "统计", "增长", "下降",
            ]

        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in keywords)

    def extract_search_queries(self, text: str) -> list[str]:
        """
        从文本中提取可搜索的关键词（只取1个最关键的）

        Args:
            text: 待提取文本

        Returns:
            搜索关键词列表（最多1个）
        """
        import re
        
        queries = []

        # 匹配年份 patterns（优先找年份+产业相关的）
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

        # 如果没有提取到，返回整个文本作为查询
        if not queries and len(text) > 5:
            queries = [text[:50]]  # 取前50字符

        # 只返回1个最关键的搜索词
        return queries[:1]  # 最多1个查询


async def main():
    """测试"""
    api_key = os.environ.get("BAIDU_API_KEY", "")
    tool = NetworkSearchTool(api_key=api_key)

    # 测试搜索
    query = "湖南产业 2026年一季度GDP"
    print(f"搜索: {query}")

    results = await tool.search(query)
    print(f"\n结果: {len(results)} 条\n")

    for i, r in enumerate(results, 1):
        print(f"{i}. {r.title}")
        print(f"   URL: {r.url}")
        print(f"   内容: {r.content[:150]}...")
        print()


if __name__ == "__main__":
    asyncio.run(main())