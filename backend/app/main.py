"""FastAPI application for Pixel Perfect UI - Figma to Website Comparison."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging

from .config import get_settings
from .api import endpoints, websocket, auth_endpoints

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Compare Figma designs with live websites to detect UI inconsistencies",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create necessary directories
Path(settings.UPLOAD_DIR).mkdir(exist_ok=True)
Path(settings.OUTPUT_DIR).mkdir(exist_ok=True)
Path(settings.STATIC_DIR).mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=settings.OUTPUT_DIR), name="static")

# Include routers
app.include_router(endpoints.router, prefix=settings.API_V1_PREFIX, tags=["comparison"])
app.include_router(websocket.router, prefix=settings.API_V1_PREFIX, tags=["websocket"])
app.include_router(auth_endpoints.router, prefix=settings.API_V1_PREFIX, tags=["authentication"])


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Install Playwright browsers if not already installed
    try:
        import subprocess
        logger.info("Checking Playwright browsers...")
        subprocess.run(["playwright", "install", "chromium"], check=False)
    except Exception as e:
        logger.warning(f"Could not auto-install Playwright browsers: {e}")
        logger.warning("Please run: playwright install chromium")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Shutting down application...")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Figma-Website UI Comparison Tool API",
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
        "health": "/api/v1/health"
    }


@app.get("/api")
async def api_root():
    """API root endpoint."""
    return {
        "message": "API v1",
        "endpoints": {
            "compare": f"{settings.API_V1_PREFIX}/compare",
            "report": f"{settings.API_V1_PREFIX}/report/{{job_id}}",
            "progress": f"{settings.API_V1_PREFIX}/progress/{{job_id}}",
            "jobs": f"{settings.API_V1_PREFIX}/jobs",
            "health": f"{settings.API_V1_PREFIX}/health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
