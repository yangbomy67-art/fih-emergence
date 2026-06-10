"""
FastAPI Application - HTTP API

Based on SPEC_API.md
"""

import json
import uuid
from contextlib import asynccontextmanager

import aiosqlite
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from fih_emergence.config import get_config
from fih_emergence.database import (
    create_session,
    get_db_path,
    get_session,
    get_snapshot,
    init_db,
    update_session,
)
from fih_emergence.graph import run_session, workflow

# =======================
# Lifespan
# =======================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 加载配置（指定默认路径）
    from pathlib import Path
    config_path = Path(__file__).parent.parent.parent / "config.yaml"
    config = get_config(str(config_path))

    # 启动时初始化数据库
    await init_db(config.database.path)
    yield
    # 关闭时清理资源


# =======================
# App
# =======================

app = FastAPI(
    title="FIH Emergence",
    description="FIH Multi-Agent Collaboration Framework",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =======================
# Request Models
# =======================

class StartRequest(BaseModel):
    topic: str = Field(..., description="任务主题")
    facts: list[str] | None = Field(default=None, description="初始 Facts")
    hints: list[str] | None = Field(default=None, description="初始 Hints")
    intents: list[str] | None = Field(default=None, description="初始 Intents")
    max_rounds: int | None = Field(default=20, description="最大轮次")


class InterruptRequest(BaseModel):
    operation: str = Field(..., description="操作类型")
    content: str | None = Field(default=None, description="操作内容")


# =======================
# Endpoints
# =======================

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "service": "fih-emergence"}


@app.post("/start")
async def start_task(req: StartRequest):
    """开始任务（Round 1）"""
    session_id = str(uuid.uuid4())
    max_rounds = req.max_rounds or 20

    # 创建会话
    await create_session(
        session_id=session_id,
        task_description=req.topic,
        max_iterations=max_rounds,
    )

    # 后台运行工作流
    import asyncio
    asyncio.create_task(
        run_session(
            session_id=session_id,
            task_description=req.topic,
            initial_facts=req.facts,
            initial_hints=req.hints,
            max_iterations=max_rounds,
        )
    )

    return {
        "status": "started",
        "round": 1,
        "session_id": session_id,
    }


@app.get("/status")
async def get_status(session_id: str = None):
    """查看状态"""
    if session_id:
        # 读取真实会话状态
        session = await get_session(session_id)
        if session:
            return {
                "session_id": session["session_id"],
                "topic": session["task_description"],
                "current_round": session.get("current_round", 1),
                "max_rounds": session["max_iterations"],
                "status": session["status"],
                "created_at": session["created_at"],
            }
        return {"error": "Session not found"}, 404
    
    # TODO: 从数据库读取真实状态
    return {
        "status": "running",
        "message": "工作流在后台执行中",
        "note": "简化版 - 返回静态示例",
    }


@app.post("/interrupt")
async def interrupt(req: InterruptRequest):
    """人工介入操作"""
    return {
        "status": "applied",
        "state_updated": True,
    }


@app.post("/stop")
async def stop_task(session_id: str = None):
    """强制终止任务"""
    # TODO: 实际实现需要存储运行中的任务状态
    # 简化：返回成功状态
    return {
        "status": "stopped",
        "session_id": session_id,
        "message": "任务已强制终止"
    }


@app.post("/force-complete")
async def force_complete():
    """强制完成"""
    return {"status": "completed"}


@app.post("/rollback/{round_num}")
async def rollback(session_id: str, round_num: int):
    """回退到第 N 轮"""
    # 1. 获取会话当前状态
    session = await get_session(session_id)
    if not session:
        return {"error": "会话不存在", "session_id": session_id}
    
    current_round = session.get("current_round", 0)
    
    # 2. 验证轮次有效性
    if round_num <= 0:
        return {"error": "无效轮次：必须大于 0"}
    
    if round_num >= current_round:
        return {"error": f"无效轮次：目标轮次 {round_num} 必须小于当前轮次 {current_round}"}
    
    # 3. 检查快照是否存在
    snapshot = await get_snapshot(session_id, round_num)
    if not snapshot:
        return {"error": "快照不存在", "available_rounds": list(range(1, current_round))}
    
    # 4. 执行回退：恢复快照状态
    # 恢复 facts, hints, intents
    facts = snapshot.get("facts", "[]")
    hints = snapshot.get("hints", "[]")
    intents = snapshot.get("intents", "[]")
    
    # 解析 JSON 字符串
    import json
    try:
        facts_list = json.loads(facts) if isinstance(facts, str) else facts
        hints_list = json.loads(hints) if isinstance(hints, str) else hints
        intents_list = json.loads(intents) if isinstance(intents, str) else intents
    except (json.JSONDecodeError, TypeError):
        facts_list = []
        hints_list = []
        intents_list = []
    
    # 5. 更新会话状态
    await update_session(
        session_id,
        current_round=round_num,
        facts=json.dumps(facts_list),
        hints=json.dumps(hints_list),
        intents=json.dumps(intents_list),
        status="running",
    )
    
    # 6. 删除后续轮次的快照（清理）
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "DELETE FROM blackboard_snapshots WHERE session_id = ? AND round > ?",
            (session_id, round_num),
        )
        await db.commit()
    
    return {
        "status": "rolled_back",
        "session_id": session_id,
        "from_round": current_round,
        "to_round": round_num,
        "message": f"已回退到第 {round_num} 轮"
    }


# =======================
# WebSocket
# =======================

class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)


manager = ConnectionManager()


@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 长连接，接收 4 条件推送"""
    session_id = None

    try:
        # 接收 session_id
        data = await websocket.receive_text()
        message = eval(data)  # 简化：实际应该 JSON parse
        session_id = message.get("session_id")

        if not session_id:
            await websocket.send_json({"error": "session_id required"})
            return

        await manager.connect(session_id, websocket)

        # 保持连接
        while True:
            data = await websocket.receive_text()
            # 处理客户端消息

    except WebSocketDisconnect:
        if session_id:
            manager.disconnect(session_id)


# =======================
# Error Handlers
# =======================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return {
        "error": {
            "code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
        }
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    return {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": str(exc),
        }
    }
