"""
NLLB model package for single-model translation architecture.

This package provides the NLLB (No Language Left Behind) model implementation
for multilingual translation in a single-model-per-instance deployment.
"""

from .model import NLLBModel
from .config import NLLBConfig

__all__ = ["NLLBModel", "NLLBConfig"]