"""
Database initialization script for PostgreSQL.
"""

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS brightedge;

-- Use the database
\c brightedge;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Core URL metadata table
CREATE TABLE IF NOT EXISTS page_metadata (
    id BIGSERIAL PRIMARY KEY,
    crawl_id UUID NOT NULL DEFAULT uuid_generate_v4(),
    url VARCHAR(2048) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    title TEXT,
    description TEXT,
    keywords JSONB DEFAULT '[]',
    author VARCHAR(255),
    published_date TIMESTAMP WITH TIME ZONE,
    canonical_url VARCHAR(2048),
    language VARCHAR(10),
    content_type VARCHAR(50) DEFAULT 'text/html',
    word_count INTEGER DEFAULT 0,
    images JSONB DEFAULT '[]',
    links JSONB DEFAULT '[]',
    topics JSONB DEFAULT '[]',
    headers JSONB DEFAULT '{}',
    content_hash VARCHAR(64),
    response_time_ms INTEGER DEFAULT 0,
    status_code INTEGER,
    crawl_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Crawl queue table
CREATE TABLE IF NOT EXISTS crawl_queue (
    id BIGSERIAL PRIMARY KEY,
    crawl_id UUID NOT NULL DEFAULT uuid_generate_v4(),
    url VARCHAR(2048) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    priority INTEGER DEFAULT 5,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    crawl_delay DECIMAL(5,2) DEFAULT 1.0,
    respect_robots_txt BOOLEAN DEFAULT TRUE,
    user_agent VARCHAR(255),
    headers JSONB DEFAULT '{}',
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Crawl history table for analytics
CREATE TABLE IF NOT EXISTS crawl_history (
    id BIGSERIAL PRIMARY KEY,
    crawl_id UUID NOT NULL,
    url VARCHAR(2048) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    error_message TEXT,
    crawl_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Domain rate limiting table
CREATE TABLE IF NOT EXISTS domain_rate_limits (
    id BIGSERIAL PRIMARY KEY,
    domain VARCHAR(255) NOT NULL UNIQUE,
    crawl_delay DECIMAL(5,2) DEFAULT 1.0,
    max_concurrent INTEGER DEFAULT 1,
    robots_txt_url VARCHAR(2048),
    robots_txt_content TEXT,
    robots_txt_updated_at TIMESTAMP WITH TIME ZONE,
    last_crawl_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_page_metadata_url ON page_metadata(url);
CREATE INDEX IF NOT EXISTS idx_page_metadata_domain ON page_metadata(domain);
CREATE INDEX IF NOT EXISTS idx_page_metadata_crawl_timestamp ON page_metadata(crawl_timestamp);
CREATE INDEX IF NOT EXISTS idx_page_metadata_topics ON page_metadata USING GIN(topics);
CREATE INDEX IF NOT EXISTS idx_page_metadata_keywords ON page_metadata USING GIN(keywords);
CREATE INDEX IF NOT EXISTS idx_page_metadata_content_hash ON page_metadata(content_hash);
CREATE INDEX IF NOT EXISTS idx_page_metadata_crawl_id ON page_metadata(crawl_id);

CREATE INDEX IF NOT EXISTS idx_crawl_queue_status ON crawl_queue(status);
CREATE INDEX IF NOT EXISTS idx_crawl_queue_priority ON crawl_queue(priority DESC);
CREATE INDEX IF NOT EXISTS idx_crawl_queue_scheduled_at ON crawl_queue(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_crawl_queue_domain ON crawl_queue(domain);
CREATE INDEX IF NOT EXISTS idx_crawl_queue_crawl_id ON crawl_queue(crawl_id);

CREATE INDEX IF NOT EXISTS idx_crawl_history_crawl_timestamp ON crawl_history(crawl_timestamp);
CREATE INDEX IF NOT EXISTS idx_crawl_history_domain ON crawl_history(domain);
CREATE INDEX IF NOT EXISTS idx_crawl_history_status ON crawl_history(status);

CREATE INDEX IF NOT EXISTS idx_domain_rate_limits_domain ON domain_rate_limits(domain);
CREATE INDEX IF NOT EXISTS idx_domain_rate_limits_last_crawl_at ON domain_rate_limits(last_crawl_at);

-- Full text search index
CREATE INDEX IF NOT EXISTS idx_page_metadata_title_desc_fts ON page_metadata 
USING GIN(to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(description, '')));

-- Trigger to update updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_page_metadata_updated_at 
    BEFORE UPDATE ON page_metadata 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_crawl_queue_updated_at 
    BEFORE UPDATE ON crawl_queue 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_domain_rate_limits_updated_at 
    BEFORE UPDATE ON domain_rate_limits 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to extract domain from URL
CREATE OR REPLACE FUNCTION extract_domain(url TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN regexp_replace(
        regexp_replace(url, '^https?://', ''),
        '/.*$', ''
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to clean old crawl history (for maintenance)
CREATE OR REPLACE FUNCTION clean_old_crawl_history(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM crawl_history 
    WHERE crawl_timestamp < NOW() - INTERVAL '%s days' 
    AND status IN ('completed', 'failed');
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
