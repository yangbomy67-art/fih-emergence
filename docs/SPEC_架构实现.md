# 架构实现

## 设计原则

- **独立运行**：不依赖 Hermes，FIH 后端作为独立服务运行
- **类 Kanban 模式**：参考 Hermes Kanban 的 Worker 生命周期模式，但完全自主实现
- **事件驱动**：LangGraph 内部状态变化通过事件机制通知外部组件

---

## 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Human Gate (客户端)                              │
│  ┌─────────────────────┐                        ┌─────────────────────┐     │
│  │    CLI: $ fih-hg    │                        │  Hermes Skill       │     │
│  │  start/status/...   │                        │    /fih start       │     │
│  └──────────┬──────────┘                        └──────────┬──────────┘     │
│             │                                             │                  │
│             └───────────────────┬─────────────────────────┘                  │
│                                 ↓                                              │
│                    HTTP + WebSocket                                           │
│                                 ↓                                              │
├───────────────────────────────────────────────────────────────────────────────┤
│                            FIH Backend Service                               │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     FastAPI Server                                 │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │    │
│  │  │  HTTP API    │  │  WebSocket   │  │  State Mgr   │              │    │
│  │  │  (/start/    │  │  (/ws/events)│  │  (LangGraph  │              │    │
│  │  │   status/    │  │              │  │   状态管理)   │              │    │
│  │  │   interrupt) │  │              │  │              │              │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    ↓                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    LangGraph 工作流                                  │    │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐          │    │
│  │  │ Manager │───▶│ Proposer│───▶│ Auditor │───▶│ Workers │──┐       │    │
│  │  └─────────┘    └─────────┘    └─────────┘    └─────────┘  │       │    │
│  │      ↑                                                      │       │    │
│  │      └──────────────────────────────────────────────────────┘       │    │
│  │                         (循环)                                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    ↓                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    SQLite Blackboard                                │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │    │
│  │  │ session_meta │  │blackboard_   │  │ ei_tracking  │              │    │
│  │  │              │  │snapshots     │  │              │              │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────────────────┘

数据流: ─── HTTP 请求/响应    ═══ WebSocket 推送    ····· 内部事件
```

---

## 组件说明

### 1. FastAPI Server

| 组件 | 职责 |
|------|------|
| **HTTP API** | 接收 Human Gate 请求，转发至 LangGraph 状态管理器 |
| **WebSocket** | 维护与 Human Gate 的长连接，推送 4 条件触发事件 |
| **State Manager** | 管理 LangGraph 工作流状态，处理 interrupt/resume |

### 2. LangGraph 工作流

采用 `langgraph.types.interrupt()` 实现暂停机制：

- **流程内暂停**：当 4 条件触发时，LangGraph 调用 `interrupt()` 暂停工作流
- **状态保存**：暂停时当前状态已保存在 SQLite checkpoint 中
- **外部通信**：WebSocket 向 Human Gate 推送暂停事件
- **恢复执行**：Human Gate 通过 `/interrupt` 发送操作指令，State Manager 调用 `graph.invoke(resume=...)` 恢复

### 3. SQLite Blackboard

持久化存储层，存储会话元数据、黑板快照、EI 追踪数据。

### 4. Worker 生命周期（类 Kanban）

参考 Hermes Kanban 的"fan-out + fan-in"模式：

1. **Manager** 发布任务（Intent）到黑板
2. **Worker_P / Worker_N** 并行从黑板读取任务，各自产出 Insight
3. **Auditor** 审计后，结果写回黑板
4. **Manager** 读取审计结���，决定下一步

关键差异：
- 不使用 Hermes Kanban 的任务队列
- 黑板作为唯一的任务分发和结果收集点
- 每个 Worker 独立调用 LLM，不依赖 Hermes Agent

---

## 事件机制

### 4 条件触发 → WebSocket 推送

LangGraph 节点内部检测到 4 条件时：

1. **先推送**：State Manager 通过 WebSocket 向 Human Gate 推送中断事件
2. **推送成功** → LangGraph 调用 `interrupt()` 暂停工作流
3. **推送失败**（客户端断连/网络错误）→ **不触发 interrupt**，记录警告日志，工作流继续执行

### 时序保证

```
节点检测 4 条件
       ↓
WebSocket 推送 (interrupt_triggered)
       ↓
推送成功? → 否 → 记录 WARNING，不 interrupt，工作流继续
       ↓ 是
调用 interrupt() 暂停工作流
       ↓
State Manager 捕获 interrupt
       ↓
等待 Human Gate 响应或超时
```

**关键设计**：推送是原子性的前置条件。若 Human Gate 客户端因网络问题未收到推送，工作流不会暂停，避免"卡在 interrupted 状态但无人响应"的死锁。

### 事件类型

| 事件名 | 触发时机 | 推送内容 |
|--------|----------|----------|
| `interrupt_triggered` | 4 条件满足 | condition, context, current_round |
| `round_completed` | 轮次结束 | round, proposal, result_ei |
| `task_completed` | 任务完成 | final_output, round_count |
| `task_error` | 异常发生 | error_message, round |

---

## 人工介入流程

```
LangGraph 节点
      ↓
检测到 4 条件 → interrupt({"condition": "xxx", ...})
      ↓
State Manager 捕获
      ↓
WebSocket 推送 → Human Gate 客户端收到
      ↓
用户选择操作 → POST /interrupt
      ↓
State Manager 调用 graph.invoke(resume={...})
      ↓
工作流恢复执行
```

---

## 与 Hermes 的关系

- **不依赖**：FIH 后端完全独立运行，不依赖 Hermes 进程
- **Human Gate 可以是 Hermes Skill**：用户可通过 Hermes Skill 调用 FIH 后端 HTTP API
- **并行运行**：FIH 后端可以与 Hermes 共存于同一机器，使用不同端口

---

## 端口配置

|| 服务 | 默认端口 |
||------|----------|
|| FIH Backend | 8000 |
|| WebSocket | 8001 (或与 8000 共享)

---

## 可观测性设计

### 日志级别

| 级别 | 使用场景 |
|------|----------|
| DEBUG | 节点进出、参数传递、详细执行路径 |
| INFO | 轮次开始/结束、状态迁移、关键决策点 |
| WARNING | 可恢复错误（如 LLM 重试）、边界条件 |
| ERROR | 不可恢复错误、异常终止、任务中止 |

### 结构化日志

每个日志条目包含：

```json
{
  "timestamp": "2026-06-09T12:00:00Z",
  "level": "INFO",
  "session_id": "uuid",
  "round": 3,
  "node": "Manager",
  "event": "intent_confirmed",
  "duration_ms": 150,
  "data": { ... }
}
```

### 节点日志

每个 LangGraph 节点进出时记录：

| 字段 | 说明 |
|------|------|
| `node` | 节点名称（Manager/Proposer/Auditor/Worker_P/Worker_N） |
| `event` | 进: `node_enter` / 出: `node_exit` |
| `duration_ms` | 节点执行耗时 |
| `state_delta` | 状态变更摘要（哪些字段变化） |

### LLM 调用日���

每次 LLM 调用记录：

| 字段 | 说明 |
|------|------|
| `prompt_tokens` | 输入 token 数 |
| `completion_tokens` | 输出 token 数 |
| `latency_ms` | 调用耗时 |
| `model` | 使用的模型 |
| `prompt_hash` | prompt 的 SHA256 前 16 位（用于去重/调试） |
| `response_hash` | response 的 SHA256 前 16 位 |

### 黑板变更日志

每轮结束后记录 Fact/Hint/Intent 的 diff：

```json
{
  "event": "blackboard_diff",
  "round": 3,
  "facts_added": [...],
  "facts_removed": [],
  "hints_added": [...],
  "intents_replaced": [...]
}
```

### 审计日志（持久化）

所有持久化日志写入 `~/.fih-emergence/logs/`，按 session_id 分文件：

- `session_{id}.log` — 本会话的结构化日志
- `error_{date}.log` — 全局错误日志（所有 sessions）

### 错误追踪

每个 ERROR 级别日志必须包含：

- `session_id`
- `round`（若适用）
- `node`
- `error_code`（见下表）
- `stack_trace`（Python traceback）

| error_code | 说明 |
|------------|------|
| `LLM_TIMEOUT` | LLM 调用超时 |
| `LLM_RATE_LIMIT` | 429 错误 |
| `LLM_SERVER_ERROR` | 5xx 错误 |
| `SQLITE_WRITE_FAIL` | SQLite 写入失败 |
| `CHECKPOINT_CORRUPT` | LangGraph checkpoint 损坏 |
| `WORKER_EMPTY_OUTPUT` | Worker 产出为空 |
| `AUDIT_FAILED` | Auditor 审计失败 |

---

> 文档版本: v1.0
> 最后更新: 2026-06-09