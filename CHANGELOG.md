# CHANGELOG.md

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

- `a1eacae` - fix: 10 个 SPEC Review 问题修复
- `785c10b` - fix: 5 Minor + 1 Nit 问题修复

---

## v1.0 (2026-06-09)

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