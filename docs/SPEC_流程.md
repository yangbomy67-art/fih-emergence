# 流程

## 完整流程（九步 + 任务来源）

```
【启动】
  空闲状态 → 等待 Human Gate 主题

【Round 1】
  Human Gate CLI: /start <topic> → Manager 接收
→ ① 黑板初始化
→ ② Manager 发布主题（来自 Human Gate）
→ ③ Proposer 多草稿生成
→ ④ Manager 确认 Intent (三要素)
→ ⑤ Auditor 事前审计 (Intent → Worker 门槛)
→ ⑥ 双 Worker GAN 对抗 (每个 Intent 独立执行)
→ ⑦ Auditor 事后审计 (Insight → 黑板 门槛)
→ ⑧ Manager 汇总裁决
→ ⑨ Manager 判断：触发 human_gate_interrupt?
       是 → 全图暂停 → Human Gate 与 Manager 通信
          → 人工操作 → 指令返回 Manager
          → 图从 Manager 处恢复
       否 → 进入 Round 2

【Round N (N≥2)】
  → ② Manager 发布主题（基于 Round N-1 的 Next Intent 建议自动生成）
  → ③-⑧ 流程...
  → ⑨ 无中断 → 进入 Round N+1 或 终止

【终止后】
  回到空闲状态（等待 Human Gate 下一轮任务）
```

## 数据流

|| 衔接要素 | Round N → N+ |
|----------|---------------|
| Facts | 累积（append-only） |
| Hints | 累积（追加新 Hint + Hint+ 候选） |
| Intent | 每轮重置 |
| Worker 建议 | 传递至 Proposer 候选人池 |
| Manager 建议 | 传递至 Proposer 参考 |
| Round 计数器 | +1 |

## 主题来源

- **Round 1**：Human Gate CLI `/start <topic>` → Manager
- **Round N+**：Manager 基于上一轮 Next Intent 建议自动生成

---

## 异常流（补充）

### 异常 A: Auditor 事前打回

```
Auditor 事前审计 → 不通过
       ↓
Proposer 重新生成候选 Intent
       ↓
retry 计数器 +1
       ↓
retry ≤ 3? → 是 → 回到 "Manager 确认 Intent"
       ↓ 否
尝试本轮其他候选 Intent
       ↓
有剩余候选? → 是 → 回到 "Manager 确认 Intent"
       ↓ 否
null round（不产出 Insight）→ 下一轮
```

### 异常 B: retry 耗尽

```
max_retry = 3 已用尽
       ↓
尝试同轮内其他候选 Intent
       ↓
全部失败 → null round（不产出 Insight）
       ↓
Round 计数器 +1
       ↓
进入下一轮（Manager 基于上一轮 Next Intent 建议生成新主题）
```

### 异常 C: Worker 产出异常

```
Worker 产出为空 / 格式错误 / 无效 Insight
       ↓
Auditor 标记本轮 Worker 产出为失败
       ↓
Manager 汇总裁决：
  - 若失败比例低 → 继续当前轮下一步
  - 若失败比例高 → 决定：
      ├─ 重试本轮 Worker（重新执行 GAN 对抗）
      └─ 终止任务（触发 force_complete 流程）
```

### 异常 D: 4 条件触发中断

```
Manager 检测到 4 条件满足
       ↓
触发 human_gate_interrupt
       ↓
LangGraph 暂停（interrupt）
       ↓
WebSocket 推送 → Human Gate 客户端
       ↓
用户选择操作 → POST /interrupt
       ↓
State Manager 调用 graph.invoke(resume={...})
       ↓
工作流从 Manager 处恢复
```

---

> 文档版本: v1.0
> 最后更新: 2026-06-09