"""
指标收集器

基于 SPEC 的监控指标
"""

from typing import Any
from datetime import datetime, timedelta
from collections import defaultdict


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        # 任务统计
        self.tasks_total = 0
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.tasks_aborted = 0
        self.total_rounds = 0

        # LLM 统计
        self.llm_calls_total = 0
        self.llm_calls_success = 0
        self.llm_calls_failed = 0
        self.llm_latencies: list[float] = []

        # 业务统计
        self.emergence_count = 0
        self.valley_count = 0
        self.human_intervention_count = 0
        self.rebuttal_count = 0

        # 历史记录（保留最近 10000 条）
        self.history: list[dict] = []
        self.max_history = 10000

    def record_task_start(self) -> None:
        """记录任务开始"""
        self.tasks_total += 1

    def record_task_completed(self, rounds: int) -> None:
        """记录任务完成"""
        self.tasks_completed += 1
        self.total_rounds += rounds
        self._record_event("task_completed", {"rounds": rounds})

    def record_task_failed(self, reason: str) -> None:
        """记录任务失败"""
        self.tasks_failed += 1
        self._record_event("task_failed", {"reason": reason})

    def record_task_aborted(self, reason: str) -> None:
        """记录任务中止"""
        self.tasks_aborted += 1
        self._record_event("task_aborted", {"reason": reason})

    def record_llm_call(self, latency_ms: float, success: bool) -> None:
        """记录 LLM 调用"""
        self.llm_calls_total += 1
        self.llm_latencies.append(latency_ms)
        if success:
            self.llm_calls_success += 1
        else:
            self.llm_calls_failed += 1
        self._record_event("llm_call", {"latency_ms": latency_ms, "success": success})

    def record_emergence(self, round_num: int) -> None:
        """记录涌现成功"""
        self.emergence_count += 1
        self._record_event("emergence", {"round": round_num})

    def record_valley(self, round_num: int) -> None:
        """记录低谷触发"""
        self.valley_count += 1
        self._record_event("valley", {"round": round_num})

    def record_human_intervention(self, round_num: int, operation: str) -> None:
        """记录人工介入"""
        self.human_intervention_count += 1
        self._record_event("human_intervention", {"round": round_num, "operation": operation})

    def record_rebuttal(self, round_num: int) -> None:
        """记录弱势方重产"""
        self.rebuttal_count += 1
        self._record_event("rebuttal", {"round": round_num})

    def _record_event(self, event_type: str, data: dict) -> None:
        """记录事件到历史"""
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": event_type,
            "data": data,
        }
        self.history.append(event)
        # 超过上限时删除最老的
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def get_metrics(self) -> dict:
        """获取当前指标"""
        avg_rounds = (
            self.total_rounds / self.tasks_completed
            if self.tasks_completed > 0
            else 0
        )
        avg_latency = (
            sum(self.llm_latencies) / len(self.llm_latencies)
            if self.llm_latencies
            else 0
        )

        return {
            "tasks": {
                "total": self.tasks_total,
                "completed": self.tasks_completed,
                "failed": self.tasks_failed,
                "aborted": self.tasks_aborted,
                "avg_rounds": round(avg_rounds, 2),
            },
            "llm": {
                "calls_total": self.llm_calls_total,
                "calls_success": self.llm_calls_success,
                "calls_failed": self.llm_calls_failed,
                "success_rate": round(
                    self.llm_calls_success / self.llm_calls_total * 100
                    if self.llm_calls_total > 0
                    else 0,
                    2,
                ),
                "avg_latency_ms": round(avg_latency, 2),
            },
            "business": {
                "emergence_count": self.emergence_count,
                "valley_count": self.valley_count,
                "human_intervention_count": self.human_intervention_count,
                "rebuttal_count": self.rebuttal_count,
            },
        }

    def reset(self) -> None:
        """重置所有指标"""
        self.__init__()


# 全局实例
metrics = MetricsCollector()


# 便捷函数
def get_metrics() -> dict:
    """获取当前指标"""
    return metrics.get_metrics()


def record_llm_call(latency_ms: float, success: bool) -> None:
    """记录 LLM 调用"""
    metrics.record_llm_call(latency_ms, success)


def record_task_completed(rounds: int) -> None:
    """记录任务完成"""
    metrics.record_task_completed(rounds)


def record_emergence(round_num: int) -> None:
    """记录涌现成功"""
    metrics.record_emergence(round_num)


def record_valley(round_num: int) -> None:
    """记录低谷触发"""
    metrics.record_valley(round_num)


def record_human_intervention(round_num: int, operation: str) -> None:
    """记录人工介入"""
    metrics.record_human_intervention(round_num, operation)