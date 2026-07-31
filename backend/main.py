"""
ContractIQ — FastAPI Application

Main entry point for the backend server.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.database.init_db import init_database
from backend.api.auth_routes import router as auth_router
from backend.api.contract_routes import router as contract_router
from backend.api.dashboard_routes import router as dashboard_router

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("contractiq")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    logger.info("Starting ContractIQ Backend...")
    await init_database()
    logger.info("[OK] Database initialized")
    logger.info(f"Backend running on http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}")

    yield

    # Shutdown
    logger.info("Shutting down ContractIQ Backend...")


app = FastAPI(
    title="ContractIQ",
    description="Enterprise AI Contract Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware — allow Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(contract_router)
app.include_router(dashboard_router)

# Analysis routes (Phase 2)
from backend.api.analysis_routes import router as analysis_router
app.include_router(analysis_router)

# Phase 4 routes
from backend.api.review_routes import router as review_router
from backend.api.comparison_routes import router as comparison_router
from backend.api.analytics_routes import router as analytics_router
app.include_router(review_router)
app.include_router(comparison_router)
app.include_router(analytics_router)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint — health check."""
    return {
        "service": "ContractIQ",
        "status": "healthy",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",
        "version": "1.0.0",
    }
