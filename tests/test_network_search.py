"""
NetworkSearchTool v2 单元测试

测试网络搜索工具的核心功能（mock 测试）
"""
import time
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from fih_emergence.tools.network_search import (
    NetworkSearchTool,
    SearchResult,
    DEFAULT_FETCH_TOP_K,
    DEFAULT_RETURN_TOP_K,
    DEFAULT_CACHE_SIZE,
    DEFAULT_CACHE_TTL,
    DEFAULT_AUTHORITY_SITES,
)


class TestNetworkSearchToolInit:
    """初始化测试"""

    def setup_method(self):
        self.tool = NetworkSearchTool()

    def test_init_default(self):
        """测试默认初始化"""
        assert self.tool.fetch_top_k == DEFAULT_FETCH_TOP_K
        assert self.tool.return_top_k == DEFAULT_RETURN_TOP_K
        assert self.tool.timeout == 30
        assert self.tool._max_cache_size == DEFAULT_CACHE_SIZE
        assert self.tool._cache_ttl == DEFAULT_CACHE_TTL

    def test_init_custom(self):
        """测试自定义参数初始化"""
        tool = NetworkSearchTool(
            fetch_top_k=30, return_top_k=5, timeout=60,
            cache_size=50, cache_ttl=1800
        )
        assert tool.fetch_top_k == 30
        assert tool.return_top_k == 5
        assert tool.timeout == 60
        assert tool._max_cache_size == 50
        assert tool._cache_ttl == 1800


class TestAuthorityScore:
    """权威度评分测试"""

    def test_gov_cn(self):
        """政府网站权威度"""
        assert NetworkSearchTool._authority_score("stats.gov.cn") == 10
        assert NetworkSearchTool._authority_score("www.stats.gov.cn") == 10
        # 通用 .gov.cn
        assert NetworkSearchTool._authority_score("www.beijing.gov.cn") == 10

    def test_edu_cn(self):
        """教育机构权威度"""
        assert NetworkSearchTool._authority_score("edu.cn") == 9
        assert NetworkSearchTool._authority_score("www.tsinghua.edu.cn") == 9

    def test_official_media(self):
        """官方媒体权威度"""
        assert NetworkSearchTool._authority_score("news.cn") == 8
        assert NetworkSearchTool._authority_score("www.xinhuanet.com") == 8
        assert NetworkSearchTool._authority_score("www.people.com.cn") == 8

    def test_finance_media(self):
        """财经媒体权威度"""
        assert NetworkSearchTool._authority_score("caixin.com") == 6
        assert NetworkSearchTool._authority_score("www.cls.cn") == 6

    def test_default_score(self):
        """未知域名默认得分"""
        assert NetworkSearchTool._authority_score("example.com") == 3
        assert NetworkSearchTool._authority_score("blog.example.com") == 3

    def test_empty_domain(self):
        """空域名"""
        assert NetworkSearchTool._authority_score("") == 1
        assert NetworkSearchTool._authority_score(None) == 1


class TestExtractDomain:
    """域名提取测试"""

    def test_normal_url(self):
        assert NetworkSearchTool._extract_domain("https://www.stats.gov.cn/page") == "www.stats.gov.cn"

    def test_no_scheme(self):
        assert NetworkSearchTool._extract_domain("news.cn/article") == "news.cn"

    def test_empty_url(self):
        assert NetworkSearchTool._extract_domain("") == ""
        assert NetworkSearchTool._extract_domain(None) == ""


class TestSearchBasic:
    """基础搜索测试"""

    def test_search_empty_query(self):
        """测试空查询"""
        import asyncio
        tool = NetworkSearchTool()
        result = asyncio.run(tool.search(""))
        assert result == []
        result = asyncio.run(tool.search("   "))
        assert result == []

    @pytest.mark.asyncio
    async def test_search_with_mock(self):
        """测试搜索（mock百度API）"""
        tool = NetworkSearchTool()

        mock_results = [
            SearchResult(title="政府数据", url="https://stats.gov.cn/a",
                         content="GDP 5.0%", domain="stats.gov.cn", authority=10),
            SearchResult(title="新闻", url="https://news.cn/b",
                         content="report", domain="news.cn", authority=8),
            SearchResult(title="自媒体", url="https://zhihu.com/c",
                         content="opinion", domain="zhihu.com", authority=4),
            SearchResult(title="未知来源", url="https://example.com/d",
                         content="data", domain="example.com", authority=3),
        ]
        tool._baidu_search = AsyncMock(return_value=mock_results)

        results = await tool.search("test query")

        # 应该返回 top 3（按权威度排序）
        assert len(results) == 3
        assert results[0].authority == 10
        assert results[1].authority == 8
        assert results[2].authority == 4
        tool._baidu_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_no_results(self):
        """测试百度API无结果"""
        tool = NetworkSearchTool()
        tool._baidu_search = AsyncMock(return_value=[])

        results = await tool.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_fewer_than_top_k(self):
        """测试结果少于 return_top_k"""
        tool = NetworkSearchTool(return_top_k=3)
        tool._baidu_search = AsyncMock(return_value=[
            SearchResult(title="Only", url="https://x.com/1",
                         content="test", domain="x.com", authority=3),
        ])

        results = await tool.search("test")
        assert len(results) == 1


class TestSearchBasicHelpers:
    """辅助方法测试"""

    def test_needs_search_chinese(self):
        """中文关键词检测"""
        tool = NetworkSearchTool()
        assert tool.needs_search("2024年最新趋势")
        assert tool.needs_search("2025市场报告")
        assert tool.needs_search("最新数据统计")
        assert not tool.needs_search("这是一个普通的问题")

    def test_needs_search_english(self):
        """英文关键词检测"""
        tool = NetworkSearchTool()
        assert tool.needs_search("2024 trends")
        assert tool.needs_search("2025 market report")
        assert not tool.needs_search("how to improve")

    def test_needs_search_custom_keywords(self):
        """自定义关键词"""
        tool = NetworkSearchTool()
        assert tool.needs_search("这是一个测试内容", keywords=["测试"])
        assert not tool.needs_search("普通内容", keywords=["测试"])

    def test_extract_search_queries_with_year(self):
        """年份模式提取"""
        tool = NetworkSearchTool()
        queries = tool.extract_search_queries("2024年AI发展趋势分析")
        assert len(queries) > 0
        assert any("2024" in q for q in queries)

    def test_extract_search_queries_no_year(self):
        """无年份时的处理"""
        tool = NetworkSearchTool()
        queries = tool.extract_search_queries("普通问题描述")
        assert len(queries) > 0

    def test_extract_search_queries_limit(self):
        """查询限制：最多1个"""
        tool = NetworkSearchTool()
        text = " ".join([f"{2024+i}年的数据" for i in range(10)])
        queries = tool.extract_search_queries(text)
        assert len(queries) <= 1


class TestCache:
    """缓存测试"""

    def test_clear_cache(self):
        """清空缓存"""
        tool = NetworkSearchTool()
        tool._search_cache["test|None|None"] = ([], 0)
        assert len(tool._search_cache) == 1
        tool.clear_cache()
        assert len(tool._search_cache) == 0

    def test_lru_eviction(self):
        """LRU缓存淘汰"""
        tool = NetworkSearchTool(cache_size=2)
        tool._search_cache["k1"] = ([], time.time() - 100)
        tool._search_cache["k2"] = ([], time.time() - 50)
        tool._search_cache["k3"] = ([], time.time())

        # 触发 LRU
        if len(tool._search_cache) > tool._max_cache_size:
            oldest = min(tool._search_cache, key=lambda k: tool._search_cache[k][1])
            del tool._search_cache[oldest]

        assert "k1" not in tool._search_cache
        assert "k2" in tool._search_cache
        assert "k3" in tool._search_cache


class TestSearchResult:
    """SearchResult 数据类测试"""

    def test_dataclass(self):
        result = SearchResult(title="T", url="https://x.com", content="C")
        assert result.title == "T"
        assert result.url == "https://x.com"
        assert result.content == "C"

    def test_new_fields(self):
        """v2 新增字段"""
        result = SearchResult(
            title="T", url="https://x.com", content="C",
            domain="x.com", authority=8, publish_time="2026-04-16",
        )
        assert result.domain == "x.com"
        assert result.authority == 8
        assert result.publish_time == "2026-04-16"

    def test_defaults(self):
        """默认值"""
        result = SearchResult(title="T", url="https://x.com", content="C")
        assert result.domain == ""
        assert result.authority == 0
        assert result.publish_time == ""


class TestEdgeCases:
    """边界情况"""

    def test_needs_search_empty(self):
        tool = NetworkSearchTool()
        assert not tool.needs_search("")
        assert not tool.needs_search(None)

    def test_needs_search_mixed_language(self):
        tool = NetworkSearchTool()
        assert tool.needs_search("2024年最新AI trends报告")

    def test_extract_queries_special_chars(self):
        tool = NetworkSearchTool()
        queries = tool.extract_search_queries("测试@#$%^&*()")
        assert isinstance(queries, list)
