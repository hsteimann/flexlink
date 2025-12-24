#!/bin/bash
# FlexLink Server Startup Script
# Starts the server, performs health checks, and displays configuration

set -e  # Exit on error

# Configuration
PORT=${1:-8000}
HOST=${2:-127.0.0.1}
MAX_WAIT=30  # Maximum seconds to wait for server startup

echo "=========================================="
echo "FlexLink Middleware - Server Startup"
echo "=========================================="
echo ""

# Check if server is already running
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Server already running on port $PORT"
    read -p "Kill existing server and restart? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔪 Killing existing server..."
        lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
        sleep 2
    else
        echo "❌ Startup cancelled"
        exit 1
    fi
fi

# Set PYTHONPATH to include src directory
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"

# Start server in background
echo "🚀 Starting FlexLink server on $HOST:$PORT..."
echo ""

uvicorn flexlink.main:app \
    --host $HOST \
    --port $PORT \
    --log-level info \
    > /tmp/flexlink-server.log 2>&1 &

SERVER_PID=$!
echo "📝 Server PID: $SERVER_PID"
echo "📋 Logs: /tmp/flexlink-server.log"
echo ""

# Wait for server to be ready
echo "⏳ Waiting for server to start..."
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://$HOST:$PORT/health > /dev/null 2>&1; then
        break
    fi
    sleep 1
    WAITED=$((WAITED + 1))
    echo -n "."
done
echo ""

# Check if server started successfully
if [ $WAITED -ge $MAX_WAIT ]; then
    echo ""
    echo "❌ Server failed to start within ${MAX_WAIT} seconds"
    echo ""
    echo "Last 20 lines of log:"
    tail -20 /tmp/flexlink-server.log
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

echo ""
echo "✅ Server started successfully!"
echo ""

# Perform health check
echo "=========================================="
echo "Health Check"
echo "=========================================="
HEALTH_RESPONSE=$(curl -s http://$HOST:$PORT/health)
echo "$HEALTH_RESPONSE" | jq '.'
echo ""

# Get and display connectors
echo "=========================================="
echo "Available Connectors"
echo "=========================================="
CONNECTORS_RESPONSE=$(curl -s http://$HOST:$PORT/api/v1/connectors)
echo "$CONNECTORS_RESPONSE" | jq '.'

# Count connectors
CONNECTOR_COUNT=$(echo "$CONNECTORS_RESPONSE" | jq '.connectors | length')
echo ""
echo "📊 Total connectors loaded: $CONNECTOR_COUNT"
echo ""

# Get and display routes
echo "=========================================="
echo "Available Routes"
echo "=========================================="
ROUTES_RESPONSE=$(curl -s http://$HOST:$PORT/api/v1/routes)
echo "$ROUTES_RESPONSE" | jq '.'

# Count routes
ROUTE_COUNT=$(echo "$ROUTES_RESPONSE" | jq '.routes | length')
echo ""
echo "📊 Total routes configured: $ROUTE_COUNT"
echo ""

# Display route summary by connector
echo "=========================================="
echo "Routes by Connector"
echo "=========================================="
echo "$ROUTES_RESPONSE" | jq -r '.routes[] | "\(.method) \(.path) -> \(.connector)"' | sort -k3

echo ""
echo "=========================================="
echo "Server Information"
echo "=========================================="
echo "🌐 Base URL: http://$HOST:$PORT"
echo "📚 API Docs: http://$HOST:$PORT/docs"
echo "🏥 Health: http://$HOST:$PORT/health"
echo "🔌 Connectors API: http://$HOST:$PORT/api/v1/connectors"
echo "🛣️  Routes API: http://$HOST:$PORT/api/v1/routes"
echo ""
echo "To stop the server:"
echo "  kill $SERVER_PID"
echo ""
echo "To view logs:"
echo "  tail -f /tmp/flexlink-server.log"
echo ""
echo "=========================================="
echo "✨ FlexLink is ready for requests!"
echo "=========================================="
