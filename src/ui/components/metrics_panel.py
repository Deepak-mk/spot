"""
Metrics panel component for the Streamlit UI.
"""

import streamlit as st
from typing import Dict, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.observability.telemetry import get_telemetry
from src.observability.cost import get_cost_tracker
from src.observability.latency import get_latency_tracker
from src.agent.control_plane import get_control_plane


def render_system_status():
    """Render system status panel."""
    st.markdown("### 🔧 System Status")
    
    control_plane = get_control_plane()
    
    # Kill switch status
    if control_plane.kill_switch.is_active():
        st.error("🛑 Kill Switch ACTIVE")
        reason = control_plane.kill_switch.get_reason()
        st.caption(reason)
    else:
        st.success("✅ All Systems Operational")
    
    # Model info
    st.markdown("**Active Model:**")
    model_name = control_plane.model_registry.get_active_model_name()
    st.code(model_name)


def render_cost_metrics():
    """Render cost tracking metrics."""
    st.markdown("### 💰 Cost Tracking")
    
    cost_tracker = get_cost_tracker()
    stats = cost_tracker.get_stats()
    
    col1, col2 = st.columns(2)
    
    with col1:
        total_cost = stats.get("total_cost", 0)
        st.metric("Total Cost", f"${total_cost:.4f}")
    
    with col2:
        budget = stats.get("budget", 0)
        remaining = budget - total_cost
        st.metric("Remaining", f"${remaining:.4f}")
    
    # Budget progress
    if budget > 0:
        progress = min(total_cost / budget, 1.0)
        st.progress(progress)
        
        if progress > 0.9:
            st.warning("⚠️ Budget nearly exhausted")
        elif progress > 0.8:
            st.info("ℹ️ Over 80% of budget used")


def render_latency_metrics():
    """Render latency metrics."""
    st.markdown("### ⏱️ Latency")
    
    latency_tracker = get_latency_tracker()
    summary = latency_tracker.get_summary()
    
    stats_list = summary.get("operation_stats", [])
    
    if not stats_list:
        st.caption("No latency data yet")
        return
    
    for stat in stats_list[:5]:  # Top 5 operations
        op_type = stat.get("operation_type", "unknown")
        p50 = stat.get("p50_ms", 0)
        p99 = stat.get("p99_ms", 0)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption(op_type)
        with col2:
            st.caption(f"P50: {p50:.1f}ms")
        with col3:
            st.caption(f"P99: {p99:.1f}ms")


def render_telemetry_summary():
    """Render telemetry summary."""
    st.markdown("### 📊 Telemetry")
    
    telemetry = get_telemetry()
    summary = telemetry.get_summary()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Requests", summary.get("total_traces", 0))
    
    with col2:
        st.metric("Active Traces", summary.get("active_traces", 0))


def render_full_metrics_panel():
    """Render the complete metrics panel."""
    render_system_status()
    st.divider()
    render_cost_metrics()
    st.divider()
    render_latency_metrics()
    st.divider()
    render_telemetry_summary()
