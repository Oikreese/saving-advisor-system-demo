#!/bin/bash
# Batch processing system management script - Unified management for Celery Worker, Beat, Flower and manual tasks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create logs directory
mkdir -p logs

# Check Redis connection
check_redis() {
    if ! command -v redis-cli &> /dev/null; then
        echo -e "${YELLOW}⚠️  redis-cli is not installed, cannot check Redis connection${NC}"
        return 0
    fi
    
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✅ Redis connection is healthy${NC}"
        return 0
    else
        echo -e "${RED}❌ Redis is not running or cannot be connected${NC}"
        echo "Please start Redis first: redis-server or docker-compose up -d redis"
        return 1
    fi
}

# Check port availability
check_port() {
    local port=$1
    local service=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Port $port ($service) is already in use${NC}"
        return 1
    else
        echo -e "${GREEN}✅ Port $port ($service) is available${NC}"
        return 0
    fi
}

# Start Celery Worker
start_worker() {
    echo ""
    echo "🚀 Starting Celery Worker..."
    
    if ! check_redis; then
        return 1
    fi
    
    celery -A app.tasks.batch_tasks worker \
        --loglevel=info \
        --concurrency=4 \
        --max-tasks-per-child=50 \
        --logfile=logs/celery_worker.log
    
    echo "✅ Celery Worker started"
}

# Start Celery Beat (background)
start_beat_background() {
    echo ""
    echo "⏰ Starting Celery Beat (background)..."
    
    if ! check_redis; then
        return 1
    fi
    
    nohup celery -A app.tasks.batch_tasks beat \
        --loglevel=info \
        --logfile=logs/celery_beat.log \
        --pidfile=logs/celery_beat.pid > logs/celery_beat_nohup.log 2>&1 &
    
    BEAT_PID=$!
    echo "  ✅ Celery Beat started (PID: $BEAT_PID)"
    echo "  📝 Log file: logs/celery_beat.log"
    echo "  🛑 Stop: kill $BEAT_PID or kill \$(cat logs/celery_beat.pid)"
}

# Start Celery Beat (foreground)
start_beat_foreground() {
    echo ""
    echo "⏰ Starting Celery Beat..."
    
    if ! check_redis; then
        return 1
    fi
    
    celery -A app.tasks.batch_tasks beat \
        --loglevel=info \
        --logfile=logs/celery_beat.log \
        --pidfile=logs/celery_beat.pid
    
    echo "✅ Celery Beat started"
}

# Start Flower (background)
start_flower_background() {
    echo ""
    echo "🌸 Starting Flower monitoring interface (background)..."
    
    if ! check_redis; then
        return 1
    fi
    
    if ! check_port 5555 "Flower"; then
        echo "Do you want to kill processes using port 5555? (y/N): "
        read -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            lsof -ti :5555 | xargs kill -9 2>/dev/null || true
            sleep 1
        else
            return 1
        fi
    fi
    
    nohup celery -A app.tasks.batch_tasks flower \
        --port=5555 \
        --broker=${REDIS_URL:-redis://localhost:6379} \
        --basic_auth=${FLOWER_USER:-admin}:${FLOWER_PASSWORD:-admin} \
        --url_prefix=flower \
        --logging=info > logs/flower_nohup.log 2>&1 &
    
    FLOWER_PID=$!
    echo "  ✅ Flower started (PID: $FLOWER_PID)"
    echo "  📊 Access: http://localhost:5555"
    echo "  👤 Username: ${FLOWER_USER:-admin}"
    echo "  🔐 Password: ${FLOWER_PASSWORD:-admin}"
    echo "  📝 Log file: logs/flower_nohup.log"
    echo "  🛑 Stop: kill $FLOWER_PID"
}

# Start Flower (foreground)
start_flower_foreground() {
    echo ""
    echo "🌸 Starting Flower monitoring interface..."
    
    if ! check_redis; then
        return 1
    fi
    
    celery -A app.tasks.batch_tasks flower \
        --port=5555 \
        --broker=${REDIS_URL:-redis://localhost:6379} \
        --basic_auth=${FLOWER_USER:-admin}:${FLOWER_PASSWORD:-admin} \
        --url_prefix=flower \
        --logging=info
    
    echo "✅ Flower monitoring interface started"
}

# Manually run all batch jobs
run_manual_jobs() {
    echo ""
    echo "======================================"
    echo "  Manual Batch Job Execution"
    echo "======================================"
    echo ""
    
    echo "1️⃣  Running user behavior analysis..."
    python scripts/batch_jobs/user_behavior_analysis.py
    echo ""
    
    echo "2️⃣  Running recommendation performance analysis..."
    python scripts/batch_jobs/recommendation_analysis.py
    echo ""
    
    echo "3️⃣  Running market trends analysis..."
    python scripts/batch_jobs/market_trend_analysis.py
    echo ""
    
    echo "======================================"
    echo "  ✅ All batch jobs completed!"
    echo "======================================"
}

# Stop all batch processing services
stop_all() {
    echo ""
    echo "🛑 Stopping all batch processing services..."
    
    # Stop Celery Worker
    pkill -f "celery.*worker.*batch_tasks" 2>/dev/null && echo "✅ Celery Worker stopped" || echo "ℹ️  Celery Worker is not running"
    
    # Stop Celery Beat
    if [ -f logs/celery_beat.pid ]; then
        kill $(cat logs/celery_beat.pid) 2>/dev/null && echo "✅ Celery Beat stopped" || echo "ℹ️  Celery Beat is not running"
        rm -f logs/celery_beat.pid
    else
        pkill -f "celery.*beat.*batch_tasks" 2>/dev/null && echo "✅ Celery Beat stopped" || echo "ℹ️  Celery Beat is not running"
    fi
    
    # Stop Flower
    pkill -f "celery.*flower" 2>/dev/null && echo "✅ Flower stopped" || echo "ℹ️  Flower is not running"
    
    echo ""
    echo "✅ All services stopped"
}

# Show service status
show_status() {
    echo ""
    echo "📊 Batch Processing Service Status:"
    echo ""
    
    # Check Worker
    if pgrep -f "celery.*worker.*batch_tasks" > /dev/null; then
        echo -e "  ${GREEN}✅ Celery Worker: Running${NC}"
    else
        echo -e "  ${RED}❌ Celery Worker: Not running${NC}"
    fi
    
    # Check Beat
    if pgrep -f "celery.*beat.*batch_tasks" > /dev/null; then
        echo -e "  ${GREEN}✅ Celery Beat: Running${NC}"
    else
        echo -e "  ${RED}❌ Celery Beat: Not running${NC}"
    fi
    
    # Check Flower
    if pgrep -f "celery.*flower" > /dev/null; then
        echo -e "  ${GREEN}✅ Flower: Running (http://localhost:5555)${NC}"
    else
        echo -e "  ${RED}❌ Flower: Not running${NC}"
    fi
    
    echo ""
}

# Main menu
show_menu() {
    echo "============================================================"
    echo "  📦 Batch Processing System Management"
    echo "============================================================"
    echo ""
    echo "  1) Start Celery Worker (foreground)"
    echo "  2) Start Celery Beat (foreground)"
    echo "  3) Start Celery Beat (background)"
    echo "  4) Start Flower monitoring (foreground)"
    echo "  5) Start Flower monitoring (background)"
    echo "  6) Manually run all batch jobs"
    echo "  7) Start complete batch processing system (Worker + Beat + Flower, background)"
    echo "  8) Check service status"
    echo "  9) Stop all batch processing services"
    echo "  0) Exit"
    echo ""
}

# Main program
main() {
    show_menu
    read -p "Please select (0-9): " choice
    
    case $choice in
        1)
            start_worker
            ;;
        2)
            start_beat_foreground
            ;;
        3)
            start_beat_background
            ;;
        4)
            start_flower_foreground
            ;;
        5)
            start_flower_background
            ;;
        6)
            run_manual_jobs
            ;;
        7)
            echo ""
            echo "🚀 Starting complete batch processing system..."
            start_worker &
            sleep 2
            start_beat_background
            sleep 2
            start_flower_background
            echo ""
            echo "✅ All services started!"
            echo "📊 Check status: bash scripts/batch_processing.sh (select option 8)"
            ;;
        8)
            show_status
            ;;
        9)
            stop_all
            ;;
        0)
            echo "👋 Exiting"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Invalid selection${NC}"
            exit 1
            ;;
    esac
}

# Run main program
main
