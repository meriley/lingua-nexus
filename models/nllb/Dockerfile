# Multi-stage Dockerfile for NLLB model
# Optimized for transformers with CPU/GPU variants
# Build arguments: --build-arg VARIANT=cpu|gpu|rocm

ARG VARIANT=cpu
ARG PYTHON_VERSION=3.11
ARG TARGETPLATFORM

# Stage 1: Base image with system dependencies
FROM python:${PYTHON_VERSION}-slim as base

# Build arguments passed to runtime
ARG VARIANT
ENV VARIANT=${VARIANT}

# Set environment variables for better Python behavior
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LINGUA_NEXUS_MODEL=nllb

# Install minimal system dependencies with security focus
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Create non-root user with specific UID/GID for consistency
RUN groupadd --gid 1000 lingua && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash lingua

# Set working directory
WORKDIR /app

# Stage 2: Dependencies installation optimized by variant
FROM base as dependencies

# Copy requirements first for maximum layer caching
COPY models/nllb/requirements.txt ./requirements.txt

# Upgrade pip to latest version
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install PyTorch based on variant with optimized URLs
RUN case "${VARIANT}" in \
    "gpu") \
        pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 ;; \
    "rocm") \
        pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm5.6 ;; \
    *) \
        pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu ;; \
    esac

# Install remaining requirements with caching optimization
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Application layer with security hardening
FROM dependencies as application

# Copy only necessary application code with proper layering
COPY models/base/ ./models/base/
COPY models/nllb/ ./models/nllb/
COPY models/__init__.py ./models/
COPY server/app/ ./server/app/

# Create cache directories with proper permissions
RUN mkdir -p /app/.cache/huggingface \
             /app/.cache/transformers \
             /app/logs \
    && chmod 755 /app/.cache/huggingface \
                 /app/.cache/transformers \
                 /app/logs

# Change ownership to non-root user
RUN chown -R lingua:lingua /app

# Switch to non-root user for security
USER lingua

# Expose application port
EXPOSE 8000

# Optimized health check with faster startup for NLLB
HEALTHCHECK --interval=30s --timeout=30s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set default command with proper module path
CMD ["python", "-m", "server.app.main"]

# Comprehensive metadata labels
LABEL maintainer="Lingua Nexus Team" \
      model="nllb" \
      version="200-distilled-600M" \
      variant="${VARIANT:-cpu}" \
      description="NLLB (No Language Left Behind) 200 translation model for Lingua Nexus" \
      org.opencontainers.image.title="Lingua Nexus NLLB 200" \
      org.opencontainers.image.description="Multilingual translation model based on NLLB-200-distilled-600M" \
      org.opencontainers.image.vendor="Lingua Nexus Team" \
      org.opencontainers.image.source="https://github.com/lingua-nexus/translation-service"

# Environment variables optimized for NLLB model
ENV LINGUA_NEXUS_NLLB_MODEL_PATH=facebook/nllb-200-distilled-600M \
    LINGUA_NEXUS_DEVICE=auto \
    LINGUA_NEXUS_NLLB_MAX_LENGTH=512 \
    LINGUA_NEXUS_NLLB_NUM_BEAMS=4 \
    LINGUA_NEXUS_NLLB_USE_PIPELINE=true \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    HUGGINGFACE_HUB_CACHE=/app/.cache/huggingface

# Performance tuning environment variables
ENV OMP_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false \
    CUDA_DEVICE_ORDER=PCI_BUS_ID

# Security hardening
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random