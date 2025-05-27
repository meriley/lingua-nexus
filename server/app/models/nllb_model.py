"""
NLLB model implementation for the multi-model translation system.

This module provides the NLLB (No Language Left Behind) model implementation
that integrates with the abstract translation interface.
"""

import os
import time
import torch
import logging
from typing import Dict, List, Optional, Any
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline

from .base import (
    TranslationModel, 
    TranslationRequest, 
    TranslationResponse,
    ModelInitializationError,
    TranslationError,
    LanguageDetectionError
)
from ..utils.language_codes import LanguageCodeConverter

logger = logging.getLogger(__name__)


class NLLBModel(TranslationModel):
    """NLLB model implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize NLLB model with configuration.
        
        Args:
            config: Configuration dictionary containing:
                - model_path: Path or name of the model (default: facebook/nllb-200-distilled-600M)
                - device: Device to use ('cpu', 'cuda', 'auto')
                - max_length: Maximum translation length (default: 512)
                - use_pipeline: Whether to use transformers pipeline (default: True)
        """
        super().__init__(config)
        
        # Model configuration
        self.model_path = config.get('model_path', 'facebook/nllb-200-distilled-600M')
        self.device = self._determine_device(config.get('device', 'auto'))
        self.max_length = config.get('max_length', 512)
        self.use_pipeline = config.get('use_pipeline', True)
        
        # Model components
        self.model = None
        self.tokenizer = None
        self.translator_pipeline = None
        
        # Load model
        self._load_model()
    
    def _determine_device(self, device_config: str) -> str:
        """Determine the appropriate device to use."""
        if device_config == 'auto':
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device_config
    
    def _load_model(self):
        """Load NLLB model and tokenizer."""
        try:
            logger.info(f"Loading NLLB model: {self.model_path} on {self.device}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            
            # Load model with memory optimizations
            torch_dtype = torch.float16 if self.device == "cuda" else torch.float32
            
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_path,
                low_cpu_mem_usage=True,
                torch_dtype=torch_dtype
            )
            self.model.to(self.device)
            
            # Create pipeline if requested
            if self.use_pipeline:
                device_id = 0 if self.device == "cuda" else -1
                self.translator_pipeline = pipeline(
                    "translation",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    device=device_id
                )
            
            self._initialized = True
            logger.info(f"NLLB model loaded successfully on {self.device}")
            
        except Exception as e:
            error_msg = f"Failed to load NLLB model: {e}"
            logger.error(error_msg)
            raise ModelInitializationError(error_msg)
    
    async def translate(self, request: TranslationRequest) -> TranslationResponse:
        """
        Translate text using NLLB model.
        
        Args:
            request: TranslationRequest containing text and language parameters
            
        Returns:
            TranslationResponse with translated text and metadata
        """
        self.validate_request(request)
        start_time = time.time()
        
        try:
            # Convert ISO codes to NLLB format
            source_lang = request.source_lang
            detected_source = None
            
            # Handle auto-detection
            if not source_lang or source_lang == 'auto':
                detected_source = await self.detect_language(request.text)
                source_lang = detected_source
            
            # Convert to NLLB language codes
            nllb_source = LanguageCodeConverter.to_model_code(source_lang, 'nllb')
            nllb_target = LanguageCodeConverter.to_model_code(request.target_lang, 'nllb')
            
            # Perform translation
            if self.use_pipeline:
                translated_text = self._translate_with_pipeline(
                    request.text, nllb_source, nllb_target
                )
            else:
                translated_text = self._translate_with_model(
                    request.text, nllb_source, nllb_target
                )
            
            processing_time = (time.time() - start_time) * 1000
            
            return TranslationResponse(
                translated_text=translated_text,
                detected_source_lang=detected_source,
                processing_time_ms=processing_time,
                model_used=self.model_name,
                metadata={
                    "source_lang_code": nllb_source,
                    "target_lang_code": nllb_target,
                    "device": self.device,
                    "use_pipeline": self.use_pipeline
                }
            )
            
        except Exception as e:
            error_msg = f"NLLB translation failed: {e}"
            logger.error(error_msg)
            raise TranslationError(error_msg)
    
    def _translate_with_pipeline(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate using transformers pipeline."""
        translation = self.translator_pipeline(
            text,
            src_lang=source_lang,
            tgt_lang=target_lang,
            max_length=min(len(text) * 2, self.max_length)
        )
        return translation[0]["translation_text"]
    
    def _translate_with_model(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate using model directly."""
        # Tokenize input
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Get target language token ID
        target_lang_id = self.tokenizer.lang_code_to_id.get(target_lang)
        if target_lang_id is None:
            raise ValueError(f"Target language '{target_lang}' not supported by NLLB tokenizer")
        
        # Generate translation
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                forced_bos_token_id=target_lang_id,
                max_length=self.max_length,
                num_beams=4,
                early_stopping=True
            )
        
        # Decode output
        translated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return translated_text
    
    def get_supported_languages(self) -> List[str]:
        """Return supported ISO language codes."""
        return list(LanguageCodeConverter.get_supported_languages('nllb'))
    
    async def detect_language(self, text: str) -> str:
        """
        Detect language using character analysis.
        
        This is a simple implementation. In production, consider using
        libraries like langdetect or fasttext for better accuracy.
        """
        try:
            if not text or not text.strip():
                return "en"  # Default for empty strings
            
            text = text.lower()
            
            # Count Cyrillic characters and letters
            cyrillic_chars = sum(1 for c in text if 0x0400 <= ord(c) <= 0x04FF)
            latin_letters = sum(1 for c in text if 'a' <= c <= 'z')
            
            # Count actual letters (Cyrillic + Latin) to ignore punctuation and numbers
            letter_count = cyrillic_chars + latin_letters
            
            # If no meaningful letters found, default to English
            if letter_count == 0:
                return "en"
            
            # Calculate percentage of Cyrillic letters among all letters
            cyrillic_percentage = cyrillic_chars / letter_count if letter_count > 0 else 0
            
            # Lower threshold for mixed content makes it more sensitive to Cyrillic
            # Predominantly Russian texts typically have > 60% Cyrillic letters
            is_russian = cyrillic_percentage > 0.25
            
            detected_lang = "ru" if is_russian else "en"
            logger.debug(f"Detected language: {detected_lang} (Cyrillic: {cyrillic_percentage:.2%})")
            
            return detected_lang
            
        except Exception as e:
            error_msg = f"Language detection failed: {e}"
            logger.error(error_msg)
            raise LanguageDetectionError(error_msg)
    
    def is_available(self) -> bool:
        """Check if model is loaded and ready."""
        return (
            self._initialized and 
            self.model is not None and 
            self.tokenizer is not None
        )
    
    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata."""
        return {
            "name": self.model_name,
            "type": "nllb",
            "model_path": self.model_path,
            "device": self.device,
            "max_length": self.max_length,
            "use_pipeline": self.use_pipeline,
            "available": self.is_available(),
            "torch_dtype": str(self.model.dtype) if self.model else None,
            "model_size": self._get_model_size() if self.model else None
        }
    
    def _get_model_size(self) -> Optional[str]:
        """Get approximate model size in memory."""
        try:
            if self.model is None:
                return None
            
            param_size = sum(p.numel() for p in self.model.parameters())
            
            # Approximate size calculation
            if self.device == "cuda":
                # FP16 on GPU
                size_mb = param_size * 2 / (1024 ** 2)
            else:
                # FP32 on CPU
                size_mb = param_size * 4 / (1024 ** 2)
            
            if size_mb > 1024:
                return f"{size_mb / 1024:.1f} GB"
            else:
                return f"{size_mb:.1f} MB"
                
        except Exception:
            return None
    
    def supports_language_pair(self, source_lang: str, target_lang: str) -> bool:
        """Check if model supports translation between given language pair."""
        supported = self.get_supported_languages()
        
        # Special handling for auto-detection
        if source_lang == 'auto':
            return target_lang in supported
            
        return source_lang in supported and target_lang in supported
    
    def cleanup(self):
        """Clean up model resources."""
        try:
            if self.model is not None:
                del self.model
                self.model = None
            
            if self.tokenizer is not None:
                del self.tokenizer
                self.tokenizer = None
                
            if self.translator_pipeline is not None:
                del self.translator_pipeline
                self.translator_pipeline = None
            
            # Clear CUDA cache if using GPU
            if self.device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self._initialized = False
            logger.info(f"NLLB model {self.model_name} cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during NLLB model cleanup: {e}")
    
    def __del__(self):
        """Cleanup on deletion."""
        self.cleanup()