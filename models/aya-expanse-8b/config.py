"""
Configuration for Aya Expanse 8B model implementation.

This module defines the configuration class and default settings for
the Aya Expanse 8B model in the single-model architecture.
"""

import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class AyaExpanse8BConfig:
    """Configuration for Aya Expanse 8B model."""
    
    # Model identification
    model_name: str = "aya-expanse-8b"
    model_version: str = "8B-GGUF"
    
    # Model path and loading - CRITICAL: Use bartowski/aya-expanse-8b-GGUF
    model_path: str = "bartowski/aya-expanse-8b-GGUF"
    device: str = "auto"  # "cpu", "cuda", "auto"
    device_map: Optional[str] = None
    
    # GGUF-specific configuration
    use_gguf: bool = True  # Prefer GGUF format
    gguf_filename: str = "aya-expanse-8b-Q4_K_M.gguf"  # Medium quantization
    n_ctx: int = 8192  # Full Aya context window
    n_gpu_layers: int = 20  # Optimal GPU layers
    
    # Model parameters
    max_length: int = 3072  # Increased for longer translations
    temperature: float = 0.1  # Low for deterministic translation
    top_p: float = 0.9
    do_sample: bool = True
    
    # Quantization settings
    use_quantization: bool = True
    load_in_8bit: bool = True  # Prefer 8-bit over 4-bit for quality
    
    # Performance settings
    batch_size: int = 1
    num_beams: int = 1
    use_cache: bool = True
    
    # Resource requirements
    memory_requirements: str = "8GB RAM + 4GB VRAM (recommended)"
    
    # Supported languages (Aya Expanse supports 114 languages)
    supported_languages: List[str] = field(default_factory=lambda: [
        "en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko",
        "ar", "hi", "th", "vi", "tr", "pl", "nl", "sv", "da", "no",
        "fi", "hu", "cs", "sk", "sl", "hr", "sr", "bg", "ro", "uk",
        "be", "lt", "lv", "et", "mt", "ga", "cy", "eu", "ca", "gl",
        "ast", "an", "oc", "rm", "la", "el", "mk", "sq", "bs", "me",
        "is", "fo", "kl", "gd", "gv", "br", "co", "sc", "nap", "scn",
        "vec", "lij", "pms", "lmo", "eml", "rgn", "fur", "lld", "rm",
        "he", "yi", "ar", "fa", "ur", "ps", "ku", "ckb", "az", "tk",
        "ky", "kk", "uz", "tg", "mn", "bo", "my", "km", "lo", "si",
        "bn", "gu", "pa", "ne", "mr", "mai", "bho", "mag", "awa", "bpy",
        "as", "or", "ml", "kn", "te", "ta", "hy", "ka", "ab", "os",
        "ce", "av", "lez", "lbe", "kbd", "ady", "krc", "uby", "inh",
        "bua", "sah", "tyv", "chv", "udm", "komi", "mhr", "mrj", "mdf"
    ])
    
    # Model-specific options
    model_options: Dict[str, Any] = field(default_factory=dict)
    
    # Custom prompt template (optional)
    custom_prompt_template: Optional[str] = None
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'AyaExpanse8BConfig':
        """
        Create configuration from dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            AyaExpanse8BConfig instance
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
        if model_path := os.getenv("LINGUA_NEXUS_AYA_MODEL_PATH"):
            env_overrides["model_path"] = model_path
        
        # Device override
        if device := os.getenv("LINGUA_NEXUS_DEVICE"):
            env_overrides["device"] = device
        
        # Max length override
        if max_length := os.getenv("LINGUA_NEXUS_AYA_MAX_LENGTH"):
            try:
                env_overrides["max_length"] = int(max_length)
            except ValueError:
                pass
        
        # Temperature override
        if temperature := os.getenv("LINGUA_NEXUS_AYA_TEMPERATURE"):
            try:
                env_overrides["temperature"] = float(temperature)
            except ValueError:
                pass
        
        # GGUF filename override
        if gguf_filename := os.getenv("LINGUA_NEXUS_AYA_GGUF_FILENAME"):
            env_overrides["gguf_filename"] = gguf_filename
        
        # GPU layers override
        if n_gpu_layers := os.getenv("LINGUA_NEXUS_AYA_GPU_LAYERS"):
            try:
                env_overrides["n_gpu_layers"] = int(n_gpu_layers)
            except ValueError:
                pass
        
        return env_overrides
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "model_path": self.model_path,
            "device": self.device,
            "device_map": self.device_map,
            "use_gguf": self.use_gguf,
            "gguf_filename": self.gguf_filename,
            "n_ctx": self.n_ctx,
            "n_gpu_layers": self.n_gpu_layers,
            "max_length": self.max_length,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "do_sample": self.do_sample,
            "use_quantization": self.use_quantization,
            "load_in_8bit": self.load_in_8bit,
            "batch_size": self.batch_size,
            "num_beams": self.num_beams,
            "use_cache": self.use_cache,
            "memory_requirements": self.memory_requirements,
            "supported_languages": self.supported_languages,
            "model_options": self.model_options,
            "custom_prompt_template": self.custom_prompt_template
        }
    
    def __str__(self) -> str:
        """String representation of configuration."""
        return f"AyaExpanse8BConfig(model_path={self.model_path}, device={self.device}, max_length={self.max_length})"