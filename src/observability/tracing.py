"""
Decision trace logging for Agentic Analytics Platform.
Captures every agent decision step for debugging and accountability.
"""

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
from pathlib import Path
from enum import Enum

from src.utils.helpers import generate_trace_id, timestamp_now, duration_ms
from src.utils.config import get_settings


class TraceEventType(Enum):
    """Types of events that can be traced."""
    QUERY_RECEIVED = "query_received"
    INTENT_CLASSIFIED = "intent_classified"
    RETRIEVAL_START = "retrieval_start"
    RETRIEVAL_END = "retrieval_end"
    CONTEXT_BUILT = "context_built"
    LLM_CALL_START = "llm_call_start"
    LLM_CALL_END = "llm_call_end"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_END = "tool_call_end"
    RESPONSE_GENERATED = "response_generated"
    ERROR_OCCURRED = "error_occurred"
    POLICY_CHECK = "policy_check"
    KILL_SWITCH_TRIGGERED = "kill_switch_triggered"


@dataclass
class TraceEvent:
    """
    Single trace event capturing a decision step or action.
    """
    event_type: TraceEventType
    timestamp: str
    step_number: int
    action: str
    duration_ms: Optional[float] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "step_number": self.step_number,
            "action": self.action,
            "success": self.success,
        }
        if self.duration_ms is not None:
            result["duration_ms"] = round(self.duration_ms, 3)
        if self.input_data:
            result["input"] = self._truncate_data(self.input_data)
        if self.output_data:
            result["output"] = self._truncate_data(self.output_data)
        if self.metadata:
            result["metadata"] = self.metadata
        if self.error_message:
            result["error"] = self.error_message
        return result
    
    def _truncate_data(self, data: dict, max_str_len: int = 500) -> dict:
        """Truncate long string values for reasonable log size."""
        result = {}
        for k, v in data.items():
            if isinstance(v, str) and len(v) > max_str_len:
                result[k] = v[:max_str_len] + f"... [truncated, {len(v)} chars total]"
            elif isinstance(v, dict):
                result[k] = self._truncate_data(v, max_str_len)
            else:
                result[k] = v
        return result


@dataclass
class Trace:
    """
    Complete trace for a single request/query.
    Contains all events from start to finish.
    """
    trace_id: str
    query: str
    start_time: str
    end_time: Optional[str] = None
    events: List[TraceEvent] = field(default_factory=list)
    total_duration_ms: Optional[float] = None
    token_usage: Optional[Dict[str, int]] = None
    cost_usd: Optional[float] = None
    success: bool = True
    error_category: Optional[str] = None
    final_response: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "query": self.query,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration_ms": round(self.total_duration_ms, 3) if self.total_duration_ms else None,
            "success": self.success,
            "error_category": self.error_category,
            "token_usage": self.token_usage,
            "cost_usd": round(self.cost_usd, 6) if self.cost_usd else None,
            "event_count": len(self.events),
            "events": [e.to_dict() for e in self.events],
            "final_response": self.final_response,
            "metadata": self.metadata,
        }


class Tracer:
    """
    Tracer for capturing decision traces.
    Thread-safe trace management with JSON export.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        settings = get_settings()
        self._output_dir = Path(output_dir or settings.observability.trace_output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._active_traces: Dict[str, Trace] = {}
        self._step_counters: Dict[str, int] = {}
        self._start_times: Dict[str, float] = {}
    
    def start_trace(self, query: str, trace_id: Optional[str] = None, 
                    metadata: Optional[dict] = None) -> str:
        """
        Start a new trace for a query.
        
        Args:
            query: The user query being processed
            trace_id: Optional pre-generated trace ID
            metadata: Optional metadata to attach
        
        Returns:
            The trace ID
        """
        trace_id = trace_id or generate_trace_id()
        
        trace = Trace(
            trace_id=trace_id,
            query=query,
            start_time=timestamp_now(),
            metadata=metadata or {}
        )
        
        self._active_traces[trace_id] = trace
        self._step_counters[trace_id] = 0
        self._start_times[trace_id] = time.perf_counter()
        
        # Add initial event
        self.add_event(
            trace_id=trace_id,
            event_type=TraceEventType.QUERY_RECEIVED,
            action="Query received and trace started",
            input_data={"query": query}
        )
        
        return trace_id
    
    def add_event(
        self,
        trace_id: str,
        event_type: TraceEventType,
        action: str,
        duration_ms: Optional[float] = None,
        input_data: Optional[dict] = None,
        output_data: Optional[dict] = None,
        metadata: Optional[dict] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """Add an event to an active trace."""
        if trace_id not in self._active_traces:
            return  # Silently ignore if trace doesn't exist
        
        self._step_counters[trace_id] += 1
        
        event = TraceEvent(
            event_type=event_type,
            timestamp=timestamp_now(),
            step_number=self._step_counters[trace_id],
            action=action,
            duration_ms=duration_ms,
            input_data=input_data,
            output_data=output_data,
            metadata=metadata,
            success=success,
            error_message=error_message
        )
        
        self._active_traces[trace_id].events.append(event)
        
        # If error, mark trace as failed
        if not success:
            self._active_traces[trace_id].success = False
    
    def end_trace(
        self,
        trace_id: str,
        success: bool = True,
        final_response: Optional[str] = None,
        token_usage: Optional[Dict[str, int]] = None,
        cost_usd: Optional[float] = None,
        error_category: Optional[str] = None
    ) -> Optional[Trace]:
        """
        End a trace and export to file.
        
        Returns:
            The completed Trace object
        """
        if trace_id not in self._active_traces:
            return None
        
        trace = self._active_traces[trace_id]
        trace.end_time = timestamp_now()
        trace.total_duration_ms = duration_ms(self._start_times[trace_id])
        trace.success = success
        trace.final_response = final_response
        trace.token_usage = token_usage
        trace.cost_usd = cost_usd
        trace.error_category = error_category
        
        # Add final event
        self.add_event(
            trace_id=trace_id,
            event_type=TraceEventType.RESPONSE_GENERATED,
            action="Trace completed",
            output_data={"success": success, "response_length": len(final_response) if final_response else 0}
        )
        
        # Export and cleanup
        self._export_trace(trace)
        del self._active_traces[trace_id]
        del self._step_counters[trace_id]
        del self._start_times[trace_id]
        
        return trace
    
    def _export_trace(self, trace: Trace) -> Path:
        """Export trace to JSON file."""
        filename = f"{trace.start_time[:10]}_{trace.trace_id[:8]}.json"
        filepath = self._output_dir / filename
        
        with open(filepath, "w") as f:
            json.dump(trace.to_dict(), f, indent=2, default=str)
        
        return filepath
    
    def get_active_trace(self, trace_id: str) -> Optional[Trace]:
        """Get an active trace by ID."""
        return self._active_traces.get(trace_id)
    
    def list_active_traces(self) -> List[str]:
        """List all active trace IDs."""
        return list(self._active_traces.keys())


# Singleton tracer instance
_tracer: Optional[Tracer] = None


def get_tracer() -> Tracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer
