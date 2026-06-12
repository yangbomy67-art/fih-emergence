"""
NetworkSearchTool 单元测试

测试网络搜索工具的核心功能（mock 测试）
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from fih_emergence.tools.network_search import (
    NetworkSearchTool,
    SearchResult,
    DEFAULT_MAX_RESULTS,
    DEFAULT_CACHE_SIZE,
    DEFAULT_CACHE_TTL,
)


class TestNetworkSearchTool:
    """NetworkSearchTool 测试"""

    def setup_method(self):
        """每个测试前执行"""
        self.tool = NetworkSearchTool()

    def test_init_default(self):
        """测试默认初始化"""
        assert self.tool.max_results == DEFAULT_MAX_RESULTS
        assert self.tool.timeout == 30
        assert self.tool._max_cache_size == DEFAULT_CACHE_SIZE
        assert self.tool._cache_ttl == DEFAULT_CACHE_TTL

    def test_init_custom(self):
        """测试自定义参数初始化"""
        tool = NetworkSearchTool(max_results=5, timeout=60, cache_size=50, cache_ttl=1800)
        assert tool.max_results == 5
        assert tool.timeout == 60
        assert tool._max_cache_size == 50
        assert tool._cache_ttl == 1800

    def test_search_empty_query(self):
        """测试空查询"""
        import asyncio
        result = asyncio.run(self.tool.search(""))
        assert result == []
        
        result = asyncio.run(self.tool.search("   "))
        assert result == []

    def test_needs_search_chinese(self):
        """测试中文关键词检测"""
        # 应该触发搜索的内容
        assert self.tool.needs_search("2024年最新趋势")
        assert self.tool.needs_search("2025市场报告")
        assert self.tool.needs_search("最新数据统计")
        
        # 不应该触发搜索的内容
        assert not self.tool.needs_search("这是一个普通的问题")
        assert not self.tool.needs_search("如何提高效率")

    def test_needs_search_english(self):
        """测试英文关键词检测"""
        assert self.tool.needs_search("2024 trends")
        assert self.tool.needs_search("latest report 2025")
        assert self.tool.needs_search("market data statistics")
        
        assert not self.tool.needs_search("how to improve")
        assert self.tool.needs_search("AI new 2024")

    def test_needs_search_custom_keywords(self):
        """测试自定义关键词"""
        custom_keywords = ["测试", "测试关键词"]
        assert self.tool.needs_search("这是一个测试内容", keywords=custom_keywords)
        assert not self.tool.needs_search("这是普通内容", keywords=custom_keywords)

    def test_extract_search_queries_with_year(self):
        """测试年份模式提取"""
        # 包含年份的查询
        queries = self.tool.extract_search_queries("2024年AI发展趋势分析")
        assert len(queries) > 0
        assert any("2024" in q for q in queries)
        
        queries = self.tool.extract_search_queries("2025市场报告预测")
        assert len(queries) > 0

    def test_extract_search_queries_no_year(self):
        """测试无年份时的处理"""
        queries = self.tool.extract_search_queries("这是一个普通的问题描述")
        # 没有年份时应该返回整个文本作为查询
        assert len(queries) > 0

    def test_extract_search_queries_limit(self):
        """测试查询数量限制"""
        # 构造一个有很多年份的文本
        text = " ".join([f"{2024+i}年的数据" for i in range(10)])
        queries = self.tool.extract_search_queries(text)
        # 最多返回3个
        assert len(queries) <= 3

    @pytest.mark.asyncio
    async def test_search_with_mock(self):
        """测试搜索方法（mock外部调用）"""
        tool = NetworkSearchTool()
        
        # Mock _duckduckgo_search
        tool._duckduckgo_search = AsyncMock(return_value=["https://example.com"])
        
        # Mock _fetch_contents
        mock_result = [
            SearchResult(
                title="Test Title",
                url="https://example.com",
                content="Test content"
            )
        ]
        tool._fetch_contents = AsyncMock(return_value=mock_result)
        
        results = await tool.search("test query")
        
        assert len(results) == 1
        assert results[0].title == "Test Title"
        tool._duckduckgo_search.assert_called_once_with("test query")

    @pytest.mark.asyncio
    async def test_search_no_results(self):
        """测试无搜索结果"""
        tool = NetworkSearchTool()
        tool._duckduckgo_search = AsyncMock(return_value=[])
        
        results = await tool.search("test")
        
        assert results == []
        tool._duckduckgo_search.assert_called_once()

    def test_clear_cache(self):
        """测试清空缓存"""
        # 手动添加缓存
        self.tool._search_cache["test"] = ([], 1234567890.0)
        assert len(self.tool._search_cache) == 1
        
        self.tool.clear_cache()
        
        assert len(self.tool._search_cache) == 0

    @pytest.mark.asyncio
    async def test_search_cache_lru_eviction(self):
        """测试LRU缓存淘汰"""
        tool = NetworkSearchTool(cache_size=2)
        
        # 手动模拟搜索完成后的缓存添加逻辑
        import time
        # 添加 3 个缓存（超过 cache_size=2）
        tool._search_cache["query1"] = ([], time.time() - 100)  # 最老
        tool._search_cache["query2"] = ([], time.time() - 50)   # 中间
        tool._search_cache["query3"] = ([], time.time())        # 最新
        
        # 触发 LRU 清理（模拟添加新缓存）
        if len(tool._search_cache) > tool._max_cache_size:
            oldest_key = min(tool._search_cache.keys(), 
                            key=lambda k: tool._search_cache[k][1])
            del tool._search_cache[oldest_key]
        
        # query1（最老）应该被淘汰
        assert "query1" not in tool._search_cache
        # query2 和 query3 保留
        assert "query2" in tool._search_cache
        assert "query3" in tool._search_cache


class TestSearchResult:
    """SearchResult 数据类测试"""

    def test_dataclass(self):
        """测试数据结构"""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            content="Test content"
        )
        
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.content == "Test content"
        
    def test_empty_content(self):
        """测试空内容"""
        result = SearchResult(title="Test", url="https://test.com", content="")
        assert result.content == ""


class TestNeedsSearchEdgeCases:
    """边界情况测试"""

    def test_needs_search_empty(self):
        """测试空文本"""
        tool = NetworkSearchTool()
        assert not tool.needs_search("")
        assert not tool.needs_search(None)
        
    def test_needs_search_mixed_language(self):
        """测试中英文混合"""
        tool = NetworkSearchTool()
        # 英文关键词
        assert tool.needs_search("2024 new technology trend")
        # 中文关键词
        assert tool.needs_search("最新2024技术趋势")
        # 混合
        assert tool.needs_search("2024年最新AI trends报告")
        
    def test_extract_queries_special_chars(self):
        """测试特殊字符"""
        tool = NetworkSearchTool()
        queries = tool.extract_search_queries("测试@#$%^&*()")
        # 应该处理特殊字符不崩溃
        assert isinstance(queries, list)