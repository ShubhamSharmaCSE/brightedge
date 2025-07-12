# BrightEdge Crawler API Documentation

This document provides comprehensive information about the BrightEdge Crawler API, including installation, usage, and API reference.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Deployment](#deployment)
- [Monitoring](#monitoring)
- [Configuration](#configuration)

## Installation

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/ShubhamSharmaCSE/brightedge.git
   cd brightedge
   ```

2. **Start services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

3. **Wait for services to be ready (about 30 seconds)**
   ```bash
   # Check service health
   curl http://localhost:8000/health
   ```

## Quick Start

### Basic Usage

1. **Crawl a single URL**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/crawl" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.example.com"}'
   ```

2. **Get crawl results**
   ```bash
   curl "http://localhost:8000/api/v1/results/{crawl_id}"
   ```

3. **Batch crawl multiple URLs**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/crawl/batch" \
     -H "Content-Type: application/json" \
     -d '{
       "urls": [
         "https://www.example.com",
         "https://www.google.com"
       ]
     }'
   ```

### Test with Provided URLs

Run the test script to verify the crawler works with the provided test URLs:

```bash
python test_crawler.py
```

This will test:
- Amazon product page
- REI blog post
- CNN news article

## API Reference

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication
Currently no authentication is required for development. In production, you would add API key authentication.

### Endpoints

#### POST /crawl
Crawl a single URL and extract metadata.

**Request Body:**
```json
{
  "url": "https://www.example.com",
  "priority": 5,
  "max_retries": 3,
  "crawl_delay": 1.0,
  "respect_robots_txt": true,
  "user_agent": "Custom-Agent/1.0",
  "headers": {
    "Custom-Header": "value"
  }
}
```

**Response:**
```json
{
  "crawl_id": "123e4567-e89b-12d3-a456-426614174000",
  "url": "https://www.example.com",
  "status": "pending",
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### POST /crawl/batch
Crawl multiple URLs in batch.

**Request Body:**
```json
{
  "urls": [
    "https://www.example.com",
    "https://www.google.com"
  ],
  "priority": 5,
  "max_retries": 3,
  "crawl_delay": 1.0,
  "respect_robots_txt": true
}
```

**Response:**
```json
{
  "batch_id": "123e4567-e89b-12d3-a456-426614174001",
  "total_urls": 2,
  "completed_urls": 0,
  "failed_urls": 0,
  "results": [
    {
      "crawl_id": "123e4567-e89b-12d3-a456-426614174002",
      "url": "https://www.example.com",
      "status": "pending"
    }
  ]
}
```

#### GET /results/{crawl_id}
Get the result of a crawl operation.

**Response:**
```json
{
  "crawl_id": "123e4567-e89b-12d3-a456-426614174000",
  "url": "https://www.example.com",
  "status": "completed",
  "metadata": {
    "title": "Example Domain",
    "description": "This domain is for use in illustrative examples",
    "keywords": ["example", "domain", "web"],
    "author": "John Doe",
    "published_date": "2024-01-01T12:00:00Z",
    "canonical_url": "https://www.example.com",
    "language": "en",
    "content_type": "text/html",
    "word_count": 150,
    "images": [
      {
        "url": "https://www.example.com/image.jpg",
        "alt_text": "Example image",
        "width": 800,
        "height": 600
      }
    ],
    "links": [
      {
        "url": "https://www.example.com/about",
        "text": "About Us",
        "title": "Learn more about us"
      }
    ],
    "topics": [
      {
        "topic": "technology",
        "confidence": 0.85,
        "keywords": ["example", "domain", "web"]
      }
    ],
    "crawl_timestamp": "2024-01-01T12:00:00Z",
    "response_time_ms": 250,
    "status_code": 200
  },
  "created_at": "2024-01-01T12:00:00Z",
  "completed_at": "2024-01-01T12:00:05Z"
}
```

#### GET /results
Get a list of crawl results with pagination and filtering.

**Query Parameters:**
- `limit` (int): Number of results to return (default: 10)
- `offset` (int): Number of results to skip (default: 0)
- `domain` (string): Filter by domain
- `status` (string): Filter by status (pending, processing, completed, failed)

**Response:**
```json
[
  {
    "crawl_id": "123e4567-e89b-12d3-a456-426614174000",
    "url": "https://www.example.com",
    "status": "completed",
    "metadata": { ... },
    "created_at": "2024-01-01T12:00:00Z",
    "completed_at": "2024-01-01T12:00:05Z"
  }
]
```

#### DELETE /results/{crawl_id}
Delete a crawl result.

**Response:**
```json
{
  "message": "Crawl result deleted successfully"
}
```

#### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0",
  "database": true,
  "redis": true,
  "queue": true
}
```

### Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

### Error Responses

All error responses follow this format:
```json
{
  "error": "ValidationError",
  "message": "Invalid URL format",
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req-123"
}
```

## Testing

### Manual Testing

1. **Test single URL crawling**
   ```bash
   # Test Amazon product page
   curl -X POST "http://localhost:8000/api/v1/crawl" \
     -H "Content-Type: application/json" \
     -d '{"url": "http://www.amazon.com/Cuisinart-CPT-122-Compact-2-Slice-Toaster/dp/B009GQ034C"}'
   ```

2. **Test batch crawling**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/crawl/batch" \
     -H "Content-Type: application/json" \
     -d '{
       "urls": [
         "http://blog.rei.com/camp/how-to-introduce-your-indoorsy-friend-to-the-outdoors/",
         "http://www.cnn.com/2013/06/10/politics/edward-snowden-profile/"
       ]
     }'
   ```

### Automated Testing

Run the comprehensive test suite:
```bash
python test_crawler.py
```

This test suite will:
- Test health check endpoint
- Crawl each provided URL individually
- Test batch crawling
- Analyze and display results
- Provide success/failure statistics

## Deployment

### Local Development
```bash
# Start all services
docker-compose up -d

# Check service health
curl http://localhost:8000/health

# View logs
docker-compose logs -f crawler-api
```

### Production Deployment
```bash
# Deploy to production
./deploy/deploy.sh production

# Run tests after deployment
./deploy/deploy.sh production test
```

## Monitoring

### Prometheus Metrics
Metrics are available at `http://localhost:8000/metrics`

Key metrics include:
- `crawler_requests_total`: Total number of requests
- `crawler_pages_crawled_total`: Total pages crawled
- `crawler_response_time_seconds`: Response time distribution
- `crawler_errors_total`: Total errors by type
- `crawler_queue_size`: Current queue size

### Grafana Dashboard
Access Grafana at `http://localhost:3000` (admin/admin)

### Health Checks
- **Liveness**: `GET /health/liveness`
- **Readiness**: `GET /health/readiness`
- **Full Health**: `GET /health`

## Configuration

### Environment Variables

Key configuration options:

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/database

# Redis
REDIS_URL=redis://host:6379

# Crawler Settings
DEFAULT_CRAWL_DELAY=1.0
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT=30

# Content Classification
ENABLE_TOPIC_CLASSIFICATION=true
MIN_TOPIC_CONFIDENCE=0.5

# Rate Limiting
RATE_LIMIT_ENABLED=true
RESPECT_ROBOTS_TXT=true
```

### Customization

1. **Custom User Agent**
   ```json
   {
     "url": "https://example.com",
     "user_agent": "MyBot/1.0"
   }
   ```

2. **Custom Headers**
   ```json
   {
     "url": "https://example.com",
     "headers": {
       "Authorization": "Bearer token",
       "Custom-Header": "value"
     }
   }
   ```

3. **Rate Limiting**
   ```json
   {
     "url": "https://example.com",
     "crawl_delay": 2.0,
     "respect_robots_txt": true
   }
   ```

## Interactive API Documentation

Once the service is running, you can explore the API interactively:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These interfaces allow you to:
- Test API endpoints directly
- View request/response schemas
- Understand parameter requirements
- Copy curl commands for testing

## Troubleshooting

### Common Issues

1. **Service not starting**
   ```bash
   # Check Docker status
   docker-compose ps
   
   # View logs
   docker-compose logs crawler-api
   ```

2. **Database connection issues**
   ```bash
   # Check database health
   docker-compose exec postgres pg_isready
   
   # Connect to database
   docker-compose exec postgres psql -U crawler -d brightedge
   ```

3. **Redis connection issues**
   ```bash
   # Check Redis health
   docker-compose exec redis redis-cli ping
   ```

4. **Crawl failures**
   - Check URL accessibility
   - Verify robots.txt compliance
   - Check rate limiting settings
   - Review error logs

### Performance Tuning

1. **Increase concurrency**
   ```bash
   export MAX_CONCURRENT_REQUESTS=200
   ```

2. **Adjust timeouts**
   ```bash
   export REQUEST_TIMEOUT=60
   ```

3. **Optimize database**
   ```bash
   export DATABASE_POOL_SIZE=20
   ```

## Support

For issues and questions:
1. Check the logs: `docker-compose logs`
2. Review the health check: `curl http://localhost:8000/health`
3. Test with the provided test script: `python test_crawler.py`
4. Create an issue on GitHub with detailed information about the problem
