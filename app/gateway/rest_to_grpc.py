#!/usr/bin/env python3
"""
REST to gRPC Gateway
Provides REST API interface for frontend, backend calls gRPC services
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import grpc
import os
import sys

# Add project path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "app", "grpc_services", "generated"))

from app.core.config import settings
from app.core.logging import logger
from app.db.database import init_db, close_db
from app.api.v1.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Saving Advisor System - REST Gateway to gRPC",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes (these routes will call gRPC services)
app.include_router(api_router, prefix=settings.API_V1_STR)

# Frontend static files
FRONTEND_DIR = "frontend"
INDEX_PATH = os.path.join(FRONTEND_DIR, "index.html")

if os.path.exists(INDEX_PATH):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    @app.get("/", response_class=HTMLResponse)
    async def read_root():
        return HTMLResponse(content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>💰 Saving Advisor System</title>
            </head>
            <body>
                <h1>💰 Saving Advisor System</h1>
                <p>REST Gateway to gRPC Services</p>
                <p><b>Frontend not found.</b> The API is running correctly.</p>
                <h2>Available APIs:</h2>
                <ul>
                    <li><a href="/docs">API Documentation (Swagger UI)</a></li>
                    <li><a href="/redoc">Alternative Documentation (ReDoc)</a></li>
                </ul>
            </body>
            </html>
        """)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "saving_advisor_gateway", "backend": "grpc"}

@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("🚀 Starting REST Gateway to gRPC...")
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"⚠️ Database initialization failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("🛑 Shutting down REST Gateway...")
    try:
        await close_db()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.gateway.rest_to_grpc:app",
        host="0.0.0.0",
        port=settings.GATEWAY_PORT,
        reload=settings.DEBUG
    )
