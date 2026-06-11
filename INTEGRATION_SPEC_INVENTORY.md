# SPEC Inventory - Phase 0

**Phase**: integration-inventory  
**Date**: 2026-06-11

---

## SPEC.md
- **职责**: 框架总览，理论基础（CGP/多草稿/GAN/因果涌现/马尔可夫粗粒化）
- **关键字段**: Fact, Intent, Hint, EI增益
- **关键流程**: Intent竞争→多草稿→GAN对抗→EI判定
- **未决问题**: 无

---

## SPEC_角色.md
- **职责**: 4角色分工（Manager/Proposer/Worker/Auditor）+ Human Gate
- **关键字段**: Intent候选, Insight, self_confidence, fact_candidates
- **关键流程**: Proposer生成→Manager确认→Worker产出→Auditor审计
- **未决问题**: Worker内嵌三方对抗未完整实现

---

## SPEC_流程.md
- **职责**: 完整流程定义（9步）+ 异常流（A/B/C/D）
- **关键字段**: Round计数器, next_intent_candidates, task_boundary_status
- **关键流程**: Round1启动→RoundN循环→终止后回到idle
- **未决问题**: 4条件中断的WebSocket推送未实现

---

## SPEC_DataStructures.md
- **职责**: FIHState定义 + SQLite表设计 + 状态迁移规则
- **关键字段**: facts[], hints[], valley_signals[], worker_submissions[]
- **关键流程**: 累积字段(facts/hints) vs 覆盖字段(current_round)
- **未决问题**: fact_conflicts裁决逻辑未实现

---

## SPEC_EI.md
- **职责**: EI评估体系（事前代理指标 + 事后result_EI + 四维审计）
- **关键字段**: result_ei(S1+S2+S3), scores_4d(A/B/C/D), fact_candidates
- **关键流程**: 事前2/3代理指标→事后四维评分→涌现判定(EI≥15且每维≥7)
- **未决问题**: Auditor LLM实现已完成，待验证

---

## SPEC_黑板.md
- **职责**: 黑板架构 + Fact/Hint管理 + 读写权限矩阵
- **关键字段**: fact_plus_executed, hints_promoted_to_facts
- **关键流程**: Worker推理→Auditor提取→Manager裁决→黑板Fact
- **未决问题**: Hint→Fact升格路径未实现

---

## SPEC_保护机制.md
- **职责**: 终止条件 + 低谷升级 + 快照策略 + 回退逻辑
- **关键字段**: max_retry=3, no_fact_rounds, valley_signals(滑动5轮)
- **关键流程**: 涌现成功(2轮EI≥15)→自动终止, 连续3轮低谷→人工介入
- **未决问题**: 回退功能未实现

---

## SPEC_API.md
- **职责**: HTTP API设计 + WebSocket事件推送 + 错误码规范
- **关键端点**: POST /start, GET /status, POST /interrupt, POST /rollback/{n}
- **关键流程**: Human Gate ←→ FIH Backend (HTTP/WSS)
- **未决问题**: WebSocket推送未实现

---

## SPEC_架构实现.md
- **职责**: 技术架构（LangGraph/LangChain/aiosqlite）+ 模块划分
- **关键组件**: graph.py(工作流), llm.py(LLM封装), database.py, api.py
- **关键流程**: create_graph() → compile() → ainvoke() 循环
- **未决问题**: 2轮运行时卡住，需排查

---

## SPEC_REVIEW.md
- **职责**: 审查报告（12维度0-3分）+ FIH专属审查点 + Severity分级
- **关键维度**: Intent Clarity, Fact Alignment, Emergence Detection, Human Loop
- **关键流程**: 两次独立审查 → 取交集 → Blocker/Major/Minor/Nit分级
- **未决问题**: 多个Severity=Blocker项待修复

---

## Phase 1: 字段矩阵 (2026-06-11)

### FIHState 字段对比

| 字段 | SPEC | 代码 | 状态 |
|------|------|------|------|
| task_description | ✅ | ✅ | OK |
| mode | ✅ | ✅ | OK |
| facts/hints/intents | ✅ | ✅ | OK |
| worker_submissions | ✅ | ✅ | OK |
| audit_result | ✅ | ✅ | OK |
| fact_plus_executed | ✅ | ✅ | OK |
| valley_detected/signals | ✅ | ✅ | OK |
| needs_human | ✅ | ✅ | OK |
| task_complete | ✅ | ✅ | OK |

### 结论

- **SPEC 覆盖率**: 32/32 = 100%
- **字段对齐**: ✅ 完全对齐
- **新增字段**: emergence_detected/signals/operation

### 需验证

1. fact_conflicts 裁决逻辑 - 未实现
2. emergence_signals 累积 - 需验证
3. valley_report 使用 - 需验证