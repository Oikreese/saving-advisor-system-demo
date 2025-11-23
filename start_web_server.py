#!/usr/bin/env python3
"""
Start Web Server (REST Gateway + Frontend)
For testing web page access
"""
import sys
import os
from pathlib import Path
import uvicorn

def main():
    project_root = Path(__file__).parent
    
    print("=" * 60)
    print("  🌐 Saving Advisor System - Web Server")
    print("=" * 60)
    # Import configuration to get ports
    sys.path.insert(0, str(project_root))
    from app.core.config import settings
    
    gateway_port = settings.GATEWAY_PORT
    grpc_port = settings.SERVER_PORT
    
    print(f"  Starting REST Gateway (port {gateway_port})")
    print(f"  Frontend: http://localhost:{gateway_port}")
    print(f"  API Docs: http://localhost:{gateway_port}/docs")
    print("=" * 60)
    print("")
    print(f"⚠️  Note: This gateway forwards REST requests to gRPC services")
    print(f"   Ensure gRPC server is running (port {grpc_port})")
    print("")
    
    # Start REST gateway
    try:
        # Run Uvicorn directly (in the same process), Ctrl+C can reliably terminate
        uvicorn.run(
            "app.gateway.rest_to_grpc:app",
            host="0.0.0.0",
            port=gateway_port,
            reload=settings.DEBUG
        )
    except KeyboardInterrupt:
        print("\n👋 Web server stopped")

if __name__ == "__main__":
    main()
