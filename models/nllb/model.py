"""
NLLB model implementation for the single-model translation architecture.

This module provides the NLLB (No Language Left Behind) model implementation
that integrates with the enhanced TranslationModel interface for single-model-per-instance deployment.
"""

import os
import time
import torch
import logging
from typing import Dict, List, Optional, Any

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline

from models.base import (
    TranslationModel,
    ModelInfo,
    ModelInitializationError,
    TranslationError,
    LanguageDetectionError,
    UnsupportedLanguageError,
    ResourceError,
    ModelNotReadyError
)
from .config import NLLBConfig

# Import utilities from server (relative imports for compatibility)
try:
    from server.app.utils.language_codes import LanguageCodeConverter
except ImportError:
    # Fallback for when running from model directory
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'server'))
    from app.utils.language_codes import LanguageCodeConverter

logger = logging.getLogger(__name__)


class NLLBModel(TranslationModel):
    """
    NLLB model implementation.
    
    This class implements the TranslationModel interface for NLLB (No Language Left Behind)
    in a single-model-per-instance architecture using transformers.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize NLLB model.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = NLLBConfig.from_dict(config or {})
        self.model = None
        self.tokenizer = None
        self.translator_pipeline = None
        self._initialized = False
        self._model_info = None
        
        logger.info(f"Initializing NLLB model with config: {self.config}")
    
    async def initialize(self) -> None:
        """Initialize model resources (weights, tokenizer, etc.)."""
        try:
            logger.info(f"Loading NLLB model from {self.config.model_path}")
            
            # Determine device
            device = self._determine_device(self.config.device)
            self.config.device = device
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_path)
            
            # Load model with memory optimizations
            torch_dtype = torch.float16 if device == "cuda" else torch.float32
            
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.config.model_path,
                low_cpu_mem_usage=True,
                torch_dtype=torch_dtype
            )
            self.model.to(device)
            
            # Create pipeline if requested
            if self.config.use_pipeline:
                device_id = 0 if device == "cuda" else -1
                self.translator_pipeline = pipeline(
                    "translation",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    device=device_id
                )
            
            self._initialized = True
            logger.info(f"NLLB model loaded successfully on {device}")
            
        except Exception as e:
            logger.error(f"Failed to initialize NLLB model: {e}")
            raise ModelInitializationError(f"Failed to load model: {e}", "nllb")
    
    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Perform text translation.
        
        Args:
            text: Input text to translate
            source_lang: Source language code (ISO 639-1)
            target_lang: Target language code (ISO 639-1)
            
        Returns:
            Translated text string
        """
        if not self._initialized:
            raise ModelNotReadyError("Model not initialized", "nllb")
        
        # Validate language support
        if not self._supports_language_pair(source_lang, target_lang):
            raise UnsupportedLanguageError(source_lang, target_lang, "nllb")
        
        try:
            logger.debug(f"Translating text from {source_lang} to {target_lang}")
            
            # Handle language detection if needed
            if source_lang == 'auto':
                detected_source = await self._detect_language(text)
                source_lang = detected_source
            
            # Convert to NLLB language codes
            nllb_source = LanguageCodeConverter.to_model_code(source_lang, 'nllb')
            nllb_target = LanguageCodeConverter.to_model_code(target_lang, 'nllb')
            
            # Perform translation
            if self.config.use_pipeline:
                translated_text = await self._translate_with_pipeline(text, nllb_source, nllb_target)
            else:
                translated_text = await self._translate_with_model(text, nllb_source, nllb_target)
            
            logger.debug(f"Translation completed: {translated_text[:100]}")
            return translated_text
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise TranslationError(f"Translation failed: {e}", "nllb")
    
    async def health_check(self) -> bool:
        """Verify model readiness for inference."""
        try:
            if not self._initialized or self.model is None or self.tokenizer is None:
                return False
            
            # Perform a quick test translation
            test_result = await self.translate("test", "en", "fr")
            return bool(test_result and len(test_result.strip()) > 0)
            
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    def get_model_info(self) -> ModelInfo:
        """Return model metadata and capabilities."""
        if self._model_info is None:
            self._model_info = ModelInfo(
                name="nllb",
                version=self.config.model_version,
                supported_languages=self.config.supported_languages,
                max_tokens=self.config.max_length,
                memory_requirements=self.config.memory_requirements,
                description="NLLB (No Language Left Behind) 200 multilingual translation model"
            )
        return self._model_info
    
    async def cleanup(self) -> None:
        """Clean up model resources."""
        try:
            logger.info("Cleaning up NLLB model resources")
            
            if self.translator_pipeline is not None:
                del self.translator_pipeline
                self.translator_pipeline = None
            
            if self.model is not None:
                del self.model
                self.model = None
            
            if self.tokenizer is not None:
                del self.tokenizer
                self.tokenizer = None
            
            # Clear CUDA cache if using GPU
            if self.config.device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self._initialized = False
            logger.info("NLLB model cleanup completed")
            
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def _supports_language_pair(self, source_lang: str, target_lang: str) -> bool:
        """Check if model supports the given language pair."""
        supported = self.config.supported_languages
        
        # Special handling for auto-detection
        if source_lang == 'auto':
            return target_lang in supported
            
        return source_lang in supported and target_lang in supported
    
    def _determine_device(self, device_config: str) -> str:
        """Determine the appropriate device to use."""
        if device_config == 'auto':
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device_config
    
    async def _translate_with_pipeline(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate using transformers pipeline."""
        translation = self.translator_pipeline(
            text,
            src_lang=source_lang,
            tgt_lang=target_lang,
            max_length=min(len(text) * 2, self.config.max_length)
        )
        return translation[0]["translation_text"]
    
    async def _translate_with_model(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate using model directly."""
        # Tokenize input
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        inputs = {k: v.to(self.config.device) for k, v in inputs.items()}
        
        # Get target language token ID
        target_lang_id = self.tokenizer.lang_code_to_id.get(target_lang)
        if target_lang_id is None:
            raise ValueError(f"Target language '{target_lang}' not supported by NLLB tokenizer")
        
        # Generate translation
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                forced_bos_token_id=target_lang_id,
                max_length=self.config.max_length,
                num_beams=self.config.num_beams,
                early_stopping=self.config.early_stopping
            )
        
        # Decode output
        translated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return translated_text
    
    async def _detect_language(self, text: str) -> str:
        """
        Detect language using character analysis.
        
        Simple implementation based on character scripts.
        """
        try:
            if not text or not text.strip():
                return "en"
            
            text_lower = text.lower()
            
            # Count Cyrillic characters and letters
            cyrillic_chars = sum(1 for c in text_lower if 0x0400 <= ord(c) <= 0x04FF)
            latin_letters = sum(1 for c in text_lower if 'a' <= c <= 'z')
            
            # Count actual letters to ignore punctuation and numbers
            letter_count = cyrillic_chars + latin_letters
            
            if letter_count == 0:
                return "en"
            
            # Calculate percentage of Cyrillic letters
            cyrillic_percentage = cyrillic_chars / letter_count
            is_russian = cyrillic_percentage > 0.25
            
            detected_lang = "ru" if is_russian else "en"
            logger.debug(f"Detected language: {detected_lang} (Cyrillic: {cyrillic_percentage:.2%})")
            
            return detected_lang
            
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            return "en"