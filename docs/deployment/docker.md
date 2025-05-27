# Docker Deployment Guide

Complete guide for deploying the NLLB Translation System using Docker.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Basic Docker Deployment](#basic-docker-deployment)
4. [Docker Compose Deployment](#docker-compose-deployment)
5. [GPU Support](#gpu-support)
6. [Production Configuration](#production-configuration)
7. [Monitoring and Logging](#monitoring-and-logging)
8. [Maintenance](#maintenance)

## Overview

Docker deployment provides the easiest and most consistent way to run the NLLB Translation System. This guide covers both basic Docker usage and production-ready Docker Compose configurations.

### Benefits of Docker Deployment

- **Consistency**: Same environment across development, testing, and production
- **Isolation**: Dependencies and conflicts are contained
- **Scalability**: Easy to scale horizontally
- **Portability**: Runs on any Docker-compatible platform
- **GPU Support**: Simplified NVIDIA GPU integration

## Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 4 cores | 8+ cores |
| **RAM** | 8 GB | 16+ GB |
| **Storage** | 20 GB | 50+ GB SSD |
| **OS** | Linux, Windows 10/11, macOS | Ubuntu 22.04 LTS |

### Software Requirements

1. **Docker Engine** (20.10+)
   ```bash
   # Ubuntu/Debian
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   ```

2. **Docker Compose** (2.0+)
   ```bash
   # Usually included with Docker Desktop
   # Or install separately:
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

3. **NVIDIA Docker** (for GPU support)
   ```bash
   # Install NVIDIA Docker runtime
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   
   sudo apt-get update && sudo apt-get install -y nvidia-docker2
   sudo systemctl restart docker
   ```

### Verify Installation

```bash
# Check Docker version
docker --version
docker-compose --version

# Test Docker
docker run hello-world

# Test GPU support (if applicable)
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
```

## Basic Docker Deployment

### Build and Run

```bash
# Clone repository
git clone https://github.com/yourusername/tg-text-translate.git
cd tg-text-translate

# Build Docker image
docker build -t nllb-translator -f server/Dockerfile server/

# Run container
docker run -d \
  --name nllb-server \
  -p 8000:8000 \
  -e API_KEY=your-secret-api-key \
  -e MODEL_NAME=facebook/nllb-200-distilled-600M \
  nllb-translator
```

### Verify Deployment

```bash
# Check container status
docker ps

# Check logs
docker logs nllb-server

# Test API
curl http://localhost:8000/health
```

### Basic Configuration

```bash
# Environment variables
docker run -d \
  --name nllb-server \
  -p 8000:8000 \
  -e HOST=0.0.0.0 \
  -e PORT=8000 \
  -e API_KEY=your-secret-api-key \
  -e MODEL_NAME=facebook/nllb-200-distilled-600M \
  -e DEVICE=cpu \
  --restart unless-stopped \
  nllb-translator
```

## Docker Compose Deployment

### Basic Configuration

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  nllb-server:
    build:
      context: ./server
      dockerfile: Dockerfile
    container_name: nllb-translator
    ports:
      - "8000:8000"
    environment:
      - HOST=0.0.0.0
      - PORT=8000
      - API_KEY=${API_KEY}
      - MODEL_NAME=${MODEL_NAME:-facebook/nllb-200-distilled-600M}
      - DEVICE=${DEVICE:-cpu}
    volumes:
      - model_cache:/app/models
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

volumes:
  model_cache:
    driver: local
```

Create `.env` file:

```bash
# Server configuration
API_KEY=your-secret-api-key-here
MODEL_NAME=facebook/nllb-200-distilled-600M
DEVICE=cpu

# Optional: Advanced configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

### Deploy with Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Stop services
docker-compose down
```

### Production Configuration

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  nllb-server:
    build:
      context: ./server
      dockerfile: Dockerfile
    container_name: nllb-translator
    ports:
      - "127.0.0.1:8000:8000"  # Bind to localhost only
    environment:
      - HOST=0.0.0.0
      - PORT=8000
      - API_KEY=${API_KEY}
      - MODEL_NAME=${MODEL_NAME}
      - DEVICE=${DEVICE}
      - LOG_LEVEL=INFO
    volumes:
      - model_cache:/app/models
      - ./logs:/app/logs
      - /etc/localtime:/etc/localtime:ro
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s
    security_opt:
      - no-new-privileges:true
    user: "1000:1000"  # Run as non-root user

  nginx:
    image: nginx:alpine
    container_name: nllb-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    restart: unless-stopped
    depends_on:
      nllb-server:
        condition: service_healthy
    security_opt:
      - no-new-privileges:true

volumes:
  model_cache:
    driver: local
```

## GPU Support

### NVIDIA GPU Configuration

Update `docker-compose.yml` for GPU support:

```yaml
version: '3.8'

services:
  nllb-server:
    build:
      context: ./server
      dockerfile: Dockerfile.gpu  # Use GPU-optimized Dockerfile
    container_name: nllb-translator-gpu
    ports:
      - "8000:8000"
    environment:
      - HOST=0.0.0.0
      - PORT=8000
      - API_KEY=${API_KEY}
      - MODEL_NAME=${MODEL_NAME:-facebook/nllb-200-distilled-1.3B}
      - DEVICE=cuda
    volumes:
      - model_cache:/app/models
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    runtime: nvidia  # Alternative to deploy.resources

volumes:
  model_cache:
```

### GPU Dockerfile

Create `server/Dockerfile.gpu`:

```dockerfile
FROM nvidia/cuda:11.8-runtime-ubuntu22.04

# Install Python
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Create non-root user
RUN groupadd -r nllb && useradd -r -g nllb nllb

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/models /app/logs && \
    chown -R nllb:nllb /app

# Switch to non-root user
USER nllb

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["python3", "server.py"]
```

### Verify GPU Usage

```bash
# Check GPU is available in container
docker exec nllb-translator-gpu nvidia-smi

# Monitor GPU usage
watch -n 1 nvidia-smi

# Check model device in logs
docker logs nllb-translator-gpu | grep -i cuda
```

## Production Configuration

### Security Hardening

1. **Non-root User**
   ```dockerfile
   # In Dockerfile
   RUN groupadd -r nllb && useradd -r -g nllb nllb
   USER nllb
   ```

2. **Read-only Filesystem**
   ```yaml
   # In docker-compose.yml
   services:
     nllb-server:
       read_only: true
       tmpfs:
         - /tmp
         - /app/logs
   ```

3. **Security Options**
   ```yaml
   services:
     nllb-server:
       security_opt:
         - no-new-privileges:true
         - apparmor:docker-default
   ```

### Reverse Proxy Configuration

Create `nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream nllb_backend {
        server nllb-server:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
        ssl_prefer_server_ciphers off;

        # Rate limiting
        limit_req_zone $binary_remote_addr zone=api:10m rate=10r/m;

        location / {
            limit_req zone=api burst=5 nodelay;
            
            proxy_pass http://nllb_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        location /health {
            proxy_pass http://nllb_backend/health;
            access_log off;
        }
    }
}
```

### SSL Certificate Setup

```bash
# Using Let's Encrypt
docker run -it --rm \
  -v $(pwd)/nginx/ssl:/etc/letsencrypt \
  certbot/certbot certonly \
  --standalone \
  -d your-domain.com

# Copy certificates
cp nginx/ssl/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
cp nginx/ssl/live/your-domain.com/privkey.pem nginx/ssl/key.pem
```

## Monitoring and Logging

### Container Monitoring

```yaml
# Add to docker-compose.yml
services:
  nllb-server:
    # ... existing configuration
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    labels:
      - "com.docker.compose.service=nllb-server"
      - "monitoring=enabled"

  prometheus:
    image: prom/prometheus:latest
    container_name: nllb-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: nllb-grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=your-grafana-password
    restart: unless-stopped

volumes:
  grafana_data:
```

### Log Management

```bash
# View logs
docker-compose logs -f nllb-server

# Log rotation
docker run -d \
  --name logrotate \
  -v /var/lib/docker/containers:/var/lib/docker/containers:ro \
  -v $(pwd)/logrotate.conf:/etc/logrotate.conf \
  blacklabelops/logrotate
```

### Health Monitoring

```bash
# Create health check script
cat > health_check.sh << 'EOF'
#!/bin/bash
HEALTH_URL="http://localhost:8000/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL")

if [ "$RESPONSE" = "200" ]; then
    echo "$(date): Service healthy"
    exit 0
else
    echo "$(date): Service unhealthy (HTTP $RESPONSE)"
    # Optional: restart service
    # docker-compose restart nllb-server
    exit 1
fi
EOF

chmod +x health_check.sh

# Add to crontab
echo "*/5 * * * * /path/to/health_check.sh >> /var/log/nllb-health.log 2>&1" | crontab -
```

## Maintenance

### Backup Procedures

```bash
# Backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/nllb-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup configurations
cp -r docker-compose.yml .env nginx/ "$BACKUP_DIR/"

# Backup model cache
docker run --rm -v nllb_model_cache:/source -v "$BACKUP_DIR":/backup alpine \
  tar czf /backup/model_cache.tar.gz -C /source .

# Backup logs
cp -r logs/ "$BACKUP_DIR/"

echo "Backup completed: $BACKUP_DIR"
EOF

chmod +x backup.sh
```

### Updates and Upgrades

```bash
# Update containers
docker-compose pull
docker-compose up -d

# Or rebuild from source
docker-compose build --no-cache
docker-compose up -d

# Clean up old images
docker image prune -f
```

### Performance Tuning

```yaml
# docker-compose.yml performance settings
services:
  nllb-server:
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G
    environment:
      - OMP_NUM_THREADS=4
      - CUDA_VISIBLE_DEVICES=0
    ulimits:
      memlock:
        soft: -1
        hard: -1
```

## Troubleshooting

### Common Docker Issues

**ImportError: cannot import name 'deprecated' from 'typing_extensions'**

This error occurs with older Docker images that have incompatible `typing_extensions` versions.

```bash
# Solution: Force rebuild with updated dependencies
docker compose build --no-cache nllb-server
docker compose down
docker compose up -d
```

**PermissionError: [Errno 13] Permission denied writing to cache directories**

Fixed in recent versions by setting proper cache environment variables.

```bash
# If still occurring, manually set cache permissions:
docker exec -it nllb-server chown -R nllb:nllb /app/.cache
```

**ImportError: Using `low_cpu_mem_usage=True` requires Accelerate**

The `accelerate` library is now included in requirements. Update to latest version:

```bash
git pull origin main
docker compose build --no-cache nllb-server
```

**Container exits during model loading**

Insufficient memory or storage space:

```bash
# Check available resources
docker system df
docker stats

# Increase Docker memory limits or free up space
docker system prune -a
```

### Troubleshooting Commands

```bash
# Container debugging
docker exec -it nllb-server bash

# Monitor startup logs
docker compose logs -f nllb-server

# Resource usage
docker stats nllb-server

# System events
docker events --filter container=nllb-server

# Container inspection
docker inspect nllb-server

# Network troubleshooting
docker network ls
docker network inspect bridge

# Health check
curl -X GET http://localhost:8000/health
```

## Multi-Environment Setup

### Development
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Staging
```bash
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d
```

### Production
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Next Steps

- [Production Deployment](./production.md) - Advanced production setup
- [Monitoring Guide](./monitoring.md) - Comprehensive monitoring setup
- [Troubleshooting](./troubleshooting.md) - Common issues and solutions
- [Performance Tuning](../development/performance.md) - Optimization techniques