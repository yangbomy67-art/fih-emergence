# 网络搜索功能探索

## 方案对比

| 方案 | 优点 | 缺点 | 成本 |
|------|------|------|------|
| **Tavily AI** | 专为 AI 设计，结构化结果，支持 RAG | 付费，免费额度有限 | $5/月起 |
| **SerpAPI** | Google 真实结果，权威性高 | 付费，按调用次数 | $50/月 |
| **DuckDuckGo** | 免费，可商用 | 需自己解析 HTML | $0 |
| **Brave Search** | 免费，隐私优先 | 覆盖不如 Google | $0 |
| **Jina AI Reader** | 免费，网页内容提取 | 非搜索 API | $0 |

## FIH Emergence 场景分析

网络搜索在 FIH 中的定位：
- **Hint 来源**：AI 搜索获取外部信息作为 Hint
- **Fact 验证**：搜索验证 Fact 准确性
- **实时知识**：获取最新行业信息

## 推荐方案

### 方案 A: Tavily API（推荐）
- 专为 AI 设计，返回结构化 JSON
- 支持 RAG 模式，直接返���答案而非链接
- 集成简单，有 Python SDK

### 方案 B: DuckDuckGo + Jina（免费方案）
- DuckDuckGo 搜索 → Jina Reader 提取内容
- 完全免费，适合开发测试

## 集成架构

```
Worker (推理) 
    ↓ 需要实时信息
Network Search Tool
    ↓ 返回内容
Hint → Auditor 审核 → Manager 裁决 → Fact
```
