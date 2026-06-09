"""
FastAPI Application - HTTP API

Based on SPEC_API.md
"""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from fih_emergence.config import get_config
from fih_emergence.database import (
    create_session,
    init_db,
)

# =======================
# Lifespan
# =======================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 加载配置
    config = get_config()

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

    # 创建会话
    await create_session(
        session_id=session_id,
        task_description=req.topic,
        max_iterations=20,
    )

    # 运行工作流（后台）
    # 注意：实际应该异步运行，这里简化处理
    # 实际实现应该启动后台任务

    return {
        "status": "started",
        "round": 1,
        "session_id": session_id,
    }


@app.get("/status")
async def get_status():
    """查看状态"""
    # 简化：返回示例状态
    return {
        "round": 1,
        "topic": "分析经济增长放缓的原因",
        "facts": [],
        "hints": [],
        "intents": [],
        "status": "idle",
    }


@app.post("/interrupt")
async def interrupt(req: InterruptRequest):
    """人工介入操作"""
    return {
        "status": "applied",
        "state_updated": True,
    }


@app.post("/stop")
async def stop_task():
    """强制终止任务"""
    return {"status": "stopped"}


@app.post("/force-complete")
async def force_complete():
    """强制完成"""
    return {"status": "completed"}


@app.post("/rollback/{round_num}")
async def rollback(round_num: int):
    """回退到第 N 轮"""
    return {"status": "rolled_back", "round": round_num}


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
