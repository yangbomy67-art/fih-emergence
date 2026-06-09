# EI 评估 + 四维审计

## 两次 EI 评估的区别

```
           Manager EI(非正式)          Auditor EI(正式)
时机       Intent 确认时              Intent 交付 Worker 前
目的       辅助从候选中选定           正式门控：通过/打回
结果       影响选择偏好               决定是否能进入 Worker
不通过     选另一个候选               打回 Proposer 重新生成
人工修正   仍做                       跳过
```

## EI 核心问题

**不动任何 Fact，仅改变此 Intent，能否产出新 Insight？**

- 能 → 有涌现潜力
- 不能 → 只是 Fact 重述，无涌现

## 代理指标（事前）

满足 2/3 即判定"能产出新 Insight"：

1. 引用了至少 2 个不同的 Fact
2. 引入了 Fact 中未覆盖的新概念
3. 产出预期可验证（不是同义反复）

## EI 追踪（事后）

- 对比事前评估与实际产出
- 判断 Intent 是否催生高质量 Insight
- 人工修正 Intent 无 EI 追踪

## 四维审计（每维10分，共40分）

### 评分锚点

| 维度 | 10分 | 7分 | 3分 | 0分 |
|------|------|-----|-----|-----|
| **A 因果自主性** | 移除任一支撑 Fact 该 Insight 仍完全成立(完全自主) | 移除支撑 Fact 后 Insight 仍大致成立但需调整表述 | 移除支撑 Fact 后 Insight 部分崩塌 | 移除任一支撑 Fact Insight 立即崩塌(完全派生) |
| **B 时间稳定性** | 最近 3 轮持续强化(每轮都被引用且新证据加固) | 最近 3 轮稳定维持(被引用但无新加固) | 最近 3 轮中有 1 轮出现质疑 | 最近 3 轮中被推翻或冲突 |
| **C 跨路径一致性** | 以不同初始 Intent 重新推演仍收敛到相同结论 | 重新推演大致收敛但有细节差异 | 重新推演结论部分发散 | 重新推演结论完全发散(无一致性) |
| **D 可传递性** | 可直接作为新任务的起点无需额外解释 | 作为新任务起点需少量补充 | 作为新任务起点需大量补充 | 无法作为新任务���点 |

### 综合判定

- **涌现**：高质量 Insight (四维≥7 且 result_EI≥15)
- **常规**：普通产出 (四维有低于7的维度)
- **退化**：低质量产出 (四维有0分项)

---

## Fact+ 升格的两条路径

### 路径①

Worker 推理 → Auditor 提取 → Manager 裁决 → 黑板 Fact
"推理产出中被验证的结论"

### 路径②

黑板 Hint → Insight 相关度匹配 → Auditor 标注升格候选 → Manager 裁决 → 黑板 Fact
"被 Insight 间接验证的已有 Hint"

**规则**：两条路径都必须经过 Auditor 标注 + Manager 裁决，不可绕过。

---

## 通信关系

```
数据流: Manager → Proposer
数据流: Manager → Auditor
控制流: Manager → Human Gate (请求中断) → 人工操作 → Manager (指令返回)

Auditor 检测条件 → 通过 valley_report 通知 Manager → Manager 判定是否触发中断
```

---

## 写权限矩阵

```
              Fact    Intent    Hint    EI     Insight   Candidate
Manager         W        W        W      W       -          -
Proposer        -        W        R      -       -          W
Worker_P        -        R        R      -       W          -
Worker_N        -        R        R      -       W          -
Auditor         -        R        R      W       R          W
HumanGate       W       W†        W      -       -          -

† 人工修正 Intent 须先经 Proposer 重新发布

说明：Worker_P/N 产出 Insight 后通过黑板传递，非直接通信。
```

---

## 中断/通信权限矩阵

```
              可触发 HumanGate   可通信对象          检测4条件
Manager            是              全部                 是
Proposer           否              仅 Manager           否
Worker_P           否              无                    否
Worker_N           否              无                    否
Auditor            否              仅 Manager           是(特定维度)

说明: Auditor 通过 valley_report 中的 interrupt_recommendation 通知 Manager
```

---

> 文档版本: v1.0
> 最后更新: 2026-06-09