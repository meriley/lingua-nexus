FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/.cache
ENV TRANSFORMERS_CACHE=/app/.cache

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade typing_extensions
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user and cache directory
RUN groupadd -r nllb && useradd -r -g nllb nllb
RUN mkdir -p /app/.cache && chown -R nllb:nllb /app
USER nllb

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "server.py"]