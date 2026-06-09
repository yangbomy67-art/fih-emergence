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

    # ═══════════════════════════════════════════════════════════
    # 任务信息
    # ═══════════════════════════════════════════════════════════
    task_description: str           # 用户输入的原始任务
    mode: str                       # 固定 "FULL"
    session_id: str                 # 会话唯一ID
    iteration: int                  # 当前轮次 (1, 2, 3, ...)
    max_iterations: int             # 最大轮次限制 (默认 20)

    # ═══════════════════════════════════════════════════════════
    # 黑板 (Facts/Hints/Intents)
    # ═══════════════════════════════════════════════════════════
    facts: list[dict]               # 已验证事实
    hints: list[dict]               # 环境输入
    intents: list[dict]             # 候选Intent列表 (每轮替换)

    # ═══════════════════════════════════════════════════════════
    # Worker 竞争结果 (固定2个 Worker，正反对抗)
    # ═══════════════════════════════════════════════════════════
    worker_submissions: list        # [Worker_P提交, Worker_N提交]
    worker_count: int               # 固定 2

    # ════════════���══════════════════════════════════════════════
    # Auditor 审计结果
    # ═══════════════════════════════════════════════════════════
    audit_result: dict | None       # 完整审计结果

    # ═══════════════════════════════════════════════════════════
    # Fact+ 执行状态
    # ═══════════════════════════════════════════════════════════
    fact_plus_executed: bool        # 本轮是否执行了 Fact+ 升格
    hints_promoted_to_facts: list   # 本轮从 Hint 升格为 Fact 的列表

    # ═══════════════════════════════════════════════════════════
    # Manager 决策结果
    # ═══════════════════════════════════════════════════════════
    winner_intent: dict | None      # 本轮胜出Intent
    next_intent_candidates: list    # 下一轮候选 Intent
    intent_ei_scores: list          # 每个候选的 intent EI 分数

    # ═══════════════════════════════════════════════════════════
    # 低谷检测 (累积存储)
    # ═══════════════════════════════════════════════════════════
    valley_detected: bool
    valley_signals: list            # 滑动窗口保留最近5轮
    valley_operation: str | None

    # ═══════════════════════════════════════════════════════════
    # Fact 冲突检测
    # ═══════════════════════════════════════════════════════════
    fact_conflicts: list[dict]      # 含 resolved 标记

    # ════════════════════════════════════��══════════════════════
    # 人工介入
    # ═══════════════════════════════════════════════════════════
    needs_human: bool               # 是否需要人工介入
    human_intervention_reason: str  # 介入原因
    human_input: dict | None        # 人工输入
    human_action_taken: str | None  # 最终执行的人工操作

    # ═══════════════════════════════════════════════════════════
    # 历史计数器
    # ═══════════════════════════════════════════════════════════
    no_fact_rounds: int             # 连续无 Fact+ 轮次
    consecutive_same_output: int    # 连续产出完全相同的轮次

    # ═══════════════════════════════════════════════════════════
    # 产出整合
    # ══════════════════════════��════════════════════════════════
    main_text_parts: list
    appendix_parts: list
    final_output: str | None

    # ═══════════════════════════════════════════════════════════
    # 控制标志
    # ═══════════════════════════════════════════════════════════
    task_complete: bool
    is_first_round: bool            # 是否首轮
    task_boundary_status: str       # "open" | "closed"

    # ═══════════════════════════════════════════════════════════
    # 持久化引用 (不序列化)
    # ═══════════════════════════════════════════════════════════
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
    final_output TEXT,
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

    created_at TEXT NOT NULL,
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

> 文档版本: v1.0
> 最后更新: 2026-06-09