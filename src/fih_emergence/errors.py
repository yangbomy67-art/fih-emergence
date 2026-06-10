"""
错误码定义

基于 SPEC_保护机制.md 的错误处理策略
"""

from enum import Enum


class ErrorCode(str, Enum):
    """统一错误码"""

    # =======================
    # 成功
    # =======================
    SUCCESS = "SUCCESS"
    TASK_COMPLETED = "TASK_COMPLETED"

    # =======================
    # LLM 调用错误 (1xxx)
    # =======================
    LLM_TIMEOUT = "LLM_001"  # 超时 (>30s)
    LLM_RATE_LIMIT = "LLM_002"  # 429 Rate Limit
    LLM_SERVER_ERROR = "LLM_003"  # 5xx 服务器错误
    LLM_CLIENT_ERROR = "LLM_004"  # 4xx 客户端错误
    LLM_CONSECUTIVE_FAILURES = "LLM_005"  # 连续失败 3 次
    LLM_UNKNOWN = "LLM_999"  # 未知错误

    # =======================
    # SQLite 错误 (2xxx)
    # =======================
    DB_WRITE_FAILED = "DB_001"  # 写入失败
    DB_LOCK_CONFLICT = "DB_002"  # 数据库锁冲突
    DB_NO_SPACE = "DB_003"  # 磁盘空间不足
    DB_CORRUPTED = "DB_004"  # 数据库损坏
    DB_NOT_FOUND = "DB_005"  # 记录不存在

    # =======================
    # API 错误 (3xxx)
    # =======================
    API_INVALID_INPUT = "API_001"  # 输入参数无效
    API_SESSION_NOT_FOUND = "API_002"  # 会话不存在
    API_SESSION_ABORTED = "API_003"  # 任务已中止
    API_ROUND_INVALID = "API_004"  # 无效轮次
    API_SNAPSHOT_NOT_FOUND = "API_005"  # 快照不存在
    API_PERMISSION_DENIED = "API_006"  # 权限不足
    API_WEBSOCKET_ERROR = "API_007"  # WebSocket 错误

    # =======================
    # 工作流错误 (4xxx)
    # =======================
    WORKFLOW_NODE_FAILED = "WF_001"  # 节点执行失败
    WORKFLOW_CHECKPOINT_CORRUPTED = "WF_002"  # Checkpoint 损坏
    WORKFLOW_INTERRUPTED = "WF_003"  # 任务被中断
    WORKFLOW_UNRECOVERABLE = "WF_004"  # 不可恢复错误

    # =======================
    # 业务错误 (5xxx)
    # =======================
    BIZ_VALLEY_UNRESOLVED = "BIZ_001"  # 低谷无法穿越
    BIZ_FACT_CONFLICT = "BIZ_002"  # Fact 冲突无法裁决
    BIZ_DUPLICATE_OUTPUT = "BIZ_003"  # 连续产出相同
    BIZ_MAX_ROUNDS_EXCEEDED = "BIZ_004"  # 超过最大轮数


# 错误码到 HTTP 状态码的映射
ERROR_TO_HTTP = {
    ErrorCode.SUCCESS: 200,
    ErrorCode.TASK_COMPLETED: 200,
    ErrorCode.LLM_TIMEOUT: 504,
    ErrorCode.LLM_RATE_LIMIT: 429,
    ErrorCode.LLM_SERVER_ERROR: 502,
    ErrorCode.LLM_CLIENT_ERROR: 400,
    ErrorCode.LLM_CONSECUTIVE_FAILURES: 503,
    ErrorCode.LLM_UNKNOWN: 500,
    ErrorCode.DB_WRITE_FAILED: 500,
    ErrorCode.DB_LOCK_CONFLICT: 503,
    ErrorCode.DB_NO_SPACE: 507,
    ErrorCode.DB_CORRUPTED: 500,
    ErrorCode.DB_NOT_FOUND: 404,
    ErrorCode.API_INVALID_INPUT: 400,
    ErrorCode.API_SESSION_NOT_FOUND: 404,
    ErrorCode.API_SESSION_ABORTED: 410,
    ErrorCode.API_ROUND_INVALID: 400,
    ErrorCode.API_SNAPSHOT_NOT_FOUND: 404,
    ErrorCode.API_PERMISSION_DENIED: 403,
    ErrorCode.API_WEBSOCKET_ERROR: 101,
    ErrorCode.WORKFLOW_NODE_FAILED: 500,
    ErrorCode.WORKFLOW_CHECKPOINT_CORRUPTED: 500,
    ErrorCode.WORKFLOW_INTERRUPTED: 409,
    ErrorCode.WORKFLOW_UNRECOVERABLE: 500,
    ErrorCode.BIZ_VALLEY_UNRESOLVED: 422,
    ErrorCode.BIZ_FACT_CONFLICT: 422,
    ErrorCode.BIZ_DUPLICATE_OUTPUT: 422,
    ErrorCode.BIZ_MAX_ROUNDS_EXCEEDED: 200,
}


def get_http_status(error_code: ErrorCode) -> int:
    """获取错误码对应的 HTTP 状态码"""
    return ERROR_TO_HTTP.get(error_code, 500)