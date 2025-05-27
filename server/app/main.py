"""Legacy NLLB Translation API

This module provides the original NLLB-only translation API endpoints.
It serves as the backward-compatible interface for the multi-model translation system.

IMPORTANT: This is a legacy implementation. For new applications, use:
- Multi-Model API (main_multimodel.py) for full model selection capabilities
- Adaptive API (app/adaptive/) for intelligent chunking and optimization

Architecture Integration:
- Uses legacy model_loader.py for NLLB model management
- Integrates with the modern adaptive translation system for enhanced capabilities
- Maintains backward compatibility with original API contracts
"""

import os
import time
from typing import Dict, Optional

import torch
from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Legacy NLLB-specific imports - deprecated in favor of model registry
from app.utils.model_loader import load_nllb_model, translate_text
from app.utils.language_detection import detect_language, detect_language_nllb_format
from app.utils.language_metadata import get_language_metadata, validate_language_code, get_language_by_code

# Import adaptive translation system for enhanced capabilities
from app.adaptive.api_endpoints import router as adaptive_router, initialize_adaptive_system

# Initialize FastAPI app with legacy NLLB API configuration
# NOTE: This is the backward-compatible API. For new features, see:
# - Multi-Model API (main_multimodel.py)
# - Adaptive API (app/adaptive/)
app = FastAPI(
    title="Legacy NLLB Translation API",
    description="Legacy API for translating text using the NLLB model. Includes adaptive translation enhancements.",
    version="1.0.0"
)

# Set up rate limiting
# Disable rate limiting when running tests
if os.getenv("TESTING") == "true":
    # Create a dummy limiter that never rate limits
    limiter = Limiter(key_func=get_remote_address, default_limits=[])
else:
    limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include adaptive translation router
app.include_router(adaptive_router)

# Add validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": exc.body
        }
    )

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key authentication
API_KEY_NAME = "X-API-Key"
API_KEY = os.getenv("API_KEY", "development-key")  # For development only

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Invalid API Key")

# Global variables for legacy NLLB model and tokenizer
# NOTE: In the modern multi-model architecture, models are managed through
# the model registry (app/models/registry.py) instead of global variables
model = None  # NLLB model instance
tokenizer = None  # NLLB tokenizer instance

# Request and response models
class TranslationRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    source_lang: Optional[str] = Field("auto")
    target_lang: str = Field(...)

class TranslationResponse(BaseModel):
    translated_text: str
    detected_source: str
    time_ms: int

# Translation function adapter for the adaptive system
# This bridges the legacy NLLB implementation with the modern adaptive architecture
async def adaptive_translation_function(text: str, source_lang: str, target_lang: str, api_key: str) -> str:
    """Legacy NLLB translation function adapter for the adaptive translation system.
    
    This function provides backward compatibility by wrapping the legacy NLLB
    translation logic for use with the modern adaptive translation system.
    
    Args:
        text: Text to translate
        source_lang: Source language code (NLLB format)
        target_lang: Target language code (NLLB format)
        api_key: Authentication API key
        
    Returns:
        str: Translated text
        
    Raises:
        HTTPException: If model not loaded, invalid API key, or translation fails
        
    Note:
        This is a legacy adapter. New implementations should use the
        multi-model translation functions in app/models/.
    """
    if not model or not tokenizer:
        raise HTTPException(status_code=503, detail="NLLB model not loaded yet")
    
    # Validate API key
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    # Detect language if set to auto (using legacy NLLB detection)
    detected_source = source_lang
    if source_lang == "auto":
        detected_source = detect_language_nllb_format(text)
    
    # Translate using legacy NLLB implementation
    return translate_text(text, model, tokenizer, source_lang=detected_source, target_lang=target_lang)

# Startup event to load legacy NLLB model and initialize adaptive system
@app.on_event("startup")
async def startup_event():
    """Initialize the legacy NLLB API server with adaptive capabilities.
    
    This startup sequence:
    1. Loads the NLLB model using legacy model_loader
    2. Initializes the modern adaptive translation system
    3. Bridges legacy and modern architectures
    
    Note: In the multi-model architecture, model loading is handled
    by the model registry rather than global variables.
    """
    global model, tokenizer
    try:
        # Load legacy NLLB model using traditional approach
        print("Loading legacy NLLB model...")
        model, tokenizer = load_nllb_model()
        print("Legacy NLLB model loaded successfully")
        
        # Initialize modern adaptive translation system with legacy adapter
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        await initialize_adaptive_system(adaptive_translation_function, redis_url)
        print("Adaptive translation system initialized successfully")
        print("Legacy NLLB API ready with adaptive enhancements")
        
    except Exception as e:
        # Don't exit - tests might be using mocks
        print(f"WARNING: Failed to load NLLB model or initialize adaptive system: {e}")
        print("Server will continue but translation endpoints may not work")
        model = None
        tokenizer = None

# Health check endpoint
@app.get("/health")
async def health_check():
    memory_usage = "N/A"
    if torch.cuda.is_available():
        memory_usage = f"{torch.cuda.memory_allocated() / 1024**3:.2f}GB"
    
    return {
        "status": "healthy",
        "model_loaded": model is not None and tokenizer is not None,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "memory_usage": memory_usage
    }

# Language metadata endpoint
@app.get("/languages")
@limiter.limit("30/minute")
async def get_supported_languages(request: Request, api_key: str = Depends(get_api_key)):
    """Get comprehensive language metadata for all supported NLLB languages.
    
    This endpoint provides language metadata specifically for the NLLB model.
    For multi-model language support, see the Multi-Model API.
    
    Returns:
        dict: Language metadata including:
            - Language codes (NLLB format)
            - Language names and families
            - Script information
            - Popularity rankings
            - Caching headers for performance
            
    Note:
        Different models in the multi-model system may support different
        language sets. This endpoint only covers NLLB languages.
    """
    try:
        metadata = get_language_metadata()
        
        # Add caching headers for better performance
        return {
            **metadata,
            "cache_headers": {
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "ETag": f"lang-metadata-v1-{len(metadata['languages'])}"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load language metadata: {str(e)}")

# Individual language lookup endpoint
@app.get("/languages/{language_code}")
@limiter.limit("60/minute")
async def get_language_info(request: Request, language_code: str, api_key: str = Depends(get_api_key)):
    """Get metadata for a specific NLLB language by its code.
    
    Args:
        language_code: NLLB format language code (e.g., 'eng_Latn', 'spa_Latn')
        
    Returns:
        dict: Language information including name, family, script, etc.
        
    Raises:
        HTTPException: 404 if language code not found in NLLB model
        
    Note:
        This is NLLB-specific. For multi-model language info, see the
        Multi-Model API which handles cross-model language code conversion.
    """
    language_info = get_language_by_code(language_code)
    
    if not language_info:
        raise HTTPException(status_code=404, detail=f"Language code '{language_code}' not found")
    
    return language_info

# Translation endpoint
@app.post("/translate", response_model=TranslationResponse)
@limiter.limit("10/minute")
async def translate(request: Request, translation_req: TranslationRequest, api_key: str = Depends(get_api_key)):
    start_time = time.time()
    
    # Check if model is loaded
    if not model or not tokenizer:
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    
    # Validate input text
    text = translation_req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text provided")
    
    # Validate language codes
    if translation_req.source_lang != "auto" and not validate_language_code(translation_req.source_lang):
        raise HTTPException(status_code=400, detail=f"Unsupported source language: {translation_req.source_lang}")
    
    if not validate_language_code(translation_req.target_lang):
        raise HTTPException(status_code=400, detail=f"Unsupported target language: {translation_req.target_lang}")
    
    if translation_req.target_lang == "auto":
        raise HTTPException(status_code=400, detail="Target language cannot be 'auto'")
    
    # Check if source and target are the same (except for auto-detect)
    if translation_req.source_lang == translation_req.target_lang and translation_req.source_lang != "auto":
        raise HTTPException(status_code=400, detail="Source and target languages cannot be the same")
    
    try:
        # Detect language if set to auto
        detected_source = translation_req.source_lang
        if translation_req.source_lang == "auto":
            try:
                detected_source = detect_language_nllb_format(text)
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Translation error: Language detection failed: {str(e)}"
                )
        
        # Translate the text
        translated_text = translate_text(
            text, 
            model, 
            tokenizer, 
            source_lang=detected_source, 
            target_lang=translation_req.target_lang
        )
        
        # Calculate time taken
        time_ms = int((time.time() - start_time) * 1000)
        
        return TranslationResponse(
            translated_text=translated_text,
            detected_source=detected_source,
            time_ms=time_ms
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error (in a real app)
        print(f"Translation error: {str(e)}")
        
        # Return a proper error response
        raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")