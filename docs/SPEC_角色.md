# 角色职责

## MANAGER（管理者）

Manager 是系统唯一与 Human Gate 交互的角色。

### 职责

- **发布主题**(含 Fact Hint Intent)
- **Intent 确认(同时完成三要素)**：
  - EI 启发式评估 (非正式，辅助选择)：初步判断候选 Intent 是否有自主涌现潜力
  - 低谷识别 Intent 建议：滑动窗口检测是否处于产出低谷
  - Next Intent 建议：基于当前轮 Facts + 已有 Intent 方向，建议 1-3 条后续 Intent 方向
- **汇总裁决**：审核 fact_candidates、hint_candidates，执行低谷穿越策略
- **Human Gate 通信（唯一接口）**

### 低谷穿越

- Auditor 识别 + 建议，Manager 裁决 + 执行

---

## PROPOSER（提议者）

### 职责

- **多草稿生成**：基于当前 Facts + Hints，生成 N=2-4 个候选 Intent，确保三类 Intent 均有覆盖
- **发布/更新 Intent**：将候选 Intent 发布到黑板供 Manager 确认
- **缺失补足**（被动响应）：仅当 Manager 判定候选 Intent 存在缺失（缺少任意一类 / 无支撑 Fact / 差异度 < 0.3）并通知时，才进行补生成

### 不承担

- **不做评判**：不负责判断候选 Intent 是否"足够好"，该职责归 Manager
- **不做 EI 评估**：EI 评估是 Manager（辅助选择）和 Auditor（门控）的职责

---

## Worker（工作者）

### 模式

双 Worker 模式（正方/反方），每个 Worker 内嵌正/反/判三方对抗。

### GAN 对抗（并行+同步）

- Phase A：Worker_P 和 Worker_N 各自产出初稿 Insight（含 self_confidence，范围 0-100%）
- Phase B：Auditor 检查双方 self_confidence（范围 0-100%）
- 若一方 > 90% → 要求弱势方重新产出（注入对抗性 Hint）

### 输出

- Insight：基于当前 Facts 推理，引用以 [F1] [H2] 形式回指
- Next Intent 建议 (1-3条)

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
- 方案：不依赖 Hermes，FIH 后端独立运行

### 4 条件触发

- 置信度异常: 正方>90% 且 反方<30%，或 45-55 僵持
- 产出停滞: 连续 3 轮无 Fact+
- 产出重复: 连续 2 轮产出相同
- Fact 冲突: 黑板中现有 Fact 存在矛盾

### 人工操作类型

- Fact+ / Fact- / Hint+
- 修正 Intent（经 Proposer 重新发布）
- 强制继续 / 强制完成
- 低谷穿越
- 回退

### 中断规则

- 嵌套中断：禁止
- 超时：5min 自动跳过

---

> 文档版本: v1.0
> 最后更新: 2026-06-09