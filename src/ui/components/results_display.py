"""
Results display component for the Streamlit UI.
"""

import streamlit as st
from typing import Dict, Any, List, Optional


def render_answer_card(
    answer: str,
    success: bool = True,
    trace_id: Optional[str] = None
):
    """
    Render an answer card.
    
    Args:
        answer: The answer text
        success: Whether the query was successful
        trace_id: Optional trace ID
    """
    if success:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
            border-left: 4px solid #10b981;
            padding: 1.5rem;
            border-radius: 0.75rem;
            margin: 1rem 0;
        ">
            {answer}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
            border-left: 4px solid #ef4444;
            padding: 1.5rem;
            border-radius: 0.75rem;
            margin: 1rem 0;
        ">
            {answer}
        </div>
        """, unsafe_allow_html=True)
    
    if trace_id:
        st.caption(f"Trace ID: `{trace_id}`")


def render_metrics_row(
    duration_ms: float,
    sources_count: int,
    token_usage: Optional[Dict[str, int]] = None
):
    """
    Render a row of metrics.
    
    Args:
        duration_ms: Response time in milliseconds
        sources_count: Number of data sources used
        token_usage: Optional token usage dict
    """
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("⏱️ Duration", f"{duration_ms:.1f}ms")
    
    with col2:
        st.metric("📚 Sources", sources_count)
    
    if token_usage:
        with col3:
            prompt_tokens = token_usage.get("prompt_tokens", 0)
            st.metric("📥 Prompt", f"{prompt_tokens}")
        
        with col4:
            completion_tokens = token_usage.get("completion_tokens", 0)
            st.metric("📤 Completion", f"{completion_tokens}")


def render_reasoning_steps(reasoning: str):
    """
    Render reasoning steps in an expandable section.
    
    Args:
        reasoning: Reasoning string (semicolon-separated steps)
    """
    with st.expander("🧠 Reasoning Steps", expanded=False):
        steps = reasoning.split(";") if reasoning else []
        
        for i, step in enumerate(steps, 1):
            step = step.strip()
            if step:
                st.markdown(f"**Step {i}:** {step}")


def render_data_sources(sources: List[str]):
    """
    Render data source badges.
    
    Args:
        sources: List of data source names
    """
    if not sources:
        return
    
    st.markdown("**Data Sources:**")
    
    # Create badges for each source
    unique_sources = list(set(sources))
    
    badges_html = " ".join([
        f"""<span style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 1rem;
            font-size: 0.8rem;
            margin-right: 0.5rem;
        ">{source}</span>"""
        for source in unique_sources
    ])
    
    st.markdown(badges_html, unsafe_allow_html=True)


def render_full_result(result: Dict[str, Any]):
    """
    Render a complete result display.
    
    Args:
        result: Result dict with answer, success, trace_id, etc.
    """
    # Main answer
    render_answer_card(
        answer=result.get("answer", "No answer"),
        success=result.get("success", True),
        trace_id=result.get("trace_id")
    )
    
    # Metrics
    render_metrics_row(
        duration_ms=result.get("duration_ms", 0),
        sources_count=len(result.get("data_sources", [])),
        token_usage=result.get("token_usage")
    )
    
    # Data sources
    render_data_sources(result.get("data_sources", []))
    
    # Reasoning
    if result.get("reasoning"):
        render_reasoning_steps(result["reasoning"])
