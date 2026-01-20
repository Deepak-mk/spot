"""
Token usage and cost tracking for Agentic Analytics Platform.
Tracks LLM API costs with budget alerting.
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from enum import Enum

from src.utils.helpers import timestamp_now, format_cost
from src.utils.config import get_settings


class CostAlertLevel(Enum):
    """Alert levels for cost tracking."""
    NORMAL = "normal"
    WARNING = "warning"  # 80% of budget
    CRITICAL = "critical"  # 100% of budget
    EXCEEDED = "exceeded"  # Over budget


@dataclass
class TokenUsage:
    """Token usage for a single LLM call."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str
    timestamp: str = field(default_factory=timestamp_now)
    trace_id: Optional[str] = None
    operation: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "model": self.model,
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "operation": self.operation,
        }


@dataclass
class CostRecord:
    """Cost record for a single LLM call."""
    token_usage: TokenUsage
    prompt_cost: float
    completion_cost: float
    total_cost: float
    
    def to_dict(self) -> dict:
        return {
            "token_usage": self.token_usage.to_dict(),
            "prompt_cost": round(self.prompt_cost, 6),
            "completion_cost": round(self.completion_cost, 6),
            "total_cost": round(self.total_cost, 6),
        }


# Pricing table (USD per 1K tokens)
MODEL_PRICING = {
    "gpt-4": {"prompt": 0.03, "completion": 0.06},
    "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
    "gpt-4o": {"prompt": 0.005, "completion": 0.015},
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
    "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
    "gpt-3.5-turbo-16k": {"prompt": 0.003, "completion": 0.004},
    # Local/open models - usually free
    "phi-3": {"prompt": 0.0, "completion": 0.0},
    "llama-3": {"prompt": 0.0, "completion": 0.0},
    "mistral": {"prompt": 0.0, "completion": 0.0},
    # Default for unknown models
    "default": {"prompt": 0.001, "completion": 0.002},
}


class CostTracker:
    """
    Tracks token usage and costs across requests.
    Provides budget alerting and cost export.
    """
    
    def __init__(self, budget_usd: Optional[float] = None):
        settings = get_settings()
        self._budget = budget_usd or 10.0  # Default $10 budget
        self._records: List[CostRecord] = []
        self._total_cost: float = 0.0
        self._total_prompt_tokens: int = 0
        self._total_completion_tokens: int = 0
        self._warning_threshold = settings.cost_warning_threshold
        self._error_threshold = settings.cost_error_threshold
        self._alert_callbacks: List[callable] = []
    
    def get_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing for a model, with fallback to default."""
        # Normalize model name
        model_lower = model.lower()
        
        for known_model, pricing in MODEL_PRICING.items():
            if known_model in model_lower:
                return pricing
        
        return MODEL_PRICING["default"]
    
    def calculate_cost(self, usage: TokenUsage) -> Tuple[float, float, float]:
        """
        Calculate cost for token usage.
        
        Returns:
            Tuple of (prompt_cost, completion_cost, total_cost)
        """
        pricing = self.get_pricing(usage.model)
        
        prompt_cost = (usage.prompt_tokens / 1000) * pricing["prompt"]
        completion_cost = (usage.completion_tokens / 1000) * pricing["completion"]
        total_cost = prompt_cost + completion_cost
        
        return prompt_cost, completion_cost, total_cost
    
    def record_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
        trace_id: Optional[str] = None,
        operation: Optional[str] = None
    ) -> CostRecord:
        """
        Record token usage and calculate costs.
        
        Returns:
            CostRecord with calculated costs
        """
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            model=model,
            trace_id=trace_id,
            operation=operation
        )
        
        prompt_cost, completion_cost, total_cost = self.calculate_cost(usage)
        
        record = CostRecord(
            token_usage=usage,
            prompt_cost=prompt_cost,
            completion_cost=completion_cost,
            total_cost=total_cost
        )
        
        self._records.append(record)
        self._total_cost += total_cost
        self._total_prompt_tokens += prompt_tokens
        self._total_completion_tokens += completion_tokens
        
        # Check budget alerts
        self._check_budget_alerts()
        
        return record
    
    def _check_budget_alerts(self) -> None:
        """Check and trigger budget alerts if thresholds exceeded."""
        ratio = self._total_cost / self._budget if self._budget > 0 else 0
        
        if ratio >= self._error_threshold:
            level = CostAlertLevel.EXCEEDED if ratio > 1.0 else CostAlertLevel.CRITICAL
        elif ratio >= self._warning_threshold:
            level = CostAlertLevel.WARNING
        else:
            level = CostAlertLevel.NORMAL
        
        if level != CostAlertLevel.NORMAL:
            for callback in self._alert_callbacks:
                callback(level, self._total_cost, self._budget, ratio)
    
    def add_alert_callback(self, callback: callable) -> None:
        """Add a callback for budget alerts."""
        self._alert_callbacks.append(callback)
    
    def get_alert_level(self) -> CostAlertLevel:
        """Get current alert level based on budget usage."""
        if self._budget <= 0:
            return CostAlertLevel.NORMAL
        
        ratio = self._total_cost / self._budget
        
        if ratio > 1.0:
            return CostAlertLevel.EXCEEDED
        elif ratio >= self._error_threshold:
            return CostAlertLevel.CRITICAL
        elif ratio >= self._warning_threshold:
            return CostAlertLevel.WARNING
        return CostAlertLevel.NORMAL
    
    def get_stats(self) -> Dict:
        """Get cost tracking statistics."""
        return {
            "total_cost_usd": round(self._total_cost, 6),
            "budget_usd": self._budget,
            "budget_used_pct": round((self._total_cost / self._budget * 100) if self._budget > 0 else 0, 2),
            "alert_level": self.get_alert_level().value,
            "total_prompt_tokens": self._total_prompt_tokens,
            "total_completion_tokens": self._total_completion_tokens,
            "total_tokens": self._total_prompt_tokens + self._total_completion_tokens,
            "request_count": len(self._records),
            "avg_cost_per_request": round(self._total_cost / len(self._records), 6) if self._records else 0,
        }
    
    def get_cost_by_trace(self, trace_id: str) -> float:
        """Get total cost for a specific trace."""
        return sum(r.total_cost for r in self._records if r.token_usage.trace_id == trace_id)
    
    def export_json(self, filepath: Optional[str] = None) -> str:
        """Export cost records to JSON file."""
        settings = get_settings()
        output_dir = Path(settings.trace_output_dir)
        
        if filepath:
            path = Path(filepath)
        else:
            path = output_dir / f"cost_report_{timestamp_now()[:10]}.json"
        
        data = {
            "generated_at": timestamp_now(),
            "stats": self.get_stats(),
            "records": [r.to_dict() for r in self._records]
        }
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        
        return str(path)
    
    def reset(self) -> None:
        """Reset all tracking data."""
        self._records.clear()
        self._total_cost = 0.0
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0


# Singleton instance
_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get the global cost tracker instance."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker
