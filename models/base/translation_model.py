"""
Enhanced Translation Model Interface for Single-Model Architecture.

This module defines the core interface that all translation models must implement
in the new single-model-per-instance architecture. This interface is designed
for resource efficiency, operational simplicity, and standardized build automation.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    """Model metadata and capabilities information."""
    
    name: str = Field(..., description="Model identifier (e.g., 'aya-expanse-8b', 'nllb')")
    version: str = Field(..., description="Model version string")
    supported_languages: List[str] = Field(..., description="List of supported language codes (ISO 639-1)")
    max_tokens: int = Field(..., description="Maximum token limit for input/output")
    memory_requirements: str = Field(..., description="Memory requirements description (e.g., '8GB RAM, 4GB VRAM')")
    description: str = Field(..., description="Human-readable model description")


class TranslationModel(ABC):
    """
    Abstract base class for all translation models in single-model architecture.
    
    This interface is designed for:
    - Single responsibility: Each instance loads exactly one model
    - Resource isolation: Dedicated memory and compute per model
    - Standardized operations: Common interface across all models
    - Health monitoring: Built-in model health checks
    - Clean lifecycle: Proper initialization and cleanup
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize model resources (weights, tokenizer, etc.).
        
        This method should:
        - Load model weights and tokenizer
        - Set up any required GPU/CPU resources
        - Perform any necessary model preparation
        - Set internal state to ready for inference
        
        Raises:
            ModelInitializationError: If model fails to initialize
            ResourceError: If insufficient resources available
        """
        pass
    
    @abstractmethod
    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Perform text translation.
        
        Args:
            text: Input text to translate
            source_lang: Source language code (ISO 639-1)
            target_lang: Target language code (ISO 639-1)
            
        Returns:
            Translated text string
            
        Raises:
            TranslationError: If translation fails
            UnsupportedLanguageError: If language pair not supported
            ValueError: If input parameters are invalid
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verify model readiness for inference.
        
        This method should:
        - Check if model is loaded and ready
        - Verify resource availability
        - Perform a quick inference test if possible
        - Return status without raising exceptions
        
        Returns:
            True if model is healthy and ready, False otherwise
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> ModelInfo:
        """
        Return model metadata and capabilities.
        
        Returns:
            ModelInfo object containing model specifications
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up model resources.
        
        This method should:
        - Release GPU/CPU memory
        - Clean up any temporary resources
        - Reset internal state
        - Prepare for graceful shutdown
        
        Should not raise exceptions during cleanup.
        """
        pass