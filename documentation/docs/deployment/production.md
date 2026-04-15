# Production Deployment

Best practices for deploying dgbit in production.

## Architecture Overview

```
                    Internet
                        │
                        ▼
                ┌───────────────┐
                │   Cloudflare  │  (DDoS protection, CDN)
                └───────────────┘
                        │
                        ▼
                ┌───────────────┐
                │    nginx      │  (TLS termination, rate limiting)
                └───────────────┘
                        │
           ┌────────────┼────────────┐
           ▼            ▼            ▼
      ┌─────────┐  ┌─────────┐  ┌─────────┐
      │   API   │  │   API   │  │   UI    │
      │  :8000  │  │  :8001  │  │  :3000  │
      └─────────┘  └─────────┘  └─────────┘
           │            │
           └──────┬─────┘
                  ▼
           ┌─────────────┐
           │  Workers    │
           │ (scaling)   │
           └─────────────┘
```

## Security

### TLS/HTTPS

Always use HTTPS in production:

```nginx
# /etc/nginx/sites-available/dgbit
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### API Key Management

Never put API keys in code or docker-compose files:

```bash
# Use Docker secrets
echo "your_api_key" | docker secret create bybit_api_key -
echo "your_api_secret" | docker secret create bybit_api_secret -
```

Or use environment files with restricted permissions:

```bash
chmod 600 .env
```

### Rate Limiting

Implement rate limiting in nginx:

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

server {
    location /api {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://localhost:8000;
    }
}
```

### Firewall

Only expose necessary ports:

```bash
# UFW example
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

## High Availability

### Load Balancing

Use nginx as a load balancer:

```nginx
upstream dgbit_api {
    least_conn;
    server api1:8000 weight=5;
    server api2:8000 weight=5;
    server api3:8000 backup;
}

server {
    location /api {
        proxy_pass http://dgbit_api;
    }
}
```

### Database Replication

For SQLite, use periodic backups. For production scale, consider PostgreSQL:

```yaml
# docker-compose.production.yml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: dgbit
      POSTGRES_USER: dgbit
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    volumes:
      - postgres-data:/var/lib/postgresql/data
```

### Health Checks

Implement robust health checks:

```yaml
services:
  api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## Performance

### Resource Allocation

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### Connection Pooling

Configure uvicorn for production:

```bash
uvicorn dgbit_api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --loop uvloop \
    --http httptools
```

### Caching

Implement caching for frequently accessed data:

```python
from functools import lru_cache
import redis

redis_client = redis.Redis(host='redis', port=6379)

def get_cached_klines(symbol: str, interval: str) -> dict:
    key = f"klines:{symbol}:{interval}"
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)
    
    data = fetch_klines(symbol, interval)
    redis_client.setex(key, 60, json.dumps(data))
    return data
```

## Monitoring

See [Monitoring Guide](monitoring.md) for detailed setup.

### Essential Metrics

- API response times
- Error rates
- Worker queue depth
- Memory/CPU usage
- Trade execution latency

### Alerting

Set up alerts for:

- API errors > 1%
- Response time > 500ms
- Worker queue > 100 jobs
- Memory usage > 80%

## Backup Strategy

### Database Backups

```bash
#!/bin/bash
# /opt/dgbit/backup.sh
BACKUP_DIR=/backups/dgbit
DATE=$(date +%Y%m%d_%H%M%S)

# Backup SQLite
docker cp dgbit-api:/app/db/dgbit.db $BACKUP_DIR/dgbit_$DATE.db

# Compress
gzip $BACKUP_DIR/dgbit_$DATE.db

# Keep last 7 days
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete
```

Add to crontab:

```bash
0 */6 * * * /opt/dgbit/backup.sh
```

### Reports Backup

```bash
# Sync reports to S3
aws s3 sync /app/reports s3://your-bucket/dgbit-reports/
```

## Deployment Checklist

Before going live:

- [ ] TLS certificates installed
- [ ] API keys secured (secrets/env files)
- [ ] Firewall configured
- [ ] Rate limiting enabled
- [ ] Health checks configured
- [ ] Logging configured
- [ ] Monitoring set up
- [ ] Alerts configured
- [ ] Backup strategy implemented
- [ ] Tested failover scenarios
- [ ] Documented runbooks

## Rollback Plan

Maintain ability to rollback:

```bash
# Tag current version before update
docker tag cryptuon/dgbit:latest cryptuon/dgbit:rollback-$(date +%Y%m%d)

# Deploy new version
docker-compose pull
docker-compose up -d

# If issues, rollback
docker-compose down
docker tag cryptuon/dgbit:rollback-20240115 cryptuon/dgbit:latest
docker-compose up -d
```

## Maintenance Windows

Schedule maintenance during low-activity periods:

```bash
#!/bin/bash
# maintenance.sh

# Notify users (if applicable)
# ...

# Stop workers gracefully
docker-compose stop backtest-worker

# Perform maintenance
docker-compose pull
docker-compose up -d

# Verify health
sleep 30
curl -f http://localhost:8000/api/health || exit 1

echo "Maintenance complete"
```
