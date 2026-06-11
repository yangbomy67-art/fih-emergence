# FIH Emergence 联调测试计划

## 测试范围

根据 SPEC 文档，设计以下测试用例：

---

## 1. 流程完整性测试 (SPEC_流程.md)

### 1.1 单轮完整流程
- [ ] Human Gate 发起任务 → Manager 接收
- [ ] 黑板初始化（facts=[], hints=[]）
- [ ] Proposer 生成候选 Intent
- [ ] Manager 确认 Intent (三要素)
- [ ] Auditor 事前审计 (Intent → Worker 门槛)
- [ ] 双 Worker GAN 对抗
- [ ] Auditor 事后审计 (Insight → 黑板 门槛)
- [ ] Manager 汇总裁决

### 1.2 多轮连续执行
- [ ] Round 1 → Round 2 正常流转
- [ ] Round N → Round N+1 数据传递
- [ ] Facts 累积（append-only）
- [ ] Hints 累积（追加新 Hint）
- [ ] Intent 每轮重置

### 1.3 异常流程
- [ ] Auditor 事前打回 → Proposer 重试
- [ ] retry 耗尽 → null round
- [ ] Worker 产出异常 → Manager 裁决
- [ ] 4 条件触发中断 → Human Gate 介入

---

## 2. EI 评估测试 (SPEC_EI.md)

### 2.1 事前审计（代理指标）
- [ ] 引用 ≥2 个 Fact（规则可判）
- [ ] 新概念引入（LLM 判断）
- [ ] 非同义反复（LLM 判断）
- [ ] 满足 2/3 → 通过门控

### 2.2 事后审计（EI 计算）
- [ ] S1 可交付形态（满分 5）
- [ ] S2 Fact 引用（满分 5）
- [ ] S3 新增视角（满分 10）
- [ ] result_EI = S1 + S2 + S3
- [ ] 四维审计 A/B/C/D（每维 10 分）
- [ ] 涌现判定：EI ≥ 15 且 四维每维 ≥ 7

### 2.3 Fact+ 升格
- [ ] Worker → Auditor 提取 → Manager 裁决 → 黑板
- [ ] Hint → 相关度匹配 → Auditor 标注 → Manager 裁决 → 黑板
- [ ] 两条路径都经过 Auditor + Manager

---

## 3. 保护机制测试 (SPEC_保护机制.md)

### 3.1 终止条件
- [ ] 达到最大轮次（max_rounds）→ 终止
- [ ] 置信度聚合 > 阈值 → 终止
- [ ] force_complete → 终止

### 3.2 低谷检测
- [ ] 连续 3 轮 EI < 10 → 低谷检测
- [ ] 连续 3 轮无 Fact+ → 低谷检测
- [ ] 低谷穿越：diversify_intent / force_human_intervention

### 3.3 涌现检测
- [ ] 连续 2 轮 EI ≥ 15 → 涌现成功 → 自动终止
- [ ] 涌现触发后不继续执行剩余轮次

### 3.4 快照策略
- [ ] 每轮 Manager 汇总裁决后保存快照
- [ ] 保留最近 10 轮
- [ ] 回退功能正常

---

## 4. 数据结构测试 (SPEC_DataStructures.md)

### 4.1 数据字段
- [ ] Intent: id, content, type, supporting_facts
- [ ] Worker: insight, self_confidence
- [ ] Auditor: result_ei, scores_4d, fact_candidates, hint_candidates
- [ ] State: facts, hints, intents, valley_signals, rounds_history

### 4.2 字段兼容性
- [ ] Proposer 兼容多种 JSON 字段名（id/intent_id, content/intent/content_text/description, type/category）
- [ ] Worker 兼容 ```json 标记和纯 JSON 格式
- [ ] Auditor 解析 LLM 返回的 JSON（带/不带 markdown）

---

## 5. API 测试 (SPEC_API.md)

### 5.1 会话管理
- [ ] POST /session 创建会话
- [ ] GET /session/{id} 获取状态
- [ ] POST /interrupt 人工中断
- [ ] POST /resume 恢复执行
- [ ] POST /rollback/{round} 回退

### 5.2 状态查询
- [ ] GET /status 返回 task_status
- [ ] GET /blackboard 返回 facts/hints
- [ ] GET /rounds/{n} 返回指定轮次数据

---

## 6. 模型兼容性测试

### 6.1 多模型支持
- [ ] glm-5.1 正常工作
- [ ] Qwen3.5-397B-A17B 正常工作
- [ ] kimi-k2.6 可处理（解析失败不中断）

### 6.2 Prompt 鲁棒性
- [ ] 各模型返回不同格式都能解析
- [ ] JSON 解析失败时保留 raw_content
- [ ] 解析失败不污染正常数据

---

## 7. 已知问题（待排查）

### 7.1 2 轮超时问题
- [ ] 第 1 轮正常完成
- [ ] 第 2 轮运行卡住（需排查 LLM 调用或 LangGraph 状态）

### 7.2 Fact 累积问题
- [ ] Auditor 提取 fact_candidates 成功
- [ ] 但 facts 列表为空（未正确写入黑板）
- [ ] 需验证 Manager 汇总裁决后的写入逻辑

### 7.3 多轮状态传递
- [ ] rounds_history 只保留最后 1 轮数据（应该保留全部）
- [ ] 需验证 rounds_history.append() 在每轮结束后都执行

---

## 测试优先级

| 优先级 | 测试项 | 原因 |
|--------|--------|------|
| **P0** | 单轮完整流程 | 核心功能 |
| **P0** | EI 动态计算 | 修复后需验证 |
| **P0** | 2 轮连续执行 | 排查超时问题 |
| **P1** | Fact 累积 | 数据完整性 |
| **P1** | 快照策略 | 保护机制 |
| **P2** | API 端点 | 完整功能 |
| **P2** | 回退功能 | 紧急恢复 |

---

## 测试数据

### 主题列表
1. "AI是否能超越人类智能"（正反相当）
2. "AI对就业市场影响"（偏向一方）
3. "测试"（简单主题）

### 预期结果
- 单轮：EI = 动态计算值（15-30）
- 2 轮：连续执行完成
- 涌现：连续 2 轮 EI ≥ 15 自动终止
- 解析失败：保留 raw_content，不返回 [Error]

---

> 文档版本: v1.0
> 创建时间: 2026-06-11