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

## 四维审计

### 维度

- 事实支撑度
- 逻辑自洽性
- 新颖性
- 对抗存活度

### 综合判定

- **涌现**：高质量 Insight
- **常规**：普通产出
- **退化**：低质量产出

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