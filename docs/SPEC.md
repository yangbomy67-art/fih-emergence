# FIH Emergence 规范文档

**涌现不是恩赐，是被治理的产物。**

FIH (Fact-Intent-Hint) 多智能体协作框架，基于因果涌现理论实现自主推理。

## 理论基础

- **霍兰德 CGP**：Fact / Hint 是制约，Intent 竞争是生成 【Intent竞争】
- **丹尼特多重草稿**：候选 Intent 并行竞争，胜出即聚焦 【多草稿生成】
- **古德费洛 GAN**：每个 Intent 内嵌正/反、判三方对抗 【GAN对抗】
- **霍尔因果涌现**：以 EI 增益判定宏观 Intent 是否真正"自主"于微观 Facts 【EI 启发式评估】【EI 追踪】
- **马尔可夫粗粒化**：动态寻找最优聚合粒度，避免过细或过粗 【EI 追踪】

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [SPEC_黑板.md](./SPEC_黑板.md) | 黑板定义（Fact/Intent/Hint/Round） |
| [SPEC_角色.md](./SPEC_角色.md) | 5 角色职责（Manager/Proposer/Worker/Auditor/HumanGate） |
| [SPEC_流程.md](./SPEC_流程.md) | 流程图 + Round 循环机制 |
| [SPEC_API.md](./SPEC_API.md) | HTTP API 端点设计 |
| [SPEC_保护机制.md](./SPEC_保护机制.md) | max_retry/终止条件/快照/回退 |
| [SPEC_EI.md](./SPEC_EI.md) | EI 评估 + 四维审计 + 通信/权限矩阵 |

---

## 快速导航

### 主题来源

- **Round 1**：Human Gate CLI `/start <topic>` → Manager
- **Round N+**：Manager 基于上一轮 Next Intent 建议自动生成

### 退出条件

- max_rounds = 20
- Manager 判定产出充分
- Human Gate 执行 force_complete

### 实现栈

- 语言：Python 3.12
- 测试：pytest
- Lint：ruff
- 包管理：uv

### 架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Human Gate (客户端)                              │
│   ┌─────────────────────┐              ┌─────────────────────┐          │
│   │    CLI: $ fih-hg    │              │  Hermes Skill       │          │
│   │  start/status/...   │              │    /fih start       │          │
│   └──────────┬──────────┘              └──────────┬──────────┘          │
│              │                                      │                      │
│              └──────────────┬───────────────────────┘                      │
│                             ↓                                              │
│                    HTTP + WebSocket                                       │
│                             ↓                                              │
├────────────────────────────────────────────────────────────────────────────┤
│                      FIH Backend Service                                  │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────┐    │
│   │                     LangGraph 工作流                            │    │
│   │  Manager → Proposer → Auditor → Workers → Manager (循环)       │    │
│   └─────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│   黑板状态: Facts (只读) | Hints (累积) | Intents (每轮重置) | Round      │
└────────────────────────────────────────────────────────────────────────────┘

图例: ─── HTTP 数据流    ═══ WebSocket 推送(4条件)
```

---

> 文档版本: v1.0
> 最后更新: 2026-06-09