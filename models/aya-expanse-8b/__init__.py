"""
Aya Expanse 8B model package for single-model translation architecture.

This package provides the Aya Expanse 8B model implementation using GGUF format
for efficient multilingual translation in a single-model-per-instance deployment.
"""

from .model import AyaExpanse8BModel
from .config import AyaExpanse8BConfig

__all__ = ["AyaExpanse8BModel", "AyaExpanse8BConfig"]