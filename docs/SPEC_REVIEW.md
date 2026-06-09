# SPEC_REVIEW.md

> 产品 SPEC 审查协议。用于审查 `docs/SPEC.md` 及 `docs/SPEC_*.md`。

## §1 目的

Reviewer 不是头脑风暴助手，而是工程质量门。

SPEC Review 的目标是判断 SPEC 是否：

- 可实现
- 可测试
- 边界明确
- 内部一致
- 风险可控
- 符合 SOUL / PLAYBOOK / Harness SPEC

## §2 审查原则

1. Evidence beats opinion.
2. Explicit SPEC text beats inferred intention.
3. Testability beats elegance.
4. Small fix beats large redesign.
5. Boundary clarity beats feature richness.
6. State clarity beats implementation speed.
7. Accepted risk must be written down.
8. No issue is valid without impact.
9. No major suggestion is valid without tradeoff.
10. No review is complete without verdict.

## §3 禁止输出

Reviewer 不得输出：

- 泛泛表扬
- 散文式评论
- 未排序建议
- 无 Evidence 的建议
- 无 Impact 的问题
- 无 Suggested Fix 的问题
- 无 tradeoff 的架构重设计
- 与 SPEC 无关的最佳实践堆砌
- 直接实现代码，除非用户明确要求

## §4 审查维度

每个维度 0-3 分：

| 分数 | 含义 |
|---:|---|
| 0 | Missing |
| 1 | Present but vague |
| 2 | Mostly clear with minor gaps |
| 3 | Clear, bounded, and testable |

必审维度：

| 维度 | 审查问题 |
|---|---|
| Intent Clarity | 目标和业务意图是否清晰 |
| Scope Boundary | 包含 / 不包含是否明确 |
| Role Boundary | 多角色职责是否清楚 |
| Flow Completeness | 主流程、异常流、恢复流是否完整 |
| State Model | 状态、状态迁移、非法状态是否明确 |
| Data Model | 输入、输出、持久化字段是否明确 |
| Failure Modes | 失败、重试、终止、回退是否明确 |
| Permission Boundary | Human Gate / 后端 / Agent 权限是否清楚 |
| Observability | Trace / audit / event / log 是否明确 |
| Testability | 是否能转成测试 |
| Implementation Risk | 风险、依赖、迁移、回滚是否明确 |
| Theory Alignment | 是否符合 FIH 理论基础与 EI 评估目标 |

## §5 FIH 项目专属审查点

由于本项目是 FIH 多智能体协作框架，Reviewer 必须额外检查：

### 5.1 Blackboard

- Fact 是否只读？
- Hint 是否累积？
- Intent 是否每轮重置？
- Round 是否单调递增？
- 快照与回退是否覆盖 Blackboard？

### 5.2 Role Protocol

- Manager 是否是唯一 Human Gate 通信者？
- Proposer 是否只负责多草稿生成？
- Worker 是否执行双 Worker GAN 对抗？
- Auditor 是否覆盖事前和事后审计？
- Human Gate 是否只通过 HTTP API 与后端通信？

### 5.3 Round Lifecycle

- Round 1 主题来源是否清楚？
- Round N+ 主题来源是否清楚？
- 终止条件是否可测试？
- max_rounds / max_retry 是否定义？
- 低谷检测与穿越是否有明确触发条件？

### 5.4 EI Evaluation

- EI 输入是什么？
- EI 输出是什么？
- EI 增益如何影响 Intent 裁决？
- 四维审计是否有判定字段？
- EI 追踪是否跨 Round 保留？

### 5.5 Human Gate

- 中断条件是否明确？
- resume 机制是否明确？
- force_complete 是否有权限边界？
- CLI 与 Hermes Skill 是否共享同一 API 契约？

### 5.6 API / WebSocket

- HTTP API 是否有输入输出错误契约？
- WebSocket 推送的 4 条件是否可验证？
- 客户端断连与重连行为是否定义？

## §6 Severity

### Blocker

有 Blocker 时不得进入实现。

使用 Blocker，当：

- 核心 Intent 不清楚
- Scope 无边界
- Stateful 行为缺少状态模型
- Acceptance Criteria 不可测试
- 权限边界缺失
- 多角色职责冲突
- Blackboard 语义不一致
- Human Gate 恢复路径缺失
- 两个模块可能实现出不兼容行为

### Major

应在实现前修复，除非显式 accepted-risk。

使用 Major，当：

- 重要异常流缺失
- 数据约束不完整
- 失败行为不清楚
- 实现风险隐藏
- API 错误契约不完整
- 终止 / 重试 / 回滚不闭环
- EI 评估只有概念，无可执行字段

### Minor

改善清晰度，但不阻塞实现。

### Nit

命名、格式、局部表述问题。

## §7 Issue Schema

每个 Issue 必须使用以下格式：

```markdown
### Issue: <ID>

- Severity:
- Dimension:
- Location:
- Evidence:
- Problem:
- Principle:
- Impact:
- Suggested Fix:
- Acceptance Criteria:

Blocker / Major 还必须补充：  
- Best Practice:
- Underlying Principle:
- Tradeoff:
- Minimal Fix:
  

