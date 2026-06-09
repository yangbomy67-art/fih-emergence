# 数据结构与黑板设计

## 一、FIHState 全局状态

```python
from typing import TypedDict, Literal, Optional

class FIHState(TypedDict):
    """
    FIH 多智能体协作系统全局状态

    存储原则:
    - 累积字段 (追加): valley_signals, facts, hints, ei_tracking, human_intervention_log
    - 覆盖字段 (最新值): no_fact_rounds, consecutive_same_output, current_round
    """

    # ═════════════════════════════════════════════════════════════
    # 任务信息
    # ═════════════════════════════════════════════════════════════
    task_description: str           # 用户输入的原始任务
    mode: str                       # 固定 "FULL"
    session_id: str                 # 会话唯一ID
    iteration: int                  # 当前轮次 (1, 2, 3, ...)
    max_iterations: int             # 最大轮次限制 (默认 20)

    # ═════════════════════════════════════════════════════════════
    # 黑板 (Facts/Hints/Intents)
    # ═════════════════════════════════════════════════════════════
    facts: list[dict]               # 已验证事实
    hints: list[dict]               # 环境输入
    intents: list[dict]             # 候选Intent列表 (每轮替换)

    # ═════════════════════════════════════════════════════════════
    # Worker 竞争结果 (固定2个 Worker，正反对抗)
    # ═════════════════════════════════════════════════════════════
    worker_submissions: list        # [Worker_P提交, Worker_N提交]
    worker_count: int               # 固定 2

    # ═════════════════════════════════════════════════════════════
    # Auditor 审计结果
    # ═════════════════════════════════════════════════════════════
    audit_result: dict | None       # 完整审计结果

    # ═════════════════════════════════════════════════════════════
    # Fact+ 执行状态
    # ═════════════════════════════════════════════════════════════
    fact_plus_executed: bool        # 本轮是否执行了 Fact+ 升格
    hints_promoted_to_facts: list   # 本轮从 Hint 升格为 Fact 的列表

    # ═════════════════════════════════════════════════════════════
    # Manager 决策结果
    # ═════════════════════════════════════════════════════════════
    winner_intent: dict | None      # 本轮胜出Intent
    next_intent_candidates: list    # 下一轮候选 Intent
    intent_ei_scores: list          # 每个候选的 intent EI 分数

    # ═════════════════════════════════════════════════════════════
    # 低谷检测 (累积存储)
    # ═════════════════════════════════════════════════════════════
    valley_detected: bool
    valley_signals: list            # 滑动窗口保留最近5轮
    valley_operation: str | None

    # ═════════════════════════════════════════════════════════════
    # Fact 冲突检测
    # ═════════════════════════════════════════════════════════════
    fact_conflicts: list[dict]      # 含 resolved 标记

    # ═════════════════════════════════════════════════════════════
    # 人工介入
    # ═════════════════════════════════════════════════════════════
    needs_human: bool               # 是否需要人工介入
    human_intervention_reason: str  # 介入原因
    human_input: dict | None        # 人工输入
    human_action_taken: str | None  # 最终执行的人工操作

    # ═════════════════════════════════════════════════════════════
    # 历史计数器
    # ═════════════════════════════════════════════════════════════
    no_fact_rounds: int             # 连续无 Fact+ 轮次
    consecutive_same_output: int    # 连续产出完全相同的轮次

    # ═══════════════════════════════════════════════════════════
        # 产出整合
        # ═══════════════════════════════════════════════════════════
    main_text_parts: list
    appendix_parts: list
    final_output: str | None

    # ═════════════════════════════════════════════════════════════
    # 控制标志
    # ═════════════════════════════════════════════════════════════
    task_complete: bool
    is_first_round: bool            # 是否首轮
    task_boundary_status: str       # "open" | "closed"

    # ═════════════════════════════════════════════════════════════
    # 持久化引用 (不序列化)
    # ═════════════════════════════════════════════════════════════
    _blackboard: object | None
```

---

## 二、黑板格式 (SQLite)

### 2.1 表: session_meta (会话元数据)

```sql
CREATE TABLE session_meta (
    session_id TEXT PRIMARY KEY,
    task_description TEXT NOT NULL,
    max_iterations INTEGER DEFAULT 20,
    mode TEXT DEFAULT 'FULL',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    current_round INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',  -- 'active' | 'completed' | 'aborted'
    final_output TEXT
);
```

### 2.2 表: blackboard_snapshots (黑板快照)

```sql
CREATE TABLE blackboard_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    round INTEGER NOT NULL,

    -- 黑板核心数据
    facts TEXT NOT NULL,           -- JSON: [{"id":..., "content":..., ...}]
    hints TEXT NOT NULL,           -- JSON: [{"id":..., "content":..., ...}]
    intents TEXT NOT NULL,        -- JSON: [{"id":..., "content":..., ...}]

    -- 胜出 Intent
    winner_intent TEXT,            -- JSON: {id, content, intent_ei_score}

    -- Worker 结果
    worker_submissions TEXT,       -- JSON: [worker_P, worker_N]

    -- 审计结果摘要
    result_ei REAL,
    pro_confidence REAL,
    con_confidence REAL,
    scores_4d TEXT,                -- JSON: {A:..., B:..., C:..., D:...}
    valley_detected INTEGER,       -- 0/1 boolean

    -- 提议
    proposal TEXT,                 -- "继续" | "Fact+" | "完成"

    created_at TEXT NOT NULL,

    UNIQUE(session_id, round)
);

CREATE INDEX idx_snapshot_session_round
ON blackboard_snapshots(session_id, round);
```

### 2.3 表: ei_tracking (EI 追踪)

```sql
CREATE TABLE ei_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    round INTEGER NOT NULL,

    -- intent EI (Manager 计算)
    intent_ei_scores TEXT,         -- JSON: [{"candidate_id":..., "score":...}]

    -- result EI (Auditor 计算)
    result_ei REAL,
    result_ei_S1 REAL,             -- 可交付形态 (0-5)
    result_ei_S2 REAL,             -- Fact引用 (0-5)
    result_ei_S3 REAL,             -- 新增视角 (0-10)

    -- 四维审计
    scores_4d TEXT,                -- JSON: {A:..., B:..., C:..., D:...}

    created_at TEXT NOT NULL,

    UNIQUE(session_id, round)
);

CREATE INDEX idx_ei_session_round
ON ei_tracking(session_id, round);
```

### 2.4 表: human_intervention_log (人工介入日志)

```sql
CREATE TABLE human_intervention_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    round INTEGER NOT NULL,

    -- 介入原因
    reason TEXT NOT NULL,          -- 触发条件类型

    -- 人工操作
    action TEXT NOT NULL,          -- 执行的操作类型
    content TEXT,                  -- 操作内容 (JSON)

    -- 结果
    rerun_worker TEXT,             -- "overwrite" | "new_round"

    created_at TEXT NOT NULL
);

CREATE INDEX idx_intervention_session
ON human_intervention_log(session_id, round);
```

---

## 三、数据目录

```
~/.fih-emergence/
├── blackboard.db              # SQLite 数据库
└── logs/                      # 日志目录
```

---

## 四、状态迁移表

### 4.1 主状态机

| 状态 | 含义 | 进入条件 | 退出条件 |
|------|------|----------|----------|
| `idle` | 空闲，等待任务 | 系统启动 / 任务终止后 | 收到 `/start` 请求 |
| `running` | 执行中 | `/start` 成功 / `interrupt` 恢复后 | 触发 `interrupt` / 任务完成 |
| `interrupted` | 等待人工介入 | 4 条件满足触发 `interrupt` | 用户响应 / 超时 5min |
| `completed` | 任务完成 | 达到终止条件且 Manager 确认 | - |
| `aborted` | 任务中止 | 用户执行 `/stop` / 不可恢复错误 | - |

### 4.2 字段迁移规则

| 迁移 | 触发条件 | 重置/更新的字段 |
|------|----------|-----------------|
| idle → running | `/start` | `current_round=1`, `task_complete=false`, `is_first_round=true`, `task_boundary_status="open"` |
| running → interrupted | 4条件触发 | `needs_human=true`, `human_intervention_reason` 设为具体原因 |
| interrupted → running (resume) | 用户响应 `/interrupt` | `needs_human=false`, `human_action_taken` 设为用户操作 |
| interrupted → running (timeout) | 超时 5min | 见 SPEC_保护机制.md §超时后的行为定义 |
| running → completed | 终止条件满足 | `task_complete=true`, `task_boundary_status="closed"`, `final_output` 设为整合产出 |
| running → aborted | `/stop` | `task_complete=false`, `task_boundary_status="closed"`, `final_output=null` |

### 4.3 轮次相关字段迁移

| 字段 | 每轮重置 | 累积 | 说明 |
|------|:--------:|:----:|------|
| `intents` | ✓ | - | 每轮重置为新候选 |
| `facts` | - | ✓ | append-only |
| `hints` | - | ✓ | append-only |
| `worker_submissions` | ✓ | - | 每轮重置 |
| `audit_result` | ✓ | - | 每轮重置 |
| `winner_intent` | ✓ | - | 每轮覆盖 |
| `fact_plus_executed` | ✓ | - | 每轮重置 |
| `hints_promoted_to_facts` | ✓ | - | 每轮重置 |
| `consecutive_same_output` | 见说明 | - | 仅当产出与上一轮完全相同时 +1，否则重置为 0 |
| `valley_signals` | - | ✓ | 滑动窗口保留最近 5 轮 |
| `valley_detected` | ✓ | - | 每轮重新检测 |

### 4.4 非法状态组合（断言检查）

以下组合应被断言拒绝（实现时应检查）：

- `task_complete=true` 且 `current_round > max_rounds` — 正常完成不应超出轮次限制
- `needs_human=true` 且 `task_complete=true` — 完成状态下不应需要人工介入
- `current_round=1` 且 `consecutive_same_output>0` — 首轮无历史产出可比较
- `task_boundary_status="closed"` 且 `needs_human=true` — 已关闭的任务不应有新介入
- `valley_detected=true` 且 `valley_signals` 为空 — 有低谷标记必有信号

---

> 文档版本: v1.0
> 最后更新: 2026-06-09