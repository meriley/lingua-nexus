"""
Abstract base classes for the multi-model translation system.

This module defines the core interfaces that all translation models must implement,
providing a common abstraction layer for different model backends.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import time


@dataclass
class TranslationRequest:
    """Request object for translation operations."""
    text: str
    source_lang: Optional[str] = None  # None for auto-detection
    target_lang: str = "en"
    model_options: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate request parameters."""
        if not self.text or not self.text.strip():
            raise ValueError("Text cannot be empty")
        if not self.target_lang:
            raise ValueError("Target language must be specified")


@dataclass  
class TranslationResponse:
    """Response object for translation operations."""
    translated_text: str
    detected_source_lang: Optional[str] = None
    confidence_score: Optional[float] = None
    processing_time_ms: float = 0
    model_used: str = ""
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate response parameters."""
        if not self.translated_text:
            raise ValueError("Translated text cannot be empty")


class TranslationModel(ABC):
    """Abstract base class for all translation models."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the translation model with configuration."""
        self.config = config
        self.model_name = config.get('name', 'unknown')
        self._initialized = False
    
    @abstractmethod
    async def translate(self, request: TranslationRequest) -> TranslationResponse:
        """
        Perform translation on the given request.
        
        Args:
            request: TranslationRequest containing text and language parameters
            
        Returns:
            TranslationResponse with translated text and metadata
            
        Raises:
            RuntimeError: If translation fails
            ValueError: If request parameters are invalid
        """
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """
        Return list of supported language codes in ISO 639-1 format.
        
        Returns:
            List of ISO 639-1 language codes (e.g., ['en', 'ru', 'es'])
        """
        pass
    
    @abstractmethod
    async def detect_language(self, text: str) -> str:
        """
        Detect the language of input text.
        
        Args:
            text: Text to analyze for language detection
            
        Returns:
            ISO 639-1 language code of detected language
            
        Raises:
            RuntimeError: If language detection fails
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if model is ready for inference.
        
        Returns:
            True if model is loaded and ready, False otherwise
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Return model metadata and configuration information.
        
        Returns:
            Dictionary containing model information including:
            - name: Model identifier
            - type: Model type (e.g., 'nllb', 'aya')
            - available: Availability status
            - Other model-specific metadata
        """
        pass
    
    def supports_language_pair(self, source_lang: str, target_lang: str) -> bool:
        """
        Check if model supports translation between given language pair.
        
        Args:
            source_lang: Source language ISO code
            target_lang: Target language ISO code
            
        Returns:
            True if language pair is supported, False otherwise
        """
        supported = self.get_supported_languages()
        return source_lang in supported and target_lang in supported
    
    def validate_request(self, request: TranslationRequest) -> None:
        """
        Validate translation request parameters.
        
        Args:
            request: TranslationRequest to validate
            
        Raises:
            ValueError: If request parameters are invalid
        """
        if not self.is_available():
            raise RuntimeError(f"Model {self.model_name} is not available")
            
        if request.target_lang not in self.get_supported_languages():
            raise ValueError(f"Target language '{request.target_lang}' not supported by {self.model_name}")
            
        if request.source_lang and request.source_lang != 'auto':
            if request.source_lang not in self.get_supported_languages():
                raise ValueError(f"Source language '{request.source_lang}' not supported by {self.model_name}")


class ModelError(Exception):
    """Base exception for model-related errors."""
    pass


class ModelInitializationError(ModelError):
    """Raised when model fails to initialize."""
    pass


class TranslationError(ModelError):
    """Raised when translation operation fails."""
    pass


class LanguageDetectionError(ModelError):
    """Raised when language detection fails."""
    pass


class UnsupportedLanguageError(ModelError):
    """Raised when requested language is not supported."""
    pass