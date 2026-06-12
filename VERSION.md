# FIH Emergence 版本

## v1.0.0 (2026-06-12) - 第一期发布

### 已实现功能
- 9步流程完整实现（Manager确认Intent → Manager汇总裁决）
- 3条件中断检测与人工介入
- 终止条件（最大轮次5/涌现成功EI≥30/3条件触发）
- Fact/Hint升格由Manager裁决
- Next Intent建议传递给Proposer
- 报告生成（Markdown格式）

### 悬置功能
- EI持续低多样化策略
- HumanGate CLI
- 回退(Rollback)功能
- 快照策略持久化

### 已知问题
- Worker JSON解析偶尔失败（LLM输出格式不稳定）

---

## 版本历史

### v0.x - 开发版本
- 内部开发迭代