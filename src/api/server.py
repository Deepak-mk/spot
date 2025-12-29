"""
FastAPI server for the Agentic Analytics Platform.
Main application entry point with middleware.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.config import get_settings
from src.utils.helpers import timestamp_now
from src.agent.control_plane import get_control_plane
from src.observability.telemetry import get_telemetry
from src.retrieval.ingest import ingest_semantic_data

# Import routes
from src.api.routes.query import router as query_router
from src.api.routes.health import router as health_router
from src.api.routes.metrics import router as metrics_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="Agentic Analytics Platform",
        description="GenAI-powered analytics with governance, retrieval, and observability",
        version=settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Request timing middleware
    @app.middleware("http")
    async def add_timing_header(request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = (time.perf_counter() - start_time) * 1000
        response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
        return response
    
    # Kill switch middleware
    @app.middleware("http")
    async def check_kill_switch(request: Request, call_next):
        # Allow health and metrics endpoints
        if request.url.path in ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        control_plane = get_control_plane()
        if control_plane.kill_switch.is_active():
            reason = control_plane.kill_switch.get_reason()
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Service temporarily unavailable",
                    "reason": f"Kill switch active: {reason}",
                    "timestamp": timestamp_now()
                }
            )
        return await call_next(request)
    
    # Include routers
    app.include_router(query_router, prefix="/api", tags=["Query"])
    app.include_router(health_router, tags=["Health"])
    app.include_router(metrics_router, tags=["Metrics"])
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        """Initialize platform on startup."""
        settings = get_settings()
        
        # Ingest semantic data
        try:
            result = ingest_semantic_data()
            print(f"✓ Ingested {result.documents_ingested} documents in {result.total_time_ms:.2f}ms")
        except Exception as e:
            print(f"⚠ Failed to ingest data: {e}")
        
        print(f"✓ Platform started: {settings.app_name} v{settings.version}")
    
    # Root endpoint
    @app.get("/")
    async def root():
        settings = get_settings()
        return {
            "name": settings.app_name,
            "version": settings.version,
            "docs": "/docs",
            "health": "/health",
        }
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
