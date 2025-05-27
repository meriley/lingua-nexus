"""
Aya-only translation API server.

This module provides a FastAPI server that only loads and serves the Aya Expanse 8B model,
optimized for memory efficiency using GGUF format when available.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .models.registry import ModelRegistry
from .models.base import TranslationRequest, TranslationResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Global model registry
model_registry = None


async def get_model_registry():
    """Dependency to get the model registry."""
    if model_registry is None:
        raise HTTPException(status_code=503, detail="Models not yet loaded")
    return model_registry


def verify_api_key(api_key: str = None):
    """Simple API key verification."""
    expected_key = os.getenv('API_KEY', '1234567')
    if api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    global model_registry
    
    logger.info("Starting up Aya-only translation API...")
    
    try:
        # Initialize model registry
        model_registry = ModelRegistry()
        
        # Configure Aya model using GGUF format with optimized GPU settings
        # Using bartowski/aya-expanse-8b-GGUF as specified
        force_cpu = os.getenv('FORCE_CPU', 'false').lower() == 'true'
        device = os.getenv('DEVICE', 'cpu' if force_cpu else 'cuda')
        
        aya_config = {
            'model_path': os.getenv('MODEL_PATH', 'bartowski/aya-expanse-8b-GGUF'),
            'device': device,
            'use_gguf': True,  # Required for Aya model
            'gguf_filename': os.getenv('GGUF_FILENAME', 'aya-expanse-8b-Q4_K_M.gguf'),
            'n_ctx': int(os.getenv('N_CTX', '8192')),
            'n_gpu_layers': int(os.getenv('N_GPU_LAYERS', '20' if device == 'cuda' else '0')),
            'use_quantization': False if force_cpu else True,  # No quantization on CPU
            'load_in_8bit': False if force_cpu else True,  # No 8-bit on CPU
            'temperature': float(os.getenv('TEMPERATURE', '0.1')),
            'top_p': float(os.getenv('TOP_P', '0.9')),
            'max_length': int(os.getenv('MAX_LENGTH', '3072'))
        }
        
        # Load only Aya model
        logger.info("Loading Aya model...")
        model_registry.create_and_register_model('aya', 'aya', aya_config)
        
        logger.info("Aya model loaded successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize Aya model: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Shutting down Aya translation API...")
        if model_registry:
            model_registry.cleanup_all()


# Create FastAPI app
app = FastAPI(
    title="Aya Translation API",
    description="Translation API using only Aya Expanse 8B model with GGUF optimization",
    version="1.0.0",
    lifespan=lifespan
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware with explicit configuration for userscripts
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Allow all origins
        "https://web.telegram.org",
        "https://k.web.telegram.org", 
        "https://z.web.telegram.org",
        "https://a.web.telegram.org"
    ],
    allow_credentials=False,  # Set to False for broader compatibility
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "*",
        "Content-Type",
        "Authorization", 
        "X-API-Key",
        "Origin",
        "Accept",
        "User-Agent"
    ],
    expose_headers=["*"]
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        registry = await get_model_registry()
        aya_model = registry.get_model('aya')
        
        if aya_model and aya_model.is_available():
            return {
                "status": "healthy",
                "model": "aya",
                "format": "GGUF" if getattr(aya_model, 'use_gguf', False) else "transformers",
                "available": True
            }
        else:
            return {
                "status": "unhealthy", 
                "model": "aya",
                "available": False,
                "error": "Model not loaded"
            }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


@app.get("/models")
async def list_models():
    """List available models."""
    try:
        registry = await get_model_registry()
        models_info = {}
        
        aya_model = registry.get_model('aya')
        if aya_model:
            models_info['aya'] = aya_model.get_model_info()
            
        return {"models": models_info}
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/translate", response_model=TranslationResponse)
async def translate_text(
    request_body: TranslationRequest,
    background_tasks: BackgroundTasks,
    _: bool = Depends(lambda: verify_api_key(os.getenv('API_KEY', '1234567')))
):
    """Translate text using Aya model."""
    try:
        registry = await get_model_registry()
        
        # Always use Aya model (only model available)
        model = registry.get_model('aya')
        if not model or not model.is_available():
            raise HTTPException(
                status_code=503, 
                detail="Aya model is not available"
            )
        
        # Perform translation
        result = await model.translate(request_body)
        
        # Log successful translation
        logger.info(f"Translation completed: {request_body.source_lang} -> {request_body.target_lang}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Aya Translation API",
        "model": "aya-101",
        "format": "GGUF-optimized",
        "endpoints": {
            "translate": "/translate",
            "health": "/health",
            "models": "/models"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)