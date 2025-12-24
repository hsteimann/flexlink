#!/bin/bash
# FlexLink Server Stop Script
# Gracefully stops the FlexLink server

PORT=${1:-8000}

echo "=========================================="
echo "FlexLink Middleware - Server Shutdown"
echo "=========================================="
echo ""

# Check if server is running
if ! lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  No server running on port $PORT"
    exit 0
fi

# Get PID
PID=$(lsof -ti:$PORT)
echo "🔍 Found server process: PID $PID"

# Try graceful shutdown first
echo "🛑 Sending SIGTERM (graceful shutdown)..."
kill -TERM $PID 2>/dev/null

# Wait for graceful shutdown
echo -n "⏳ Waiting for server to stop"
for i in {1..10}; do
    if ! lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo ""
        echo "✅ Server stopped gracefully"
        exit 0
    fi
    echo -n "."
    sleep 1
done

# Force kill if still running
echo ""
echo "⚠️  Server didn't stop gracefully, forcing shutdown..."
kill -9 $PID 2>/dev/null

sleep 1

if ! lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "✅ Server stopped (forced)"
else
    echo "❌ Failed to stop server"
    exit 1
fi
