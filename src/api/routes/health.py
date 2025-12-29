"""
Health check route for the Agentic Analytics Platform.
"""

from fastapi import APIRouter
from typing import Dict, Any

from src.utils.config import get_settings
from src.utils.helpers import timestamp_now
from src.agent.control_plane import get_control_plane
from src.retrieval.vector_store import get_vector_store


router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    Returns 200 if service is running.
    """
    settings = get_settings()
    control_plane = get_control_plane()
    vector_store = get_vector_store()
    
    return {
        "status": "healthy",
        "timestamp": timestamp_now(),
        "app": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "kill_switch_active": control_plane.kill_switch.is_active(),
        "vector_store_documents": vector_store.count(),
    }


@router.get("/health/detailed")
async def detailed_health() -> Dict[str, Any]:
    """
    Detailed health check with component status.
    """
    settings = get_settings()
    control_plane = get_control_plane()
    vector_store = get_vector_store()
    
    # Check components
    components = {
        "control_plane": {
            "status": "healthy",
            "kill_switch": control_plane.kill_switch.get_state(),
            "active_model": control_plane.model_registry.get_active_model_name(),
        },
        "vector_store": {
            "status": "healthy" if vector_store.count() > 0 else "empty",
            "document_count": vector_store.count(),
        },
        "config": {
            "status": "healthy",
            "llm_model": settings.llm.model_name,
            "log_level": settings.observability.log_level,
        }
    }
    
    # Overall status
    all_healthy = all(
        c.get("status") in ["healthy", "empty"] 
        for c in components.values()
    )
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": timestamp_now(),
        "app": settings.app_name,
        "version": settings.version,
        "components": components
    }


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check - verifies service can handle requests.
    """
    vector_store = get_vector_store()
    control_plane = get_control_plane()
    
    # Check if kill switch is active
    if control_plane.kill_switch.is_active():
        return {
            "ready": False,
            "reason": "Kill switch active",
            "timestamp": timestamp_now()
        }
    
    # Check if vector store has data
    if vector_store.count() == 0:
        return {
            "ready": False,
            "reason": "Vector store empty - data not ingested",
            "timestamp": timestamp_now()
        }
    
    return {
        "ready": True,
        "timestamp": timestamp_now()
    }
