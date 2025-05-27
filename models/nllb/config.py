"""
Configuration for NLLB model implementation.

This module defines the configuration class and default settings for
the NLLB (No Language Left Behind) model in the single-model architecture.
"""

import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class NLLBConfig:
    """Configuration for NLLB model."""
    
    # Model identification
    model_name: str = "nllb"
    model_version: str = "200-distilled-600M"
    
    # Model path and loading
    model_path: str = "facebook/nllb-200-distilled-600M"
    device: str = "auto"  # "cpu", "cuda", "auto"
    device_map: Optional[str] = None
    
    # Model parameters
    max_length: int = 512
    num_beams: int = 4
    early_stopping: bool = True
    
    # Pipeline configuration
    use_pipeline: bool = True  # Use transformers pipeline for simplicity
    
    # Performance settings
    batch_size: int = 1
    use_cache: bool = True
    
    # Resource requirements
    memory_requirements: str = "2GB RAM (CPU) or 1GB VRAM (GPU)"
    
    # Supported languages (NLLB-200 supports 200+ languages)
    supported_languages: List[str] = field(default_factory=lambda: [
        "en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko",
        "ar", "hi", "th", "vi", "tr", "pl", "nl", "sv", "da", "no",
        "fi", "hu", "cs", "sk", "sl", "hr", "sr", "bg", "ro", "uk",
        "be", "lt", "lv", "et", "mt", "ga", "cy", "eu", "ca", "gl",
        "he", "yi", "fa", "ur", "ps", "ku", "az", "tk", "ky", "kk",
        "uz", "tg", "mn", "my", "km", "lo", "si", "bn", "gu", "pa",
        "ne", "mr", "as", "or", "ml", "kn", "te", "ta", "hy", "ka",
        "af", "am", "bm", "eu", "be", "bn", "bs", "bg", "ca", "ceb",
        "ny", "zh", "co", "hr", "cs", "da", "nl", "en", "eo", "et",
        "tl", "fi", "fr", "fy", "gl", "ka", "de", "el", "gu", "ht",
        "ha", "haw", "iw", "hi", "hmn", "hu", "is", "ig", "id", "ga",
        "it", "ja", "jw", "kn", "kk", "km", "ko", "ku", "ky", "lo",
        "la", "lv", "lt", "lb", "mk", "mg", "ms", "ml", "mt", "mi",
        "mr", "mn", "my", "ne", "no", "ps", "fa", "pl", "pt", "pa",
        "ro", "ru", "sm", "gd", "sr", "st", "sn", "sd", "si", "sk",
        "sl", "so", "es", "su", "sw", "sv", "tg", "ta", "te", "th",
        "tr", "uk", "ur", "uz", "vi", "cy", "xh", "yi", "yo", "zu"
    ])
    
    # Model-specific options
    model_options: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'NLLBConfig':
        """
        Create configuration from dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            NLLBConfig instance
        """
        # Override with environment variables if set
        env_overrides = cls._get_env_overrides()
        config_dict.update(env_overrides)
        
        return cls(**{k: v for k, v in config_dict.items() if hasattr(cls, k)})
    
    @classmethod
    def _get_env_overrides(cls) -> Dict[str, Any]:
        """Get configuration overrides from environment variables."""
        env_overrides = {}
        
        # Model path override
        if model_path := os.getenv("LINGUA_NEXUS_NLLB_MODEL_PATH"):
            env_overrides["model_path"] = model_path
        
        # Device override
        if device := os.getenv("LINGUA_NEXUS_DEVICE"):
            env_overrides["device"] = device
        
        # Max length override
        if max_length := os.getenv("LINGUA_NEXUS_NLLB_MAX_LENGTH"):
            try:
                env_overrides["max_length"] = int(max_length)
            except ValueError:
                pass
        
        # Number of beams override
        if num_beams := os.getenv("LINGUA_NEXUS_NLLB_NUM_BEAMS"):
            try:
                env_overrides["num_beams"] = int(num_beams)
            except ValueError:
                pass
        
        # Pipeline usage override
        if use_pipeline := os.getenv("LINGUA_NEXUS_NLLB_USE_PIPELINE"):
            env_overrides["use_pipeline"] = use_pipeline.lower() in ("true", "1", "yes")
        
        return env_overrides
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "model_path": self.model_path,
            "device": self.device,
            "device_map": self.device_map,
            "max_length": self.max_length,
            "num_beams": self.num_beams,
            "early_stopping": self.early_stopping,
            "use_pipeline": self.use_pipeline,
            "batch_size": self.batch_size,
            "use_cache": self.use_cache,
            "memory_requirements": self.memory_requirements,
            "supported_languages": self.supported_languages,
            "model_options": self.model_options
        }
    
    def __str__(self) -> str:
        """String representation of configuration."""
        return f"NLLBConfig(model_path={self.model_path}, device={self.device}, max_length={self.max_length})"