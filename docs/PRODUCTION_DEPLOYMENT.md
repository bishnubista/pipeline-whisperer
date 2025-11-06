# Production Deployment Guide

Complete guide for deploying Pipeline Whisperer to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Configuration](#configuration)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Database Setup](#database-setup)
6. [Monitoring](#monitoring)
7. [Backup & Recovery](#backup--recovery)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **CPU**: 4+ cores recommended
- **RAM**: 8GB+ recommended
- **Storage**: 50GB+ for application and databases
- **OS**: Ubuntu 20.04+, Debian 11+, or compatible Linux distribution

### Software Dependencies

- Docker 24.0+ and Docker Compose 2.20+
- PostgreSQL 15+ (for production database)
- Redis 7+ (for caching)
- SSL certificates (for HTTPS)

### External Services

- OpenAI API key
- Lightfield CRM API key
- Truefoundry API key
- Sentry DSN (optional but recommended)

## Configuration

### 1. Environment Variables

Copy the production environment template:

```bash
cp .env.production.example .env.production
```

Edit `.env.production` with your values:

```bash
# Security - REQUIRED
API_KEYS=your-secure-api-key-here
POSTGRES_PASSWORD=your-strong-password-here
REDIS_PASSWORD=your-redis-password-here

# Database - REQUIRED
DATABASE_URL=postgresql://pipeline:${POSTGRES_PASSWORD}@postgres:5432/pipeline_whisperer

# External Services - REQUIRED
OPENAI_API_KEY=sk-...
LIGHTFIELD_API_KEY=lf_...
TRUEFOUNDRY_API_KEY=tf_...

# Monitoring - RECOMMENDED
SENTRY_DSN_PYTHON=https://...@sentry.io/...
SENTRY_ENVIRONMENT=production

# Performance Tuning
WORKER_COUNT=4
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=5000
```

### 2. Security Configuration

Enable API key authentication:

```bash
API_KEY_REQUIRED=true
API_KEYS=key1,key2,key3  # Comma-separated list
```

Generate secure API keys:

```bash
openssl rand -hex 32
```

### 3. CORS Configuration

Configure allowed origins:

```bash
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

## Docker Deployment

### Quick Start

```bash
# 1. Build images
docker-compose -f docker-compose.production.yml build

# 2. Start services
docker-compose -f docker-compose.production.yml up -d

# 3. Run database migrations
docker-compose -f docker-compose.production.yml exec agent-api alembic upgrade head

# 4. Verify health
curl http://localhost:8000/health/detailed
```

### Production Best Practices

1. **Use external databases**: Don't run PostgreSQL/Redis in containers for production
2. **Enable health checks**: All services have health check configurations
3. **Set resource limits**: Configure memory and CPU limits in docker-compose.yml
4. **Use secrets management**: Store sensitive data in Docker secrets or external vault

### Scaling with Docker

```bash
# Scale API workers
docker-compose -f docker-compose.production.yml up -d --scale agent-api=3

# View logs
docker-compose -f docker-compose.production.yml logs -f agent-api
```

## Kubernetes Deployment

### 1. Create Namespace

```bash
kubectl create namespace pipeline-whisperer
```

### 2. Create Secrets

```bash
kubectl create secret generic pipeline-secrets \
  --from-literal=postgres-password=your-password \
  --from-literal=redis-password=your-password \
  --from-literal=openai-api-key=sk-... \
  --from-literal=api-keys=key1,key2 \
  -n pipeline-whisperer
```

### 3. Deploy Services

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/ -n pipeline-whisperer

# Check deployment status
kubectl get pods -n pipeline-whisperer
kubectl get services -n pipeline-whisperer
```

### 4. Configure Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: pipeline-whisperer
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.yourdomain.com
    secretName: pipeline-tls
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: agent-api
            port:
              number: 8000
```

### 5. Horizontal Pod Autoscaling

```bash
kubectl autoscale deployment agent-api \
  --cpu-percent=70 \
  --min=2 \
  --max=10 \
  -n pipeline-whisperer
```

## Database Setup

### PostgreSQL Production Configuration

```sql
-- Create database
CREATE DATABASE pipeline_whisperer;

-- Create user
CREATE USER pipeline WITH PASSWORD 'your-secure-password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE pipeline_whisperer TO pipeline;

-- Enable extensions
\c pipeline_whisperer
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
```

### Run Migrations

```bash
# Using Docker
docker-compose -f docker-compose.production.yml exec agent-api alembic upgrade head

# Using Kubernetes
kubectl exec -it deployment/agent-api -n pipeline-whisperer -- alembic upgrade head
```

### Database Indexes (Performance)

```sql
-- Add indexes for common queries
CREATE INDEX idx_leads_score ON leads(score);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_created_at ON leads(created_at);
CREATE INDEX idx_outreach_logs_lead_id ON outreach_logs(lead_id);
CREATE INDEX idx_experiments_variant_type ON experiments(variant_type);
```

## Monitoring

### Health Checks

Pipeline Whisperer provides multiple health check endpoints:

- `/health/liveness` - Container is alive
- `/health/readiness` - Service is ready for traffic
- `/health/startup` - Service has started successfully
- `/health/detailed` - Comprehensive system status

### Sentry Integration

Configure Sentry for error tracking:

```bash
SENTRY_DSN_PYTHON=https://...@sentry.io/...
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% of transactions
```

### Prometheus Metrics

Expose metrics for Prometheus:

```python
# Custom metrics endpoint at /metrics
from prometheus_client import Counter, Histogram

request_count = Counter('api_requests_total', 'Total API requests')
request_duration = Histogram('api_request_duration_seconds', 'Request duration')
```

### Logging

Structured JSON logs are automatically generated:

```bash
# View logs in real-time
docker-compose -f docker-compose.production.yml logs -f agent-api

# Export logs to file
docker-compose -f docker-compose.production.yml logs agent-api > api.log
```

## Backup & Recovery

### Automated Backups

Set up daily backups with cron:

```bash
# Add to crontab
0 2 * * * /path/to/pipeline-whisperer/scripts/backup_database.sh

# With environment variables
0 2 * * * BACKUP_DIR=/backups RETENTION_DAYS=30 /path/to/scripts/backup_database.sh
```

### Manual Backup

```bash
# Create backup
./scripts/backup_database.sh

# Backups are stored in ./backups/ directory
ls -lh backups/
```

### Restore from Backup

```bash
# Restore specific backup
./scripts/restore_database.sh backups/pipeline_postgres_20250106_120000.sql.gz

# Warning: This will replace the current database!
```

### Backup to S3

```bash
# Install AWS CLI
apt-get install awscli

# Upload to S3
aws s3 sync ./backups/ s3://your-bucket/pipeline-backups/ \
  --storage-class GLACIER \
  --exclude "*" --include "*.gz"
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

```bash
# Check database is running
docker-compose ps postgres

# Check connection
psql -h localhost -U pipeline -d pipeline_whisperer

# View logs
docker-compose logs postgres
```

#### 2. Redis Connection Failed

```bash
# Test Redis connection
redis-cli -h localhost -p 6379 -a your-password ping

# View Redis logs
docker-compose logs redis
```

#### 3. API Returns 503

```bash
# Check health endpoints
curl http://localhost:8000/health/detailed

# Check logs for errors
docker-compose logs agent-api | grep ERROR

# Restart service
docker-compose restart agent-api
```

#### 4. High Memory Usage

```bash
# Check resource usage
docker stats

# Reduce worker count
# In .env.production:
WORKER_COUNT=2
DB_POOL_SIZE=10
```

### Performance Optimization

1. **Enable Redis caching**:
   ```bash
   REDIS_ENABLED=true
   CACHE_TTL_SECONDS=600
   ```

2. **Tune database connection pool**:
   ```bash
   DB_POOL_SIZE=20
   DB_MAX_OVERFLOW=10
   DB_POOL_RECYCLE=3600
   ```

3. **Enable compression**:
   ```bash
   ENABLE_COMPRESSION=true
   ```

4. **Increase rate limits for production**:
   ```bash
   RATE_LIMIT_PER_MINUTE=200
   RATE_LIMIT_PER_HOUR=10000
   ```

### Security Hardening

1. **Enable HTTPS only**:
   ```bash
   ENABLE_HTTPS=true
   ```

2. **Rotate API keys regularly**:
   ```bash
   # Generate new key
   NEW_KEY=$(openssl rand -hex 32)

   # Add to API_KEYS (keep old keys temporarily)
   API_KEYS=old-key,${NEW_KEY}

   # After migration, remove old key
   API_KEYS=${NEW_KEY}
   ```

3. **Update dependencies**:
   ```bash
   # Update Python packages
   uv pip list --outdated
   uv pip install -U package-name

   # Update Docker images
   docker-compose pull
   ```

## Load Testing

Test system performance before going live:

```bash
# Install k6
curl https://github.com/grafana/k6/releases/download/v0.48.0/k6-v0.48.0-linux-amd64.tar.gz | tar xvz
sudo mv k6 /usr/local/bin/

# Run load test
k6 run k6-load-test.js

# Expected results:
# - 1000+ req/sec without errors
# - p95 latency < 200ms
# - 0% error rate
```

## Production Checklist

Before going live, verify:

- [ ] All environment variables configured
- [ ] Database migrations applied
- [ ] SSL certificates installed
- [ ] API keys rotated from defaults
- [ ] Sentry configured and receiving events
- [ ] Health checks passing
- [ ] Backups automated and tested
- [ ] Rate limits configured
- [ ] CORS origins restricted
- [ ] Logs being collected
- [ ] Monitoring dashboards setup
- [ ] Documentation updated
- [ ] Team trained on runbooks
- [ ] Rollback plan documented

## Support

For issues or questions:

- GitHub Issues: https://github.com/your-org/pipeline-whisperer/issues
- Documentation: https://docs.pipeline-whisperer.com
- Email: support@pipeline-whisperer.com

---

**Last Updated**: 2025-01-06
**Version**: 0.2.0
**Maintained By**: Pipeline Whisperer Team
