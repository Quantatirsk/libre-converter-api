# ==============================================================================
# libre-convert-api Dockerfile
# Multi-format document conversion service using LibreOffice
# ==============================================================================

FROM ubuntu:24.04 AS base

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# ==============================================================================
# Stage 1: Font preparation
# ==============================================================================
FROM base AS fonts

WORKDIR /fonts
RUN apt-get update && apt-get install -y --no-install-recommends curl unzip \
    && curl -fsSL -o Fonts.zip https://static.vect.one/resources/Fonts.zip \
    && unzip Fonts.zip \
    && rm Fonts.zip \
    && rm -rf /var/lib/apt/lists/*

# ==============================================================================
# Stage 2: Runtime
# ==============================================================================
FROM base AS runtime

# Install LibreOffice and dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        # LibreOffice components
        libreoffice-core \
        libreoffice-writer \
        libreoffice-calc \
        libreoffice-impress \
        # Python
        python3 \
        python3-pip \
        python3-venv \
        # Utilities
        curl \
        fontconfig \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/archives/*

# Install Chinese fonts
COPY --from=fonts /fonts/Fonts /usr/share/fonts/truetype/Fonts
RUN fc-cache -fv

# Create non-root user
RUN useradd -m -s /bin/bash -u 1000 converter
WORKDIR /app

# Setup Python virtual environment
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .
COPY gunicorn.conf.py .

# Set ownership
RUN chown -R converter:converter /app

# Switch to non-root user
USER converter

# Environment defaults
ENV API_PORT=28001
ENV API_WORKERS=auto
ENV API_TIMEOUT=300
ENV API_MAX_FILE_SIZE=524288000
ENV API_MAX_CONCURRENT=10
ENV API_AUTH_ENABLED=false
ENV API_AUTH_TOKEN=""
ENV LOG_LEVEL=info
ENV LOG_FORMAT=json

EXPOSE 28001

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:28001/health || exit 1

CMD ["gunicorn", "main:app", "-c", "gunicorn.conf.py"]
