#!/usr/bin/env python3
"""
Saving Advisor System - gRPC Server Main Entry
Fully gRPC-based open source version
"""
import sys
import os
import asyncio
import signal
from concurrent import futures

# Add project root directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import gRPC server factory and use renamed grpc_services package
from grpc import server as grpc_server
from app.grpc_services.generated import analysis_pb2_grpc, saving_advisor_pb2_grpc
from app.grpc_services.services.analysis_service import SyncAnalysisService
from app.grpc_services.services.saving_advisor_service import SyncSavingAdvisorService
from app.db.database import init_db, close_db
from app.core.config import settings
from app.core.logging import logger

class SavingAdvisorGRPCServer:
    """Saving Advisor gRPC Server"""
    
    def __init__(self, port: int = 50051, max_workers: int = 10):
        self.port = port
        self.max_workers = max_workers
        self.server = None
        
    async def start(self):
        """Start gRPC server"""
        try:
            # Initialize database
            logger.info("🔧 Initializing database...")
            await init_db()
            logger.info("✅ Database initialization completed")
            
            # Create gRPC server
            self.server = grpc_server(futures.ThreadPoolExecutor(max_workers=self.max_workers))
            
            # Register services
            analysis_pb2_grpc.add_AnalysisServiceServicer_to_server(
                SyncAnalysisService(), self.server
            )
            saving_advisor_pb2_grpc.add_SavingAdvisorServiceServicer_to_server(
                SyncSavingAdvisorService(), self.server
            )
            
            # Configure listen address
            listen_addr = f'[::]:{self.port}'
            self.server.add_insecure_port(listen_addr)
            
            # Start server
            self.server.start()
            logger.info(f"🚀 gRPC server started successfully: {listen_addr}")
            logger.info("📋 Available services:")
            logger.info("  - AnalysisService: Portfolio analysis")
            logger.info("  - SavingAdvisorService: Complete financial advice")
            logger.info("🔄 Press Ctrl+C to stop the server")
            
            # Wait for server termination
            self.server.wait_for_termination()
            
        except Exception as e:
            logger.error(f"❌ Failed to start gRPC server: {e}")
            raise
    
    async def stop(self):
        """Stop gRPC server"""
        if self.server:
            logger.info("🛑 Stopping gRPC server...")
            self.server.stop(grace=5)
            
            # Close database connections
            try:
                await close_db()
                logger.info("✅ Database connections closed")
            except Exception as e:
                logger.error(f"⚠️ Error closing database: {e}")
                
            logger.info("👋 gRPC server stopped")

async def serve():
    """Start gRPC server"""
    server = SavingAdvisorGRPCServer(port=settings.SERVER_PORT or 50051)
    
    # Set up signal handlers
    def signal_handler(signum, frame):
        logger.info(f"🛑 Received signal {signum}, shutting down server...")
        asyncio.create_task(server.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("⌨️ Received keyboard interrupt, shutting down server...")
        await server.stop()
    except Exception as e:
        logger.error(f"❌ Server runtime error: {e}")
        await server.stop()
        sys.exit(1)

def main():
    """Main function"""
    logger.info("🚀 Starting Saving Advisor System gRPC server...")
    logger.info("📍 Architecture: Fully gRPC-based")
    logger.info("🔧 Database: PostgreSQL + Redis")
    logger.info("🤖 AI Service: OpenAI GPT-4")
    logger.info("-" * 60)
    
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("👋 gRPC server stopped")
    except Exception as e:
        logger.error(f"❌ Failed to start gRPC server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()