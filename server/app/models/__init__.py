"""
Multi-model translation system package.

This package provides abstractions for different translation models
including NLLB, Aya 8B, and future model integrations.
"""

from .base import TranslationModel, TranslationRequest, TranslationResponse
from .registry import ModelRegistry

__all__ = [
    'TranslationModel',
    'TranslationRequest', 
    'TranslationResponse',
    'ModelRegistry'
]