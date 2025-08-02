# Multi-stage Dockerfile for AutoTrainX API
# Optimized for production with security best practices

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VERSION=1.0.0
ARG VCS_REF

# Add metadata labels
LABEL maintainer="AutoTrainX Team" \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="autotrainx-api" \
      org.label-schema.description="AutoTrainX ML Training API" \
      org.label-schema.version=$VERSION \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.schema-version="1.0"

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /build

# Copy requirements first for better caching
COPY requirements.txt api/requirements.txt ./

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r api/requirements.txt

# Production stage
FROM python:3.11-slim as production

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Essential utilities
    curl \
    wget \
    ca-certificates \
    # Image processing (for PIL/Pillow)
    libjpeg62-turbo \
    libpng16-16 \
    # ML/AI dependencies
    libgomp1 \
    # Monitoring tools
    procps \
    # Clean up
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r autotrainx && \
    useradd -r -g autotrainx -d /app -s /bin/bash -c "AutoTrainX User" autotrainx

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set work directory
WORKDIR /app

# Copy application code
COPY --chown=autotrainx:autotrainx . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/workspace /app/models /app/DB && \
    chown -R autotrainx:autotrainx /app

# Create volume mount points
VOLUME ["/app/workspace", "/app/models", "/app/logs", "/app/DB"]

# Switch to non-root user
USER autotrainx

# Environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

# Development stage (for local development)
FROM production as development

# Switch back to root for development installations
USER root

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    ruff \
    mypy \
    ipython \
    jupyterlab

# Install additional debugging tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim \
    htop \
    tree \
    && rm -rf /var/lib/apt/lists/*

# Switch back to application user
USER autotrainx

# Override command for development (with reload)
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]