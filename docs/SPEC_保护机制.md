# 流程保护机制

## 最大重试次数

- Auditor 事前打回 Proposer: max_retry=3
- 超过后优先级：
  1. 尝试其他候选（同一轮内剩余候选）
  2. 全部候选都失败 → Manager 基于现有黑板状态重新发布新主题，进入下一轮
- Round 计数器仍 +1（记录为 null round，不产出 Insight）

## 终止条件（三选一）

- 达到最大轮次（max_rounds，默认 20）
- Manager 主观判断产出充分（置信度聚合 > 阈值）
- Human Gate 执行 force_complete

## 人工超时

- Human Gate 等待操作: timeout=5min
- 超时后: 自动跳过，继续流程

## 低谷升级

- 连续3轮同类低谷 → 拒绝同类穿越，强制人工介入

## Fact 冲突裁决

- 置信度优先保留
- 或触发人工裁决

## 快照策略

- **保存时机**：每轮 Manager 汇总裁决后
- **保存内容**：`{ round: N, facts[], hints[], confirmed_intent, audit_4d_result }`
- **保留策略**：保留最近 10 轮，超过后自动清理第 11 轮
- **回退时**：恢复到指定轮次的快照 + 清除该轮之后的所有后续轮次

---

> 文档版本: v1.0
> 最后更新: 2026-06-09