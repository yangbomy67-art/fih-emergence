# PLAYBOOK.md

> 机制、模板、工具箱。SOUL/AGENTS 规定"以什么为重"和"硬规则"，本文件规定"具体怎么做"。
> 优先级最低：当 PLAYBOOK 模板与 SOUL/AGENTS/SPEC 冲突时，以后者为准。

## §1 默认栈与选型矩阵

| 维度 | 默认 | 何时偏离 |
|---|---|---|
| 语言 | Python 3.12 | SPEC 指定 / 已有 manifest |
| 测试框架 | pytest | 已有项目约定 |
| Property test | Hypothesis | 纯 CRUD 可省 |
| Lint / Format | ruff | — |
| 类型检查 | mypy | — |
| CI | GitHub Actions，required checks 全开 | — |
| 包管理 | uv | — |
| 容器 | distroless / alpine | 需调试时切 debian-slim |

> 选型偏离默认时必须在 Trace [DECISION] 写明理由。

## §2 仲裁优先级与冲突案例库

**优先级**：SPEC > AGENTS > SOUL > PLAYBOOK > default

### 案例库（活文档，每次裁决补一条）

| # | 冲突 | 裁决 | 依据 |
|---|---|---|---|
| 1 | SPEC 要求 React 18，PLAYBOOK 默认 Next.js 15（自带 React 19） | 用 React 18 | SPEC > PLAYBOOK |
| 2 | 用户口述"加个 console.log 就行"，AGENTS §1.4 要求可证伪 | 拒绝并追问 | AGENTS > 用户上下文（非 SPEC） |
| 3 | PLAYBOOK 模板鼓励多写注释，SOUL "克制输出" | 注释只写 why 不写 what | SOUL > PLAYBOOK |
| ... | | | |

## §3 Harness 工具箱（分层）

### L1 确定性闸门
- 编译 / 类型：mypy --strict
- 单测：pytest
- Lint：ruff
- 依赖环：pydeps
- SAST：Semgrep
- SCA：osv-scanner
- Mutation：mutmut（抽样运行）

### L2 语义证明
- Property test：Hypothesis
- Differential test：自写 oracle 跑新旧实现 diff
- Contract test：Pact / Schemathesis
- Benchmark harness：pytest-benchmark
- Fuzz：Atheris
- LLM-as-judge：独立模型 + rubric + 校准集

### L3 呈现层
- PR 模板（§4）
- 风险分级脚本（§6）
- Trace schema 校验器（CI 必跑）
- Stack PR 工具：Graphite / Sapling / git-spice

## §4 PR / Patch 模板

### 4.1 Patch 卡片模板
```markdown
## 意图
<1 句话，1 个语义意图>

## SCOPE
- files: N
- lines: N (≤400)
- dirs: N (≤3)

## RISK
- level: safe | local | risky
- reason: <一句话>

## Evidence
- [ ] 测试：<test name>
- [ ] Property：<property name>
- [ ] Benchmark：<before vs after, p50/p95>
- [ ] Fuzz：<run id, corpus size>

## Diff
<最小 diff>

## Rollback
<git revert / feature flag / migration down>

## Trace
[ROLE] ...
[BASIS] ...
[CONFLICT] ...
[SCOPE] ...
[RISK] ...
[EVIDENCE] ...
[DECISION] ...
[ROLLBACK] ...
```

### 4.2 追问模板
```markdown
## 待确认
<单一问题>

## 默认行为
不答则按 <X> 处理，理由：<...>

## 影响面
<哪些决策依赖此问题的答案>
```

### 4.3 拒绝模板
```markdown
## 拒绝输出
原因：<硬门槛 / 安全基线 / 无法形式化>
依据：AGENTS §<n> / SPEC §<n>
建议路径：<拆分 / 补 SPEC / 补不变式>
```

## §5 Trace 示例

### 5.1 新功能
```
[ROLE]      builder
[BASIS]     L1-SPEC §A.3 验收契约
[SCOPE]     3 files / 180 lines / 1 intent
[RISK]      local —— 仅触达 user-service 内部
[EVIDENCE]  test:user.signup.spec.ts (5 cases) + property:idempotent_signup
[DECISION]  用 argon2id 而非 bcrypt，对应 SPEC §E.2
[ROLLBACK]  git revert，无 schema 变更
```

### 5.2 重构
```
[ROLE]      builder
[BASIS]     L2-AGENTS §3.3 语义证明
[SCOPE]     2 files / 90 lines / 1 intent
[RISK]      local
[EVIDENCE]  differential:old_vs_new (10000 random inputs, 0 diff)
[DECISION]  抽出 pricing pure function，便于 property test
[ROLLBACK]  git revert
```

### 5.3 拒绝
```
[ROLE]      reviewer
[BASIS]     L2-AGENTS §1.4 可证伪
[CONFLICT]  用户要求"优化一下这段代码"，无 SPEC 不变式
[DECISION]  拒绝输出，追问要优化哪个度量（延迟 / 内存 / 可读性）
```

> 更多示例（修 bug / 迁移 / 安全修复）按需补充。

## §6 风险分级规则

自动启发式（可写成 CI 脚本）：
- 触达 `**/migrations/**` → risky
- 触达 `**/auth/** | **/crypto/** | **/payment/**` → risky
- 修改公共 API schema → risky
- 仅 `**/*.md | **/*.test.* | **/*.spec.*` → safe
- 其他单文件、单目录、≤200 行 → local
- 其他 → risky（保守默认）

## §7 反馈指标（团队 Dashboard）

- AI 建议接受率
- 接受后 7 日内回滚率
- 接受后引发线上事故率
- 平均 review 时长 / PR 大小分布
- Trace schema 完整率
- 拒绝率（过低说明门槛太松，过高说明 SPEC 不足）

## §8 任务生命周期

### 8.1 启动自检
见 SOUL"启动自检"。

### 8.2 收尾自检
- [ ] SPEC / CHANGELOG / API doc 同步
- [ ] Trace schema 校验通过
- [ ] L1 闸门 100% 绿
- [ ] L2 证据齐全
- [ ] 风险分级复核
- [ ] 回滚方式可执行

### 8.3 灰度与回滚 SOP
- risky 变更走 feature flag，默认 off
- 上线后观察 <X> 分钟关键指标
- 回滚优先级：feature flag off > git revert > migration down

## §9 反模式清单（禁止出现）

- 含糊措辞："考虑"、"可能更好"、"建议优化"、"也许应该"
- 超大 PR（>400 行 / 多语义意图 / 跨多目录）
- 无 Evidence 的性能 / 安全声明
- 未填 Trace 字段
- 静默处理规则冲突
- 把解释写在正文而非 Trace
- 凑数建议（一次给 5 条但只有 1 条有 diff）
- 绕过 L1 闸门（"测试先跳过，等会儿补"）

---

> 文档版本: v1.0
> 最后更新: 2026-06-09