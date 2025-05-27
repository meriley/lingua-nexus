"""Legacy NLLB Model Loader

⚠️  DEPRECATED: This module is part of the legacy NLLB-only architecture.

For new applications, use the modern multi-model architecture:
- app/models/registry.py - Model factory and registration system
- app/models/nllb_model.py - Modern NLLB model implementation
- app/models/aya_model.py - Aya model with GGUF optimization
- app/models/base.py - Abstract model interface

Migration Path:
1. Replace direct model loading with ModelRegistry.get_model()
2. Use model-specific implementations instead of generic functions
3. Leverage model registry for multi-model support

This module is maintained for backward compatibility only.
"""

import os
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline

# Legacy NLLB-specific configuration
# NOTE: In multi-model architecture, configuration is handled per-model
MODEL_NAME = os.getenv("MODEL_NAME", "facebook/nllb-200-distilled-600M")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MAX_LENGTH = 512  # Legacy fixed max length - modern models use adaptive sizing

def load_nllb_model():
    """Load the NLLB translation model and tokenizer with optimizations.
    
    ⚠️  DEPRECATED: Use ModelRegistry.get_model('nllb') instead.
    
    This function provides the legacy NLLB model loading approach.
    The modern multi-model architecture uses:
    - Model registry for centralized model management
    - Per-model configuration and optimization
    - Lazy loading and memory management
    - Cross-model compatibility layers
    
    Returns:
        tuple: (model, tokenizer) - NLLB model and tokenizer instances
        
    Raises:
        Exception: If model loading fails
        
    Migration:
        Replace with:
        ```python
        from app.models.registry import ModelRegistry
        model = ModelRegistry.get_model('nllb')
        ```
    """
    print(f"[LEGACY] Loading NLLB model: {MODEL_NAME} on {DEVICE}")
    print("⚠️  Using deprecated model loader. Consider migrating to ModelRegistry.")
    
    # Load tokenizer using legacy approach
    # NOTE: Modern implementation includes tokenizer validation and fallbacks
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    
    # Load model with basic memory optimizations
    # NOTE: Modern implementation includes:
    # - Advanced quantization (GGUF support)
    # - Dynamic memory management
    # - Model-specific optimization strategies
    model = AutoModelForSeq2SeqLM.from_pretrained(
        MODEL_NAME,
        low_cpu_mem_usage=True,  # Basic optimization
        torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32
    )
    model.to(DEVICE)
    
    print(f"[LEGACY] NLLB model loaded successfully on {DEVICE}")
    print("For enhanced performance, consider using the modern model registry.")
    return model, tokenizer

def translate_text(text, model, tokenizer, source_lang, target_lang):
    """Translate text using the loaded NLLB model and tokenizer.
    
    ⚠️  DEPRECATED: Use model.translate() method from modern model classes.
    
    This function provides basic NLLB translation without the advanced
    features available in the modern multi-model architecture:
    - Adaptive chunking for long texts
    - Quality assessment and optimization
    - Cross-model language code conversion
    - Intelligent caching and performance monitoring
    
    Args:
        text (str): Text to translate (limited to MAX_LENGTH)
        model: Loaded NLLB model instance
        tokenizer: Loaded NLLB tokenizer instance
        source_lang (str): NLLB source language code (e.g., "eng_Latn", "rus_Cyrl")
        target_lang (str): NLLB target language code
        
    Returns:
        str: Translated text
        
    Raises:
        Exception: If translation fails
        
    Limitations:
        - Fixed max length (no adaptive chunking)
        - No quality assessment
        - No caching
        - NLLB language codes only
        
    Migration:
        Use the modern approach:
        ```python
        from app.models.registry import ModelRegistry
        model = ModelRegistry.get_model('nllb')
        result = model.translate(text, source_lang, target_lang)
        ```
    """
    # Create legacy translation pipeline
    # NOTE: Modern implementation uses optimized model-specific pipelines
    # with better memory management and error handling
    translator = pipeline(
        "translation", 
        model=model, 
        tokenizer=tokenizer, 
        device=0 if DEVICE == "cuda" else -1
    )
    
    # Perform basic translation with fixed length limits
    # LIMITATION: No adaptive chunking for long texts like modern implementation
    translation = translator(
        text,
        src_lang=source_lang,
        tgt_lang=target_lang,
        max_length=min(len(text) * 2, MAX_LENGTH)  # Fixed limit vs adaptive sizing
    )
    
    # Extract translated text (basic approach)
    # Modern implementation includes quality validation and fallback handling
    translated_text = translation[0]["translation_text"]
    
    # Legacy: Return raw translation without quality assessment
    # Modern implementation includes confidence scoring and validation
    return translated_text