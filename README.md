# BrightEdge Web Crawler

A production-grade, scalable web crawler service built with FastAPI, PostgreSQL, and AWS infrastructure.

## Features

- **High-Performance Crawling**: Async/await based crawler with configurable concurrency
- **Content Classification**: AI-powered topic detection and content categorization
- **Metadata Extraction**: Comprehensive HTML metadata parsing (title, description, keywords, etc.)
- **Rate Limiting**: Domain-aware rate limiting with robots.txt compliance
- **Scalable Architecture**: Microservices with AWS ECS, SQS, and RDS
- **Monitoring**: Prometheus metrics, structured logging, and health checks
- **Production Ready**: Docker containers, infrastructure as code, CI/CD

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   Crawler API    │    │  Crawler Worker │
│                 │────│   (FastAPI)      │────│   (SQS Consumer)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                │                        │
                       ┌──────────────────┐    ┌─────────────────┐
                       │   PostgreSQL     │    │      Redis      │
                       │   (Metadata)     │    │    (Cache)      │
                       └──────────────────┘    └─────────────────┘
```

## Quick Start

### Local Development

```bash
# Clone the repository
git clone https://github.com/ShubhamSharmaCSE/brightedge.git
cd brightedge

# Start services with Docker Compose
docker-compose up -d

# Run tests
pytest tests/

# Access API documentation
open http://localhost:8000/docs
```

### API Usage

```bash
# Crawl a single URL
curl -X POST "http://localhost:8000/api/v1/crawl" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.example.com"}'

# Batch crawl multiple URLs
curl -X POST "http://localhost:8000/api/v1/crawl/batch" \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://www.example.com", "https://www.google.com"]}'

# Get crawl results
curl "http://localhost:8000/api/v1/results/{crawl_id}"
```

## Project Structure

```
brightedge/
├── infrastructure/          # Terraform IaC
├── services/
│   ├── crawler-api/        # Main API service
│   ├── crawler-worker/     # Background workers
│   └── shared/            # Shared utilities
├── deploy/                # Deployment configs
├── monitoring/           # Observability configs
├── tests/               # Test suites
└── docs/               # Documentation
```

## Technology Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL 14+
- **Cache**: Redis 7+
- **Queue**: AWS SQS
- **Storage**: AWS S3
- **Containers**: Docker + Docker Compose
- **Orchestration**: AWS ECS Fargate
- **Monitoring**: Prometheus + Grafana
- **IaC**: Terraform

## Development Setup

1. **Prerequisites**
   - Python 3.11+
   - Docker & Docker Compose
   - AWS CLI (for deployment)
   - Terraform (for infrastructure)

2. **Environment Setup**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r services/crawler-api/requirements.txt
   ```

3. **Database Setup**
   ```bash
   # Start PostgreSQL and Redis
   docker-compose up -d postgres redis
   
   # Run migrations
   alembic upgrade head
   ```

## Deployment

### AWS Infrastructure

```bash
# Deploy infrastructure
cd infrastructure
terraform init
terraform plan
terraform apply

# Deploy services
cd ../deploy
./deploy.sh production
```

### Environment Variables

```bash
# API Service
DATABASE_URL=postgresql://user:password@localhost:5432/brightedge
REDIS_URL=redis://localhost:6379
AWS_SQS_QUEUE_URL=https://sqs.region.amazonaws.com/account/queue-name
AWS_S3_BUCKET=brightedge-content-storage

# Worker Service
WORKER_CONCURRENCY=10
MAX_RETRIES=3
CRAWL_DELAY=1.0
```

## Monitoring

- **Metrics**: Prometheus metrics available at `/metrics`
- **Health**: Health checks at `/health`
- **Logs**: Structured JSON logs with correlation IDs
- **Tracing**: OpenTelemetry distributed tracing

## Testing

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Load tests
pytest tests/load/

# Coverage report
pytest --cov=services/ --cov-report=html
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
