# FIH Emergence 联调测试计划 (v2.0)

**基于已知问题重新设计**  
**Date**: 2026-06-11

---

## 背景：已知问题

| 优先级 | 问题 | 当前状态 |
|--------|------|----------|
| **P0-Blocker** | Fact累积未写入黑板 | 待修复 |
| **P0-Blocker** | 2轮运行偶尔卡住 | 偶发，需复现 |
| **P1-Major** | WebSocket推送 | 未实现 |
| **P1-Major** | 回退功能 | 未实现 |

---

## 测试策略

### 核心原则
1. **先修P0问题，再验证功能**
2. **每个问题至少2个测试用例**
3. **自动化 + 手动结合**

---

## Phase 1: P0 问题修复验证 (1天)

### 1.1 Fact累积写入修复

**目标**: 验证 fact_candidates 能正确写入黑板 facts[]

| 测试用例 | 步骤 | 预期 |
|----------|------|------|
| TC-Fact-01 | 运行1轮，检查 audit_result.fact_candidates | 非空 |
| TC-Fact-02 | 运行2轮，检查 rounds_history[*].facts | 累积增长 |
| TC-Fact-03 | Auditor 提取 fact_candidates，Manager 裁决后写入黑板 | facts>0 |

**验证脚本**:
```python
# 验证 facts 累积
r = await run_session('test', 'AI', max_iterations=2)
assert len(r['rounds_history'][0]['facts']) > 0
assert len(r['rounds_history'][1]['facts']) > len(r['rounds_history'][0]['facts'])
```

### 1.2 2轮运行卡住问题排查

**目标**: 定位并修复第2轮卡住的根本原因

| 测试用例 | 步骤 | 预期 |
|----------|------|------|
| TC-Round2-01 | 运行2轮，设置30s超时 | 不超时 |
| TC-Round2-02 | 运行3轮，观察卡住位置 | 定位卡住节点 |
| TC-Round2-03 | 对比1轮vs2轮vs3轮执行时间 | 线性增长 |

**排查方向**:
- LLM 调用超时
- LangGraph 状态死锁
- 数据库写入阻塞

---

## Phase 2: 基础功能回归 (1天)

### 2.1 单轮完整流程

| 测试用例 | 步骤 | 预期 |
|----------|------|------|
| TC-Single-01 | run_session(topic, max=1) | 1轮完成 |
| TC-Single-02 | 验证 intents 非空 | Intent已生成 |
| TC-Single-03 | 验证 worker_submissions 非空 | Worker产出 |
| TC-Single-04 | 验证 ei_score > 0 | EI计算正常 |

### 2.2 多轮连续执行

| 测试用例 | 步骤 | 预期 |
|----------|------|------|
| TC-Multi-01 | run_session(max=3) | 3轮都完成 |
| TC-Multi-02 | 验证每轮 ei_score 独立计算 | 动态变化 |
| TC-Multi-03 | 验证 rounds_history 包含所有轮次 | 3条记录 |

---

## Phase 3: 保护机制验证 (0.5天)

### 3.1 涌现检测

| 测试用例 | 步骤 | 预期 |
|----------|------|------|
| TC-Emerge-01 | 连续2轮EI>=15 | 自动终止 |
| TC-Emerge-02 | 连续2轮EI<15 | 继续运行 |
| TC-Emerge-03 | 验证 task_complete=true | 状态正确 |

### 3.2 最大轮次

| 测试用例 | 步骤 | 预期 |
|----------|------|------|
| TC-MaxRound-01 | max=2，运行足够触发涌现 | 2轮终止(非1轮) |
| TC-MaxRound-02 | max=5，无涌现触发 | 5轮终止 |

### 3.3 置信度异常

| 测试用例 | 步骤 | 预期 |
|----------|------|------|
| TC-Confidence-01 | 一方confidence>90% | 触发弱势方重产 |
| TC-Confidence-02 | 双方confidence正常 | 不触发重产 |

---

## Phase 4: 数据完整性验证 (0.5天)

### 4.1 字段累积

| 测试用例 | 步骤 | 预期 |
|----------|------|------|
| TC-Accum-01 | 运行3轮，facts应累积 | facts数量>=3 |
| TC-Accum-02 | 运行3轮，hints应累积 | hints数量>=3 |
| TC-Accum-03 | 运行3轮，valley_signals应累积 | 3条记录 |

### 4.2 状态迁移

| 测试用例 | 步骤 | 预期 |
|----------|------|------|
| TC-State-01 | idle→running | 状态正确切换 |
| TC-State-02 | running→completed | task_complete=true |
| TC-State-03 | intents每轮重置 | 3轮intent内容不同 |

---

## Phase 5: P1 功能实现验证 (待定)

### 5.1 WebSocket推送

| 测试用例 | 步骤 | 预期 |
|----------|------|------|
| TC-WS-01 | 4条件触发时 | WebSocket推送消息 |
| TC-WS-02 | 人工介入后 | WebSocket推送恢复消息 |

### 5.2 回退功能

| 测试用例 | 步骤 | 预期 |
|----------|------|------|
| TC-Rollback-01 | 回退到第1轮 | facts/hints恢复到第1轮状态 |
| TC-Rollback-02 | 回退后继续运行 | 能正常执行后续轮次 |

---

## 测试数据

### 主题库

| 主题 | 特点 | 适用测试 |
|------|------|----------|
| "测试" | 简单 | 单轮/多轮基础测试 |
| "AI是否能超越人类智能" | 正反相当 | 多轮/涌现检测 |
| "AI对就业影响" | 偏向一方 | 对抗测试 |
| "量子计算未来" | 专业领域 | 知识扩展测试 |

### 预期结果基准

| 指标 | 基准值 |
|------|--------|
| 单轮执行时间 | <60s |
| 2轮执行时间 | <120s |
| EI 范围 | 15-35 |
| Fact 产出率 | >=1/轮 |

---

## 执行顺序

```
Phase 1 (P0修复)
    ↓
Phase 2 (回归测试) ← 修复后立即执行
    ↓
Phase 3 (保护机制)
    ↓
Phase 4 (数据完整性)
    ↓
Phase 5 (P1功能)
```

---

## 里程碑

| 日期 | 目标 |
|------|------|
| Day 1 | Phase 1: P0问题修复 + 验证 |
| Day 2 | Phase 2-3: 回归测试 + 保护机制 |
| Day 3 | Phase 4: 数据完整性 |
| Day 4+ | Phase 5: P1功能 |

---

## 交付物

1. **测试脚本**: `tests/integration/*.py`
2. **测试报告**: `TEST_REPORT_v2.md`
3. **问题追踪**: `ISSUE_TRACKER.md`

---

> 版本: v2.0  
> 作者: FIH Team  
> 状态: 待执行