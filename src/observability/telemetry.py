"""
Unified telemetry interface for Agentic Analytics Platform.
Combines tracing, cost, and latency tracking with decorators.
"""

import functools
import time
from dataclasses import dataclass
from typing import Optional, Callable, Any, Dict, TypeVar, ParamSpec
from contextlib import contextmanager

from src.observability.tracing import Tracer, TraceEventType, get_tracer
from src.observability.cost import CostTracker, get_cost_tracker, CostAlertLevel
from src.observability.latency import LatencyTracker, OperationType, get_latency_tracker
from src.utils.helpers import generate_trace_id, timestamp_now, duration_ms
from src.utils.config import get_settings


# Type hints for decorators
P = ParamSpec('P')
T = TypeVar('T')


@dataclass
class TelemetryContext:
    """Context for a telemetry-tracked operation."""
    trace_id: str
    operation: str
    start_time: float
    
    def elapsed_ms(self) -> float:
        return duration_ms(self.start_time)


class Telemetry:
    """
    Unified telemetry interface combining all observability components.
    Single entry point for tracing, cost tracking, and latency measurement.
    """
    
    def __init__(
        self,
        tracer: Optional[Tracer] = None,
        cost_tracker: Optional[CostTracker] = None,
        latency_tracker: Optional[LatencyTracker] = None
    ):
        self._tracer = tracer or get_tracer()
        self._cost_tracker = cost_tracker or get_cost_tracker()
        self._latency_tracker = latency_tracker or get_latency_tracker()
        self._settings = get_settings()
    
    @property
    def tracer(self) -> Tracer:
        return self._tracer
    
    @property
    def cost_tracker(self) -> CostTracker:
        return self._cost_tracker
    
    @property
    def latency_tracker(self) -> LatencyTracker:
        return self._latency_tracker
    
    def start_request(self, query: str, trace_id: Optional[str] = None,
                      metadata: Optional[dict] = None) -> str:
        """
        Start tracking a new request.
        Initializes trace and latency measurement.
        
        Returns:
            Trace ID for the request
        """
        trace_id = trace_id or generate_trace_id()
        
        # Start trace
        self._tracer.start_trace(query, trace_id, metadata)
        
        # Start total request latency
        self._latency_tracker.start(OperationType.TOTAL_REQUEST, trace_id)
        
        return trace_id
    
    def end_request(
        self,
        trace_id: str,
        success: bool = True,
        response: Optional[str] = None,
        token_usage: Optional[Dict[str, int]] = None,
        error_category: Optional[str] = None
    ) -> Dict:
        """
        End tracking for a request.
        Finalizes trace and returns summary.
        """
        # Stop total request latency
        timer_id = f"{OperationType.TOTAL_REQUEST.value}_{trace_id}"
        # Find the correct timer
        for tid in list(self._latency_tracker._active_timers.keys()):
            if OperationType.TOTAL_REQUEST.value in tid:
                op, start, tr_id = self._latency_tracker._active_timers[tid]
                if tr_id == trace_id:
                    self._latency_tracker.stop(tid, success=success)
                    break
        
        # Calculate costs if token usage provided
        cost_usd = None
        if token_usage:
            record = self._cost_tracker.record_usage(
                prompt_tokens=token_usage.get("prompt_tokens", 0),
                completion_tokens=token_usage.get("completion_tokens", 0),
                model=token_usage.get("model", self._settings.llm.model_name),
                trace_id=trace_id,
                operation="total_request"
            )
            cost_usd = record.total_cost
        
        # End trace
        trace = self._tracer.end_trace(
            trace_id=trace_id,
            success=success,
            final_response=response,
            token_usage=token_usage,
            cost_usd=cost_usd,
            error_category=error_category
        )
        
        # Get latency records for this trace
        latency_records = self._latency_tracker.get_records_for_trace(trace_id)
        
        return {
            "trace_id": trace_id,
            "success": success,
            "duration_ms": trace.total_duration_ms if trace else None,
            "cost_usd": cost_usd,
            "token_usage": token_usage,
            "latency_breakdown": [r.to_dict() for r in latency_records],
            "event_count": len(trace.events) if trace else 0,
        }
    
    def add_trace_event(
        self,
        trace_id: str,
        event_type: TraceEventType,
        action: str,
        **kwargs
    ) -> None:
        """Add an event to the trace."""
        self._tracer.add_event(trace_id, event_type, action, **kwargs)
    
    def record_llm_call(
        self,
        trace_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
        duration_ms: float,
        success: bool = True
    ) -> None:
        """Record an LLM call with cost and latency."""
        # Record cost
        self._cost_tracker.record_usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model,
            trace_id=trace_id,
            operation="llm_call"
        )
        
        # Record latency
        self._latency_tracker.record(
            operation=OperationType.LLM_CALL,
            duration_ms=duration_ms,
            trace_id=trace_id,
            success=success
        )
        
        # Add trace event
        self._tracer.add_event(
            trace_id=trace_id,
            event_type=TraceEventType.LLM_CALL_END,
            action=f"LLM call completed ({model})",
            duration_ms=duration_ms,
            output_data={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            },
            success=success
        )
    
    def track_tokens(
        self,
        trace_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> None:
        """Track token usage for an LLM call."""
        self._cost_tracker.record_usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model,
            trace_id=trace_id,
            operation="llm_call"
        )
    
    @contextmanager
    def measure_operation(
        self,
        trace_id: str,
        operation: OperationType,
        operation_name: str,
        event_type: TraceEventType = TraceEventType.TOOL_CALL_START
    ):
        """
        Context manager for measuring an operation with full telemetry.
        
        Usage:
            with telemetry.measure_operation(trace_id, OperationType.RETRIEVAL, "vector_search"):
                # ... do operation ...
        """
        # Add start event
        self._tracer.add_event(
            trace_id=trace_id,
            event_type=event_type,
            action=f"Starting: {operation_name}"
        )
        
        start_time = time.perf_counter()
        success = True
        error_msg = None
        
        try:
            yield
        except Exception as e:
            success = False
            error_msg = str(e)
            raise
        finally:
            elapsed = duration_ms(start_time)
            
            # Record latency
            self._latency_tracker.record(
                operation=operation,
                duration_ms=elapsed,
                trace_id=trace_id,
                success=success
            )
            
            # Add end event
            end_event_type = TraceEventType.TOOL_CALL_END if event_type == TraceEventType.TOOL_CALL_START else TraceEventType.RESPONSE_GENERATED
            self._tracer.add_event(
                trace_id=trace_id,
                event_type=end_event_type,
                action=f"Completed: {operation_name}",
                duration_ms=elapsed,
                success=success,
                error_message=error_msg
            )
    
    def get_cost_alert_level(self) -> CostAlertLevel:
        """Get current cost alert level."""
        return self._cost_tracker.get_alert_level()
    
    def get_summary(self) -> Dict:
        """Get comprehensive telemetry summary."""
        return {
            "timestamp": timestamp_now(),
            "cost": self._cost_tracker.get_stats(),
            "latency": self._latency_tracker.get_summary(),
            "active_traces": self._tracer.list_active_traces(),
        }
    
    def export_all(self) -> Dict[str, str]:
        """Export all telemetry data to files."""
        return {
            "cost_report": self._cost_tracker.export_json(),
        }


def trace_operation(
    operation: OperationType = OperationType.TOOL_EXECUTION,
    event_type: TraceEventType = TraceEventType.TOOL_CALL_START
):
    """
    Decorator for tracing function execution with telemetry.
    
    The decorated function must accept 'trace_id' as a keyword argument.
    
    Usage:
        @trace_operation(OperationType.RETRIEVAL)
        def search_vectors(query: str, trace_id: str = None):
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            trace_id = kwargs.get('trace_id')
            if not trace_id:
                # No trace ID, just execute the function
                return func(*args, **kwargs)
            
            telemetry = get_telemetry()
            operation_name = func.__name__
            
            with telemetry.measure_operation(trace_id, operation, operation_name, event_type):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Singleton instance
_telemetry: Optional[Telemetry] = None


def get_telemetry() -> Telemetry:
    """Get the global telemetry instance."""
    global _telemetry
    if _telemetry is None:
        _telemetry = Telemetry()
    return _telemetry
