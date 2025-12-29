"""
Memory module for the Agentic Analytics Platform.
Provides short-term conversation state and context management.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from collections import deque

from src.utils.helpers import timestamp_now, generate_trace_id


@dataclass
class Message:
    """A single message in the conversation."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: str = field(default_factory=timestamp_now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }


@dataclass
class ConversationContext:
    """Context for a single conversation/session."""
    session_id: str
    messages: List[Message] = field(default_factory=list)
    created_at: str = field(default_factory=timestamp_now)
    last_activity: str = field(default_factory=timestamp_now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str, metadata: Dict = None) -> Message:
        """Add a message to the conversation."""
        msg = Message(role=role, content=content, metadata=metadata or {})
        self.messages.append(msg)
        self.last_activity = timestamp_now()
        return msg
    
    def get_history(self, max_messages: int = 10) -> List[Dict[str, str]]:
        """Get recent message history in LLM format."""
        recent = self.messages[-max_messages:] if max_messages else self.messages
        return [{"role": m.role, "content": m.content} for m in recent]
    
    def clear(self):
        """Clear conversation history."""
        self.messages.clear()
        self.last_activity = timestamp_now()


class ConversationMemory:
    """
    Manages conversation memory for the agent.
    Supports multiple sessions with history limits.
    """
    
    def __init__(self, max_history_per_session: int = 20, max_sessions: int = 100):
        self._sessions: Dict[str, ConversationContext] = {}
        self._max_history = max_history_per_session
        self._max_sessions = max_sessions
        self._session_order: deque = deque()  # LRU tracking
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> ConversationContext:
        """Get existing session or create new one."""
        if session_id is None:
            session_id = generate_trace_id()[:16]
        
        if session_id in self._sessions:
            # Move to end of LRU
            if session_id in self._session_order:
                self._session_order.remove(session_id)
            self._session_order.append(session_id)
            return self._sessions[session_id]
        
        # Create new session
        context = ConversationContext(session_id=session_id)
        self._sessions[session_id] = context
        self._session_order.append(session_id)
        
        # Enforce max sessions
        while len(self._sessions) > self._max_sessions:
            oldest_id = self._session_order.popleft()
            if oldest_id in self._sessions:
                del self._sessions[oldest_id]
        
        return context
    
    def add_message(self, session_id: str, role: str, content: str,
                    metadata: Dict = None) -> Message:
        """Add a message to a session."""
        context = self.get_or_create_session(session_id)
        msg = context.add_message(role, content, metadata)
        
        # Enforce max history
        if len(context.messages) > self._max_history:
            context.messages = context.messages[-self._max_history:]
        
        return msg
    
    def get_history(self, session_id: str, max_messages: int = 10) -> List[Dict[str, str]]:
        """Get message history for a session."""
        if session_id not in self._sessions:
            return []
        return self._sessions[session_id].get_history(max_messages)
    
    def get_session(self, session_id: str) -> Optional[ConversationContext]:
        """Get a session by ID."""
        return self._sessions.get(session_id)
    
    def clear_session(self, session_id: str) -> bool:
        """Clear a session's history."""
        if session_id in self._sessions:
            self._sessions[session_id].clear()
            return True
        return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session entirely."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            if session_id in self._session_order:
                self._session_order.remove(session_id)
            return True
        return False
    
    def list_sessions(self) -> List[Dict]:
        """List all active sessions."""
        return [
            {
                "session_id": ctx.session_id,
                "message_count": len(ctx.messages),
                "created_at": ctx.created_at,
                "last_activity": ctx.last_activity,
            }
            for ctx in self._sessions.values()
        ]
    
    def get_stats(self) -> Dict:
        """Get memory statistics."""
        total_messages = sum(len(ctx.messages) for ctx in self._sessions.values())
        return {
            "active_sessions": len(self._sessions),
            "total_messages": total_messages,
            "max_sessions": self._max_sessions,
            "max_history_per_session": self._max_history,
        }


@dataclass
class AgentState:
    """State for a single agent execution."""
    trace_id: str
    query: str
    session_id: Optional[str] = None
    current_step: int = 0
    max_steps: int = 10
    retrieved_context: List[Any] = field(default_factory=list)
    tool_results: List[Any] = field(default_factory=list)
    intermediate_thoughts: List[str] = field(default_factory=list)
    final_response: Optional[str] = None
    is_complete: bool = False
    error: Optional[str] = None
    
    def add_thought(self, thought: str):
        """Add an intermediate thought."""
        self.intermediate_thoughts.append(thought)
        self.current_step += 1
    
    def add_tool_result(self, result: Any):
        """Add a tool execution result."""
        self.tool_results.append(result)
    
    def complete(self, response: str):
        """Mark execution as complete."""
        self.final_response = response
        self.is_complete = True
    
    def fail(self, error: str):
        """Mark execution as failed."""
        self.error = error
        self.is_complete = True
    
    def can_continue(self) -> bool:
        """Check if execution can continue."""
        return not self.is_complete and self.current_step < self.max_steps


# Singleton memory instance
_conversation_memory: Optional[ConversationMemory] = None


def get_conversation_memory() -> ConversationMemory:
    """Get the global conversation memory instance."""
    global _conversation_memory
    if _conversation_memory is None:
        _conversation_memory = ConversationMemory()
    return _conversation_memory
