#!/bin/bash
# Check port availability and configuration

# If no port argument provided, check configured ports
if [ -z "$1" ]; then
    echo "🔍 Checking port configuration..."
    echo ""
    
    # Check port configuration
    python3 -c "
import sys
sys.path.insert(0, '.')
from app.core.config import settings

print(f'✅ gRPC server port: {settings.SERVER_PORT}')
print(f'✅ REST gateway port: {settings.GATEWAY_PORT}')
print('')

if settings.SERVER_PORT == settings.GATEWAY_PORT:
    print('❌ Error: gRPC and REST gateway are using the same port!')
    sys.exit(1)
else:
    print('✅ Port configuration is correct: gRPC and REST gateway use different ports')
    sys.exit(0)
" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "🔍 Checking port availability..."
        echo ""
        
        # Get configured ports
        GRPC_PORT=$(python3 -c "import sys; sys.path.insert(0, '.'); from app.core.config import settings; print(settings.SERVER_PORT)" 2>/dev/null || echo "50051")
        GATEWAY_PORT=$(python3 -c "import sys; sys.path.insert(0, '.'); from app.core.config import settings; print(settings.GATEWAY_PORT)" 2>/dev/null || echo "8080")
        
        echo "Checking gRPC port ($GRPC_PORT)..."
        check_single_port $GRPC_PORT
        
        echo ""
        echo "Checking REST gateway port ($GATEWAY_PORT)..."
        check_single_port $GATEWAY_PORT
    else
        echo ""
        echo "❌ Port configuration has issues, please check app/core/config.py"
        exit 1
    fi
else
    # Check specified port
    check_single_port "$1"
fi

# Function to check a single port
check_single_port() {
    local PORT=$1
    
    # Use lsof to find processes using the port
    PROCESSES=$(lsof -i :$PORT 2>/dev/null)
    
    if [ -z "$PROCESSES" ]; then
        echo "  ✅ Port $PORT is not in use"
        return 0
    fi
    
    echo "  ⚠️  Port $PORT is being used by the following processes:"
    echo ""
    echo "$PROCESSES" | sed 's/^/    /'
    echo ""
    echo "  To kill these processes, run:"
    echo "    bash scripts/kill_port.sh $PORT"
    echo ""
}
