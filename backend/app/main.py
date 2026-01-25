"""
FastAPI main application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import scan

app = FastAPI(
    title="NetScout API",
    description="OSINT System API for domain analysis",
    version="0.1.0"
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
app.include_router(scan.router, prefix="/api", tags=["scan"])


@app.get("/")
async def root():
    return {"message": "NetScout API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
