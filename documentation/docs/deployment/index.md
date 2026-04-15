# Deployment

Deploy dgbit for production use.

<div class="grid cards" markdown>

-   :material-docker:{ .lg .middle } **Docker**

    ---

    Deploy with Docker and docker-compose

    [:octicons-arrow-right-24: Docker Guide](docker.md)

-   :material-server:{ .lg .middle } **Production**

    ---

    Production deployment best practices

    [:octicons-arrow-right-24: Production Guide](production.md)

-   :material-chart-box:{ .lg .middle } **Monitoring**

    ---

    Monitor your dgbit deployment

    [:octicons-arrow-right-24: Monitoring Guide](monitoring.md)

</div>

## Deployment Options

| Method | Best For | Complexity |
|--------|----------|------------|
| Docker Compose | Single server, development | Low |
| Kubernetes | Production, scaling | High |
| Bare Metal | Maximum control | Medium |

## Quick Start

The fastest way to deploy dgbit:

```bash
# Clone repository
git clone https://github.com/cryptuon/dgbit.git
cd dgbit

# Configure environment
cp dgbit-api/.env.example dgbit-api/.env
# Edit .env with your settings

# Start services
docker-compose up -d

# Check status
docker-compose ps
```
