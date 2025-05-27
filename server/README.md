# NLLB Translation Server

This is the server component of the NLLB Translation System. It provides a REST API for translating text between English and Russian using the No Language Left Behind (NLLB) model.

## Features

- FastAPI-based REST API
- NLLB model integration with PyTorch
- Automatic language detection
- API authentication with API keys
- Rate limiting
- Docker deployment support
- Proxmox LXC deployment support

## Requirements

- Python 3.9+
- PyTorch 2.0+
- CUDA 11.7+ (for GPU acceleration, optional)
- 8GB+ RAM (16GB+ recommended)

### Dependencies

The server requires these key Python packages:
- `fastapi==0.95.1` - Web framework
- `transformers==4.29.0` - HuggingFace transformers
- `torch==2.0.0` - PyTorch for model inference
- `accelerate>=0.18.0` - Model loading acceleration
- `typing_extensions>=4.4.0` - Type system extensions

## Installation

### Using Docker

1. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   # Edit the .env file to set your API key and other configurations
   ```

2. Build and start using Docker Compose:
   ```bash
   docker-compose up -d
   ```

3. Check the logs:
   ```bash
   docker-compose logs -f nllb-server
   ```

### Manual Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy and configure environment variables:
   ```bash
   cp .env.example .env
   # Edit the .env file to set your API key and other configurations
   ```

4. Start the server:
   ```bash
   python server.py
   ```

## API Usage

### Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "device": "cuda",
  "memory_usage": "1.2GB"
}
```

### Translate Text

```
POST /translate
```

Headers:
```
X-API-Key: your-api-key
Content-Type: application/json
```

Request Body:
```json
{
  "text": "Hello world",
  "source_lang": "auto",  // "auto", "eng_Latn", or "rus_Cyrl"
  "target_lang": "rus_Cyrl"  // "eng_Latn" or "rus_Cyrl"
}
```

Response:
```json
{
  "translated_text": "Привет мир",
  "detected_source": "eng_Latn",
  "time_ms": 123
}
```

## Model Optimization

The server includes several optimizations for improved performance:
- Low CPU memory usage for model loading
- Half-precision (FP16) on GPU for faster inference
- Automatic batch processing for concurrent requests

## Troubleshooting

### Common Docker Issues

**ImportError: cannot import name 'deprecated' from 'typing_extensions'**
- **Solution**: This has been fixed in recent versions. Rebuild your Docker image:
  ```bash
  docker compose build --no-cache nllb-server
  docker compose up -d
  ```

**PermissionError: [Errno 13] Permission denied: '/home/nllb'**
- **Solution**: Fixed by setting proper cache directories. Update to latest Docker configuration.

**ImportError: Using `low_cpu_mem_usage=True` requires Accelerate**
- **Solution**: The `accelerate` library is now included in requirements.txt

### General Issues

- **Model loading issues**: Ensure you have enough RAM (8GB+ recommended)
- **CUDA errors**: Check that your CUDA version is compatible with PyTorch
- **API authentication failures**: Verify the API key in your .env file
- **Slow translation**: Consider using a GPU for better performance
- **First startup delay**: Model download (~2.4GB) takes several minutes on first run

### Docker Startup Verification

Check if the server is starting properly:
```bash
# Check container status
docker ps

# Monitor logs during startup
docker compose logs -f nllb-server

# Test health endpoint (wait for model to load)
curl -X GET http://localhost:8000/health
```