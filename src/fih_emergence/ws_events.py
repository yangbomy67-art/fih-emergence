"""
WebSocket 事件管理器

基于 SPEC 的 3 条件推送
"""

from typing import Any
import json
import asyncio

from fastapi import WebSocket


class WSManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.connections: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        """客户端连接"""
        await websocket.accept()
        async with self._lock:
            self.connections[session_id] = websocket

    async def disconnect(self, session_id: str) -> None:
        """客户端断开"""
        async with self._lock:
            self.connections.pop(session_id, None)

    async def send(self, session_id: str, event: dict) -> bool:
        """发送事件到指定会话"""
        async with self._lock:
            ws = self.connections.get(session_id)
            if ws:
                try:
                    await ws.send_json(event)
                    return True
                except Exception:
                    self.connections.pop(session_id, None)
        return False

    async def broadcast(self, event: dict) -> None:
        """广播到所有连接"""
        async with self._lock:
            for session_id, ws in list(self.connections.items()):
                try:
                    await ws.send_json(event)
                except Exception:
                    self.connections.pop(session_id, None)


# 全局实例
ws_manager = WSManager()


# =======================
# 推送事件类型
# =======================

class WSEvent:
    """WebSocket 事件"""

    # 任务状态更新
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # 3 条件中断推送
    EMERGENCE_SUCCESS = "emergence_success"  # 涌现成功 (连续2轮EI>=30)
    VALLEY_UNRESOLVED = "valley_unresolved"  # 低谷穿越失败 (4+轮无Fact+)
    DUPLICATE_OUTPUT = "duplicate_output"  # 产出重复 (连续2轮相同)
    FACT_CONFLICT = "fact_conflict"  # Fact冲突

    # 人工介入请求
    HUMAN_INTERVENTION = "human_intervention"


def create_event(
    event_type: str,
    session_id: str,
    round_num: int,
    data: dict | None = None,
    message: str = "",
) -> dict:
    """创建标准事件格式"""
    from datetime import datetime
    return {
        "type": event_type,
        "session_id": session_id,
        "round": round_num,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message": message,
        "data": data or {},
    }


# =======================
# 推送函数
# =======================

async def push_task_started(session_id: str, round_num: int = 1) -> None:
    """推送任务开始"""
    event = create_event(
        WSEvent.TASK_STARTED,
        session_id,
        round_num,
        message=f"任务已启动，当前第 {round_num} 轮",
    )
    await ws_manager.send(session_id, event)


async def push_task_progress(session_id: str, round_num: int, ei_score: float | None = None) -> None:
    """推送任务进度"""
    data = {"ei_score": ei_score} if ei_score else {}
    event = create_event(
        WSEvent.TASK_PROGRESS,
        session_id,
        round_num,
        data,
        message=f"第 {round_num} 轮执行完成",
    )
    await ws_manager.send(session_id, event)


async def push_task_completed(session_id: str, round_num: int, final_output: str) -> None:
    """推送任务完成"""
    event = create_event(
        WSEvent.TASK_COMPLETED,
        session_id,
        round_num,
        {"final_output": final_output},
        message="任务已完成",
    )
    await ws_manager.send(session_id, event)


async def push_emergence_success(session_id: str, round_num: int, ei_score: float) -> None:
    """推送涌现成功（连续2轮EI>=30）"""
    event = create_event(
        WSEvent.EMERGENCE_SUCCESS,
        session_id,
        round_num,
        {"ei_score": ei_score},
        message="检测到涌现成功，任务自动完成",
    )
    await ws_manager.send(session_id, event)


async def push_valley_unresolved(session_id: str, round_num: int, no_fact_rounds: int) -> None:
    """推送低谷穿越失败（4+轮无Fact+）"""
    event = create_event(
        WSEvent.VALLEY_UNRESOLVED,
        session_id,
        round_num,
        {"no_fact_rounds": no_fact_rounds},
        message="低谷穿越失败，需要人工介入",
    )
    await ws_manager.send(session_id, event)
    # 同时推送人工介入请求
    await push_human_intervention(session_id, round_num, "valley_unresolved")


async def push_duplicate_output(session_id: str, round_num: int, output_preview: str) -> None:
    """推送产出重复（连续2轮产出相同）"""
    event = create_event(
        WSEvent.DUPLICATE_OUTPUT,
        session_id,
        round_num,
        {"output_preview": output_preview[:100]},
        message="检测到连续产出相同，需要人工介入",
    )
    await ws_manager.send(session_id, event)
    await push_human_intervention(session_id, round_num, "duplicate_output")


async def push_fact_conflict(session_id: str, round_num: int, conflicting_facts: list) -> None:
    """推送Fact冲突"""
    event = create_event(
        WSEvent.FACT_CONFLICT,
        session_id,
        round_num,
        {"conflicting_facts": conflicting_facts},
        message="检测到Fact冲突，需要人工裁决",
    )
    await ws_manager.send(session_id, event)
    await push_human_intervention(session_id, round_num, "fact_conflict")


async def push_human_intervention(
    session_id: str,
    round_num: int,
    reason: str,
    options: list[str] | None = None,
) -> None:
    """推送人工介入请求"""
    event = create_event(
        WSEvent.HUMAN_INTERVENTION,
        session_id,
        round_num,
        {
            "reason": reason,
            "options": options or ["continue", "force_complete", "rollback"],
        },
        message=f"需要人工介入: {reason}",
    )
    await ws_manager.send(session_id, event)


async def push_error(session_id: str, round_num: int, error: str) -> None:
    """推送错误"""
    event = create_event(
        WSEvent.TASK_FAILED,
        session_id,
        round_num,
        {"error": error},
        message=f"任务执行出错: {error}",
    )
    await ws_manager.send(session_id, event)