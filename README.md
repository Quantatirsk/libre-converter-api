# libre-converter-api

A production-ready document conversion API service built on LibreOffice, packaged as a minimal Docker container with multi-process async capabilities.

## Features

- **Multi-format Support**: DOC, DOCX, XLS, XLSX, PPT, PPTX, PDF, ODF, CSV, RTF, HTML, TXT
- **Chinese Font Support**: 27 bundled Chinese fonts for proper Chinese rendering
- **Multi-architecture**: Supports both `linux/amd64` and `linux/arm64` (Apple Silicon)
- **Production Ready**: Gunicorn + Uvicorn workers, JSON logging, metrics
- **Optional Authentication**: Bearer token auth controlled via environment
- **Resource Limits**: Configurable file size, concurrency, and timeout limits

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/Quantatirsk/libre-converter-api.git
cd libre-converter-api

# Configure environment
cp .env.example .env
# Edit .env as needed

# Start the service
docker-compose up -d
```

### Using Docker

```bash
# Run without authentication
docker run -d -p 28001:28001 quantatrisk/libre-converter-api:latest

# Run with authentication
docker run -d -p 28001:28001 \
  -e API_AUTH_ENABLED=true \
  -e API_AUTH_TOKEN=your-secret-token \
  quantatrisk/libre-converter-api:latest
```

## API Usage

### Health Check

```bash
curl http://localhost:28001/health
```

### List Supported Formats

```bash
curl http://localhost:28001/formats
```

### Convert Document

```bash
# DOCX to PDF
curl -X POST "http://localhost:28001/convert?to=pdf" \
  -F "file=@document.docx" \
  -o document.pdf

# With authentication
curl -X POST "http://localhost:28001/convert?to=pdf" \
  -H "Authorization: Bearer your-token" \
  -F "file=@document.docx" \
  -o document.pdf
```

## Supported Conversions

| Input | Output Options |
|-------|---------------|
| doc, docx, odt, rtf | doc, docx, pdf, odt, txt, rtf, html |
| xls, xlsx, ods, csv | xls, xlsx, pdf, ods, csv |
| ppt, pptx, odp | ppt, pptx, pdf, odp |

## Configuration

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

## Building

```bash
# Build and push multi-architecture image
./build.sh

# Build with custom tag
./build.sh v1.0.0
```

## Documentation

- [Design Document](docs/DESIGN.md) - Architecture and design decisions
- [Deployment Guide](docs/DEPLOYMENT.md) - Detailed deployment instructions

## License

MIT
