"""
Base module for the single-model translation architecture.

This module provides the core interfaces and exceptions that all translation
models must implement in the new single-model-per-instance design.
"""

from .translation_model import TranslationModel, ModelInfo
from .exceptions import (
    ModelError,
    ModelInitializationError,
    TranslationError,
    LanguageDetectionError,
    UnsupportedLanguageError,
    ResourceError,
    ModelNotReadyError
)
from .request_models import (
    TranslationRequest,
    TranslationResponse,
    HealthCheckResponse,
    ErrorResponse
)

__all__ = [
    # Core interfaces
    "TranslationModel",
    "ModelInfo",
    
    # Request/Response models
    "TranslationRequest",
    "TranslationResponse", 
    "HealthCheckResponse",
    "ErrorResponse",
    
    # Exceptions
    "ModelError",
    "ModelInitializationError", 
    "TranslationError",
    "LanguageDetectionError",
    "UnsupportedLanguageError",
    "ResourceError",
    "ModelNotReadyError"
]