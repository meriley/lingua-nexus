"""
Pydantic models for API requests and responses in the single-model architecture.

This module defines the standardized request/response models that work with
the new TranslationModel interface for consistent API integration.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class TranslationRequest(BaseModel):
    """Request model for translation operations."""
    
    text: str = Field(..., description="Text to translate", min_length=1, max_length=10000)
    source_lang: str = Field(..., description="Source language code (ISO 639-1)")
    target_lang: str = Field(..., description="Target language code (ISO 639-1)")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional translation options")
    
    @field_validator('text')
    @classmethod
    def text_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Text cannot be empty or whitespace only')
        return v.strip()
    
    @field_validator('source_lang', 'target_lang')
    @classmethod
    def language_codes_must_be_valid(cls, v):
        if not v or len(v) < 2:
            raise ValueError('Language code must be at least 2 characters')
        return v.lower()


class TranslationResponse(BaseModel):
    """Response model for translation operations."""
    
    translated_text: str = Field(..., description="Translated text result")
    source_lang: str = Field(..., description="Source language used")
    target_lang: str = Field(..., description="Target language used")
    model_name: str = Field(..., description="Model that performed the translation")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    confidence: Optional[float] = Field(None, description="Translation confidence score (0-1)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class HealthCheckResponse(BaseModel):
    """Response model for health check operations."""
    
    status: str = Field(..., description="Health status ('healthy', 'unhealthy', 'initializing')")
    model_name: str = Field(..., description="Name of the model being checked")
    model_info: Optional[Dict[str, Any]] = Field(None, description="Model information if available")
    timestamp: float = Field(..., description="Timestamp of health check")
    details: Optional[str] = Field(None, description="Additional status details")


class ErrorResponse(BaseModel):
    """Response model for error conditions."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    model_name: Optional[str] = Field(None, description="Model that caused the error")
    timestamp: float = Field(..., description="Error timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")