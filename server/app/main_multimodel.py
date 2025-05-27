"""
Multi-model FastAPI application for translation services.

This module provides a FastAPI application that supports multiple translation models
through a unified interface, allowing dynamic model selection and management.
"""

import os
import time
import asyncio
from typing import Dict, Optional, List, Any
from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field, validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.models.registry import ModelRegistry
from app.models.base import TranslationRequest as BaseTranslationRequest, TranslationResponse as BaseTranslationResponse
from app.utils.language_codes import LanguageCodeConverter

# Global model registry
model_registry: Optional[ModelRegistry] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for model loading and cleanup."""
    global model_registry
    
    try:
        # Startup: Initialize model registry
        print("Starting up multi-model translation API...")
        model_registry = ModelRegistry()
        
        # Load default models based on environment configuration
        models_to_load = os.getenv("MODELS_TO_LOAD", "nllb").split(",")
        
        for model_name in models_to_load:
            model_name = model_name.strip()
            if model_name:
                try:
                    print(f"Loading model: {model_name}")
                    await model_registry.load_model(model_name)
                    print(f"Successfully loaded model: {model_name}")
                except Exception as e:
                    print(f"Failed to load model {model_name}: {e}")
        
        print("Multi-model API startup complete")
        yield
        
    finally:
        # Shutdown: Cleanup models
        print("Shutting down multi-model API...")
        if model_registry:
            model_registry.cleanup_all()
        print("Multi-model API shutdown complete")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Multi-Model Translation API",
    description="API for translating text using multiple models (NLLB, Aya Expanse, etc.)",
    version="2.0.0",
    lifespan=lifespan
)

# Set up rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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

# Request and response models
class TranslationRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Text to translate")
    source_lang: Optional[str] = Field("auto", description="Source language code (ISO 639-1) or 'auto' for detection")
    target_lang: str = Field(..., description="Target language code (ISO 639-1)")
    model: Optional[str] = Field("nllb", description="Model to use for translation")
    model_options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Model-specific options")
    
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty')
        return v.strip()
    
    @validator('model')
    def validate_model(cls, v):
        if v and not v.isalnum() and v not in ['_', '-']:
            raise ValueError('Invalid model name format')
        return v

class TranslationResponse(BaseModel):
    translated_text: str = Field(..., description="Translated text")
    detected_source_lang: Optional[str] = Field(None, description="Detected source language (if auto-detection was used)")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    model_used: str = Field(..., description="Model that performed the translation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the translation")

class ModelInfo(BaseModel):
    name: str
    type: str
    available: bool
    supported_languages: List[str]
    device: Optional[str] = None
    model_size: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class LanguageInfo(BaseModel):
    iso_code: str
    name: str
    models_supporting: List[str]

# Health check endpoint
@app.get("/health")
async def health_check():
    """Check API health and model status."""
    if not model_registry:
        return {
            "status": "starting",
            "models_loaded": 0,
            "models_available": []
        }
    
    available_models = model_registry.list_available_models()
    memory_usage = "N/A"
    
    if torch.cuda.is_available():
        memory_usage = f"{torch.cuda.memory_allocated() / 1024**3:.2f}GB"
    
    return {
        "status": "healthy",
        "models_loaded": len(available_models),
        "models_available": available_models,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "memory_usage": memory_usage
    }

# Models management endpoints
@app.get("/models", response_model=List[ModelInfo])
async def list_models(api_key: str = Depends(get_api_key)):
    """List all available models and their status."""
    if not model_registry:
        raise HTTPException(status_code=503, detail="Model registry not initialized")
    
    models_info = []
    for model_name in model_registry.list_available_models():
        try:
            model_info = model_registry.get_model_info(model_name)
            models_info.append(ModelInfo(
                name=model_name,
                type=model_info.get("type", "unknown"),
                available=model_info.get("available", False),
                supported_languages=model_registry.get_model(model_name).get_supported_languages() if model_info.get("available") else [],
                device=model_info.get("device"),
                model_size=model_info.get("model_size"),
                metadata=model_info
            ))
        except Exception as e:
            models_info.append(ModelInfo(
                name=model_name,
                type="unknown",
                available=False,
                supported_languages=[],
                metadata={"error": str(e)}
            ))
    
    return models_info

@app.post("/models/{model_name}/load")
async def load_model(model_name: str, api_key: str = Depends(get_api_key)):
    """Load a specific model."""
    if not model_registry:
        raise HTTPException(status_code=503, detail="Model registry not initialized")
    
    try:
        await model_registry.load_model(model_name)
        return {"message": f"Model {model_name} loaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model {model_name}: {str(e)}")

@app.delete("/models/{model_name}")
async def unload_model(model_name: str, api_key: str = Depends(get_api_key)):
    """Unload a specific model."""
    if not model_registry:
        raise HTTPException(status_code=503, detail="Model registry not initialized")
    
    try:
        model_registry.unload_model(model_name)
        return {"message": f"Model {model_name} unloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unload model {model_name}: {str(e)}")

# Language support endpoints
@app.get("/languages", response_model=List[LanguageInfo])
@limiter.limit("30/minute")
async def get_supported_languages(request: Request, api_key: str = Depends(get_api_key)):
    """Get all supported languages across all models."""
    if not model_registry:
        raise HTTPException(status_code=503, detail="Model registry not initialized")
    
    # Collect languages from all available models
    all_languages = set()
    language_models = {}
    
    for model_name in model_registry.list_available_models():
        try:
            model = model_registry.get_model(model_name)
            if model and model.is_available():
                supported_langs = model.get_supported_languages()
                for lang in supported_langs:
                    all_languages.add(lang)
                    if lang not in language_models:
                        language_models[lang] = []
                    language_models[lang].append(model_name)
        except Exception:
            continue
    
    # Build response
    languages_info = []
    for iso_code in sorted(all_languages):
        languages_info.append(LanguageInfo(
            iso_code=iso_code,
            name=LanguageCodeConverter.get_language_name(iso_code),
            models_supporting=language_models.get(iso_code, [])
        ))
    
    return languages_info

@app.get("/languages/{model_name}")
@limiter.limit("60/minute")
async def get_model_languages(request: Request, model_name: str, api_key: str = Depends(get_api_key)):
    """Get supported languages for a specific model."""
    if not model_registry:
        raise HTTPException(status_code=503, detail="Model registry not initialized")
    
    try:
        model = model_registry.get_model(model_name)
        if not model or not model.is_available():
            raise HTTPException(status_code=404, detail=f"Model {model_name} not found or not loaded")
        
        supported_languages = model.get_supported_languages()
        return {
            "model": model_name,
            "supported_languages": supported_languages,
            "language_names": {lang: LanguageCodeConverter.get_language_name(lang) for lang in supported_languages}
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get languages for model {model_name}: {str(e)}")

# Translation endpoint
@app.post("/translate", response_model=TranslationResponse)
@limiter.limit("10/minute")
async def translate(request: Request, translation_req: TranslationRequest, api_key: str = Depends(get_api_key)):
    """Translate text using the specified model."""
    if not model_registry:
        raise HTTPException(status_code=503, detail="Model registry not initialized")
    
    try:
        # Get the model
        model = model_registry.get_model(translation_req.model)
        if not model or not model.is_available():
            available_models = model_registry.list_available_models()
            raise HTTPException(
                status_code=404, 
                detail=f"Model '{translation_req.model}' not found or not loaded. Available models: {available_models}"
            )
        
        # Validate language support
        if translation_req.source_lang != "auto" and not model.supports_language_pair(translation_req.source_lang, translation_req.target_lang):
            raise HTTPException(
                status_code=400, 
                detail=f"Model '{translation_req.model}' does not support translation from '{translation_req.source_lang}' to '{translation_req.target_lang}'"
            )
        
        if not model.supports_language_pair("auto", translation_req.target_lang):
            raise HTTPException(
                status_code=400, 
                detail=f"Model '{translation_req.model}' does not support target language '{translation_req.target_lang}'"
            )
        
        # Create base translation request
        base_request = BaseTranslationRequest(
            text=translation_req.text,
            source_lang=translation_req.source_lang,
            target_lang=translation_req.target_lang,
            model_options=translation_req.model_options
        )
        
        # Perform translation
        response = await model.translate(base_request)
        
        # Convert to API response format
        return TranslationResponse(
            translated_text=response.translated_text,
            detected_source_lang=response.detected_source_lang,
            processing_time_ms=response.processing_time_ms,
            model_used=response.model_used,
            metadata=response.metadata
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error (in a real app)
        print(f"Translation error: {str(e)}")
        
        # Return a proper error response
        raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")

# Batch translation endpoint
@app.post("/translate/batch")
@limiter.limit("5/minute")
async def translate_batch(
    request: Request, 
    translation_requests: List[TranslationRequest], 
    api_key: str = Depends(get_api_key)
):
    """Translate multiple texts in batch."""
    if not model_registry:
        raise HTTPException(status_code=503, detail="Model registry not initialized")
    
    if len(translation_requests) > 10:  # Limit batch size
        raise HTTPException(status_code=400, detail="Batch size cannot exceed 10 translations")
    
    results = []
    errors = []
    
    for i, req in enumerate(translation_requests):
        try:
            # Reuse the single translation logic
            single_request = Request(scope=request.scope)
            result = await translate(single_request, req, api_key)
            results.append({
                "index": i,
                "success": True,
                "result": result
            })
        except HTTPException as e:
            errors.append({
                "index": i,
                "success": False,
                "error": e.detail,
                "status_code": e.status_code
            })
        except Exception as e:
            errors.append({
                "index": i,
                "success": False,
                "error": str(e),
                "status_code": 500
            })
    
    return {
        "results": results,
        "errors": errors,
        "total_processed": len(results),
        "total_errors": len(errors)
    }

# Legacy compatibility endpoint
@app.post("/translate/legacy", response_model=dict)
async def translate_legacy(request: Request, translation_req: dict, api_key: str = Depends(get_api_key)):
    """Legacy translation endpoint for backward compatibility."""
    try:
        # Convert legacy request format
        modern_req = TranslationRequest(
            text=translation_req.get("text", ""),
            source_lang=translation_req.get("source_lang", "auto"),
            target_lang=translation_req.get("target_lang", ""),
            model="nllb"  # Default to NLLB for legacy requests
        )
        
        # Get translation
        result = await translate(request, modern_req, api_key)
        
        # Convert to legacy response format
        return {
            "translated_text": result.translated_text,
            "detected_source": result.detected_source_lang or modern_req.source_lang,
            "time_ms": int(result.processing_time_ms)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Legacy translation error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)