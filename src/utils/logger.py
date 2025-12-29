"""
Structured logging utilities for Agentic Analytics Platform.
Provides JSON-formatted logs for production and readable logs for development.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Optional, Any, Dict
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    Each log entry is a single JSON object for easy parsing.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, "trace_id"):
            log_entry["trace_id"] = record.trace_id
        if hasattr(record, "operation"):
            log_entry["operation"] = record.operation
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data
            
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry, default=str)


class ConsoleFormatter(logging.Formatter):
    """
    Human-readable formatter for development/console output.
    Color-coded by log level.
    """
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.utcnow().strftime("%H:%M:%S.%f")[:-3]
        
        # Build base message
        msg = f"{color}[{timestamp}] {record.levelname:8}{self.RESET} "
        msg += f"{record.name}: {record.getMessage()}"
        
        # Add trace_id if present
        if hasattr(record, "trace_id"):
            msg += f" [trace:{record.trace_id[:8]}]"
            
        # Add duration if present
        if hasattr(record, "duration_ms"):
            msg += f" ({record.duration_ms:.2f}ms)"
            
        return msg


class PlatformLogger:
    """
    Platform-aware logger wrapper.
    Provides context injection and structured logging helpers.
    """
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
        self._context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs):
        """Set persistent context fields for all log messages."""
        self._context.update(kwargs)
    
    def clear_context(self):
        """Clear all context fields."""
        self._context.clear()
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal log method with context injection."""
        extra = {**self._context, **kwargs}
        self._logger.log(level, message, extra={"extra_data": extra} if extra else {})
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)
    
    def operation_start(self, operation: str, trace_id: str, **kwargs):
        """Log the start of an operation."""
        record = self._logger.makeRecord(
            self._logger.name, logging.INFO,
            "", 0, f"Starting: {operation}", (), None
        )
        record.trace_id = trace_id
        record.operation = operation
        for k, v in kwargs.items():
            setattr(record, k, v)
        self._logger.handle(record)
    
    def operation_end(self, operation: str, trace_id: str, duration_ms: float, 
                      success: bool = True, **kwargs):
        """Log the end of an operation with duration."""
        status = "Completed" if success else "Failed"
        record = self._logger.makeRecord(
            self._logger.name, logging.INFO if success else logging.ERROR,
            "", 0, f"{status}: {operation}", (), None
        )
        record.trace_id = trace_id
        record.operation = operation
        record.duration_ms = duration_ms
        for k, v in kwargs.items():
            setattr(record, k, v)
        self._logger.handle(record)


# Logger registry
_loggers: Dict[str, PlatformLogger] = {}


def get_logger(name: str, log_level: Optional[str] = None, 
               log_format: Optional[str] = None) -> PlatformLogger:
    """
    Get or create a logger with the specified name.
    
    Args:
        name: Logger name (usually __name__ of the module)
        log_level: Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Override format ("json" or "text")
    
    Returns:
        PlatformLogger instance
    """
    if name in _loggers:
        return _loggers[name]
    
    # Import here to avoid circular dependency
    from src.utils.config import get_settings
    settings = get_settings()
    
    # Determine settings
    level = getattr(logging, (log_level or settings.observability.log_level).upper())
    fmt = log_format or settings.observability.log_format
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()  # Remove any existing handlers
    
    # Add handler based on format
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    if fmt == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(ConsoleFormatter())
    
    logger.addHandler(handler)
    
    # Wrap in PlatformLogger
    platform_logger = PlatformLogger(logger)
    _loggers[name] = platform_logger
    
    return platform_logger


def get_root_logger() -> PlatformLogger:
    """Get the root platform logger."""
    return get_logger("agentic-analytics-platform")
