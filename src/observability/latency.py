"""
Latency metrics tracking for Agentic Analytics Platform.
Captures per-operation latency with percentile calculations.
"""

import time
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from enum import Enum
from contextlib import contextmanager

from src.utils.helpers import timestamp_now, duration_ms, format_duration


class OperationType(Enum):
    """Types of operations to track latency for."""
    TOTAL_REQUEST = "total_request"
    LLM_CALL = "llm_call"
    RETRIEVAL = "retrieval"
    EMBEDDING = "embedding"
    RERANKING = "reranking"
    TOOL_EXECUTION = "tool_execution"
    POLICY_CHECK = "policy_check"
    CONTEXT_BUILD = "context_build"


@dataclass
class LatencyRecord:
    """Single latency measurement."""
    operation: OperationType
    duration_ms: float
    timestamp: str = field(default_factory=timestamp_now)
    trace_id: Optional[str] = None
    success: bool = True
    metadata: Optional[Dict] = None
    
    def to_dict(self) -> dict:
        return {
            "operation": self.operation.value,
            "duration_ms": round(self.duration_ms, 3),
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "success": self.success,
            "metadata": self.metadata,
        }


@dataclass
class LatencyStats:
    """Aggregated latency statistics for an operation type."""
    operation: OperationType
    count: int
    min_ms: float
    max_ms: float
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    total_ms: float
    
    def to_dict(self) -> dict:
        return {
            "operation": self.operation.value,
            "count": self.count,
            "min_ms": round(self.min_ms, 3),
            "max_ms": round(self.max_ms, 3),
            "mean_ms": round(self.mean_ms, 3),
            "median_ms": round(self.median_ms, 3),
            "p95_ms": round(self.p95_ms, 3),
            "p99_ms": round(self.p99_ms, 3),
            "total_ms": round(self.total_ms, 3),
        }


class LatencyTracker:
    """
    Tracks operation latencies with percentile calculations.
    Provides timing context managers and decorators.
    """
    
    def __init__(self):
        self._records: Dict[OperationType, List[LatencyRecord]] = {
            op: [] for op in OperationType
        }
        self._active_timers: Dict[str, tuple] = {}  # timer_id -> (operation, start_time, trace_id)
    
    def start(self, operation: OperationType, trace_id: Optional[str] = None) -> str:
        """
        Start timing an operation.
        
        Returns:
            Timer ID to use with stop()
        """
        timer_id = f"{operation.value}_{id(operation)}_{time.perf_counter()}"
        self._active_timers[timer_id] = (operation, time.perf_counter(), trace_id)
        return timer_id
    
    def stop(self, timer_id: str, success: bool = True, 
             metadata: Optional[Dict] = None) -> Optional[LatencyRecord]:
        """
        Stop timing and record the latency.
        
        Returns:
            LatencyRecord if timer was valid, None otherwise
        """
        if timer_id not in self._active_timers:
            return None
        
        operation, start_time, trace_id = self._active_timers.pop(timer_id)
        elapsed_ms = duration_ms(start_time)
        
        record = LatencyRecord(
            operation=operation,
            duration_ms=elapsed_ms,
            trace_id=trace_id,
            success=success,
            metadata=metadata
        )
        
        self._records[operation].append(record)
        return record
    
    def record(self, operation: OperationType, duration_ms: float,
               trace_id: Optional[str] = None, success: bool = True,
               metadata: Optional[Dict] = None) -> LatencyRecord:
        """Record a latency measurement directly."""
        record = LatencyRecord(
            operation=operation,
            duration_ms=duration_ms,
            trace_id=trace_id,
            success=success,
            metadata=metadata
        )
        self._records[operation].append(record)
        return record
    
    @contextmanager
    def measure(self, operation: OperationType, trace_id: Optional[str] = None):
        """
        Context manager for measuring operation latency.
        
        Usage:
            with latency_tracker.measure(OperationType.LLM_CALL, trace_id):
                # ... do LLM call ...
        """
        timer_id = self.start(operation, trace_id)
        success = True
        try:
            yield
        except Exception:
            success = False
            raise
        finally:
            self.stop(timer_id, success=success)
    
    def _calculate_percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile from sorted values."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * (percentile / 100)
        f = int(k)
        c = f + 1
        
        if c >= len(sorted_values):
            return sorted_values[-1]
        
        return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)
    
    def get_stats(self, operation: OperationType) -> Optional[LatencyStats]:
        """Get aggregated statistics for an operation type."""
        records = self._records[operation]
        if not records:
            return None
        
        durations = [r.duration_ms for r in records]
        
        return LatencyStats(
            operation=operation,
            count=len(durations),
            min_ms=min(durations),
            max_ms=max(durations),
            mean_ms=statistics.mean(durations),
            median_ms=statistics.median(durations),
            p95_ms=self._calculate_percentile(durations, 95),
            p99_ms=self._calculate_percentile(durations, 99),
            total_ms=sum(durations)
        )
    
    def get_all_stats(self) -> Dict[str, LatencyStats]:
        """Get statistics for all operation types that have data."""
        result = {}
        for operation in OperationType:
            stats = self.get_stats(operation)
            if stats and stats.count > 0:
                result[operation.value] = stats.to_dict()
        return result
    
    def get_records_for_trace(self, trace_id: str) -> List[LatencyRecord]:
        """Get all latency records for a specific trace."""
        result = []
        for records in self._records.values():
            result.extend([r for r in records if r.trace_id == trace_id])
        return sorted(result, key=lambda r: r.timestamp)
    
    def get_total_latency_for_trace(self, trace_id: str) -> float:
        """Get total latency in ms for a trace."""
        records = self.get_records_for_trace(trace_id)
        return sum(r.duration_ms for r in records)
    
    def get_summary(self) -> Dict:
        """Get a summary of all latency tracking."""
        total_records = sum(len(r) for r in self._records.values())
        all_durations = []
        for records in self._records.values():
            all_durations.extend([r.duration_ms for r in records])
        
        return {
            "total_records": total_records,
            "operations_tracked": len([op for op in OperationType if self._records[op]]),
            "total_time_ms": round(sum(all_durations), 3) if all_durations else 0,
            "avg_duration_ms": round(statistics.mean(all_durations), 3) if all_durations else 0,
            "stats_by_operation": self.get_all_stats()
        }
    
    def reset(self) -> None:
        """Reset all latency data."""
        for op in OperationType:
            self._records[op].clear()
        self._active_timers.clear()


# Singleton instance
_latency_tracker: Optional[LatencyTracker] = None


def get_latency_tracker() -> LatencyTracker:
    """Get the global latency tracker instance."""
    global _latency_tracker
    if _latency_tracker is None:
        _latency_tracker = LatencyTracker()
    return _latency_tracker
