# Multi-stage Dockerfile for Aya Expanse 8B model
# Optimized for GGUF format with CPU/GPU variants
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
    LINGUA_NEXUS_MODEL=aya-expanse-8b

# Install system dependencies with minimal attack surface
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    curl \
    git \
    gcc \
    g++ \
    libopenblas-dev \
    pkg-config \
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
COPY models/aya-expanse-8b/requirements.txt ./requirements.txt

# Upgrade pip to latest version
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install PyTorch based on variant with platform optimization
RUN case "${VARIANT}" in \
    "gpu") \
        pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 ;; \
    "rocm") \
        pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm5.6 ;; \
    *) \
        pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu ;; \
    esac

# Install llama-cpp-python with appropriate acceleration
RUN case "${VARIANT}" in \
    "gpu") \
        CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install --no-cache-dir llama-cpp-python[cublas] ;; \
    "rocm") \
        CMAKE_ARGS="-DLLAMA_HIPBLAS=on" pip install --no-cache-dir llama-cpp-python ;; \
    *) \
        CMAKE_ARGS="-DLLAMA_OPENBLAS=on" pip install --no-cache-dir llama-cpp-python ;; \
    esac

# Install remaining requirements
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Application layer with security hardening
FROM dependencies as application

# Copy only necessary application code with proper layering
COPY models/base/ ./models/base/
COPY models/aya-expanse-8b/ ./models/aya-expanse-8b/
COPY models/__init__.py ./models/
COPY server/app/ ./server/app/
COPY server/__init__.py ./server/

# Create cache directories with proper permissions
RUN mkdir -p /app/.cache/huggingface \
             /app/.cache/llama-cpp \
             /app/logs \
    && chmod 755 /app/.cache/huggingface \
                 /app/.cache/llama-cpp \
                 /app/logs

# Change ownership to non-root user
RUN chown -R lingua:lingua /app

# Switch to non-root user for security
USER lingua

# Expose application port
EXPOSE 8000

# Optimized health check with model-specific startup time
HEALTHCHECK --interval=30s --timeout=30s --start-period=240s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set PYTHONPATH and run Aya model server
ENV PYTHONPATH=/app
CMD ["python", "-m", "server.app.main_aya"]

# Comprehensive metadata labels
LABEL maintainer="Lingua Nexus Team" \
      model="aya-expanse-8b" \
      version="8B-GGUF" \
      variant="${VARIANT:-cpu}" \
      description="Aya Expanse 8B translation model (GGUF format) for Lingua Nexus" \
      org.opencontainers.image.title="Lingua Nexus Aya Expanse 8B" \
      org.opencontainers.image.description="Multilingual translation model based on Aya Expanse 8B" \
      org.opencontainers.image.vendor="Lingua Nexus Team" \
      org.opencontainers.image.source="https://github.com/lingua-nexus/translation-service"

# Environment variables optimized for different deployment scenarios
ENV LINGUA_NEXUS_AYA_MODEL_PATH=bartowski/aya-expanse-8b-GGUF \
    LINGUA_NEXUS_DEVICE=auto \
    LINGUA_NEXUS_AYA_MAX_LENGTH=3072 \
    LINGUA_NEXUS_AYA_TEMPERATURE=0.1 \
    LINGUA_NEXUS_AYA_GGUF_FILENAME=aya-expanse-8b-Q4_K_M.gguf \
    LINGUA_NEXUS_AYA_GPU_LAYERS=20 \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    LLAMA_CPP_CACHE=/app/.cache/llama-cpp

# Performance tuning environment variables
ENV OMP_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false \
    CUDA_DEVICE_ORDER=PCI_BUS_ID

# Security hardening
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random