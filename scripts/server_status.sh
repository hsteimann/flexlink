#!/bin/bash
# FlexLink Server Status Script
# Shows current server status and basic stats

PORT=${1:-8000}
HOST=${2:-127.0.0.1}

echo "=========================================="
echo "FlexLink Middleware - Server Status"
echo "=========================================="
echo ""

# Check if server is running
if ! lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "❌ Server not running on port $PORT"
    echo ""
    echo "To start the server:"
    echo "  ./scripts/start_server.sh"
    exit 1
fi

PID=$(lsof -ti:$PORT)
echo "✅ Server is running"
echo "📝 PID: $PID"
echo "🌐 URL: http://$HOST:$PORT"
echo ""

# Check if server is responding
if ! curl -s http://$HOST:$PORT/health > /dev/null 2>&1; then
    echo "⚠️  Server is running but not responding to requests"
    echo ""
    echo "Check logs at: /tmp/flexlink-server.log"
    exit 1
fi

# Get health status
echo "=========================================="
echo "Health Check"
echo "=========================================="
curl -s http://$HOST:$PORT/health | jq '.'
echo ""

# Get connector count
CONNECTORS=$(curl -s http://$HOST:$PORT/api/v1/connectors | jq -r '.connectors | join(", ")')
CONNECTOR_COUNT=$(curl -s http://$HOST:$PORT/api/v1/connectors | jq '.connectors | length')

echo "=========================================="
echo "Configuration"
echo "=========================================="
echo "🔌 Connectors ($CONNECTOR_COUNT): $CONNECTORS"

# Get route count
ROUTE_COUNT=$(curl -s http://$HOST:$PORT/api/v1/routes | jq '.routes | length')
echo "🛣️  Routes: $ROUTE_COUNT configured"
echo ""

# Show uptime
ELAPSED=$(ps -o etime= -p $PID | tr -d ' ')
echo "⏱️  Uptime: $ELAPSED"
echo ""

# Show memory usage
MEM=$(ps -o rss= -p $PID | awk '{print $1/1024 " MB"}')
echo "💾 Memory: $MEM"
echo ""

echo "=========================================="
echo "Quick Links"
echo "=========================================="
echo "📚 API Docs: http://$HOST:$PORT/docs"
echo "📋 Logs: tail -f /tmp/flexlink-server.log"
echo "🛑 Stop: ./scripts/stop_server.sh"
echo ""
