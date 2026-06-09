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

### 超时后的行为定义

当 Human Gate 操作超时时：

1. **状态清除**：
   - `needs_human = false`
   - `human_intervention_reason` 设为 `"timeout"`

2. **操作记录**：
   - `human_action_taken = "timeout_skipped"`
   - 在 `human_intervention_log` 表写入记录：
     - `reason`: `"timeout"`
     - `action`: `"timeout_skipped"`
     - `content`: `null`
     - `rerun_worker`: `"none"`

3. **流程恢复**：
   - 恢复到中断点继续执行**当前轮**的剩余步骤
   - **不是**跳到下一轮，而是从被 interrupt 的节点继续

4. **日志**：
   - 记录超时事件到系统日志（INFO 级别）

## 低谷升级

- 连续3轮同类低谷 → 拒绝同类穿越，强制人工介入

## Fact 冲突裁决

- 置信度优先保留
- 或触发人工裁决

## 快照策略

- **保存时机**：每轮 Manager 汇总裁决后
- **保存内容**：`{ round: N, facts[], hints[], winner_intent, audit_4d_result }`
- **保留策略**：保留最近 10 轮，超过后自动清理第 11 轮
- **回退时**：恢复到指定轮次的快照 + 清除该轮之后的所有后续轮次

## 运行时失败处理

### LLM 调用失败

| 失败类型 | 处理策略 |
|----------|----------|
| **超时** (>30s) | 重试最多 2 次，每次间隔 5s |
| **429 Rate Limit** | 退避 30s 后重试，总共最多 3 次 |
| **5xx 服务器错误** | 重试最多 2 次，每次间隔 10s |
| **4xx 客户端错误** | 不重试，直接返回错误（输入格式/参数问题） |
| **连续失败 3 次** | 切换到降级模式：使用上一次的 worker_submissions 或标记本轮产出失败 |

### SQLite 失败

| 失败类型 | 处理策略 |
|----------|----------|
| **写入失败** | 回滚本事务，确保状态一致性 |
| **数据库锁冲突** | 重试最多 3 次，每次退避 1s |
| **磁盘空间不足** | 记录错误日志，标记任务为 `aborted` 状态，通知 Human Gate |
| **数据库损坏** | 尝试从最新快照恢复；若快照也损坏，标记任务为 `aborted` |

### Checkpoint 损坏

- **检测**：LangGraph 加载 checkpoint 时若解析失败，触发恢复流程
- **恢复路径**：
  1. 尝试加载最近一次成功的快照
  2. 若快照存在，恢复到该轮次状态，重新执行该轮
  3. 若无有效快照，标记任务为 `aborted`，通知 Human Gate
  4. 记录错误日志，包含损坏的 checkpoint 标识和时间戳

### 不可恢复错误

当以下情况发生时，任务必须中止（`aborted`）：

- SQLite 和快照均不可用
- LangGraph 工作流内部状态崩溃且无法重建
- 连续 5 轮均无法产出有效产出

中止时：
- 保存当前黑板状态到 `final_output`（若可读）
- 写入 `session_meta.status = "aborted"`
- 通过 WebSocket 推送 `task_error` 事件给 Human Gate

---

> 文档版本: v1.0
> 最后更新: 2026-06-09