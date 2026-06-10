"""
Database - SQLite Blackboard operations.

Based on SPEC_DataStructures.md §2
"""

import json
from datetime import datetime
from pathlib import Path

import aiosqlite

# 数据目录
DATA_DIR = Path("./data")

# 全局数据库路径
_DB_PATH: str | None = None


def get_db_path() -> Path:
    """获取数据库路径"""
    if _DB_PATH:
        return Path(_DB_PATH)
    return DATA_DIR / "blackboard.db"


def set_db_path(path: str) -> None:
    """设置数据库路径（供 init_db 调用）"""
    global _DB_PATH
    _DB_PATH = path


async def init_db(db_path: str = None) -> None:
    """初始化数据库，创建所有表"""
    if db_path:
        db_file = Path(db_path)
        set_db_path(db_path)  # 保存路径供其他函数使用
    else:
        db_file = get_db_path()

    db_file.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(db_file) as db:
        # session_meta
        await db.execute("""
            CREATE TABLE IF NOT EXISTS session_meta (
                session_id TEXT PRIMARY KEY,
                task_description TEXT NOT NULL,
                max_iterations INTEGER DEFAULT 20,
                mode TEXT DEFAULT 'FULL',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                current_round INTEGER DEFAULT 0,
                task_status TEXT DEFAULT 'pending',
                facts TEXT DEFAULT '[]',
                hints TEXT DEFAULT '[]',
                intents TEXT DEFAULT '[]',
                final_output TEXT,
                error_message TEXT
            )
        """)

        # blackboard_snapshots
        await db.execute("""
            CREATE TABLE IF NOT EXISTS blackboard_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                round INTEGER NOT NULL,
                facts TEXT NOT NULL,
                hints TEXT NOT NULL,
                intents TEXT NOT NULL,
                winner_intent TEXT,
                worker_submissions TEXT,
                result_ei REAL,
                pro_confidence REAL,
                con_confidence REAL,
                scores_4d TEXT,
                valley_detected INTEGER,
                proposal TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(session_id, round)
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshot_session_round
            ON blackboard_snapshots(session_id, round)
        """)

        # ei_tracking
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ei_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                round INTEGER NOT NULL,
                intent_ei_scores TEXT,
                result_ei REAL,
                result_ei_S1 REAL,
                result_ei_S2 REAL,
                result_ei_S3 REAL,
                scores_4d TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(session_id, round)
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_ei_session_round
            ON ei_tracking(session_id, round)
        """)

        # human_intervention_log
        await db.execute("""
            CREATE TABLE IF NOT EXISTS human_intervention_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                round INTEGER NOT NULL,
                reason TEXT NOT NULL,
                action TEXT NOT NULL,
                content TEXT,
                rerun_worker TEXT,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_intervention_session
            ON human_intervention_log(session_id, round)
        """)

        await db.commit()


async def create_session(
    session_id: str,
    task_description: str,
    max_iterations: int = 20,
) -> None:
    """创建新会话"""
    now = datetime.utcnow().isoformat() + "Z"
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """INSERT INTO session_meta
               (session_id, task_description, max_iterations, mode, created_at, updated_at, current_round, task_status, facts, hints, intents)
               VALUES (?, ?, ?, 'FULL', ?, ?, 0, 'pending', '[]', '[]', '[]')""",
            (session_id, task_description, max_iterations, now, now),
        )
        await db.commit()


async def get_session(session_id: str) -> dict | None:
    """获取会话元数据"""
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM session_meta WHERE session_id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_session(session_id: str, **kwargs) -> None:
    """更新会话元数据"""
    kwargs["updated_at"] = datetime.utcnow().isoformat() + "Z"
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [session_id]
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            f"UPDATE session_meta SET {set_clause} WHERE session_id = ?", values
        )
        await db.commit()


async def save_snapshot(
    session_id: str,
    round_num: int,
    facts: list,
    hints: list,
    intents: list,
    winner_intent: dict | None = None,
    worker_submissions: list | None = None,
    result_ei: float | None = None,
    pro_confidence: float | None = None,
    con_confidence: float | None = None,
    scores_4d: dict | None = None,
    valley_detected: bool = False,
    proposal: str | None = None,
) -> None:
    """保存黑板快照"""
    now = datetime.utcnow().isoformat() + "Z"
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """INSERT OR REPLACE INTO blackboard_snapshots
               (session_id, round, facts, hints, intents, winner_intent, worker_submissions,
                result_ei, pro_confidence, con_confidence, scores_4d, valley_detected, proposal, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                round_num,
                json.dumps(facts),
                json.dumps(hints),
                json.dumps(intents),
                json.dumps(winner_intent) if winner_intent else None,
                json.dumps(worker_submissions) if worker_submissions else None,
                result_ei,
                pro_confidence,
                con_confidence,
                json.dumps(scores_4d) if scores_4d else None,
                1 if valley_detected else 0,
                proposal,
                now,
            ),
        )
        await db.commit()


async def get_snapshot(session_id: str, round_num: int) -> dict | None:
    """获取黑板快照"""
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM blackboard_snapshots WHERE session_id = ? AND round = ?",
            (session_id, round_num),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def save_ei_tracking(
    session_id: str,
    round_num: int,
    intent_ei_scores: list | None = None,
    result_ei: float | None = None,
    result_ei_s1: float | None = None,  # noqa: N803
    result_ei_s2: float | None = None,  # noqa: N803
    result_ei_s3: float | None = None,  # noqa: N803
    scores_4d: dict | None = None,
) -> None:
    """保存 EI 追踪数据"""
    now = datetime.utcnow().isoformat() + "Z"
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """INSERT OR REPLACE INTO ei_tracking
               (session_id, round, intent_ei_scores, result_ei, result_ei_S1, result_ei_S2, result_ei_S3, scores_4d, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                round_num,
                json.dumps(intent_ei_scores) if intent_ei_scores else None,
                result_ei,
                result_ei_s1,
                result_ei_s2,
                result_ei_s3,
                json.dumps(scores_4d) if scores_4d else None,
                now,
            ),
        )
        await db.commit()


async def log_human_intervention(
    session_id: str,
    round_num: int,
    reason: str,
    action: str,
    content: dict | None = None,
    rerun_worker: str | None = None,
) -> None:
    """记录人工介入日志"""
    now = datetime.utcnow().isoformat() + "Z"
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """INSERT INTO human_intervention_log
               (session_id, round, reason, action, content, rerun_worker, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                round_num,
                reason,
                action,
                json.dumps(content) if content else None,
                rerun_worker,
                now,
            ),
        )
        await db.commit()
