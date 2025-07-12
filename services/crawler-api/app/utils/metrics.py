"""
Prometheus metrics configuration for the crawler API.
"""

from prometheus_client import Counter, Histogram, Gauge, Info
from typing import Dict, Any
import structlog

logger = structlog.get_logger()

# Define metrics
crawler_requests_total = Counter(
    'crawler_requests_total',
    'Total number of crawler requests',
    ['status', 'domain', 'method']
)

crawler_request_duration_seconds = Histogram(
    'crawler_request_duration_seconds',
    'Time spent processing crawler requests',
    ['domain', 'status']
)

crawler_queue_size = Gauge(
    'crawler_queue_size',
    'Current size of the crawler queue'
)

crawler_active_workers = Gauge(
    'crawler_active_workers',
    'Number of active crawler workers'
)

crawler_errors_total = Counter(
    'crawler_errors_total',
    'Total number of crawler errors',
    ['error_type', 'domain']
)

crawler_pages_crawled_total = Counter(
    'crawler_pages_crawled_total',
    'Total number of pages crawled',
    ['domain', 'status_code']
)

crawler_response_time_seconds = Histogram(
    'crawler_response_time_seconds',
    'Response time for crawled pages',
    ['domain']
)

crawler_content_size_bytes = Histogram(
    'crawler_content_size_bytes',
    'Size of crawled content in bytes',
    ['domain', 'content_type']
)

crawler_topics_detected_total = Counter(
    'crawler_topics_detected_total',
    'Total number of topics detected',
    ['topic']
)

crawler_rate_limit_waits_total = Counter(
    'crawler_rate_limit_waits_total',
    'Total number of rate limit waits',
    ['domain']
)

crawler_robots_txt_checks_total = Counter(
    'crawler_robots_txt_checks_total',
    'Total number of robots.txt checks',
    ['domain', 'allowed']
)

# Application info
app_info = Info(
    'crawler_app_info',
    'Information about the crawler application'
)

# Cache metrics
cache_operations_total = Counter(
    'cache_operations_total',
    'Total number of cache operations',
    ['operation', 'result']
)

cache_hit_ratio = Gauge(
    'cache_hit_ratio',
    'Cache hit ratio'
)

# Database metrics
database_connections_active = Gauge(
    'database_connections_active',
    'Number of active database connections'
)

database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Time spent executing database queries',
    ['query_type']
)


def setup_metrics(app):
    """Setup metrics for the FastAPI application."""
    try:
        # Set application info
        app_info.info({
            'version': '1.0.0',
            'environment': 'development',
            'name': 'brightedge-crawler-api'
        })
        
        logger.info("metrics_setup_complete")
        
    except Exception as e:
        logger.error("metrics_setup_failed", error=str(e))


def record_request(method: str, status: str, domain: str = None):
    """Record a request metric."""
    try:
        crawler_requests_total.labels(
            status=status,
            domain=domain or 'unknown',
            method=method
        ).inc()
    except Exception as e:
        logger.error("record_request_failed", error=str(e))


def record_request_duration(domain: str, status: str, duration: float):
    """Record request duration metric."""
    try:
        crawler_request_duration_seconds.labels(
            domain=domain,
            status=status
        ).observe(duration)
    except Exception as e:
        logger.error("record_request_duration_failed", error=str(e))


def record_error(error_type: str, domain: str = None):
    """Record an error metric."""
    try:
        crawler_errors_total.labels(
            error_type=error_type,
            domain=domain or 'unknown'
        ).inc()
    except Exception as e:
        logger.error("record_error_failed", error=str(e))


def record_page_crawled(domain: str, status_code: int):
    """Record a page crawled metric."""
    try:
        crawler_pages_crawled_total.labels(
            domain=domain,
            status_code=str(status_code)
        ).inc()
    except Exception as e:
        logger.error("record_page_crawled_failed", error=str(e))


def record_response_time(domain: str, response_time: float):
    """Record response time metric."""
    try:
        crawler_response_time_seconds.labels(
            domain=domain
        ).observe(response_time / 1000.0)  # Convert ms to seconds
    except Exception as e:
        logger.error("record_response_time_failed", error=str(e))


def record_content_size(domain: str, content_type: str, size: int):
    """Record content size metric."""
    try:
        crawler_content_size_bytes.labels(
            domain=domain,
            content_type=content_type
        ).observe(size)
    except Exception as e:
        logger.error("record_content_size_failed", error=str(e))


def record_topic_detected(topic: str):
    """Record topic detection metric."""
    try:
        crawler_topics_detected_total.labels(
            topic=topic
        ).inc()
    except Exception as e:
        logger.error("record_topic_detected_failed", error=str(e))


def record_rate_limit_wait(domain: str):
    """Record rate limit wait metric."""
    try:
        crawler_rate_limit_waits_total.labels(
            domain=domain
        ).inc()
    except Exception as e:
        logger.error("record_rate_limit_wait_failed", error=str(e))


def record_robots_txt_check(domain: str, allowed: bool):
    """Record robots.txt check metric."""
    try:
        crawler_robots_txt_checks_total.labels(
            domain=domain,
            allowed=str(allowed).lower()
        ).inc()
    except Exception as e:
        logger.error("record_robots_txt_check_failed", error=str(e))


def update_queue_size(size: int):
    """Update queue size metric."""
    try:
        crawler_queue_size.set(size)
    except Exception as e:
        logger.error("update_queue_size_failed", error=str(e))


def update_active_workers(count: int):
    """Update active workers metric."""
    try:
        crawler_active_workers.set(count)
    except Exception as e:
        logger.error("update_active_workers_failed", error=str(e))


def record_cache_operation(operation: str, result: str):
    """Record cache operation metric."""
    try:
        cache_operations_total.labels(
            operation=operation,
            result=result
        ).inc()
    except Exception as e:
        logger.error("record_cache_operation_failed", error=str(e))


def update_cache_hit_ratio(ratio: float):
    """Update cache hit ratio metric."""
    try:
        cache_hit_ratio.set(ratio)
    except Exception as e:
        logger.error("update_cache_hit_ratio_failed", error=str(e))


def update_database_connections(count: int):
    """Update database connections metric."""
    try:
        database_connections_active.set(count)
    except Exception as e:
        logger.error("update_database_connections_failed", error=str(e))


def record_database_query(query_type: str, duration: float):
    """Record database query metric."""
    try:
        database_query_duration_seconds.labels(
            query_type=query_type
        ).observe(duration)
    except Exception as e:
        logger.error("record_database_query_failed", error=str(e))
