"""
Metrics route for the Agentic Analytics Platform.
Exposes observability data.
"""

from fastapi import APIRouter
from typing import Dict, Any

from src.utils.helpers import timestamp_now
from src.agent.control_plane import get_control_plane
from src.observability.telemetry import get_telemetry
from src.observability.cost import get_cost_tracker
from src.observability.latency import get_latency_tracker


router = APIRouter()


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """
    Get platform metrics.
    Returns cost, latency, and control plane status.
    """
    telemetry = get_telemetry()
    summary = telemetry.get_summary()
    
    return {
        "timestamp": timestamp_now(),
        **summary
    }


@router.get("/metrics/cost")
async def get_cost_metrics() -> Dict[str, Any]:
    """
    Get cost tracking metrics.
    """
    cost_tracker = get_cost_tracker()
    return {
        "timestamp": timestamp_now(),
        **cost_tracker.get_stats()
    }


@router.get("/metrics/latency")
async def get_latency_metrics() -> Dict[str, Any]:
    """
    Get latency metrics by operation.
    """
    latency_tracker = get_latency_tracker()
    return {
        "timestamp": timestamp_now(),
        **latency_tracker.get_summary()
    }


@router.get("/metrics/control-plane")
async def get_control_plane_status() -> Dict[str, Any]:
    """
    Get control plane status.
    """
    control_plane = get_control_plane()
    return control_plane.get_status()


@router.post("/metrics/kill-switch/enable")
async def enable_kill_switch(reason: str = "manual"):
    """
    Enable the kill switch.
    """
    control_plane = get_control_plane()
    control_plane.kill_switch.enable(reason, "api")
    
    return {
        "success": True,
        "kill_switch": control_plane.kill_switch.get_state()
    }


@router.post("/metrics/kill-switch/disable")
async def disable_kill_switch():
    """
    Disable the kill switch.
    """
    control_plane = get_control_plane()
    control_plane.kill_switch.disable("api")
    
    return {
        "success": True,
        "kill_switch": control_plane.kill_switch.get_state()
    }
