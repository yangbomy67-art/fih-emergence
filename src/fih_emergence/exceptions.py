"""
自定义异常类

基于 errors.py 的错误码定义
"""

from fih_emergence.errors import ErrorCode, get_http_status


class FIHException(Exception):
    """FIH 基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.LLM_UNKNOWN,
        details: dict | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.http_status = get_http_status(error_code)

    def to_dict(self) -> dict:
        return {
            "error": self.error_code.value,
            "message": self.message,
            "details": self.details,
        }


# =======================
# LLM 异常
# =======================


class LLMTimeoutError(FIHException):
    """LLM 调用超时"""

    def __init__(self, message: str = "LLM 调用超时", details: dict | None = None):
        super().__init__(message, ErrorCode.LLM_TIMEOUT, details)


class LLMRateLimitError(FIHException):
    """LLM 速率限制"""

    def __init__(self, message: str = "LLM 速率限制 (429)", details: dict | None = None):
        super().__init__(message, ErrorCode.LLM_RATE_LIMIT, details)


class LLMServerError(FIHException):
    """LLM 服务器错误"""

    def __init__(self, message: str = "LLM 服务器错误 (5xx)", details: dict | None = None):
        super().__init__(message, ErrorCode.LLM_SERVER_ERROR, details)


class LLMClientError(FIHException):
    """LLM 客户端错误"""

    def __init__(self, message: str = "LLM 客户端错误 (4xx)", details: dict | None = None):
        super().__init__(message, ErrorCode.LLM_CLIENT_ERROR, details)


class LLMConsecutiveFailuresError(FIHException):
    """LLM 连续失败"""

    def __init__(self, message: str = "LLM 连续失败 3 次", details: dict | None = None):
        super().__init__(message, ErrorCode.LLM_CONSECUTIVE_FAILURES, details)


# =======================
# 数据库异常
# =======================


class DatabaseError(FIHException):
    """数据库基础异常"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.DB_WRITE_FAILED,
        details: dict | None = None,
    ):
        super().__init__(message, error_code, details)


class DatabaseWriteError(DatabaseError):
    """数据库写入失败"""

    def __init__(self, message: str = "数据库写入失败", details: dict | None = None):
        super().__init__(message, ErrorCode.DB_WRITE_FAILED, details)


class DatabaseLockError(DatabaseError):
    """数据库锁冲突"""

    def __init__(self, message: str = "数据库锁冲突", details: dict | None = None):
        super().__init__(message, ErrorCode.DB_LOCK_CONFLICT, details)


class DatabaseNotFoundError(DatabaseError):
    """记录不存在"""

    def __init__(self, message: str = "记录不存在", details: dict | None = None):
        super().__init__(message, ErrorCode.DB_NOT_FOUND, details)


# =======================
# API 异常
# =======================


class APIError(FIHException):
    """API 基础异常"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.API_INVALID_INPUT,
        details: dict | None = None,
    ):
        super().__init__(message, error_code, details)


class SessionNotFoundError(APIError):
    """会话不存在"""

    def __init__(self, session_id: str):
        super().__init__(
            f"会话不存在: {session_id}",
            ErrorCode.API_SESSION_NOT_FOUND,
            {"session_id": session_id},
        )


class RoundInvalidError(APIError):
    """无效轮次"""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, ErrorCode.API_ROUND_INVALID, details)


class SnapshotNotFoundError(APIError):
    """快照不存在"""

    def __init__(self, round_num: int, available: list[int] | None = None):
        super().__init__(
            f"快照不存在: 第 {round_num} 轮",
            ErrorCode.API_SNAPSHOT_NOT_FOUND,
            {"round": round_num, "available_rounds": available or []},
        )


# =======================
# 工作流异常
# =======================


class WorkflowError(FIHException):
    """工作流基础异常"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.WORKFLOW_NODE_FAILED,
        details: dict | None = None,
    ):
        super().__init__(message, error_code, details)


class CheckpointCorruptedError(WorkflowError):
    """Checkpoint 损坏"""

    def __init__(self, message: str = "Checkpoint 损坏", details: dict | None = None):
        super().__init__(message, ErrorCode.WORKFLOW_CHECKPOINT_CORRUPTED, details)


class UnrecoverableError(WorkflowError):
    """不可恢复错误"""

    def __init__(self, message: str = "任务无法恢复", details: dict | None = None):
        super().__init__(message, ErrorCode.WORKFLOW_UNRECOVERABLE, details)


# =======================
# 业务异常
# =======================


class BusinessError(FIHException):
    """业务异常"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.BIZ_VALLEY_UNRESOLVED,
        details: dict | None = None,
    ):
        super().__init__(message, error_code, details)


class ValleyUnresolvedError(BusinessError):
    """低谷无法穿越"""

    def __init__(self, message: str = "低谷无法穿越，需要人工介入", details: dict | None = None):
        super().__init__(message, ErrorCode.BIZ_VALLEY_UNRESOLVED, details)


class FactConflictError(BusinessError):
    """Fact 冲突"""

    def __init__(self, message: str = "Fact 存在矛盾，需要人工裁决", details: dict | None = None):
        super().__init__(message, ErrorCode.BIZ_FACT_CONFLICT, details)


class DuplicateOutputError(BusinessError):
    """连续产出相同"""

    def __init__(self, message: str = "连续 2 轮产出相同，需要人工介入", details: dict | None = None):
        super().__init__(message, ErrorCode.BIZ_DUPLICATE_OUTPUT, details)