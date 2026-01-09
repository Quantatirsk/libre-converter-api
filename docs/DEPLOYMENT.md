# libre-convert-api Deployment Guide

## Quick Start

```bash
# Clone and build
docker build -t libre-convert-api .

# Run with default settings (no auth)
docker run -d -p 28001:28001 libre-convert-api

# Run with authentication
docker run -d -p 28001:28001 \
  -e API_AUTH_ENABLED=true \
  -e API_AUTH_TOKEN=your-secret-token \
  libre-convert-api
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_AUTH_ENABLED` | `false` | Enable Bearer token authentication |
| `API_AUTH_TOKEN` | `""` | Secret token for authentication |
| `API_PORT` | `28001` | Server port |
| `API_WORKERS` | `auto` | Worker count (auto = CPU cores) |
| `API_TIMEOUT` | `300` | Request timeout in seconds |
| `API_MAX_FILE_SIZE` | `524288000` | Max upload size (500MB) |
| `API_MAX_CONCURRENT` | `10` | Max concurrent conversions |
| `LOG_LEVEL` | `info` | Log level (debug/info/warning/error) |
| `LOG_FORMAT` | `json` | Log format (json/text) |

### .env File

```bash
# Authentication
API_AUTH_ENABLED=true
API_AUTH_TOKEN=your-secret-token-here

# Performance
API_WORKERS=4
API_TIMEOUT=300
API_MAX_CONCURRENT=10

# Limits
API_MAX_FILE_SIZE=524288000

# Logging
LOG_LEVEL=info
LOG_FORMAT=json
```

## Docker Compose

```yaml
version: '3.8'

services:
  libre-convert-api:
    build: .
    image: libre-convert-api:latest
    container_name: libre-convert-api
    ports:
      - "28001:28001"
    env_file:
      - .env
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 1G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:28001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

## API Usage

### Health Check

```bash
curl http://localhost:28001/health
# {"status":"ok"}
```

### List Formats

```bash
# Without auth
curl http://localhost:28001/formats

# With auth
curl -H "Authorization: Bearer your-token" \
     http://localhost:28001/formats
```

### Convert Document

```bash
# DOC to PDF
curl -X POST "http://localhost:28001/convert?to=pdf" \
     -H "Authorization: Bearer your-token" \
     -F "file=@document.doc" \
     -o document.pdf

# XLSX to CSV
curl -X POST "http://localhost:28001/convert?to=csv" \
     -H "Authorization: Bearer your-token" \
     -F "file=@spreadsheet.xlsx" \
     -o spreadsheet.csv

# PPTX to PDF
curl -X POST "http://localhost:28001/convert?to=pdf" \
     -H "Authorization: Bearer your-token" \
     -F "file=@presentation.pptx" \
     -o presentation.pdf
```

## Production Deployment

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: libre-convert-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: libre-convert-api
  template:
    metadata:
      labels:
        app: libre-convert-api
    spec:
      containers:
      - name: libre-convert-api
        image: libre-convert-api:latest
        ports:
        - containerPort: 28001
        env:
        - name: API_AUTH_ENABLED
          value: "true"
        - name: API_AUTH_TOKEN
          valueFrom:
            secretKeyRef:
              name: libre-convert-secret
              key: token
        resources:
          requests:
            memory: "1Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "4"
        livenessProbe:
          httpGet:
            path: /health
            port: 28001
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 28001
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: libre-convert-api
spec:
  selector:
    app: libre-convert-api
  ports:
  - port: 28001
    targetPort: 28001
```

### Behind Nginx

```nginx
upstream libre_convert {
    server 127.0.0.1:28001;
    keepalive 32;
}

server {
    listen 80;
    server_name convert.example.com;

    client_max_body_size 500M;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;

    location / {
        proxy_pass http://libre_convert;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Connection "";
    }
}
```

## Monitoring

### Metrics in Logs

Each conversion logs:
```json
{
  "timestamp": "2024-01-09T15:30:00.000Z",
  "level": "info",
  "event": "conversion_complete",
  "input_format": "docx",
  "output_format": "pdf",
  "input_size_bytes": 1048576,
  "output_size_bytes": 524288,
  "duration_ms": 1523,
  "client_ip": "192.168.1.100"
}
```

### Prometheus (Optional)

Add to your scrape config:
```yaml
scrape_configs:
  - job_name: 'libre-convert-api'
    static_configs:
      - targets: ['localhost:28001']
    metrics_path: /metrics
```

## Troubleshooting

### Common Issues

**1. Conversion returns 500**
```bash
# Check LibreOffice installation
docker exec -it libre-convert-api libreoffice --version
```

**2. Chinese characters show as boxes**
```bash
# Verify fonts are installed
docker exec -it libre-convert-api fc-list :lang=zh
```

**3. High memory usage**
- Reduce `API_MAX_CONCURRENT`
- Add memory limits to container

**4. Slow conversions**
- Increase worker count
- Use SSD for container storage
- Pre-warm LibreOffice with dummy conversion

### Debug Mode

```bash
docker run -it -p 28001:28001 \
  -e LOG_LEVEL=debug \
  -e LOG_FORMAT=text \
  libre-convert-api
```

## Security Recommendations

1. **Always enable auth in production**
   ```bash
   API_AUTH_ENABLED=true
   API_AUTH_TOKEN=$(openssl rand -hex 32)
   ```

2. **Run behind reverse proxy**
   - TLS termination
   - Rate limiting
   - IP allowlisting

3. **Use read-only filesystem**
   ```bash
   docker run --read-only \
     --tmpfs /tmp:rw,noexec,nosuid \
     libre-convert-api
   ```

4. **Non-root user** (already configured in Dockerfile)

## Build Options

### Custom Font Bundle

Replace `zhFonts.zip` before building:
```bash
cp /path/to/your/fonts.zip zhFonts.zip
docker build -t libre-convert-api .
```

### Exclude Components

For smaller image without presentations:
```dockerfile
# In Dockerfile, remove:
# RUN apt-get install libreoffice-impress
```
