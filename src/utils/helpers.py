"""
Common helper utilities for Agentic Analytics Platform.
Provides trace ID generation, timestamps, error classification, and decorators.
"""

import uuid
import time
import functools
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Any, Optional, TypeVar, ParamSpec
from dataclasses import dataclass


# Type hints for decorators
P = ParamSpec('P')
T = TypeVar('T')


class ErrorCategory(Enum):
    """
    Error classification for diagnosability.
    Each category maps to a specific layer for debugging.
    """
    RETRIEVAL_ERROR = "RETRIEVAL_ERROR"     # Vector search, embedding issues
    RUNTIME_ERROR = "RUNTIME_ERROR"         # Agent loop, LLM call issues
    DATA_ERROR = "DATA_ERROR"               # Semantic data, metadata issues
    CONTROL_PLANE_ERROR = "CONTROL_PLANE_ERROR"  # Policy, permissions issues
    VALIDATION_ERROR = "VALIDATION_ERROR"   # Input validation issues
    TIMEOUT_ERROR = "TIMEOUT_ERROR"         # Operation timeout
    UNKNOWN_ERROR = "UNKNOWN_ERROR"         # Unclassified errors


@dataclass
class PlatformError:
    """
    Structured platform error with classification and context.
    """
    category: ErrorCategory
    message: str
    trace_id: Optional[str] = None
    operation: Optional[str] = None
    details: Optional[dict] = None
    original_exception: Optional[Exception] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging/serialization."""
        return {
            "category": self.category.value,
            "message": self.message,
            "trace_id": self.trace_id,
            "operation": self.operation,
            "details": self.details,
        }
    
    def __str__(self) -> str:
        return f"[{self.category.value}] {self.message}"


def generate_trace_id() -> str:
    """
    Generate a unique trace ID for request tracking.
    Format: 8-character hex string for readability + full UUID available.
    """
    return uuid.uuid4().hex


def generate_short_id() -> str:
    """Generate a short 8-character ID for display purposes."""
    return uuid.uuid4().hex[:8]


def timestamp_now() -> str:
    """
    Get current timestamp in ISO 8601 format with UTC timezone.
    Example: 2024-12-29T09:30:00.123456Z
    """
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def timestamp_epoch_ms() -> int:
    """Get current timestamp as milliseconds since epoch."""
    return int(time.time() * 1000)


def duration_ms(start_time: float) -> float:
    """
    Calculate duration in milliseconds from a start time.
    
    Args:
        start_time: Start time from time.perf_counter()
    
    Returns:
        Duration in milliseconds
    """
    return (time.perf_counter() - start_time) * 1000


def classify_error(exception: Exception) -> ErrorCategory:
    """
    Classify an exception into an error category.
    
    Args:
        exception: The exception to classify
    
    Returns:
        Appropriate ErrorCategory
    """
    error_type = type(exception).__name__
    error_msg = str(exception).lower()
    
    # Classify based on exception type and message
    if "timeout" in error_msg:
        return ErrorCategory.TIMEOUT_ERROR
    elif "permission" in error_msg or "access" in error_msg:
        return ErrorCategory.CONTROL_PLANE_ERROR
    elif "validation" in error_msg or "invalid" in error_msg:
        return ErrorCategory.VALIDATION_ERROR
    elif "embedding" in error_msg or "vector" in error_msg or "retrieval" in error_msg:
        return ErrorCategory.RETRIEVAL_ERROR
    elif "data" in error_msg or "metadata" in error_msg or "schema" in error_msg:
        return ErrorCategory.DATA_ERROR
    elif "llm" in error_msg or "model" in error_msg or "openai" in error_msg:
        return ErrorCategory.RUNTIME_ERROR
    else:
        return ErrorCategory.UNKNOWN_ERROR


def create_error(
    category: ErrorCategory,
    message: str,
    trace_id: Optional[str] = None,
    operation: Optional[str] = None,
    details: Optional[dict] = None,
    exception: Optional[Exception] = None
) -> PlatformError:
    """
    Factory function to create a structured platform error.
    """
    return PlatformError(
        category=category,
        message=message,
        trace_id=trace_id,
        operation=operation,
        details=details,
        original_exception=exception
    )


def safe_dict_get(d: dict, *keys, default: Any = None) -> Any:
    """
    Safely get nested dictionary values.
    
    Args:
        d: Dictionary to search
        *keys: Sequence of keys for nested access
        default: Default value if any key is missing
    
    Returns:
        Value at nested key path, or default
    """
    current = d
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate a string to max length with suffix."""
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


def format_token_count(count: int) -> str:
    """Format token count with K/M suffix for readability."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def format_cost(cost: float) -> str:
    """Format cost in USD with appropriate precision."""
    if cost < 0.01:
        return f"${cost:.4f}"
    elif cost < 1.00:
        return f"${cost:.3f}"
    else:
        return f"${cost:.2f}"


def format_duration(ms: float) -> str:
    """Format duration with appropriate units."""
    if ms < 1:
        return f"{ms * 1000:.0f}μs"
    elif ms < 1000:
        return f"{ms:.1f}ms"
    elif ms < 60000:
        return f"{ms / 1000:.2f}s"
    else:
        return f"{ms / 60000:.1f}m"
