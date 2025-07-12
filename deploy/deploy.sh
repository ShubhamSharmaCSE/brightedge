#!/bin/bash

# BrightEdge Crawler Deployment Script

set -e

ENVIRONMENT=${1:-development}
PROJECT_NAME="brightedge-crawler"

echo "🚀 Deploying BrightEdge Crawler to $ENVIRONMENT"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install it first."
    exit 1
fi

# Build and start services
echo "🔧 Building and starting services..."
docker-compose -f docker-compose.yml build
docker-compose -f docker-compose.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check API health
API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "000")
if [ "$API_HEALTH" = "200" ]; then
    echo "✅ API service is healthy"
else
    echo "❌ API service is not healthy (HTTP $API_HEALTH)"
fi

# Check database connection
DB_STATUS=$(docker-compose exec -T postgres pg_isready -U crawler -d brightedge || echo "failed")
if [[ "$DB_STATUS" == *"accepting connections"* ]]; then
    echo "✅ Database is healthy"
else
    echo "❌ Database is not healthy"
fi

# Check Redis connection
REDIS_STATUS=$(docker-compose exec -T redis redis-cli ping || echo "failed")
if [ "$REDIS_STATUS" = "PONG" ]; then
    echo "✅ Redis is healthy"
else
    echo "❌ Redis is not healthy"
fi

# Show service status
echo "📊 Service Status:"
docker-compose ps

# Show logs if there are any issues
if [ "$API_HEALTH" != "200" ]; then
    echo "🔍 API Service Logs:"
    docker-compose logs --tail=20 crawler-api
fi

echo "🎉 Deployment completed!"
echo "📍 API Documentation: http://localhost:8000/docs"
echo "📍 Prometheus Metrics: http://localhost:9090"
echo "📍 Grafana Dashboard: http://localhost:3000 (admin/admin)"

# Run tests if requested
if [ "$2" = "test" ]; then
    echo "🧪 Running tests..."
    python test_crawler.py
fi
