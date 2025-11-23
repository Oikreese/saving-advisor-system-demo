#!/bin/bash
# Kill processes using the specified port

PORT=${1:-8080}

echo "🔍 Finding processes using port $PORT..."

PIDS=$(lsof -ti :$PORT 2>/dev/null)

if [ -z "$PIDS" ]; then
    echo "✅ Port $PORT is not in use, no cleanup needed"
    exit 0
fi

echo "⚠️  Found the following processes using port $PORT:"
lsof -i :$PORT
echo ""

read -p "Do you want to kill these processes? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🛑 Killing processes..."
    echo "$PIDS" | xargs kill -9
    sleep 1
    
    # Verify success
    REMAINING=$(lsof -ti :$PORT 2>/dev/null)
    if [ -z "$REMAINING" ]; then
        echo "✅ Port $PORT has been released"
    else
        echo "⚠️  Some processes may still be running, please check manually"
        lsof -i :$PORT
    fi
else
    echo "❌ Operation cancelled"
    exit 1
fi
