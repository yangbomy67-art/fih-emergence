# SPEC_NetworkSearch - 网络搜索功能 v2

> 版本: 2.0 | 更新: 2026-06-14
> 变更: 取消 LLM 压缩，改为权威度过滤 + Top 3 原文存储

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

## 2. 架构 v2（方案C + 权威度过滤）

```
Round N:
    1. Worker 推理产出 insight（不搜索）
        ↓ {"insight": "...", "confidence": 80}
    2. Auditor 审核
        ↓ 识别 Insight 中所有需验证声明
        ↓ 按影响力排序 → 选排第1的 → 生成 1 个查询意图
        ↓ 调用 search_web(query, top_k=50, site_filter=[...], time_range=[...])
        ↓ 百度 API 返回 50 条结果
        ↓ 域名权威度评分 → 排序 → 取 Top 3
        ↓ 3 条原文直接写入黑板作为 Hints（不压缩）
        ↓ 有内容 → 写入；无内容 → 不写入
    3. 进入 Round N+1
        ↓ Worker 推理时自然读取黑板中的搜索结果 Hints（3 条完整对象）
        ↓ 产出已融合实时信息的 insight
```

**关键变更（v1 → v2）**：
- ~~LLM 压缩搜索结果为 1 条内容~~ → **权威度过滤取 Top 3 原文**
- ~~max_results=3~~ → **API 拉 50 条，过滤后取 3**
- ~~无过滤~~ → **时间过滤 + 站点过滤 + 权威度评分**

---

## 3. 实现方案

### 搜索 API

| 组件 | 说明 |
|------|------|
| 百度千帆 AI 搜索 | `POST https://qianfan.baidubce.com/v2/ai_search/web_search` |
| 免费额度 | 1500 次/月（按日分发 ~50 次/日） |
| 搜索深度 | top_k 最大 50 |
| 时间过滤 | `search_filter.range.page_time` — 精确日期范围 |
| 站点过滤 | `search_filter.match.site` — 最多 100 个指定站点 |

### 权威度评分（内置，不依赖外部 API）

```
域名权威度评分规则：
  .gov.cn          → 10（政府）
  .edu.cn          → 9（学术）
  stats.gov.cn     → 10（统计局）
  news.cn, xinhuanet.com → 8（官媒）
  std.gov.cn 等标准机构 → 8
  知名财经/科技媒体  → 5
  其他              → 3
  无域名            → 1
```

---

## 4. 接口设计

### NetworkSearchTool v2

```python
from dataclasses import dataclass

@dataclass
class SearchResult:
    title: str
    url: str
    content: str       # 摘要内容
    domain: str         # 提取的域名
    authority: int      # 权威度评分 1-10
    publish_time: str   # 发布时间（如有）

class NetworkSearchTool:
    def __init__(
        self,
        api_key: str,
        fetch_top_k: int = 50,        # API 拉取数量
        return_top_k: int = 3,        # 过滤后返回数量
        timeout: int = 30,
    ):
        ...

    async def search(
        self,
        query: str,
        site_filter: list[str] = None,    # 指定站点
        time_range: tuple[str, str] = None, # ("2026-01-01", "2026-06-01")
    ) -> list[SearchResult]:
        """
        1. 调用百度 API，传 top_k=50 + site_filter + time_range
        2. 提取域名，计算 authority 评分
        3. 按 authority DESC 排序
        4. 返回 Top return_top_k 条
        """
        ...

    @staticmethod
    def authority_score(url: str) -> int:
        """域名权威度评分"""
        ...
```

### Auditor 集成 v2

```python
class Auditor:
    async def post_audit_insight(self, worker_id, insight, facts) -> dict:
        """
        审核 Worker 产出
        1. 四维审计
        2. 提取 Fact/Hint candidates
        3. 如需实时验证 → 调用网络搜索（1个查询意图）
           → 百度 API 拉 50 条
           → 权威度排序取 Top 3
           → 3 条原文写入黑板作为 Hints
           → 无内容则不写入
        """
        if self._needs_search_verification(insight, facts):
            results = await self.search_tool.search(
                query=search_query,
                site_filter=DEFAULT_AUTHORITY_SITES,   # 默认高权威站点
                time_range=self._infer_time_range(insight),
            )
            if results:
                for r in results:
                    hint_candidates.append({
                        "title": r.title,
                        "url": r.url,
                        "content": r.content,           # 原文，不压缩
                        "authority": r.authority,
                        "source": "web_search",
                    })
            # 无搜索结果 → 不写入黑板
        
        return audit_result
```

**移除的方法**：`_compress_search_results()` — 不再需要 LLM 压缩

---

## 5. 数据流 v2

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
│          → 需要: search_web(query, top_k=50, site_filter, time_range)
│             → 权威度排序 → 取 Top 3 原文                     │
│             → 有内容: 3 条 Hint 写入黑板                      │
│             → 无内容/搜索失败: 不写入黑板，记录日志           │
│                                                              │
│ 3. Manager 汇总裁决                                          │
│    → Fact/Hint 升格                                          │
│                                                              │
│ 4. 进入 Round N+1                                            │
│    → Worker 推理时读取黑板 (含上一轮 Auditor 注入的 3 条 Hint) │
│    → 每条 Hint 含 {title, url, content, authority}           │
│    → 产出融合实时信息的 insight                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. 配置

```yaml
# config.yaml
network_search:
  enabled: true
  api_key_env: "BAIDU_API_KEY"
  fetch_top_k: 50       # API 拉取数量
  return_top_k: 3        # 过滤后返回数量
  timeout: 30
  # 默认高权威站点（Auditor 搜索时自动添加）
  default_sites:
    - "stats.gov.cn"
    - "news.cn"
    - "xinhuanet.com"
    - "gov.cn"
    - "edu.cn"
  # Auditor 搜索触发条件
  auditor_trigger:
    keywords: ["最新", "2024", "2025", "2026", "趋势", "市场", "报告", "数据", "统计"]
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
- 检查 Insight 中所有涉及"最新趋势"、"市场数据"、"具体数值"、"2024/2025/2026"等需外部验证的声明
- 按对 Insight 结论的影响力排序：如果该声明被否定，Insight 整体是否仍成立？
- **只输出影响力排第 1 的声明**作为搜索查询意图
- **数字必须原样保留**：查询中若含数值（如 4.8%），必须原样写入

### 3. 输出格式
```json
{
  "passed": true,
  "scores_4d": {"A": 8, "B": 7, "C": 6, "D": 9},
  "result_ei": 30,
  "fact_candidates": [...],
  "hint_candidates": [...],
  "search_needed": true,
  "search_query": "湖南2026一季度GDP增速 4.8%"
}
```

注意：search_query 只输出 1 个字符串（非数组），选择对 Insight 结论影响最大的待验证声明。
"""
```

---

## 8. 边界条件

| 条件 | 处理 |
|------|------|
| 搜索失败 | 不写入黑板，记录日志，Auditor 继续审核 |
| 无搜索结果 | 不写入黑板，记录日志 |
| API 返回 < 3 条 | 有多少存多少 |
| 权威度评分后无结果 | 不写入黑板 |
| 速率限制 | 缓存 + 延迟 |
| BAIDU_API_KEY 未设置 | 跳过搜索，记录 WARNING |
| enabled=false | 跳过搜索 |

---

## 9. 安全与合规

- **URL 验证**：只允许 HTTP/HTTPS
- **搜索频率限制**：同一 session 相同关键词不重复搜索（缓存 TTL=3600s）
- **API Key**：只能从环境变量读取，不可硬编码

---

## 10. 验收标准 v2

| ID | 标准 | 测试方法 |
|----|------|----------|
| NS-01 | Auditor 判断是否需要搜索 | 模拟需要/不需要 |
| NS-02 | API 调用传 top_k=50 + site_filter | 检查请求 payload |
| NS-03 | 权威度评分正确（gov.cn=10, 未知=3） | 单元测试 |
| NS-04 | 50 条过滤后取 Top 3 | 验证 return_top_k |
| NS-05 | 搜索结果以原文写入 Hint（不压缩） | 检查 hint.content == API返回 |
| NS-06 | 3 条 Hint 写入黑板 | 检查 hints 字段长度=3 |
| NS-07 | 下一轮 Worker 能读取 3 条 Hint | 验证数据流 |
| NS-08 | 搜索失败不影响审核流程 | 模拟网络错误 |
| NS-09 | enabled=false 时跳过 | 配置开关测试 |
| NS-10 | API Key 未设置时跳过并 WARNING | 环境变量测试 |

---

## 11. 文件变更 v2

| 文件 | 变更 |
|------|------|
| `src/fih_emergence/tools/network_search.py` | 新增 authority_score + site_filter + time_range + fetch/return 分离 |
| `src/fih_emergence/roles/auditor.py` | 移除 _compress_search_results，传 site_filter + time_range |
| `src/fih_emergence/prompts/__init__.py` | 不变（Auditor prompt 无需改） |
| `src/fih_emergence/config.py` | 新增 fetch_top_k, return_top_k, default_sites |
| `config.yaml` | 新增 network_search 配置段 |
| `tests/test_network_search.py` | 更新 + 新增 authority_score / top_k 测试 |

---

## 12. 变更记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v2.0 | 2026-06-14 | 取消 LLM 压缩；API top_k=50→权威度排序→Top 3 原文存储；新增 site_filter/time_range |
| v1.0 | 2026-06-12 | 初始版本，DuckDuckGo + Jina Reader → 百度 API，LLM 压缩 |
