"""
Aya Expanse 8B model implementation for the single-model translation architecture.

This module provides the Aya Expanse 8B GGUF model implementation that integrates
with the enhanced TranslationModel interface for single-model-per-instance deployment.
"""

import os
import time
import torch
import logging
from typing import Dict, List, Optional, Any, Union

from transformers import (
    AutoModelForSeq2SeqLM, 
    AutoTokenizer, 
    BitsAndBytesConfig,
    pipeline
)

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False

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
from .config import AyaExpanse8BConfig

# Import utilities from server (relative imports for compatibility)
try:
    from server.app.utils.language_codes import LanguageCodeConverter
    from server.app.utils.model_compat import (
        get_device,
        get_device_map,
        check_memory_availability,
        prepare_model_kwargs,
        clear_memory_cache,
        get_model_memory_footprint
    )
except ImportError:
    # Fallback for when running from model directory
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'server'))
    from app.utils.language_codes import LanguageCodeConverter
    from app.utils.model_compat import (
        get_device,
        get_device_map,
        check_memory_availability,
        prepare_model_kwargs,
        clear_memory_cache,
        get_model_memory_footprint
    )

logger = logging.getLogger(__name__)


class AyaExpanse8BModel(TranslationModel):
    """
    Aya Expanse 8B model implementation.
    
    This class implements the TranslationModel interface for Aya Expanse 8B
    in a single-model-per-instance architecture using GGUF format for efficiency.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Aya Expanse 8B model.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = AyaExpanse8BConfig.from_dict(config or {})
        self.model = None
        self.tokenizer = None
        self.text_generator = None
        self._initialized = False
        self._model_info = None
        
        logger.info(f"Initializing Aya Expanse 8B model with config: {self.config}")
    
    async def initialize(self) -> None:
        """Initialize model resources (weights, tokenizer, etc.)."""
        try:
            logger.info(f"Loading Aya Expanse 8B model from {self.config.model_path}")
            
            if self.config.use_gguf and LLAMA_CPP_AVAILABLE:
                await self._load_gguf_model()
            else:
                await self._load_transformers_model()
            
            self._initialized = True
            logger.info("Aya Expanse 8B model initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Aya Expanse 8B model: {e}")
            raise ModelInitializationError(f"Failed to load model: {e}", "aya-expanse-8b")
    
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
            raise ModelNotReadyError("Model not initialized", "aya-expanse-8b")
        
        # Validate language support
        if not self._supports_language_pair(source_lang, target_lang):
            raise UnsupportedLanguageError(source_lang, target_lang, "aya-expanse-8b")
        
        try:
            logger.debug(f"Translating text from {source_lang} to {target_lang}")
            
            # Handle language detection if needed
            if source_lang == 'auto':
                detected_source = await self._detect_language(text)
                source_lang = detected_source
            
            # Convert ISO codes to Aya language names
            source_lang_name = LanguageCodeConverter.to_model_code(source_lang, 'aya')
            target_lang_name = LanguageCodeConverter.to_model_code(target_lang, 'aya')
            
            # Create translation prompt
            prompt = self._create_translation_prompt(text, source_lang_name, target_lang_name)
            
            # Generate translation
            if self.config.use_gguf and LLAMA_CPP_AVAILABLE:
                generated_text = await self._generate_gguf(prompt)
            else:
                generated_text = await self._generate_transformers(prompt)
            
            # Parse and clean the response
            translated_text = self._parse_translation_response(generated_text, text)
            
            # Fallback if translation seems empty
            if not translated_text or len(translated_text.strip()) < 2:
                logger.warning("Empty translation result, using raw generation")
                translated_text = generated_text.strip()
            
            logger.debug(f"Translation completed: {translated_text[:100]}")
            return translated_text
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise TranslationError(f"Translation failed: {e}", "aya-expanse-8b")
    
    async def health_check(self) -> bool:
        """Verify model readiness for inference."""
        try:
            if not self._initialized or self.model is None:
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
                name="aya-expanse-8b",
                version=self.config.model_version,
                supported_languages=self.config.supported_languages,
                max_tokens=self.config.max_length,
                memory_requirements=self.config.memory_requirements,
                description="Aya Expanse 8B multilingual translation model (GGUF format)"
            )
        return self._model_info
    
    async def cleanup(self) -> None:
        """Clean up model resources."""
        try:
            logger.info("Cleaning up Aya Expanse 8B model resources")
            
            if self.text_generator is not None:
                del self.text_generator
                self.text_generator = None
            
            if self.model is not None:
                if self.config.use_gguf and LLAMA_CPP_AVAILABLE and hasattr(self.model, 'close'):
                    self.model.close()
                del self.model
                self.model = None
            
            if self.tokenizer is not None:
                del self.tokenizer
                self.tokenizer = None
            
            clear_memory_cache()
            self._initialized = False
            logger.info("Aya Expanse 8B model cleanup completed")
            
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def _supports_language_pair(self, source_lang: str, target_lang: str) -> bool:
        """Check if model supports the given language pair."""
        supported = self.config.supported_languages
        
        # Special handling for auto-detection
        if source_lang == 'auto':
            return target_lang in supported
            
        return source_lang in supported and target_lang in supported
    
    async def _load_gguf_model(self):
        """Load model using GGUF format with llama-cpp-python."""
        if not LLAMA_CPP_AVAILABLE:
            raise ModelInitializationError("llama-cpp-python is required for GGUF models but not installed")
        
        logger.info(f"Loading GGUF model from {self.config.model_path}: {self.config.gguf_filename}")
        
        # Progressive quantization fallback
        quantization_fallback = [
            self.config.gguf_filename,
            'aya-expanse-8b-Q4_K_M.gguf',
            'aya-expanse-8b-Q3_K_M.gguf',
            'aya-expanse-8b-Q2_K.gguf'
        ]
        
        # Remove duplicates while preserving order
        unique_fallback = []
        for filename in quantization_fallback:
            if filename not in unique_fallback:
                unique_fallback.append(filename)
        
        from huggingface_hub import hf_hub_download
        
        model_file = None
        successful_filename = None
        
        # Try each quantization level
        for filename in unique_fallback:
            try:
                logger.info(f"Attempting to download GGUF file: {filename}")
                model_file = hf_hub_download(
                    repo_id=self.config.model_path,
                    filename=filename,
                    cache_dir=os.environ.get('HF_HOME', '/app/.cache/huggingface')
                )
                successful_filename = filename
                logger.info(f"Successfully downloaded GGUF file: {model_file}")
                break
            except Exception as e:
                logger.warning(f"Failed to download {filename}: {e}")
                continue
        
        if model_file is None:
            raise ModelInitializationError(f"Failed to download any GGUF files from {self.config.model_path}")
        
        # Update config with successful filename
        self.config.gguf_filename = successful_filename
        
        # Initialize llama.cpp model
        try:
            self.model = Llama(
                model_path=model_file,
                n_ctx=self.config.n_ctx,
                n_gpu_layers=self.config.n_gpu_layers,
                verbose=False,
                use_mmap=True,
                use_mlock=False,
                n_threads=None,
                n_batch=512,
                seed=-1
            )
            logger.info(f"GGUF model '{successful_filename}' loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize GGUF model: {e}")
            raise ModelInitializationError(f"Failed to initialize GGUF model: {e}")
    
    async def _load_transformers_model(self):
        """Load model using transformers library (fallback)."""
        logger.info("Loading model using transformers library")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_path,
            trust_remote_code=True
        )
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Prepare model configuration
        model_config = {
            'device': self.config.device,
            'torch_dtype': 'auto',
            'trust_remote_code': True,
            'low_cpu_mem_usage': True,
            'use_cache': True
        }
        
        # Add quantization config if enabled
        if self.config.use_quantization:
            quantization_config = self._get_quantization_config()
            if quantization_config:
                model_config['quantization_config'] = quantization_config
        
        model_kwargs = prepare_model_kwargs(model_config)
        
        # Load model
        try:
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.config.model_path,
                **model_kwargs
            )
        except Exception as e:
            # Retry without quantization if it fails
            if 'quantization_config' in model_kwargs:
                logger.warning("Retrying without quantization")
                fallback_kwargs = {k: v for k, v in model_kwargs.items() if k != 'quantization_config'}
                self.model = AutoModelForSeq2SeqLM.from_pretrained(
                    self.config.model_path,
                    **fallback_kwargs
                )
            else:
                raise e
        
        # Create text generation pipeline
        device_id = 0 if self.config.device.startswith('cuda') else -1
        self.text_generator = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            device=device_id,
            return_full_text=False,
            pad_token_id=self.tokenizer.eos_token_id
        )
    
    def _get_quantization_config(self) -> Optional[BitsAndBytesConfig]:
        """Get quantization configuration for memory optimization."""
        try:
            import bitsandbytes as bnb
            
            if self.config.load_in_8bit:
                return BitsAndBytesConfig(
                    load_in_8bit=True,
                    bnb_8bit_compute_dtype=torch.float16,
                    bnb_8bit_quant_type="int8",
                    bnb_8bit_use_double_quant=False
                )
            else:
                return BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_compute_dtype=torch.float16
                )
        except Exception as e:
            logger.warning(f"Failed to create quantization config: {e}")
            return None
    
    def _create_translation_prompt(self, text: str, source_lang: str, target_lang: str) -> str:
        """Create translation prompt for Aya model."""
        if self.config.custom_prompt_template:
            return self.config.custom_prompt_template.format(
                source_lang=source_lang,
                target_lang=target_lang,
                text=text
            )
        
        system_prompt = f"You are a helpful multilingual translation assistant. Translate accurately from {source_lang} to {target_lang}."
        user_prompt = f"Translate the following text from {source_lang} to {target_lang}. Return only the translation without any additional text or explanation.\n\nText to translate: {text}"
        
        if self.config.use_gguf and LLAMA_CPP_AVAILABLE:
            return f"<|START_OF_TURN_TOKEN|><|SYSTEM_TOKEN|>{system_prompt}<|END_OF_TURN_TOKEN|><|START_OF_TURN_TOKEN|><|USER_TOKEN|>{user_prompt}<|END_OF_TURN_TOKEN|><|START_OF_TURN_TOKEN|><|CHATBOT_TOKEN|>"
        else:
            return f"<|SYSTEM|>{system_prompt}<|USER|>{user_prompt}<|ASSISTANT|>"
    
    async def _generate_gguf(self, prompt: str) -> str:
        """Generate text using GGUF model."""
        generation_config = {
            "max_tokens": self.config.max_length,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "repeat_penalty": 1.0,
            "echo": False
        }
        
        try:
            response = self.model(prompt, **generation_config)
            choice = response['choices'][0] if response.get('choices') else {}
            return choice.get('text', '')
        except Exception as e:
            logger.error(f"GGUF generation failed: {e}")
            raise TranslationError(f"Text generation failed: {e}")
    
    async def _generate_transformers(self, prompt: str) -> str:
        """Generate text using transformers pipeline."""
        generation_config = {
            "max_length": len(prompt) + self.config.max_length,
            "max_new_tokens": self.config.max_length,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "do_sample": self.config.do_sample,
            "pad_token_id": self.tokenizer.eos_token_id,
            "eos_token_id": self.tokenizer.eos_token_id
        }
        
        try:
            generated = self.text_generator(prompt, **generation_config)
            return generated[0]["generated_text"]
        except Exception as e:
            logger.error(f"Transformers generation failed: {e}")
            raise TranslationError(f"Text generation failed: {e}")
    
    def _parse_translation_response(self, generated_text: str, original_text: str) -> str:
        """Parse and clean the generated translation response."""
        translation = generated_text.strip()
        
        # Remove potential repetition of original text
        if original_text in translation:
            translation = translation.replace(original_text, "").strip()
        
        # Remove common prefixes
        prefixes_to_remove = [
            "Translation:", "Translated text:", "Output:", "Result:",
            "The translation is:", "Here is the translation:",
            "Translated:", "Answer:"
        ]
        
        for prefix in prefixes_to_remove:
            if translation.lower().startswith(prefix.lower()):
                translation = translation[len(prefix):].strip()
        
        # Remove quotes if entire translation is quoted
        if (translation.startswith('"') and translation.endswith('"')) or \
           (translation.startswith("'") and translation.endswith("'")):
            translation = translation[1:-1].strip()
        
        return translation
    
    async def _detect_language(self, text: str) -> str:
        """Detect language using character-based analysis."""
        try:
            # Simple character-based detection
            text_lower = text.lower()
            
            # Count Cyrillic characters
            cyrillic_chars = sum(1 for c in text_lower if 0x0400 <= ord(c) <= 0x04FF)
            latin_letters = sum(1 for c in text_lower if 'a' <= c <= 'z')
            
            letter_count = cyrillic_chars + latin_letters
            
            if letter_count == 0:
                return "en"
            
            cyrillic_percentage = cyrillic_chars / letter_count
            return "ru" if cyrillic_percentage > 0.25 else "en"
            
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            return "en"