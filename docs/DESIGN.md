# libre-convert-api Design Document

## Overview

A production-ready document conversion service built on LibreOffice, packaged as a minimal Docker container with multi-process async API capabilities.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Container                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Gunicorn (Master)                       │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐            │    │
│  │  │ Uvicorn  │ │ Uvicorn  │ │ Uvicorn  │  ... (N)   │    │
│  │  │ Worker 1 │ │ Worker 2 │ │ Worker 3 │            │    │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘            │    │
│  │       │            │            │                   │    │
│  │       └────────────┼────────────┘                   │    │
│  │                    ▼                                │    │
│  │           ┌────────────────┐                        │    │
│  │           │   FastAPI App  │                        │    │
│  │           │  - /convert    │                        │    │
│  │           │  - /formats    │                        │    │
│  │           │  - /health     │                        │    │
│  │           └───────┬────────┘                        │    │
│  │                   │                                 │    │
│  │                   ▼                                 │    │
│  │           ┌────────────────┐                        │    │
│  │           │  LibreOffice   │                        │    │
│  │           │  (headless)    │                        │    │
│  │           └────────────────┘                        │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Chinese Fonts│  │  Temp Dir    │  │  Semaphore   │       │
│  │ (27 fonts)   │  │  /tmp/...    │  │  (10 slots)  │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. LibreOffice Runtime

Minimal installation with only required components:

| Package | Size | Purpose |
|---------|------|---------|
| libreoffice-core | ~150MB | Core conversion engine |
| libreoffice-writer | ~20MB | DOC, DOCX, ODT, RTF, TXT, HTML |
| libreoffice-calc | ~15MB | XLS, XLSX, ODS, CSV |
| libreoffice-impress | ~15MB | PPT, PPTX, ODP |

### 2. Chinese Font Bundle

27 fonts (~220MB) including:
- SimHei (黑体)
- SimSun (宋体)
- Microsoft YaHei (微软雅黑)
- KaiTi (楷体)
- FangSong (仿宋)
- STSong, STKaiti, STFangsong (华文系列)

### 3. FastAPI Application

```python
# Core endpoints
POST /convert?to=<format>  # Convert document
GET  /formats              # List supported formats
GET  /health               # Health check (no auth)
```

### 4. Process Model

```
Gunicorn Master
    │
    ├── Uvicorn Worker 1 (async)
    ├── Uvicorn Worker 2 (async)
    ├── Uvicorn Worker 3 (async)
    └── Uvicorn Worker N (async)

Workers = CPU cores (auto-detected)
```

## Supported Conversions

### Document Formats
| Input | Output Options |
|-------|---------------|
| doc | docx, pdf, odt, txt, rtf, html |
| docx | doc, pdf, odt, txt, rtf, html |
| odt | doc, docx, pdf, txt, rtf, html |
| rtf | doc, docx, pdf, odt |

### Spreadsheet Formats
| Input | Output Options |
|-------|---------------|
| xls | xlsx, pdf, ods, csv |
| xlsx | xls, pdf, ods, csv |
| ods | xls, xlsx, pdf, csv |
| csv | xls, xlsx, ods |

### Presentation Formats
| Input | Output Options |
|-------|---------------|
| ppt | pptx, pdf, odp |
| pptx | ppt, pdf, odp |
| odp | ppt, pptx, pdf |

## Security Model

### Authentication

Optional Bearer token authentication controlled via environment:

```bash
# .env
API_AUTH_ENABLED=true
API_AUTH_TOKEN=your-secret-token
```

When enabled:
```bash
curl -H "Authorization: Bearer your-secret-token" \
     -F "file=@doc.docx" \
     "http://localhost:28001/convert?to=pdf"
```

When disabled (`API_AUTH_ENABLED=false`):
- All endpoints accessible without authentication
- Suitable for internal/trusted networks

### Endpoint Security Matrix

| Endpoint | Auth Required |
|----------|--------------|
| POST /convert | Yes (if enabled) |
| GET /formats | Yes (if enabled) |
| GET /health | No (always public) |

## Resource Limits

| Resource | Limit | Rationale |
|----------|-------|-----------|
| Max file size | 500MB | Prevent memory exhaustion |
| Concurrent conversions | 10 | LibreOffice process limit |
| Request timeout | 300s | Large file conversion time |
| Worker processes | CPU cores | Optimal parallelism |

## Logging

JSON-structured logging with metrics:

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

## Error Handling

| Error | HTTP Code | Response |
|-------|-----------|----------|
| Unsupported input format | 400 | Supported formats list |
| Unsupported conversion | 400 | Available outputs for input |
| File too large | 413 | Max size limit |
| Too many requests | 429 | Retry-After header |
| Conversion failed | 500 | LibreOffice error message |
| Auth failed | 401 | Unauthorized |

## Design Decisions

### Why Ubuntu Minimal over Alpine?
- LibreOffice has better compatibility with glibc
- Fewer runtime issues with font rendering
- Easier debugging with standard tools

### Why Gunicorn + Uvicorn?
- Gunicorn: Robust process management, graceful restarts
- Uvicorn: High-performance async ASGI server
- Combined: Production-ready with proper signal handling

### Why Semaphore for Concurrency?
- LibreOffice is CPU-intensive
- Uncontrolled parallelism causes OOM
- Semaphore provides backpressure mechanism

### Why JSON Logging?
- Machine-parseable for log aggregation
- Structured metrics for monitoring
- Easy integration with ELK/Loki/CloudWatch

## File Flow

```
Request
   │
   ▼
┌──────────────┐
│ Auth Check   │──── 401 if invalid
│ (if enabled) │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Size Check   │──── 413 if > 500MB
│              │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Semaphore    │──── 429 if full (10 slots)
│ Acquire      │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Temp Dir     │
│ Write Input  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ LibreOffice  │──── 500 if conversion fails
│ --headless   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Read Output  │
│ Cleanup Temp │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Log Metrics  │
│ Return File  │
└──────────────┘
```

## Container Optimization

### Multi-stage Build
```dockerfile
# Stage 1: Font preparation
FROM ubuntu:24.04 AS fonts
# Extract and organize fonts

# Stage 2: Runtime
FROM ubuntu:24.04-minimal
# Install LibreOffice + copy fonts
```

### Size Optimization
- `--no-install-recommends` for apt
- Remove apt cache after install
- No documentation packages
- Single layer for related operations

### Expected Image Size
| Component | Size |
|-----------|------|
| Ubuntu Minimal | ~30MB |
| LibreOffice (core+writer+calc+impress) | ~200MB |
| Chinese Fonts | ~220MB |
| Python + deps | ~50MB |
| **Total** | **~500MB** |
