"""
日志配置

基于 SPEC 的日志策略
"""

import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Any

from fih_emergence.errors import ErrorCode


def setup_logging(level: str = "INFO", log_dir: str = "logs") -> None:
    """配置日志"""
    # 确保日志目录存在
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # 今天的日志文件
    today = datetime.now().strftime("%Y%m%d")
    log_file = log_path / f"fih-{today}.log"
    
    # 根日志级别
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )

    # 设置第三方库日志级别
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    
    # 清理 30 天前的日志
    cleanup_old_logs(log_path, days=30)


def cleanup_old_logs(log_dir: Path, days: int = 30) -> None:
    """清理旧日志文件"""
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=days)
    
    for log_file in log_dir.glob("fih-*.log"):
        if log_file.stat().st_mtime < cutoff.timestamp():
            try:
                log_file.unlink()
            except Exception:
                pass


# 预定义的日志记录器
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"fih.{name}")


# =======================
# 结构化日志工具
# =======================

import json
from datetime import datetime


class StructuredLogger:
    """结构化日志记录器"""

    def __init__(self, name: str):
        self.logger = get_logger(name)

    def log(
        self,
        level: str,
        message: str,
        session_id: str | None = None,
        round_num: int | None = None,
        error_code: ErrorCode | None = None,
        **kwargs: Any,
    ) -> None:
        """结构化日志"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "message": message,
            "logger": self.logger.name,
        }

        if session_id:
            log_data["session_id"] = session_id
        if round_num is not None:
            log_data["round"] = round_num
        if error_code:
            log_data["error_code"] = error_code.value if hasattr(error_code, 'value') else str(error_code)

        log_data.update(kwargs)

        # 输出 JSON 格式日志
        self.logger.log(getattr(logging, level.upper()), json.dumps(log_data))

    def info(self, message: str, **kwargs: Any) -> None:
        self.log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self.log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self.log("ERROR", message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        self.log("DEBUG", message, **kwargs)


# =======================
# 预配置的日志记录器
# =======================

api_logger = StructuredLogger("api")
workflow_logger = StructuredLogger("workflow")
llm_logger = StructuredLogger("llm")
db_logger = StructuredLogger("db")
audit_logger = StructuredLogger("audit")