"""Translation Service Entry Point

This is the main entry point for the multi-model translation service.
It provides a development server for running the translation APIs.

Available API Implementations:
- app.main:app - Legacy NLLB API (backward compatible)
- app.main_multimodel:app - Multi-Model API (full model selection)
- app.main_aya:app - Aya-specific API (optimized for Aya models)

Environment Configuration:
- HOST: Server bind address (default: 0.0.0.0)
- PORT: Server port (default: 8000)
- API_KEY: Authentication key for secure endpoints
- REDIS_URL: Redis connection for caching (default: redis://localhost:6379)
- MODEL_NAME: Default model name for legacy API

Production Deployment:
For production, use a production WSGI server like Gunicorn:
    gunicorn app.main_multimodel:app -w 4 -k uvicorn.workers.UvicornWorker

Development Usage:
    python server.py  # Runs legacy NLLB API
    
Testing:
    TESTING=true python server.py  # Disables rate limiting for tests
"""

import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables from .env file
# This allows configuration without modifying code
load_dotenv()

if __name__ == "__main__":
    # Get server configuration from environment variables with sensible defaults
    host = os.getenv("HOST", "0.0.0.0")  # Bind to all interfaces by default
    port = int(os.getenv("PORT", "8000"))  # Standard development port
    
    # Determine which API implementation to run
    # Default to legacy NLLB API for backward compatibility
    app_module = os.getenv("APP_MODULE", "app.main:app")
    
    print(f"Starting Translation Service:")
    print(f"  API: {app_module}")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Environment: {'Testing' if os.getenv('TESTING') else 'Development'}")
    
    # Run the FastAPI application with Uvicorn
    # reload=True enables auto-reload on code changes for development
    uvicorn.run(
        app_module,
        host=host,
        port=port,
        reload=True,  # Enable auto-reload for development
        log_level="info"  # Provide informative logging
    )