"""
Control Plane for Agentic Analytics Platform.
Provides tight governance: policy config, kill switch, model versioning,
agent registry, and permissions with full observability integration.

"AI that cannot be governed or explained cannot be operated."
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any, Callable
from pathlib import Path
from enum import Enum
from threading import Lock

from src.utils.helpers import timestamp_now, generate_trace_id, ErrorCategory, PlatformError
from src.utils.config import get_settings
from src.observability.tracing import get_tracer, TraceEventType


class AgentStatus(Enum):
    """Status of an agent in the registry."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    TERMINATED = "terminated"
    ERROR = "error"


class PermissionLevel(Enum):
    """Permission levels for access control."""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


@dataclass
class PolicyConfig:
    """
    Policy configuration for agent governance.
    Defines limits, allowed operations, and blocked patterns.
    """
    max_tokens_per_request: int = 8000
    max_loops_per_request: int = 10
    max_retries: int = 3
    timeout_seconds: int = 60
    allowed_tools: List[str] = field(default_factory=lambda: [
        "sql_query", "metadata_lookup", "semantic_search", "calculate"
    ])
    blocked_tools: List[str] = field(default_factory=list)
    blocked_query_patterns: List[str] = field(default_factory=lambda: [
        "DROP", "DELETE", "TRUNCATE", "ALTER", "INSERT", "UPDATE"
    ])
    require_approval_for: List[str] = field(default_factory=list)
    rate_limit_requests_per_minute: int = 60
    enable_cost_limits: bool = True
    max_cost_per_request_usd: float = 0.10
    max_cost_per_day_usd: float = 10.00
    blocked_topics: List[str] = field(default_factory=lambda: [
        "politics", "religion", "hate speech", "medical advice", "legal advice"
    ])
    enable_content_guardrails: bool = True
    
    @classmethod
    def from_file(cls, path: str) -> "PolicyConfig":
        """Load policy from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)
    
    def to_dict(self) -> dict:
        return {
            "max_tokens_per_request": self.max_tokens_per_request,
            "max_loops_per_request": self.max_loops_per_request,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "allowed_tools": self.allowed_tools,
            "blocked_tools": self.blocked_tools,
            "blocked_query_patterns": self.blocked_query_patterns,
            "rate_limit_requests_per_minute": self.rate_limit_requests_per_minute,
            "enable_cost_limits": self.enable_cost_limits,
            "max_cost_per_request_usd": self.max_cost_per_request_usd,
            "max_cost_per_day_usd": self.max_cost_per_day_usd,
            "blocked_topics": self.blocked_topics,
            "enable_content_guardrails": self.enable_content_guardrails,
        }


@dataclass
class KillSwitchState:
    """State of the kill switch."""
    enabled: bool = False
    reason: Optional[str] = None
    triggered_at: Optional[str] = None
    triggered_by: Optional[str] = None
    auto_disable_at: Optional[str] = None


class KillSwitch:
    """
    Kill switch for immediate agent termination.
    All state changes are logged for audit.
    """
    
    def __init__(self):
        self._state = KillSwitchState()
        self._lock = Lock()
        self._callbacks: List[Callable[[KillSwitchState], None]] = []
        self._history: List[Dict] = []
    
    def enable(self, reason: str, triggered_by: str = "system",
               auto_disable_after_seconds: Optional[int] = None) -> None:
        """
        Enable the kill switch, stopping all agent operations.
        
        Args:
            reason: Why the kill switch was triggered
            triggered_by: Who/what triggered it (user, system, cost_alert, etc.)
            auto_disable_after_seconds: Optional auto-disable timeout
        """
        with self._lock:
            self._state.enabled = True
            self._state.reason = reason
            self._state.triggered_at = timestamp_now()
            self._state.triggered_by = triggered_by
            
            if auto_disable_after_seconds:
                # Calculate auto-disable time
                from datetime import timedelta
                disable_time = datetime.now(timezone.utc) + timedelta(seconds=auto_disable_after_seconds)
                self._state.auto_disable_at = disable_time.isoformat().replace("+00:00", "Z")
            
            # Log to history
            self._history.append({
                "action": "enable",
                "timestamp": self._state.triggered_at,
                "reason": reason,
                "triggered_by": triggered_by,
            })
            
            # Notify callbacks
            for callback in self._callbacks:
                callback(self._state)
            
            # Log to tracer if available
            try:
                tracer = get_tracer()
                for trace_id in tracer.list_active_traces():
                    tracer.add_event(
                        trace_id=trace_id,
                        event_type=TraceEventType.KILL_SWITCH_TRIGGERED,
                        action=f"Kill switch enabled: {reason}",
                        metadata={"triggered_by": triggered_by}
                    )
            except Exception:
                pass  # Don't fail if tracer unavailable
    
    def disable(self, disabled_by: str = "system") -> None:
        """Disable the kill switch, allowing operations to resume."""
        with self._lock:
            if not self._state.enabled:
                return
            
            self._history.append({
                "action": "disable",
                "timestamp": timestamp_now(),
                "disabled_by": disabled_by,
                "was_enabled_for": self._state.reason,
            })
            
            self._state = KillSwitchState()
            
            for callback in self._callbacks:
                callback(self._state)
    
    def is_active(self) -> bool:
        """Check if kill switch is currently active."""
        with self._lock:
            if not self._state.enabled:
                return False
            
            # Check auto-disable
            if self._state.auto_disable_at:
                now = datetime.now(timezone.utc)
                disable_at = datetime.fromisoformat(
                    self._state.auto_disable_at.replace("Z", "+00:00")
                )
                if now >= disable_at:
                    self.disable("auto_timeout")
                    return False
            
            return True
    
    def get_reason(self) -> Optional[str]:
        """Get the reason for kill switch activation."""
        with self._lock:
            return self._state.reason if self._state.enabled else None
    
    def get_state(self) -> Dict:
        """Get full kill switch state."""
        with self._lock:
            return {
                "enabled": self._state.enabled,
                "reason": self._state.reason,
                "triggered_at": self._state.triggered_at,
                "triggered_by": self._state.triggered_by,
                "auto_disable_at": self._state.auto_disable_at,
            }
    
    def get_history(self) -> List[Dict]:
        """Get kill switch history."""
        with self._lock:
            return list(self._history)
    
    def add_callback(self, callback: Callable[[KillSwitchState], None]) -> None:
        """Add callback for kill switch state changes."""
        self._callbacks.append(callback)


@dataclass
class ModelVersion:
    """Model version metadata."""
    model_id: str
    model_name: str
    version: str
    registered_at: str
    is_active: bool = False
    metadata: Dict = field(default_factory=dict)


class ModelRegistry:
    """
    Registry for model versions with switching and rollback.
    """
    
    def __init__(self):
        self._models: Dict[str, ModelVersion] = {}
        self._active_model_id: Optional[str] = None
        self._history: List[Dict] = []
        self._lock = Lock()
    
    def register_model(
        self,
        model_name: str,
        version: str,
        metadata: Optional[Dict] = None,
        set_active: bool = False
    ) -> str:
        """
        Register a new model version.
        
        Returns:
            Model ID
        """
        with self._lock:
            model_id = f"{model_name}:{version}"
            
            model = ModelVersion(
                model_id=model_id,
                model_name=model_name,
                version=version,
                registered_at=timestamp_now(),
                metadata=metadata or {}
            )
            
            self._models[model_id] = model
            
            self._history.append({
                "action": "register",
                "timestamp": model.registered_at,
                "model_id": model_id,
            })
            
            if set_active or self._active_model_id is None:
                self._set_active(model_id)
            
            return model_id
    
    def _set_active(self, model_id: str) -> None:
        """Internal method to set active model."""
        if self._active_model_id and self._active_model_id in self._models:
            self._models[self._active_model_id].is_active = False
        
        self._active_model_id = model_id
        if model_id in self._models:
            self._models[model_id].is_active = True
    
    def switch_model(self, model_id: str, reason: str = "manual") -> bool:
        """
        Switch to a different model version.
        
        Returns:
            True if switch successful
        """
        with self._lock:
            if model_id not in self._models:
                return False
            
            previous_model = self._active_model_id
            self._set_active(model_id)
            
            self._history.append({
                "action": "switch",
                "timestamp": timestamp_now(),
                "from_model": previous_model,
                "to_model": model_id,
                "reason": reason,
            })
            
            return True
    
    def rollback(self) -> bool:
        """
        Rollback to the previous model version.
        
        Returns:
            True if rollback successful
        """
        with self._lock:
            # Find the last switch in history
            for entry in reversed(self._history):
                if entry["action"] == "switch" and entry["from_model"]:
                    return self.switch_model(entry["from_model"], "rollback")
            return False
    
    def get_active_model(self) -> Optional[ModelVersion]:
        """Get the currently active model."""
        with self._lock:
            if self._active_model_id:
                return self._models.get(self._active_model_id)
            return None
    
    def get_active_model_name(self) -> Optional[str]:
        """Get the name of the currently active model."""
        model = self.get_active_model()
        return model.model_name if model else None
    
    def list_models(self) -> List[Dict]:
        """List all registered models."""
        with self._lock:
            return [
                {
                    "model_id": m.model_id,
                    "model_name": m.model_name,
                    "version": m.version,
                    "is_active": m.is_active,
                    "registered_at": m.registered_at,
                }
                for m in self._models.values()
            ]
    
    def get_history(self) -> List[Dict]:
        """Get model registry history."""
        with self._lock:
            return list(self._history)


@dataclass  
class AgentInfo:
    """Information about a registered agent."""
    agent_id: str
    name: str
    status: AgentStatus
    registered_at: str
    last_activity: Optional[str] = None
    current_trace_id: Optional[str] = None
    request_count: int = 0
    error_count: int = 0
    metadata: Dict = field(default_factory=dict)


class AgentRegistry:
    """
    Registry for tracking agent instances and their states.
    """
    
    def __init__(self):
        self._agents: Dict[str, AgentInfo] = {}
        self._lock = Lock()
    
    def register_agent(self, name: str, metadata: Optional[Dict] = None) -> str:
        """
        Register a new agent.
        
        Returns:
            Agent ID
        """
        with self._lock:
            agent_id = f"agent_{generate_trace_id()[:8]}"
            
            agent = AgentInfo(
                agent_id=agent_id,
                name=name,
                status=AgentStatus.IDLE,
                registered_at=timestamp_now(),
                metadata=metadata or {}
            )
            
            self._agents[agent_id] = agent
            return agent_id
    
    def update_status(self, agent_id: str, status: AgentStatus,
                      trace_id: Optional[str] = None) -> bool:
        """Update agent status."""
        with self._lock:
            if agent_id not in self._agents:
                return False
            
            agent = self._agents[agent_id]
            agent.status = status
            agent.last_activity = timestamp_now()
            
            if trace_id:
                agent.current_trace_id = trace_id
            
            if status == AgentStatus.RUNNING:
                agent.request_count += 1
            elif status == AgentStatus.ERROR:
                agent.error_count += 1
            
            return True
    
    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent info by ID."""
        with self._lock:
            return self._agents.get(agent_id)
    
    def list_agents(self, status: Optional[AgentStatus] = None) -> List[Dict]:
        """List all agents, optionally filtered by status."""
        with self._lock:
            agents = self._agents.values()
            if status:
                agents = [a for a in agents if a.status == status]
            
            return [
                {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "status": a.status.value,
                    "last_activity": a.last_activity,
                    "request_count": a.request_count,
                    "error_count": a.error_count,
                }
                for a in agents
            ]
    
    def terminate_all(self, reason: str = "kill_switch") -> int:
        """Terminate all running agents. Returns count terminated."""
        with self._lock:
            count = 0
            for agent in self._agents.values():
                if agent.status == AgentStatus.RUNNING:
                    agent.status = AgentStatus.TERMINATED
                    agent.last_activity = timestamp_now()
                    count += 1
            return count


class PermissionChecker:
    """
    Permission checking for tool and data access control.
    """
    
    def __init__(self, policy: PolicyConfig):
        self._policy = policy
        self._user_permissions: Dict[str, PermissionLevel] = {}
        self._tool_permissions: Dict[str, PermissionLevel] = {
            tool: PermissionLevel.READ for tool in policy.allowed_tools
        }
    
    def set_user_permission(self, user_id: str, level: PermissionLevel) -> None:
        """Set permission level for a user."""
        self._user_permissions[user_id] = level
    
    def can_execute_tool(self, tool_name: str, user_id: Optional[str] = None) -> bool:
        """Check if a tool can be executed."""
        # Check if tool is blocked
        if tool_name in self._policy.blocked_tools:
            return False
        
        # Check if tool is allowed
        if tool_name not in self._policy.allowed_tools:
            return False
        
        # Check user permission if specified
        if user_id and user_id in self._user_permissions:
            user_level = self._user_permissions[user_id]
            if user_level == PermissionLevel.NONE:
                return False
        
        return True
    
    def can_access_data(self, data_type: str, user_id: Optional[str] = None) -> bool:
        """Check if data can be accessed."""
        if user_id and user_id in self._user_permissions:
            user_level = self._user_permissions[user_id]
            return user_level in [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.ADMIN]
        return True  # Default allow if no restrictions
    
    def validate_query(self, query: str) -> tuple[bool, Optional[str]]:
        """
        Validate a query against blocked patterns.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        query_upper = query.upper()
        
        for pattern in self._policy.blocked_query_patterns:
            if pattern.upper() in query_upper:
                return False, f"Query contains blocked pattern: {pattern}"
        
        return True, None


class ControlPlane:
    """
    Master control plane orchestrating all governance components.
    Every operation is logged. This is the "air traffic control" for the agent.
    """
    
    def __init__(self, policy: Optional[PolicyConfig] = None):
        self._policy = policy or PolicyConfig()
        self._kill_switch = KillSwitch()
        self._model_registry = ModelRegistry()
        self._agent_registry = AgentRegistry()
        self._permission_checker = PermissionChecker(self._policy)
        self._request_timestamps: List[float] = []
        self._daily_cost: float = 0.0
        self._lock = Lock()
        
        # Register default model
        settings = get_settings()
        self._model_registry.register_model(
            model_name=settings.llm.model_name,
            version="default",
            set_active=True
        )
        
        # Link kill switch to agent registry
        self._kill_switch.add_callback(self._on_kill_switch_change)
    
    def _on_kill_switch_change(self, state: KillSwitchState) -> None:
        """Handle kill switch state changes."""
        if state.enabled:
            terminated = self._agent_registry.terminate_all("kill_switch")
            # Log would go here
    
    @property
    def policy(self) -> PolicyConfig:
        return self._policy
    
    @property
    def kill_switch(self) -> KillSwitch:
        return self._kill_switch
    
    @property
    def model_registry(self) -> ModelRegistry:
        return self._model_registry
    
    @property
    def agent_registry(self) -> AgentRegistry:
        return self._agent_registry
    
    @property
    def permission_checker(self) -> PermissionChecker:
        return self._permission_checker
    
    def check_can_proceed(self, trace_id: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """
        Check if an operation can proceed.
        Validates kill switch, rate limits, and other policies.
        
        Returns:
            Tuple of (can_proceed, reason_if_blocked)
        """
        # Check kill switch
        if self._kill_switch.is_active():
            reason = self._kill_switch.get_reason()
            self._log_policy_check(trace_id, "kill_switch", False, reason)
            return False, f"Kill switch active: {reason}"
        
        # Check rate limit
        if not self._check_rate_limit():
            self._log_policy_check(trace_id, "rate_limit", False, "Rate limit exceeded")
            return False, "Rate limit exceeded"
        
        # Check daily cost limit
        if self._policy.enable_cost_limits:
            if self._daily_cost >= self._policy.max_cost_per_day_usd:
                self._log_policy_check(trace_id, "cost_limit", False, "Daily cost limit exceeded")
                return False, "Daily cost limit exceeded"
        
        self._log_policy_check(trace_id, "all_checks", True, None)
        return True, None
    
    def _check_rate_limit(self) -> bool:
        """Check if within rate limit."""
        with self._lock:
            now = time.time()
            minute_ago = now - 60
            
            # Remove old timestamps
            self._request_timestamps = [
                ts for ts in self._request_timestamps if ts > minute_ago
            ]
            
            # Check limit
            if len(self._request_timestamps) >= self._policy.rate_limit_requests_per_minute:
                return False
            
            # Record this request
            self._request_timestamps.append(now)
            return True
    
    def _log_policy_check(self, trace_id: Optional[str], check_type: str,
                          passed: bool, reason: Optional[str]) -> None:
        """Log a policy check to the tracer."""
        if not trace_id:
            return
        
        try:
            tracer = get_tracer()
            tracer.add_event(
                trace_id=trace_id,
                event_type=TraceEventType.POLICY_CHECK,
                action=f"Policy check: {check_type}",
                success=passed,
                error_message=reason,
                metadata={"check_type": check_type}
            )
        except Exception:
            pass
    
    def validate_content(self, text: str) -> tuple[bool, Optional[str]]:
        """
        Validate text content against policy guardrails.
        Currently implements keyword matching. Future: Integrate NeMo Guardrails.
        """
        if not self._policy.enable_content_guardrails:
            return True, None
            
        # Basic keyword check (The "Level 1" Content Guardrail)
        text_lower = text.lower()
        for topic in self._policy.blocked_topics:
            if topic in text_lower:
                return False, f"Content blocked: violates '{topic}' policy."
                
        return True, None

    def validate_request(self, query: str, trace_id: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """
        Full validation of an incoming request.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if we can proceed at all
        can_proceed, reason = self.check_can_proceed(trace_id)
        if not can_proceed:
            return False, reason
        
        # Validate query permission (SQL injection patterns)
        valid_perm, perm_error = self._permission_checker.validate_query(query)
        if not valid_perm:
            self._log_policy_check(trace_id, "query_permission", False, perm_error)
            return False, perm_error
            
        # Validate query content (Topic/Guardrails)
        valid_content, content_error = self.validate_content(query)
        if not valid_content:
            self._log_policy_check(trace_id, "content_guardrail", False, content_error)
            return False, content_error
        
        return True, None
    
    def validate_tool_call(self, tool_name: str, trace_id: Optional[str] = None,
                           user_id: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """
        Validate if a tool can be called.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self._permission_checker.can_execute_tool(tool_name, user_id):
            reason = f"Tool not allowed: {tool_name}"
            self._log_policy_check(trace_id, "tool_permission", False, reason)
            return False, reason
        
        self._log_policy_check(trace_id, "tool_permission", True, None)
        return True, None
    
    def record_cost(self, cost_usd: float) -> None:
        """Record cost for daily tracking."""
        with self._lock:
            self._daily_cost += cost_usd
        
        # Check if we should trigger kill switch
        if self._policy.enable_cost_limits:
            if self._daily_cost >= self._policy.max_cost_per_day_usd:
                self._kill_switch.enable(
                    reason=f"Daily cost limit exceeded: ${self._daily_cost:.4f}",
                    triggered_by="cost_monitor"
                )
    
    def get_status(self) -> Dict:
        """Get comprehensive control plane status."""
        return {
            "timestamp": timestamp_now(),
            "kill_switch": self._kill_switch.get_state(),
            "active_model": self._model_registry.get_active_model_name(),
            "agents": self._agent_registry.list_agents(),
            "policy": self._policy.to_dict(),
            "rate_limit": {
                "requests_last_minute": len(self._request_timestamps),
                "limit": self._policy.rate_limit_requests_per_minute,
            },
            "daily_cost": {
                "current_usd": round(self._daily_cost, 6),
                "limit_usd": self._policy.max_cost_per_day_usd,
            }
        }
    
    def reset_daily_cost(self) -> None:
        """Reset daily cost counter (call at midnight)."""
        with self._lock:
            self._daily_cost = 0.0


# Singleton instance
_control_plane: Optional[ControlPlane] = None


def get_control_plane() -> ControlPlane:
    """Get the global control plane instance."""
    global _control_plane
    if _control_plane is None:
        _control_plane = ControlPlane()
    return _control_plane
