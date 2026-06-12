"""
NetworkSearchTool - 网络搜索工具

基于 DuckDuckGo + Jina Reader 的免费方案

用法:
    tool = NetworkSearchTool()
    results = await tool.search("AI agents 2024 trends")
"""

import asyncio
import logging
import re
import time
import urllib.parse
from dataclasses import dataclass
from typing import Optional

import aiohttp
from aiohttp import ClientTimeout

logger = logging.getLogger("fih.network_search")

# 默认配置
DEFAULT_MAX_RESULTS = 3
DEFAULT_TIMEOUT = 30
DEFAULT_CACHE_SIZE = 100
DEFAULT_CACHE_TTL = 3600  # 1小时
JINA_READER_BASE = "https://r.jina.ai/"


@dataclass
class SearchResult:
    """搜索结果"""
    title: str
    url: str
    content: str  # 提取的网页内容摘要


class NetworkSearchTool:
    """网络搜索工具 (DuckDuckGo + Jina Reader)"""

    def __init__(
        self,
        max_results: int = DEFAULT_MAX_RESULTS,
        timeout: int = DEFAULT_TIMEOUT,
        cache_size: int = DEFAULT_CACHE_SIZE,
        cache_ttl: int = DEFAULT_CACHE_TTL,
    ):
        self.max_results = max_results
        self.timeout = timeout
        self._max_cache_size = cache_size
        self._cache_ttl = cache_ttl
        # 缓存格式: {query: (results, timestamp)}
        self._search_cache: dict[str, tuple[list[SearchResult], float]] = {}

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
            # 1. DuckDuckGo 搜索获取 URLs
            urls = await self._duckduckgo_search(query)
            if not urls:
                logger.warning(f"DuckDuckGo 无搜索结果: {query}")
                return []

            # 2. Jina Reader 提取内容
            results = await self._fetch_contents(urls)

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

    async def _duckduckgo_search(self, query: str) -> list[str]:
        """
        DuckDuckGo HTML 搜索

        Returns:
            URL 列表
        """
        # 编码查询
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        timeout = ClientTimeout(total=self.timeout)

        urls = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=timeout) as resp:
                    if resp.status != 200:
                        logger.warning(f"DuckDuckGo 请求失败: {resp.status}")
                        return []

                    html = await resp.text()

                    # 解析 HTML 提取 URL
                    # 匹配 <a class="result__a" href="...">
                    pattern = r'<a class="result__a"[^>]*href="([^"]*)"'
                    matches = re.findall(pattern, html)

                    for href in matches[:self.max_results]:
                        # DuckDuckGo 使用 /l/?uddg=URL 格式
                        if "/l/?uddg=" in href:
                            actual_url = href.split("/l/?uddg=")[1]
                            actual_url = urllib.parse.unquote(actual_url)
                            # 验证是有效 URL
                            if actual_url.startswith("http"):
                                urls.append(actual_url)

                        # 直接 URL
                        elif href.startswith("http"):
                            urls.append(href)

        except asyncio.TimeoutError:
            logger.warning(f"DuckDuckGo 请求超时: {query}")
        except Exception as e:
            logger.error(f"DuckDuckGo 请求异常: {e}")

        # 去重
        urls = list(dict.fromkeys(urls))[:self.max_results]
        return urls

    async def _fetch_contents(self, urls: list[str]) -> list[SearchResult]:
        """
        使用 Jina Reader 提取网页内容

        Args:
            urls: URL 列表

        Returns:
            搜索结果列表（含标题和内容）
        """
        results = []
        timeout = ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    # Jina Reader 提取（保留原始URL协议）
                    jina_url = JINA_READER_BASE + url
                    async with session.get(jina_url, timeout=timeout) as resp:
                        if resp.status != 200:
                            logger.warning(f"Jina 提取失败: {url}, status: {resp.status}")
                            # 即使提取失败，也保留 URL 作为结果
                            results.append(SearchResult(
                                title=url,
                                url=url,
                                content="[内容提取失败]"
                            ))
                            continue

                        text = await resp.text()

                        # Jina 返回格式：第一行是标题，后续是内容
                        lines = text.split("\n")
                        title = lines[0].strip() if lines else url
                        content = "\n".join(lines[1:]).strip()[:500]  # 限制内容长度

                        results.append(SearchResult(
                            title=title[:200],  # 限制标题长度
                            url=url,
                            content=content[:500] if content else "[无内容]"
                        ))

                except asyncio.TimeoutError:
                    logger.warning(f"Jina 请求超时: {url}")
                    results.append(SearchResult(
                        title=url,
                        url=url,
                        content="[请求超时]"
                    ))
                except Exception as e:
                    logger.warning(f"Jina 提取异常: {url}, error: {e}")
                    results.append(SearchResult(
                        title=url,
                        url=url,
                        content=f"[提取异常: {type(e).__name__}]"
                    ))

                # 速率限制
                await asyncio.sleep(1)

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
        if keywords is None:
            # 默认关键词
            keywords = [
                "最新", "2024", "2025", "2026", "趋势", "市场", "报告",
                "最新", "new", "latest", "2024", "2025", "trend", "report",
                "数据", "统计", "增长", "下降", "数据", "statistics",
            ]

        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in keywords)

    def extract_search_queries(self, text: str) -> list[str]:
        """
        从文本中提取可搜索的关键词

        Args:
            text: 待提取文本

        Returns:
            搜索关键词列表
        """
        # 简单的关键词提取：找包含年份/趋势等词汇的短语
        queries = []

        # 匹配年份 patterns
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

        return queries[:3]  # 最多3个查询


async def main():
    """测试"""
    tool = NetworkSearchTool()

    # 测试搜索
    query = "AI agents 2024 trends"
    print(f"搜索: {query}")

    results = await tool.search(query)
    print(f"\n结果: {len(results)} 条\n")

    for i, r in enumerate(results, 1):
        print(f"{i}. {r.title}")
        print(f"   URL: {r.url}")
        print(f"   内容: {r.content[:100]}...")
        print()


if __name__ == "__main__":
    asyncio.run(main())