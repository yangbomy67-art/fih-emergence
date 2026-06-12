# CHANGELOG.md

## v1.0.3 (2026-06-12)

### feat: 网络搜索功能（方案C - Auditor守门员模式）

当 Auditor 审核 Worker 产出时，判断是否需要搜索获取实时信息，搜索结果作为 Hint 注入黑板。

#### 实现细节
- **tools/network_search.py**: 新增 NetworkSearchTool（DuckDuckGo + Jina Reader）
- **config.py**: 新增 NetworkSearchConfig 配置类
- **roles/auditor.py**: 集成搜索能力，needs_search_verification() / search_and_format_hints()
- **graph.py**: node_auditor_post 中调用网络搜索

#### 数据流
```
Worker 推理 → Auditor 审核 → 需要搜索? → 执行搜索 → 新Hint写入黑板
                                                   ↓
下一轮 Worker 推理时读取搜索Hint → 产出含实时信息的insight
```

#### 方案说明
- **方案C**: 仅 Auditor 可触发搜索（守门员模式）
- **免费方案**: DuckDuckGo 搜索 + Jina Reader 内容提取 = $0/月

#### Trace

```
[ROLE]      builder
[BASIS]     第二期开发 - 网络搜索功能 SPEC
[SCOPE]     4 files modified
[DECISION]  方案C: Auditor守门员模式，DuckDuckGo+Jina免费方案
```

#### Files Changed

| 文件 | 变更 |
|------|------|
| tools/network_search.py | 新增 NetworkSearchTool 类 |
| config.py | 新增 NetworkSearchConfig |
| roles/auditor.py | 集成网络搜索能力 |
| graph.py | Auditor审核时触发搜索 |

---

## v1.0.2 (2026-06-12)

### feat: diversify_intent 多样化 Intent 实现

当 EI 持续低（3+ 轮 <10）时，系统自动触发多样化策略，引导 Proposer 突破思维定式。

#### 实现细节
- **state.py**: 新增 `diversify_intent_triggered` 字段
- **prompts/__init__.py**: 新增 `PROPOSER_DIVERSIFY` prompt，包含4种多样化策略（角度转换/逆向思维/跨界融合/极端假设）
- **proposer.py**: `generate_intents()` 方法新增 `diversify` 参数
- **graph.py**: 检测到 `valley_operation == "diversify_intent"` 时设置标志，传递给下一轮 Proposer

#### Trace

```
[ROLE]      builder
[BASIS]     第一期悬置功能：diversify_intent
[SCOPE]     4 files modified
[DECISION]  graph 检测 EI 持续低 → 设置 diversify_intent_triggered → Proposer 使用多样化 prompt
```

#### Files Changed

| 文件 | 变更 |
|------|------|
| state.py | 新增 diversify_intent_triggered 字段 |
| prompts/__init__.py | 新增 PROPOSER_DIVERSIFY |
| proposer.py | generate_intents() 支持 diversify 参数 |
| graph.py | valley_operation==diversify_intent 时触发 |

---

## v1.0.1 (2026-06-09)

### fix: SPEC Review 问题修复

#### Blocker Fixed
- **B-01**: Manager/Proposer Intent 职责交叉 → Proposer 仅生成候选，不做评判

#### Major Fixed
- **M-02**: 异常流补充 (Auditor打回/retry耗尽/Worker异常/4条件中断)
- **M-03**: 超时后 resume 行为定义 (状态清除/流程恢复/日志记录)
- **M-04**: FIHState 状态迁移表 (主状态机/字段规则/非法断言)
- **M-05**: SQL DDL 语法错误修复 (2处尾逗号)
- **M-06**: 运行时失败处理 (LLM/SQLite/Checkpoint/不可恢复错误)
- **M-07**: Candidate 权限列定义为 Intent(candidates)
- **M-08**: 可观测性设计 (日志级别/结构化日志/节点/LLM/黑板日志)
- **M-09**: EI 可测试性 (result_EI公式/置信度阈值/代理指标判定)
- **M-10**: interrupt+WebSocket 时序保证 (先推送失败则不interrupt)

#### Trace

```
[ROLE]      reviewer → builder
[BASIS]     SPEC_REVIEW.md 审查协议
[SCOPE]     7 files / 546 insertions
[DECISION]  修复后总分 16/36 → 27/36
[VERDICT]   REJECT → APPROVE
```

#### Files Changed

| 文件 | 变更 |
|------|------|
| docs/SPEC_角色.md | Proposer 职责重构 |
| docs/SPEC_流程.md | 异常流补充 |
| docs/SPEC_保护机制.md | 超时行为 + 运行时失败处理 |
| docs/SPEC_DataStructures.md | 状态迁移表 + SQL 语法修复 |
| docs/SPEC_EI.md | result_EI 公式 + 权限矩阵澄清 |
| docs/SPEC_架构实现.md | 可观测性设计 + interrupt 时序 |

#### Commit

- `4bbc4f6` - test: 补充 Manager 角色单元测试 (28 tests)
- `e6a04f0` - fix: Lint 修复 (ruff check --fix)
- `008fa90` - docs: 更新 CHANGELOG v1.0.1 记录 Minor/Nit 修复
- `785c10b` - fix: 5 Minor + 1 Nit 问题修复
- `87033c2` - docs: 更新 CHANGELOG v1.0.1 记录 SPEC Review 修复
- `a1eacae` - fix: 10 个 SPEC Review 问题修复

### init: 项目初始化 + SPEC 文档

#### Trace

```
[ROLE]      builder
[BASIS]     用户需求：新建项目 fih-emeragence，基于 .bak 旧版架构写 SPEC
[CONFLICT]  未读 PLAYBOOK 就动手，违反 AGENTS §1 "先 SPEC 后 Code" 启动自检
[SCOPE]     9 files / ~800 lines / 2 dirs (docs/, .)
[RISK]      safe —— 纯文档项目，无代码变更
[EVIDENCE]  7 SPEC docs + PLAYBOOK.md + README.md (更新)
[DECISION]  按 .bak 旧版架构编写 SPEC（5角色 + 独立后端 + HTTP/WebSocket），用户确认方向后执行
[ROLLBACK]  git revert
```

#### Details

- 9 files changed, 809 insertions(+)
- commit: d34dba9 (SPEC docs)
- commit: 5018ee8 (PLAYBOOK.md)

#### Files

| 文件 | 说明 |
|------|------|
| README.md | 项目总览 |
| PLAYBOOK.md | 机制、模板、工具箱 |
| docs/SPEC.md | 总纲 |
| docs/SPEC_黑板.md | Fact/Intent/Hint/Round |
| docs/SPEC_角色.md | 5角色职责 |
| docs/SPEC_流程.md | 9步循环 |
| docs/SPEC_API.md | HTTP/WebSocket |
| docs/SPEC_保护机制.md | 重试/终止/快照 |
| docs/SPEC_EI.md | EI评估 + 四维审计 + 权限矩阵 |

---

> 文档版本: v1.0
> 最后更新: 2026-06-09