"""
FastAPI main application
"""

import sys
import os
import logging
from contextlib import asynccontextmanager

# Add project root for src imports (backend/app/main.py -> netscout/)
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _project_root)

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.endpoints import scan, auth, investigations, notifications
from app.db.database import init_db, get_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
    except Exception as e:
        logger.error("Database init failed: %s. Is PostgreSQL running? (docker compose up -d)", e)
        raise
    try:
        from app.services.scheduler_service import start_scheduler
        start_scheduler()
    except Exception as e:
        logger.warning("Scheduler start skipped: %s", e)
    yield
    try:
        from app.services.scheduler_service import get_scheduler
        sched = get_scheduler()
        if sched.running:
            sched.shutdown(wait=False)
    except Exception:
        pass


app = FastAPI(
    title="NetScout API",
    description="OSINT System API for domain analysis",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(scan.router, prefix="/api", tags=["scan"])
app.include_router(investigations.router, prefix="/api")
app.include_router(notifications.router, prefix="/api", tags=["notifications"])


@app.get("/")
async def root():
    return {"message": "NetScout API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
