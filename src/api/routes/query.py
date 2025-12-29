"""
Query route for the Agentic Analytics Platform.
Handles /query endpoint for agent interactions.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from src.agent.runtime import get_agent_runtime, run_query
from src.agent.control_plane import get_control_plane
from src.utils.helpers import generate_trace_id


router = APIRouter()


class QueryRequest(BaseModel):
    """Request body for query endpoint."""
    query: str = Field(..., description="Analytics question to answer", min_length=1)
    session_id: Optional[str] = Field(None, description="Session ID for conversation context")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is the total revenue by region?",
                "session_id": "session_abc123"
            }
        }


class QueryResponse(BaseModel):
    """Response from query endpoint."""
    trace_id: str
    query: str
    answer: str
    reasoning: Optional[str] = None
    data_sources: List[str] = []
    duration_ms: float
    success: bool
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "trace_id": "abc123def456",
                "query": "What is the total revenue by region?",
                "answer": "Revenue by region can be calculated...",
                "reasoning": "Retrieved 5 context chunks; Generated response",
                "data_sources": ["metric", "table", "column"],
                "duration_ms": 150.5,
                "success": True
            }
        }


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Submit an analytics query to the agent.
    
    The agent will:
    1. Validate the request against policies
    2. Retrieve relevant context from the semantic layer
    3. Generate an answer using retrieved context
    4. Return structured response with trace information
    """
    # Check control plane
    control_plane = get_control_plane()
    trace_id = generate_trace_id()
    
    can_proceed, reason = control_plane.check_can_proceed(trace_id)
    if not can_proceed:
        raise HTTPException(status_code=429, detail=reason)
    
    # Run query
    result = run_query(request.query, request.session_id)
    
    return QueryResponse(
        trace_id=result.trace_id,
        query=result.query,
        answer=result.answer,
        reasoning=result.reasoning,
        data_sources=result.data_sources,
        duration_ms=result.duration_ms,
        success=result.success,
        error=result.error
    )


@router.get("/query/simple")
async def simple_query(
    q: str = Query(..., description="Analytics question"),
    session_id: Optional[str] = Query(None, description="Session ID")
):
    """
    Simple GET endpoint for quick queries.
    Useful for testing and simple integrations.
    """
    result = run_query(q, session_id)
    
    return {
        "answer": result.answer,
        "trace_id": result.trace_id,
        "success": result.success
    }


@router.get("/query/history/{session_id}")
async def get_session_history(session_id: str, max_messages: int = 10):
    """
    Get conversation history for a session.
    """
    from src.agent.memory import get_conversation_memory
    
    memory = get_conversation_memory()
    history = memory.get_history(session_id, max_messages)
    
    return {
        "session_id": session_id,
        "messages": history,
        "count": len(history)
    }


@router.delete("/query/session/{session_id}")
async def clear_session(session_id: str):
    """
    Clear conversation history for a session.
    """
    from src.agent.memory import get_conversation_memory
    
    memory = get_conversation_memory()
    cleared = memory.clear_session(session_id)
    
    return {
        "session_id": session_id,
        "cleared": cleared
    }
