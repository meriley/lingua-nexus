"""
Model-specific exceptions for the single-model translation architecture.

This module defines exceptions that can be raised by translation model implementations,
providing clear error handling and diagnostics for the single-model-per-instance pattern.
"""


class ModelError(Exception):
    """Base exception for all model-related errors."""
    
    def __init__(self, message: str, model_name: str = "unknown"):
        """
        Initialize model error.
        
        Args:
            message: Error description
            model_name: Name of the model that caused the error
        """
        self.model_name = model_name
        super().__init__(f"[{model_name}] {message}")


class ModelInitializationError(ModelError):
    """Raised when model fails to initialize properly."""
    pass


class TranslationError(ModelError):
    """Raised when translation operation fails."""
    pass


class LanguageDetectionError(ModelError):
    """Raised when language detection fails."""
    pass


class UnsupportedLanguageError(ModelError):
    """Raised when requested language pair is not supported."""
    
    def __init__(self, source_lang: str, target_lang: str, model_name: str = "unknown"):
        """
        Initialize unsupported language error.
        
        Args:
            source_lang: Source language code
            target_lang: Target language code
            model_name: Name of the model
        """
        message = f"Language pair {source_lang} -> {target_lang} not supported"
        super().__init__(message, model_name)
        self.source_lang = source_lang
        self.target_lang = target_lang


class ResourceError(ModelError):
    """Raised when insufficient resources are available for model operation."""
    pass


class ModelNotReadyError(ModelError):
    """Raised when attempting to use model before proper initialization."""
    pass