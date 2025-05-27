"""
Single-Model Translation API Server.

This module provides a FastAPI server for single-model-per-instance translation
using the new TranslationModel interface. Each server instance loads exactly
one model for resource efficiency and operational simplicity.
"""

import os
import time
import asyncio
import logging
from typing import Dict, Optional, Any
from contextlib import asynccontextmanager

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

# Import from the project root models directory
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from models.base import (
    TranslationModel,
    ModelInfo,
    TranslationRequest as BaseTranslationRequest,
    TranslationResponse as BaseTranslationResponse,
    HealthCheckResponse,
    ErrorResponse,
    ModelInitializationError,
    TranslationError,
    ModelNotReadyError
)

logger = logging.getLogger(__name__)

# Global model instance
translation_model: Optional[TranslationModel] = None
model_name: Optional[str] = None


class LanguageDetectionRequest(BaseModel):
    """Request model for language detection."""
    text: str = Field(..., description="Text to detect language for", min_length=1, max_length=1000)


class SingleModelServer:
    """Single-model server management class."""
    
    def __init__(self, model_name: str):
        """
        Initialize single-model server.
        
        Args:
            model_name: Name of the model to load
        """
        self.model_name = model_name
        self.model: Optional[TranslationModel] = None
        self._initialized = False
    
    async def startup(self):
        """Initialize the single model instance."""
        try:
            logger.info(f"Initializing single-model server for: {self.model_name}")
            self.model = await self._load_model(self.model_name)
            await self.model.initialize()
            self._initialized = True
            logger.info(f"Single-model server initialized successfully: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize single-model server: {e}")
            raise ModelInitializationError(f"Server startup failed: {e}", self.model_name)
    
    async def shutdown(self):
        """Clean up model resources."""
        try:
            if self.model:
                logger.info(f"Shutting down model: {self.model_name}")
                await self.model.cleanup()
                self.model = None
            self._initialized = False
            logger.info("Single-model server shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def _load_model(self, model_name: str) -> TranslationModel:
        """
        Dynamic model loading based on environment configuration.
        
        Args:
            model_name: Name of the model to load
            
        Returns:
            TranslationModel instance
        """
        logger.info(f"Loading model: {model_name}")
        
        if model_name == "aya-expanse-8b":
            from models.aya_expanse_8b.model import AyaExpanse8BModel
            return AyaExpanse8BModel()
        elif model_name == "nllb":
            from models.nllb.model import NLLBModel
            return NLLBModel()
        else:
            raise ValueError(f"Unknown model: {model_name}. Supported models: aya-expanse-8b, nllb")
    
    def is_ready(self) -> bool:
        """Check if server is ready."""
        return self._initialized and self.model is not None
    
    async def get_model_info(self) -> ModelInfo:
        """Get model information."""
        if not self.is_ready():
            raise ModelNotReadyError("Model not ready", self.model_name)
        return self.model.get_model_info()
    
    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Perform translation."""
        if not self.is_ready():
            raise ModelNotReadyError("Model not ready", self.model_name)
        return await self.model.translate(text, source_lang, target_lang)
    
    async def health_check(self) -> bool:
        """Perform health check."""
        if not self.is_ready():
            return False
        return await self.model.health_check()


# Global server instance
server: Optional[SingleModelServer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for model loading and cleanup."""
    global server
    
    try:
        # Startup: Initialize single-model server
        model_name = os.getenv("LINGUA_NEXUS_MODEL", "nllb")
        logger.info(f"Starting single-model server for: {model_name}")
        
        server = SingleModelServer(model_name)
        await server.startup()
        
        logger.info(f"Single-model translation API ready: {model_name}")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        # Don't exit completely - allow health checks to report the issue
        yield
        
    finally:
        # Shutdown: Clean up resources
        if server:
            await server.shutdown()


# Initialize FastAPI app
def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    model_name = os.getenv("LINGUA_NEXUS_MODEL", "nllb")
    
    app = FastAPI(
        title=f"Lingua Nexus - {model_name.title()} Translation API",
        description=f"Single-model translation API for {model_name}",
        version="2.0.0",
        lifespan=lifespan
    )
    
    # Set up rate limiting (disable during testing)
    if os.getenv("TESTING") == "true":
        limiter = Limiter(key_func=get_remote_address, default_limits=[])
    else:
        limiter = Limiter(key_func=get_remote_address)
    
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
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
    
    # API Key authentication
    API_KEY_NAME = "X-API-Key"
    API_KEY = os.getenv("API_KEY", "development-key")
    api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
    
    async def get_api_key(api_key_header: str = Security(api_key_header)):
        if api_key_header == API_KEY:
            return api_key_header
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    # Health check endpoint
    @app.get("/health", response_model=HealthCheckResponse)
    async def health_check():
        """Check server and model health."""
        timestamp = time.time()
        
        if not server:
            return HealthCheckResponse(
                status="unhealthy",
                model_name="unknown",
                timestamp=timestamp,
                details="Server not initialized"
            )
        
        try:
            is_healthy = await server.health_check()
            model_info = None
            
            if server.is_ready():
                model_info_obj = await server.get_model_info()
                model_info = model_info_obj.dict()
            
            return HealthCheckResponse(
                status="healthy" if is_healthy else "unhealthy",
                model_name=server.model_name,
                model_info=model_info,
                timestamp=timestamp,
                details="Model ready" if is_healthy else "Model not responding"
            )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthCheckResponse(
                status="unhealthy",
                model_name=server.model_name if server else "unknown",
                timestamp=timestamp,
                details=f"Health check error: {str(e)}"
            )
    
    # Model info endpoint
    @app.get("/model/info")
    @limiter.limit("30/minute")
    async def get_model_info(request: Request, api_key: str = Depends(get_api_key)):
        """Get detailed model information."""
        if not server or not server.is_ready():
            raise HTTPException(status_code=503, detail="Model not ready")
        
        try:
            model_info = await server.get_model_info()
            return model_info.dict()
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get model info: {str(e)}")
    
    # Translation endpoint
    @app.post("/translate")
    @limiter.limit("10/minute")
    async def translate(
        request: Request, 
        translation_req: BaseTranslationRequest, 
        api_key: str = Depends(get_api_key)
    ):
        """Translate text using the loaded model."""
        start_time = time.time()
        
        if not server or not server.is_ready():
            raise HTTPException(status_code=503, detail="Model not ready")
        
        try:
            # Perform translation
            translated_text = await server.translate(
                translation_req.text,
                translation_req.source_lang,
                translation_req.target_lang
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            return BaseTranslationResponse(
                translated_text=translated_text,
                source_lang=translation_req.source_lang,
                target_lang=translation_req.target_lang,
                model_name=server.model_name,
                processing_time_ms=processing_time
            )
            
        except ModelNotReadyError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except TranslationError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")
    
    # Language detection endpoint (if supported)
    @app.post("/detect")
    @limiter.limit("20/minute")
    async def detect_language(
        request: Request,
        detection_request: LanguageDetectionRequest,
        api_key: str = Depends(get_api_key)
    ):
        """Detect language of input text."""
        if not server or not server.is_ready():
            raise HTTPException(status_code=503, detail="Model not ready")
        
        try:
            # Use model's language detection if available
            detected_lang = await server.model._detect_language(detection_request.text) if hasattr(server.model, '_detect_language') else "en"
            
            return {
                "text": detection_request.text[:100] + "..." if len(detection_request.text) > 100 else detection_request.text,
                "detected_language": detected_lang,
                "confidence": 0.8,  # Placeholder confidence
                "model": server.model_name
            }
            
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            raise HTTPException(status_code=500, detail=f"Language detection failed: {str(e)}")
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    # Run server
    uvicorn.run(app, host=host, port=port)