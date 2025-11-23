#!/bin/bash
# Start Saving Advisor System services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================================"
echo "  🚀 Saving Advisor System - Service Startup Script"
echo "============================================================"
echo ""

# Check port availability
check_port() {
    local port=$1
    local service=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Port $port ($service) is already in use${NC}"
        echo "Processes using this port:"
        lsof -i :$port
        echo ""
        read -p "Do you want to kill these processes and continue? (y/N): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "🛑 Killing processes using port $port..."
            lsof -ti :$port | xargs kill -9 2>/dev/null || true
            sleep 1
            echo -e "${GREEN}✅ Port $port has been released${NC}"
        else
            echo -e "${RED}❌ Operation cancelled${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✅ Port $port ($service) is available${NC}"
    fi
}

# Check required services
echo "📋 Checking service dependencies..."
if ! docker ps >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Docker is not running, please start Docker first${NC}"
fi

# Read ports from configuration
GRPC_PORT=$(python3 -c "import sys; sys.path.insert(0, '.'); from app.core.config import settings; print(settings.SERVER_PORT)" 2>/dev/null || echo "50051")
GATEWAY_PORT=$(python3 -c "import sys; sys.path.insert(0, '.'); from app.core.config import settings; print(settings.GATEWAY_PORT)" 2>/dev/null || echo "8080")

echo ""
echo "🔍 Checking port availability..."
check_port $GRPC_PORT "gRPC Server"
check_port $GATEWAY_PORT "REST Gateway"

echo ""
echo "============================================================"
echo "  Startup Options:"
echo "============================================================"
echo "  1) Start gRPC server only (port $GRPC_PORT)"
echo "  2) Start REST gateway only (port $GATEWAY_PORT)"
echo "  3) Start both gRPC server and REST gateway"
echo "  4) Exit"
echo ""
read -p "Please select (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🚀 Starting gRPC server..."
        PYTHONPATH="$PYTHONPATH:$PROJECT_ROOT/app/grpc_services/generated" \
        python3 app/main.py
        ;;
    2)
        echo ""
        echo "🚀 Starting REST gateway..."
        python3 start_web_server.py
        ;;
    3)
        echo ""
        echo "🚀 Starting gRPC server and REST gateway..."
        echo ""
        
        # Create logs directory
        mkdir -p logs
        
        # Start gRPC server (background)
        echo "📡 Starting gRPC server (port $GRPC_PORT)..."
        PYTHONPATH="$PYTHONPATH:$PROJECT_ROOT/app/grpc_services/generated" \
        nohup python3 app/main.py > logs/grpc_server.log 2>&1 &
        GRPC_PID=$!
        echo "  ✅ gRPC server started (PID: $GRPC_PID)"
        echo "  📝 Log file: logs/grpc_server.log"
        
        # Wait a bit to ensure gRPC server starts
        sleep 2
        
        # Start REST gateway (background)
        echo "🌐 Starting REST gateway (port $GATEWAY_PORT)..."
        nohup python3 start_web_server.py > logs/rest_gateway.log 2>&1 &
        GATEWAY_PID=$!
        echo "  ✅ REST gateway started (PID: $GATEWAY_PID)"
        echo "  📝 Log file: logs/rest_gateway.log"
        
        echo ""
        echo "============================================================"
        echo "  ✅ Services started successfully!"
        echo "============================================================"
        echo ""
        echo "📊 Service status:"
        echo "  - gRPC server: http://localhost:$GRPC_PORT (PID: $GRPC_PID)"
        echo "  - REST gateway: http://localhost:$GATEWAY_PORT (PID: $GATEWAY_PID)"
        echo ""
        echo "📝 View logs:"
        echo "  - gRPC server: tail -f logs/grpc_server.log"
        echo "  - REST gateway: tail -f logs/rest_gateway.log"
        echo ""
        echo "🛑 Stop services:"
        echo "  kill $GRPC_PID $GATEWAY_PID"
        echo "  or use: bash scripts/kill_port.sh $GRPC_PORT $GATEWAY_PORT"
        echo ""
        echo "💡 Tip: Services are running in the background, you can close this terminal window"
        echo ""
        ;;
    4)
        echo "👋 Exiting"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ Invalid selection${NC}"
        exit 1
        ;;
esac

