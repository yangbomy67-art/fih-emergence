# SPEC_NetworkSearch - 网络搜索功能

## 目标

为 FIH Emergence 添加网络搜索能力，让 AI 可以获取实时外部信息作为 Hint。

---

## 1. 定位

网络搜索是 **Hint 来源** 的一种扩展：

| 来源 | 说明 | 触发者 |
|------|------|--------|
| 人工输入 | Human Gate 初始提供 | - |
| Worker 推理产出 | GAN 对抗产生的洞察 | Auditor |
| **网络搜索** | Auditor 审核时验证获取实时信息 | **Auditor** |

> **重要**：仅 Auditor 可以触发搜索（方案C：Auditor 守门员模式）

---

## 2. 架构（方案C）

```
Round N:
    1. Worker 推理产出 insight（不搜索）
        ↓ {"insight": "...", "confidence": 80}
    2. Auditor 审核
        ↓ "这个产出涉及最新趋势，需要验证"
        ↓ 调用 search_web("AI agents 2024")
        ↓ 搜索结果写入黑板作为 Hint
    3. 进入 Round N+1
        ↓ Worker 推理时自然读取黑板中的搜索结果 Hint
        ↓ 产出已融合实时信息的 insight
```

---

## 3. 实现方案

### 方案: DuckDuckGo + Jina Reader（免费）

| 组件 | 作用 | 依赖 |
|------|------|------|
| DuckDuckGo HTML | 搜索获取 URL | 无需 API Key |
| Jina Reader | 提取网页内容 | `curl` + URL |

### 成本
- **DuckDuckGo**: 免费
- **Jina Reader**: 免费（`https://r.jina.ai/http://<url>`）
- **总计**: $0

---

## 4. 接口设计

### NetworkSearchTool

```python
class NetworkSearchTool:
    """网络搜索工具"""
    
    def __init__(self, max_results: int = 3):
        self.max_results = max_results
    
    async def search(self, query: str) -> list[SearchResult]:
        """
        执行搜索
        
        Args:
            query: 搜索关键词
            
        Returns:
            [{"title": "...", "url": "...", "content": "..."}, ...]
        """
        pass
```

### Auditor 集成

Auditor 在审核 Worker 产出时，判断是否需要搜索验证：

```python
class Auditor:
    async def post_audit_insight(self, worker_id, insight, facts) -> dict:
        """
        审核 Worker 产出
        1. 四维审计
        2. 提取 Fact/Hint candidates
        3. 如需实时验证 → 调用网络搜索 → 结果写入黑板
        """
        # 检查是否需要搜索
        if self._needs_search_verification(insight, facts):
            search_results = await self.search_tool.search(query)
            # 写入黑板作为 Hint（下一轮生效）
            hint_candidates = self._format_as_hints(search_results)
        
        return audit_result
```

---

## 5. 数据流详解

```
┌─────────────────────────────────────────────────────────────┐
│ Round N                                                      │
├─────────────────────────────────────────────────────────────┤
│ 1. Worker_P / Worker_N 推理                                  │
│    → 产出 insight (不含搜索结果)                             │
│                                                              │
│ 2. graph.py → node_auditor_post                             │
│    → Auditor 审核                                           │
│       ├─ 四维审计 (A/B/C/D)                                  │
│       ├─ 提取 fact_candidates                               │
│       ├─ 提取 hint_candidates                                │
│       └─ **判断是否需要搜索验证**                            │
│          → 需要: search_web(query) → 新 Hint 写入黑板        │
│          → 不需要: 跳过                                      │
│                                                              │
│ 3. Manager 汇总裁决                                          │
│    → Fact/Hint 升格                                          │
│                                                              │
│ 4. 进入 Round N+1                                            │
│    → Worker 推理时读取黑板 (含上一轮 Auditor 注入的搜索Hint) │
│    → 产出融合实时信息的 insight                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. 配置

```yaml
# config.yaml
network_search:
  enabled: true
  max_results: 3
  provider: "duckduckgo"  # 免费方案
  timeout: 30
  # Auditor 搜索触发条件
  auditor_trigger:
    # 需要搜索的内容类型
    keywords: ["最新", "2024", "2025", "趋势", "市场", "报告"]
    # 置信度低于多少时触发搜索验证
    confidence_threshold: 70
```

---

## 7. Auditor Prompt 修改

```python
AUDITOR_POST_CHECK = """你是一个 FIH Auditor，负责事后审计。

## 待审计 Insight（来自 WORKER_ID）
INSIGHT_PLACEHOLDER

## 当前黑板 Facts
FACTS_PLACEHOLDER

## 审核要求

### 1. 四维审计（每维10分）
A. 因果自主性
B. 时间稳定性
C. 跨路径一致性
D. 可传递性

### 2. 实时信息验证
- 检查 Insight 是否涉及"最新趋势"、"市场数据"、"2024/2025"等内容
- 如涉及，标记需要搜索验证（设置 search_needed: true + 搜索关键词）

### 3. 输出格式
```json
{
  "passed": true,
  "scores_4d": {"A": 8, "B": 7, "C": 6, "D": 9},
  "result_ei": 30,
  "fact_candidates": [...],
  "hint_candidates": [...],
  "search_needed": true,
  "search_queries": ["AI agents 2024 trends"]
}
```
"""
```

---

## 8. 边界条件

| 条件 | 处理 |
|------|------|
| 搜索失败 | 返回空 Hint，记录日志，Auditor 继续完成审核 |
| 无搜索结果 | 只记录 "无需搜索���证"，不影响主流程 |
| 内容提取失败 | 只保留 URL 作为 Hint 内容 |
| 速率限制 | 添加 1s 延迟 |
| 搜索结果过多 | 限制 max_results=3，取最新/最相关 |

---

## 9. 安全与合规

- **URL 验证**：只允许 HTTP/HTTPS，排除 javascript:, data: 等协议
- **内容过滤**：基础广告、追踪器内容过滤
- **搜索频率限制**：同一 session 相同关键词不重复搜索

---

## 10. 验收标准

| ID | 标准 | 测试 |
|----|------|------|
| NS-01 | Auditor 审核时判断是否需要搜索 | 模拟需要/不需要两种场景 |
| NS-02 | 搜索返回 3 条结果 | 调用 search() 验证 |
| NS-03 | 内容提取成功 | Jina Reader 返回文本 |
| NS-04 | 搜索结果写入黑板作为 Hint | 检查 hints 字段 |
| NS-05 | 下一轮 Worker 能读取搜索 Hint | 验证数据流 |
| NS-06 | 搜索失败不影响审核流程 | 模拟失败测试 |
| NS-07 | 配置开关生效 | enabled=false 时跳过 |

---

## 11. 文件变更

| 文件 | 变更 |
|------|------|
| `src/fih_emergence/tools/network_search.py` | 新增 NetworkSearchTool 类 |
| `src/fih_emergence/roles/auditor.py` | 集成搜索能力 |
| `src/fih_emergence/prompts/__init__.py` | 修改 Auditor prompt |
| `src/fih_emergence/config.py` | 新增 network_search 配置 |
| `config.yaml` | 新增 network_search 配置段 |
| `tests/test_network_search.py` | 新增单元测试 |

---

## 12. 待探索

- [ ] 多语言搜索支持
- [ ] 搜索结果缓存（避免同轮重复搜索）
- [ ] Worker 也能主动搜索的混合模式