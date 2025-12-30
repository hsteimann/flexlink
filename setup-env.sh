#!/bin/bash
# FlexLink Environment Setup Script

set -e

echo "🔧 FlexLink Environment Configuration"
echo "======================================"
echo ""

# Check if .env already exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Setup cancelled. Keeping existing .env file."
        exit 0
    fi
fi

# Copy template
echo "📋 Creating .env from .env.example..."
cp .env.example .env

echo "✅ .env file created!"
echo ""
echo "📝 Please edit .env and configure your credentials:"
echo ""
echo "   Required for PriceEdge integration:"
echo "   - PRICEEDGE_BASE_URL (your PriceEdge API endpoint)"
echo "   - PRICEEDGE_KEY_NAME (your API key name)"
echo "   - PRICEEDGE_API_TOKEN (your API token)"
echo ""
echo "   Optional for PostgreSQL connector:"
echo "   - POSTGRES_CONNECTION_STRING"
echo "   - POSTGRES_TABLE_NAME"
echo ""
echo "💡 Quick edit commands:"
echo "   nano .env          # Simple editor"
echo "   vim .env           # Vim editor"
echo "   code .env          # VS Code"
echo ""
echo "🐳 After configuring, rebuild your Docker container:"
echo "   docker-compose down"
echo "   docker-compose build"
echo "   docker-compose up -d"
echo ""
