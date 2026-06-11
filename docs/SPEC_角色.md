# 角色职责

## MANAGER（管理者）

Manager 是系统日常执行者，Human Gate 是上级/导师角色。大部分工作由 Manager 驱动，只有 Manager 处理不了的场景才由 Human Gate 介入指导。

### 角色定位

| 角色 | 定位 | 职责 |
|------|------|------|
| **Manager** | 日常执行者 | 发布主题、Intent确认、汇总裁决、触发中断等 |
| **Human Gate** | 上级/导师 | 关键决策：发起任务、人工介入（3条件）、修正 Intent、强制完成等 |

### Human Gate "教 Manager 干活" 的场景

| 场景 | Human Gate 做什么 | Manager 做什么 |
|------|-------------------|----------------|
| **修正 Intent** | Human Gate 修正 Intent | 接收修正，交给 Proposer 重新生成 |
| **3条件触发** | 人工介入选择操作 | 执行对应操作（Fact+/Fact-/Hint+/Hint-/continue/force_complete） |
| **强制完成** | Human Gate 决定跳过剩余轮次 | 终止任务，输出最终成果 |
| **回退** | Human Gate 决定回退到第N轮 | 执行回退逻辑 |

> **注意**：Human Gate 修正 Intent 后，Manager 直接提给 Proposer 重新生成。

### 职责

- **发布主题**(含 Fact Hint Intent)
- **Intent 确认**��从 Proposer 的候选 Intent(c) 中选择一个，确认后写入 Intent
- **Intent 确认时填写三要素（辅助决策，非门控）**：
  - **EI 启发式评估**（非正式，辅助选择）：初步判断候选 Intent 是否有自主涌现潜力，帮助选择更有涌现潜力的方向
  - **低谷识别 Intent 建议**：滑动窗口检测是否处于产出低谷，帮助决定是否需要调整策略
  - **Next Intent 建议**：基于当前轮 Facts + 已有 Intent 方向，建议 1-3 条后续 Intent 方向，为下一轮 Proposer 提供参考
- **汇总裁决**：审核 fact_candidates、hint_candidates，执行低谷穿越策略
- **Fact 升格裁决**：审核 Auditor 提取的 fact_candidates，决定是否写入 Facts
- **Hint→Fact 升格评估**：对 Auditor 建议升格的 Hint 进行全局评估，决定是否升格
- **Human Gate 通信**：唯一与 Human Gate 交互的角色

> **注意**：三要素是"辅助决策"而非"门控"。不通过不会阻止流程，只是影响选择偏好。

### 低谷穿越

- Auditor 识别 + 建议，Manager 裁决 + 执行
- **滑动窗口**：最近 3 轮，用于检测产出低谷

### 置信度异常（弱势方重产）

- 程序自动检测：P>80% 且 N<30% → Worker N 重产
- 程序自动检测：N>80% 且 P<30% → Worker P 重产
- 无需人工介入，Manager 不可干预

---

## PROPOSER（提议者）

### 职责

- **多草稿生成**：基于当前 Facts + Hints + 上一轮 Next Intent 建议，生成 N=2-4 个候选 Intent，确保三类 Intent 均有覆盖
- **发布/更新 Intent**：将候选 Intent 发布到黑板供 Manager 确认
- **缺失补足**（被动响应）：仅当 Manager 判定候选 Intent 存在缺失（缺少任意一类 / 无支撑 Fact / 差异度 < 0.3）并通知时，才进行补生成

### Proposer 生成候选的输入

| 输入 | 来源 | 状态 |
|------|------|------|
| **Facts** | 黑板读取 | ✅ 已实现 |
| **Hints** | 黑板读取 | ✅ 已实现 |
| **上一轮 Next Intent 建议** | Manager 填写，Proposer 读取 | ⚠️ 待实现（需要 Manager 写入 + Proposer 读取） |
| **task_description** | 任务主题（数据库/内存） | ✅ 已实现 |

> **待实现**：当前代码中 Manager 填写 Next Intent 建议后未持久化供 Proposer 读取，需要新增字段并实现读写逻辑。

### 不承担

- **不做评判**：不负责判断候选 Intent 是否"足够好"，该职责归 Manager
- **不做 EI 评估**：EI 评估是 Manager（辅助选择）和 Auditor（审计）的职责

---

## Worker（工作者）

### 模式

双 Worker 模式（正方/反方），每个 Worker 内嵌正/反、判三方对抗。

### GAN 对抗（并行+同步）

**两层对抗，串行执行**：

1. **Worker 内嵌三方对抗**（Phase A1）：
   - Worker 内部生成初稿 → 自反驳 → 自判断
   - 产出包含 self_confidence（0-100%）

2. **双 Worker 间对抗**（Phase A2）：
   - Worker_P 和 Worker_N 并行产出初稿 Insight
   - 各自包含 self_confidence

3. **Auditor 信心检查**（Phase B）：
   - Auditor 检查双方 self_confidence
   - 若一方 > 90% → 要求弱势方重新产出（注入对抗性 Hint）

### 执行顺序图

```
Worker_P / Worker_N 各自内部:
  生成初稿 → 自反驳 → 自判断 → self_confidence
                    ↓
        并行产出 → Auditor 检查信心
                    ↓
        若信心差距大 → 弱势方重产
                    ↓
        产出 Insight
```

---

## Auditor（审计员）

规则：交给 Worker 的 Intent 和 Worker 生产的 Insight 均要通过 Auditor 审计。

### 事前审计 (Intent → Worker 门槛)

- EI 启发式评估 (正式，门控)

### 事后审计 (Insight → 黑板 门槛)

- EI 追踪 (事后)
- Fact+候选
- Hint+候选（可 search web）
- 快照策略
- 四维审计
- 低谷识别

---

## Human Gate

### 架构

- 双形态：CLI + Hermes Skill
- 通信：HTTP API ↔ FIH Backend Service
### 3 条件中断（需要人工介入）

- 低谷穿越失败: 连续 4+ 轮无 Fact+ → 人工介入
- 产出重复: 连续 2 轮产出相同 → 人工介入
- Fact 冲突: 黑板中现有 Fact 存在矛盾 → 人工介入

> 置信度异常（弱势方重产）：程序内部逻辑，当正方>80%且反方<30%时自动触发弱势方重产，无需人工介入。

### 人工操作类型

| 操作 | 触发方式 | 触发条件 |
|------|----------|----------|
| **Fact+** | `POST /interrupt` + `fact_plus` | 用户显式确认或 Auditor 提取 + Manager 裁决 |
| **Fact-** | `POST /interrupt` + `fact_minus` | 用户手动标记无效，或 Fact 冲突时人工介入 |
| **Hint+** | `POST /interrupt` + `hint_plus` | Auditor 标注候选 + Manager 确认 |
| **修正 Intent** | `POST /interrupt` + `corrected_intent` | Auditor 拒绝（EI 不通过）或人工介入 |
| **强制继续** | `POST /interrupt` + `action=continue` | 跳过当前中断继续执行 |
| **强制完成** | `POST /force-complete` | 直接标记任务完成 |
| **低谷穿越** | `POST /interrupt` + `action=valley_traverse` | 连续 3 轮无 Fact+ 时人工注入新方向 |
| **回退** | `POST /rollback/{round_num}` | 回退到第 N 轮（需快照存在） |

### 中断规则

- 嵌套中断：禁止
- 超时：5min 自动跳过

---

> 文档版本: v1.0
> 最后更新: 2026-06-09