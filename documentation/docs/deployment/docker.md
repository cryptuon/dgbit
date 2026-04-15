# Docker Deployment

Deploy dgbit using Docker and docker-compose.

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 2GB+ RAM available

## Quick Start

```bash
# Clone repository
git clone https://github.com/cryptuon/dgbit.git
cd dgbit

# Configure environment
cp dgbit-api/.env.example dgbit-api/.env
nano dgbit-api/.env  # Edit with your settings

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

## Services

The docker-compose.yml defines these services:

| Service | Description | Port |
|---------|-------------|------|
| `api` | FastAPI REST API | 8000 |
| `backtest-worker` | Background job processor | - |
| `ui` | Vue 3 frontend | 3000 |
| `data-service` | Market data provider | - |

## Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```env
# Required for live trading
BYBIT_API_KEY=your_api_key
BYBIT_API_SECRET=your_api_secret
BYBIT_TESTNET=true

# Application settings
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### docker-compose.yml

The default configuration:

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
    volumes:
      - dgbit-db:/app/db
      - dgbit-reports:/app/reports
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Building Images

### Build All Services

```bash
docker-compose build
```

### Build Specific Service

```bash
docker-compose build api
```

### Build with No Cache

```bash
docker-compose build --no-cache
```

## Running Services

### Start All Services

```bash
docker-compose up -d
```

### Start Specific Services

```bash
# API only
docker-compose up -d api

# API + worker
docker-compose up -d api backtest-worker
```

### Start with Full Stack

```bash
docker-compose --profile full up -d
```

This includes the UI and data-service.

## Viewing Logs

### All Services

```bash
docker-compose logs -f
```

### Specific Service

```bash
docker-compose logs -f api
```

### Last N Lines

```bash
docker-compose logs --tail=100 api
```

## Stopping Services

### Stop All

```bash
docker-compose down
```

### Stop and Remove Volumes

```bash
docker-compose down -v
```

### Stop Specific Service

```bash
docker-compose stop api
```

## Scaling Workers

Scale the backtest worker for more throughput:

```bash
docker-compose up -d --scale backtest-worker=3
```

## Volumes

Data persistence is handled through Docker volumes:

| Volume | Purpose |
|--------|---------|
| `dgbit-db` | SQLite database |
| `dgbit-reports` | Backtest HTML reports |
| `dgbit-logs` | Application logs |
| `dgbit-ipc` | NNG IPC sockets |

### Backup Volumes

```bash
# Backup database
docker run --rm -v dgbit-db:/data -v $(pwd):/backup alpine \
    tar cvf /backup/dgbit-db-backup.tar /data

# Restore
docker run --rm -v dgbit-db:/data -v $(pwd):/backup alpine \
    tar xvf /backup/dgbit-db-backup.tar -C /
```

## Health Checks

The API service includes health checks:

```bash
# Check container health
docker-compose ps

# Manual health check
curl http://localhost:8000/api/health
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs api

# Check container status
docker-compose ps -a

# Inspect container
docker inspect dgbit-api
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Use different port
docker-compose up -d -e API_PORT=8001
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Limit memory per container
# In docker-compose.yml:
services:
  api:
    deploy:
      resources:
        limits:
          memory: 1G
```

### Permissions Issues

```bash
# Fix volume permissions
docker-compose down
sudo chown -R $(id -u):$(id -g) ./data
docker-compose up -d
```

## Production Recommendations

1. **Use secrets management** - Don't put API keys in docker-compose.yml
2. **Enable TLS** - Use a reverse proxy (nginx, traefik)
3. **Set resource limits** - Prevent runaway containers
4. **Configure logging** - Ship logs to central system
5. **Regular backups** - Backup volumes regularly

### Example Production docker-compose.yml

```yaml
services:
  api:
    image: cryptuon/dgbit:0.1.0
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=WARNING
    secrets:
      - bybit_api_key
      - bybit_api_secret
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

secrets:
  bybit_api_key:
    external: true
  bybit_api_secret:
    external: true
```

## Next Steps

- [Production Guide](production.md) - Full production setup
- [Monitoring](monitoring.md) - Set up monitoring
