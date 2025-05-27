"""
Aya Expanse 8B model implementation for the multi-model translation system.

This module provides the Aya Expanse 8B GGUF model implementation
that integrates with the abstract translation interface using GGUF format
for efficient CPU inference.
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

from .base import (
    TranslationModel, 
    TranslationRequest, 
    TranslationResponse,
    ModelInitializationError,
    TranslationError,
    LanguageDetectionError
)
from ..utils.language_codes import LanguageCodeConverter
from ..utils.model_compat import (
    get_device,
    get_device_map,
    check_memory_availability,
    prepare_model_kwargs,
    clear_memory_cache,
    get_model_memory_footprint
)

logger = logging.getLogger(__name__)


class AyaModel(TranslationModel):
    """Aya Expanse 8B model implementation using instruction-following approach."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Aya Expanse 8B model with configuration.
        
        Args:
            config: Configuration dictionary containing:
                - model_path: Path or name of the model (default: CohereForAI/aya-23-8B)
                - device: Device to use ('cpu', 'cuda', 'auto')
                - max_length: Maximum generation length (default: 512)
                - temperature: Generation temperature (default: 0.3)
                - top_p: Top-p sampling (default: 0.9)
                - use_quantization: Enable quantization (default: True for GPU)
                - load_in_8bit: Use 8-bit quantization instead of 4-bit (default: True)
                - custom_prompt_template: Custom prompt template override
        """
        super().__init__(config)
        
        # Model configuration - use GGUF model by default
        default_path = 'bartowski/aya-expanse-8b-GGUF'
        self.model_path = config.get('model_path', default_path)
        self.device = self._determine_device(config.get('device', 'auto'))
        self.max_length = config.get('max_length', 3072)  # Increased for longer translations to prevent truncation
        self.temperature = config.get('temperature', 0.1)  # Lowered for more deterministic translation output
        self.top_p = config.get('top_p', 0.9)
        self.use_quantization = config.get('use_quantization', self.device == 'cuda')
        self.load_in_8bit = config.get('load_in_8bit', True)  # Default to 8-bit
        self.custom_prompt_template = config.get('custom_prompt_template')
        
        # GGUF-specific configuration
        self.use_gguf = config.get('use_gguf', LLAMA_CPP_AVAILABLE)  # Only use GGUF if available
        self.gguf_filename = config.get('gguf_filename', 'aya-expanse-8b-Q4_K_M.gguf')  # Medium quantization
        self.n_ctx = config.get('n_ctx', 8192)  # Full Aya context window (8K)
        self.n_gpu_layers = config.get('n_gpu_layers', 20 if self.device.startswith('cuda') else 0)  # Optimal 20 layers on GPU if CUDA
        
        # Model components
        self.model = None
        self.tokenizer = None
        self.text_generator = None
        
        # Load model
        self._load_model()
    
    def _determine_device(self, device_config: str) -> str:
        """Determine the appropriate device to use."""
        device = get_device(device_config)
        return device.type if device.index is None else f"{device.type}:{device.index}"
    
    def _get_quantization_config(self) -> Optional[BitsAndBytesConfig]:
        """Get quantization configuration for memory optimization."""
        if not self.use_quantization or self.device == 'cpu':
            return None
        
        # Check if bitsandbytes is properly installed and working
        try:
            import bitsandbytes as bnb
            
            # Test if CUDA libraries are available by trying a simple operation
            if torch.cuda.is_available():
                try:
                    # Create a small test tensor and try quantization
                    test_tensor = torch.tensor([1.0], dtype=torch.float16, device='cuda')
                    # This will fail if CUDA libraries are missing
                    _ = bnb.functional.int8_vectorwise_quant(test_tensor)
                    logger.debug("bitsandbytes CUDA validation successful")
                except Exception as cuda_error:
                    logger.warning(f"bitsandbytes CUDA test failed: {cuda_error}")
                    logger.info("Disabling quantization due to CUDA library issues")
                    # Disable quantization for this instance to prevent crashes
                    self.use_quantization = False
                    return None
                    
        except ImportError:
            logger.warning("bitsandbytes not available, disabling quantization")
            self.use_quantization = False
            return None
        except Exception as import_error:
            logger.warning(f"bitsandbytes validation failed: {import_error}")
            self.use_quantization = False
            return None
            
        try:
            if self.load_in_8bit:
                # 8-bit quantization (more accurate, uses ~16GB for 8B model)
                return BitsAndBytesConfig(
                    load_in_8bit=True,
                    bnb_8bit_compute_dtype=torch.float16,
                    bnb_8bit_quant_type="int8",
                    bnb_8bit_use_double_quant=False
                )
            else:
                # 4-bit quantization (more memory efficient, uses ~8GB for 8B model)
                return BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_compute_dtype=torch.float16
                )
        except Exception as e:
            logger.warning(f"Failed to create quantization config: {e}")
            self.use_quantization = False
            return None
    
    def _load_model(self):
        """Load Aya Expanse 8B model using GGUF format."""
        try:
            logger.info(f"Loading Aya Expanse model: {self.model_path} on {self.device}")
            
            if self.use_gguf and LLAMA_CPP_AVAILABLE:
                self._load_gguf_model()
            else:
                self._load_transformers_model()
            
            self._initialized = True
            logger.info(f"Aya Expanse model loaded successfully on {self.device}")
            
        except Exception as e:
            error_msg = f"Failed to load Aya Expanse model: {e}"
            logger.error(error_msg)
            # Clear memory on failure
            clear_memory_cache()
            raise ModelInitializationError(error_msg)
    
    def _load_gguf_model(self):
        """Load model using GGUF format with llama-cpp-python and progressive quantization fallback."""
        if not LLAMA_CPP_AVAILABLE:
            raise ModelInitializationError("llama-cpp-python is required for GGUF models but not installed")
        
        logger.info(f"Loading GGUF model from {self.model_path}: {self.gguf_filename}")
        
        # Progressive quantization fallback sequence
        quantization_fallback = [
            self.gguf_filename,  # Use configured quantization first
            'aya-expanse-8b-Q4_K_M.gguf',  # Recommended medium quantization (5.06GB)
            'aya-expanse-8b-Q3_K_M.gguf',  # Lower quantization fallback (4.05GB)
            'aya-expanse-8b-Q2_K.gguf'     # Lowest fallback (3.08GB)
        ]
        
        # Remove duplicates while preserving order
        unique_fallback = []
        for filename in quantization_fallback:
            if filename not in unique_fallback:
                unique_fallback.append(filename)
        
        # For GGUF models, we need to download the specific GGUF file
        from huggingface_hub import hf_hub_download
        
        model_file = None
        successful_filename = None
        
        # Try each quantization level
        for filename in unique_fallback:
            try:
                logger.info(f"Attempting to download GGUF file: {filename}")
                model_file = hf_hub_download(
                    repo_id=self.model_path,
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
            raise ModelInitializationError(f"Failed to download any GGUF files from {self.model_path}. Tried: {unique_fallback}")
        
        # Update filename to what actually worked
        self.gguf_filename = successful_filename
        
        # Initialize llama.cpp model with memory optimization
        try:
            # Calculate memory limits (6GB target)
            available_memory_gb = 6.0
            
            # Use full context window for better translation quality
            context_window = self.n_ctx  # Use full 8K context for better translations
            
            self.model = Llama(
                model_path=model_file,
                n_ctx=context_window,
                n_gpu_layers=self.n_gpu_layers,
                verbose=False,
                use_mmap=True,
                use_mlock=False,  # Disable mlock to allow swapping if needed
                n_threads=None,  # Use default CPU thread count
                n_batch=512,  # Reasonable batch size for CPU
                seed=-1  # Random seed
            )
            logger.info(f"GGUF model '{successful_filename}' loaded successfully")
            logger.info(f"Configuration: ctx={context_window}, gpu_layers={self.n_gpu_layers}")
        except Exception as e:
            logger.error(f"Failed to initialize GGUF model: {e}")
            raise ModelInitializationError(f"Failed to initialize GGUF model: {e}")
        
        # For GGUF models, we don't need a separate tokenizer as it's built-in
        self.tokenizer = None
        self.text_generator = None  # We'll use direct model generation
    
    def _load_transformers_model(self):
        """Load model using transformers library (fallback)."""
        logger.info("Loading model using transformers library")
        
        # Check memory availability based on quantization settings
        if not self.use_quantization:
            required_memory = 32  # FP16 needs ~32GB for 8B model
        elif self.load_in_8bit:
            required_memory = 16  # 8-bit needs ~16GB
        else:
            required_memory = 8   # 4-bit needs ~8GB
        if not check_memory_availability(required_memory, self.device):
            logger.warning(f"Insufficient memory for model on {self.device}, attempting with quantization")
            self.use_quantization = True
            required_memory = 16
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path,
            trust_remote_code=True
        )
        
        # Set pad token if not exists
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Prepare model loading configuration
        model_config = {
            'device': self.device,
            'torch_dtype': 'auto',
            'trust_remote_code': True,
            'low_cpu_mem_usage': True,
            'use_cache': True
        }
        
        # Add quantization config if enabled
        quantization_config = self._get_quantization_config()
        if quantization_config:
            model_config['quantization_config'] = quantization_config
            quant_type = "8-bit" if self.load_in_8bit else "4-bit"
            logger.info(f"Using {quant_type} quantization for memory optimization")
        
        # Get model loading kwargs with compatibility adjustments
        model_kwargs = prepare_model_kwargs(model_config)
        
        # Add device map for multi-GPU or specific device handling
        if self.device == 'auto' or self.device.startswith('cuda'):
            device_map = get_device_map(required_memory)
            if isinstance(device_map, dict) and device_map:
                model_kwargs['device_map'] = device_map
            elif device_map == 'auto':
                model_kwargs['device_map'] = 'auto'
        
        # Load model with fallback for quantization issues
        try:
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_path,
                **model_kwargs
            )
        except Exception as loading_error:
            # Check if this is a quantization-related error
            error_str = str(loading_error).lower()
            if any(keyword in error_str for keyword in ['bitsandbytes', 'quantization', 'cint8_vector_quant', 'libcusparse']):
                logger.warning(f"Model loading failed with quantization: {loading_error}")
                logger.info("Retrying model loading without quantization...")
                
                # Remove quantization config and retry
                fallback_kwargs = {k: v for k, v in model_kwargs.items() if k != 'quantization_config'}
                fallback_kwargs.update({
                    'torch_dtype': torch.float16,
                    'low_cpu_mem_usage': True,
                    'trust_remote_code': True
                })
                
                self.model = AutoModelForSeq2SeqLM.from_pretrained(
                    self.model_path,
                    **fallback_kwargs
                )
                self.use_quantization = False
                logger.info("Model loaded successfully without quantization")
            else:
                # Re-raise if not quantization-related
                raise loading_error
        
        # Handle device placement if not using device_map
        if 'device_map' not in model_kwargs or model_kwargs['device_map'] is None:
            if not quantization_config and hasattr(self.model, 'to'):
                self.model.to(self.device)
        
        # Create text generation pipeline
        # For pipeline, we need to handle device differently
        if self.device.startswith('cuda'):
            device_id = 0 if self.device == 'cuda' else int(self.device.split(':')[1])
        else:
            device_id = -1  # CPU
        
        self.text_generator = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            device=device_id if 'device_map' not in model_kwargs else None,
            return_full_text=False,  # Only return generated text
            pad_token_id=self.tokenizer.eos_token_id
        )
        
        # Log memory footprint
        if hasattr(self.model, 'parameters'):
            memory_gb = get_model_memory_footprint(self.model)
            logger.info(f"Model memory footprint: {memory_gb:.2f} GB")
    
    def _create_translation_prompt(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str
    ) -> str:
        """
        Create translation prompt for Aya model using proper special token format.
        
        Args:
            text: Text to translate
            source_lang: Source language name
            target_lang: Target language name
            
        Returns:
            Formatted prompt for translation
        """
        if self.custom_prompt_template:
            return self.custom_prompt_template.format(
                source_lang=source_lang,
                target_lang=target_lang,
                text=text
            )
        
        # Aya Expanse specific prompt format with special tokens (official GGUF format)
        # Format: <BOS_TOKEN><|START_OF_TURN_TOKEN|><|SYSTEM_TOKEN|>{system_prompt}<|END_OF_TURN_TOKEN|><|START_OF_TURN_TOKEN|><|USER_TOKEN|>{user_prompt}<|END_OF_TURN_TOKEN|><|START_OF_TURN_TOKEN|><|CHATBOT_TOKEN|><|END_OF_TURN_TOKEN|><|START_OF_TURN_TOKEN|><|CHATBOT_TOKEN|>
        system_prompt = f"You are a helpful multilingual translation assistant. Translate accurately from {source_lang} to {target_lang}."
        user_prompt = f"Translate the following text from {source_lang} to {target_lang}. Return only the translation without any additional text or explanation.\n\nText to translate: {text}"
        
        if self.use_gguf and LLAMA_CPP_AVAILABLE:
            # Use correct Aya Expanse special token format for GGUF (remove leading BOS_TOKEN to avoid duplication)
            return f"<|START_OF_TURN_TOKEN|><|SYSTEM_TOKEN|>{system_prompt}<|END_OF_TURN_TOKEN|><|START_OF_TURN_TOKEN|><|USER_TOKEN|>{user_prompt}<|END_OF_TURN_TOKEN|><|START_OF_TURN_TOKEN|><|CHATBOT_TOKEN|>"
        else:
            # Fallback format for transformers (simplified)
            return f"<|SYSTEM|>{system_prompt}<|USER|>{user_prompt}<|ASSISTANT|>"
    
    def _generate_gguf(self, prompt: str, model_options: Optional[Dict] = None) -> str:
        """Generate text using GGUF model with comprehensive logging."""
        generation_config = {
            "max_tokens": self.max_length,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "repeat_penalty": 1.0,  # Disabled aggressive repetition penalty to prevent early stopping
            "echo": False  # Don't echo the prompt
        }
        
        # Add model-specific options from request
        if model_options:
            generation_config.update(model_options)
        
        # Enable debug mode via environment variable or config
        debug_mode = os.environ.get('GGUF_DEBUG_MODE', 'false').lower() == 'true'
        
        # Pre-generation logging
        prompt_tokens = len(prompt.split())  # Rough token count
        logger.info(f"=== GGUF Generation Start ===")
        logger.info(f"Prompt length: {len(prompt)} chars, ~{prompt_tokens} tokens")
        logger.info(f"Generation config: {generation_config}")
        logger.info(f"Model context window: {self.n_ctx} tokens")
        
        if debug_mode:
            logger.debug(f"Full prompt: {prompt}")
            logger.debug(f"Model GPU layers: {self.n_gpu_layers}")
            logger.debug(f"Model file: {self.gguf_filename}")
        
        try:
            start_time = time.time()
            
            # Generate with comprehensive logging
            response = self.model(prompt, **generation_config)
            
            generation_time = time.time() - start_time
            
            # Extract response details
            choice = response['choices'][0] if response.get('choices') else {}
            generated_text = choice.get('text', '')
            finish_reason = choice.get('finish_reason', 'unknown')
            
            # Extract usage statistics if available
            usage = response.get('usage', {})
            prompt_tokens_actual = usage.get('prompt_tokens', prompt_tokens)
            completion_tokens = usage.get('completion_tokens', len(generated_text.split()))
            total_tokens = usage.get('total_tokens', prompt_tokens_actual + completion_tokens)
            
            # Post-generation logging
            logger.info(f"=== GGUF Generation Complete ===")
            logger.info(f"Generation time: {generation_time:.2f}s")
            logger.info(f"Finish reason: {finish_reason}")
            logger.info(f"Token usage - Prompt: {prompt_tokens_actual}, Completion: {completion_tokens}, Total: {total_tokens}")
            logger.info(f"Generated text length: {len(generated_text)} chars, ~{completion_tokens} tokens")
            logger.info(f"Generated text preview: {generated_text[:200]}{'...' if len(generated_text) > 200 else ''}")
            
            # Debug mode: detailed analysis
            if debug_mode:
                logger.debug(f"Full generated text: {generated_text}")
                logger.debug(f"Full response object: {response}")
                
                # Check for potential truncation indicators
                if finish_reason != 'stop':
                    logger.warning(f"Generation finished with reason: {finish_reason} (not 'stop')")
                
                if completion_tokens >= generation_config['max_tokens'] * 0.95:
                    logger.warning(f"Generation used {completion_tokens}/{generation_config['max_tokens']} tokens (95%+ of limit)")
                
                # Analyze content structure
                lines = generated_text.split('\n')
                paragraphs = [line.strip() for line in lines if line.strip()]
                logger.debug(f"Generated content structure: {len(lines)} lines, {len(paragraphs)} paragraphs")
                
                # Check for repetition patterns
                words = generated_text.lower().split()
                if len(words) > 10:
                    unique_words = len(set(words))
                    repetition_ratio = unique_words / len(words)
                    logger.debug(f"Word repetition analysis: {unique_words}/{len(words)} unique words (ratio: {repetition_ratio:.2f})")
                    if repetition_ratio < 0.5:
                        logger.warning(f"High repetition detected (ratio: {repetition_ratio:.2f})")
            
            # Critical issue detection
            if not generated_text.strip():
                logger.error("CRITICAL: Generated text is empty!")
            elif len(generated_text.strip()) < 20:
                logger.warning(f"WARNING: Generated text is very short ({len(generated_text)} chars)")
            
            # Check for early stopping indicators
            if finish_reason in ['length', 'max_tokens']:
                logger.warning(f"Generation stopped due to token limit: {finish_reason}")
            elif finish_reason == 'stop':
                logger.info("Generation completed normally (stop token reached)")
            else:
                logger.warning(f"Generation stopped for unclear reason: {finish_reason}")
            
            logger.info(f"=== GGUF Generation End ===")
            
            return generated_text
            
        except Exception as e:
            logger.error(f"GGUF generation failed: {e}")
            logger.error(f"Failed prompt length: {len(prompt)} chars")
            logger.error(f"Failed generation config: {generation_config}")
            raise TranslationError(f"Text generation failed: {e}")
    
    def _generate_transformers(self, prompt: str, model_options: Optional[Dict] = None) -> str:
        """Generate text using transformers pipeline."""
        generation_config = {
            "max_length": len(prompt) + self.max_length,
            "max_new_tokens": self.max_length,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "do_sample": True,
            "pad_token_id": self.tokenizer.eos_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
            "repetition_penalty": 1.1,
            "length_penalty": 1.0
        }
        
        # Add model-specific options from request
        if model_options:
            generation_config.update(model_options)
        
        try:
            generated = self.text_generator(
                prompt,
                **generation_config
            )
            return generated[0]["generated_text"]
        except Exception as e:
            logger.error(f"Transformers generation failed: {e}")
            raise TranslationError(f"Text generation failed: {e}")
    
    def _parse_translation_response(self, generated_text: str, original_text: str) -> str:
        """
        Parse and clean the generated translation response.
        
        Args:
            generated_text: Raw generated text from model
            original_text: Original text being translated
            
        Returns:
            Cleaned translation text
        """
        # Remove common artifacts and clean the response
        translation = generated_text.strip()
        
        # Remove potential repetition of original text
        if original_text in translation:
            translation = translation.replace(original_text, "").strip()
        
        # Remove common prefixes/suffixes
        prefixes_to_remove = [
            "Translation:", "Translated text:", "Output:", "Result:",
            "The translation is:", "Here is the translation:",
            "Translated:", "Answer:"
        ]
        
        for prefix in prefixes_to_remove:
            if translation.lower().startswith(prefix.lower()):
                translation = translation[len(prefix):].strip()
        
        # Remove quotes if the entire translation is quoted
        if (translation.startswith('"') and translation.endswith('"')) or \
           (translation.startswith("'") and translation.endswith("'")):
            translation = translation[1:-1].strip()
        
        # CRITICAL FIX: Do NOT truncate multi-line translations for long texts
        # Only remove truly empty lines, preserve paragraph structure
        lines = translation.split('\n')
        cleaned_lines = []
        for line in lines:
            # Keep lines that have content, preserve structure
            if line.strip() or (cleaned_lines and cleaned_lines[-1].strip()):
                cleaned_lines.append(line)
        
        # Only join non-empty lines back together, preserving paragraph breaks
        if len(cleaned_lines) > 1:
            translation = '\n'.join(cleaned_lines).strip()
        
        return translation
    
    async def translate(self, request: TranslationRequest) -> TranslationResponse:
        """
        Translate text using Aya Expanse 8B model.
        
        Args:
            request: TranslationRequest containing text and language parameters
            
        Returns:
            TranslationResponse with translated text and metadata
        """
        self.validate_request(request)
        start_time = time.time()
        
        try:
            # Handle language detection and conversion
            source_lang = request.source_lang
            detected_source = None
            
            # Handle auto-detection
            if not source_lang or source_lang == 'auto':
                detected_source = await self.detect_language(request.text)
                source_lang = detected_source
            
            # Convert ISO codes to Aya language names
            source_lang_name = LanguageCodeConverter.to_model_code(source_lang, 'aya')
            target_lang_name = LanguageCodeConverter.to_model_code(request.target_lang, 'aya')
            
            # Create prompt
            prompt = self._create_translation_prompt(
                request.text, 
                source_lang_name, 
                target_lang_name
            )
            
            # Generate translation using appropriate method
            if self.use_gguf and LLAMA_CPP_AVAILABLE:
                generated_text = self._generate_gguf(prompt, request.model_options)
            else:
                generated_text = self._generate_transformers(prompt, request.model_options)
            
            # Extract and clean translation
            translated_text = self._parse_translation_response(generated_text, request.text)
            
            # Fallback if translation seems empty or invalid
            if not translated_text or len(translated_text.strip()) < 2:
                logger.warning(f"Empty translation result, using raw generation")
                translated_text = generated_text.strip()
            
            processing_time = (time.time() - start_time) * 1000
            
            return TranslationResponse(
                translated_text=translated_text,
                detected_source_lang=detected_source,
                processing_time_ms=processing_time,
                model_used=self.model_name,
                metadata={
                    "source_lang_name": source_lang_name,
                    "target_lang_name": target_lang_name,
                    "device": self.device,
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "prompt_tokens": len(self.tokenizer.encode(prompt)) if self.tokenizer else len(prompt.split()),
                    "use_quantization": self.use_quantization,
                    "quantization_type": "8-bit" if self.load_in_8bit else "4-bit" if self.use_quantization else "none",
                    "raw_generation": generated_text[:200] + "..." if len(generated_text) > 200 else generated_text
                }
            )
            
        except Exception as e:
            error_msg = f"Aya translation failed: {e}"
            logger.error(error_msg)
            raise TranslationError(error_msg)
    
    async def detect_language(self, text: str) -> str:
        """
        Detect language using the Aya Expanse model with instruction prompt.
        
        This uses the model's multilingual understanding to detect the language.
        Falls back to character-based detection for reliability.
        """
        try:
            if not text or not text.strip():
                return "en"
            
            # Try model-based detection first
            try:
                detection_prompt = f"""<|USER|>What language is this text written in? Answer with just the language name in English.

Text: {text[:200]}<|ASSISTANT|>"""
                
                if self.use_gguf and LLAMA_CPP_AVAILABLE:
                    response = self.model(
                        detection_prompt,
                        max_tokens=10,
                        temperature=0.1,
                        echo=False
                    )
                    detected_lang_name = response['choices'][0]['text'].strip().lower()
                else:
                    generated = self.text_generator(
                        detection_prompt,
                        max_new_tokens=10,
                        temperature=0.1,
                        do_sample=False,
                        pad_token_id=self.tokenizer.eos_token_id
                    )
                    detected_lang_name = generated[0]["generated_text"].strip().lower()
                
                # Convert language name to ISO code
                for iso_code, lang_name in LanguageCodeConverter.AYA_MAPPING.items():
                    if lang_name.lower() in detected_lang_name or detected_lang_name in lang_name.lower():
                        logger.debug(f"Model detected language: {lang_name} -> {iso_code}")
                        return iso_code
                        
            except Exception as e:
                logger.debug(f"Model-based detection failed: {e}, falling back to character analysis")
            
            # Fallback to character-based detection (same logic as NLLB)
            return await self._detect_language_character_based(text)
            
        except Exception as e:
            error_msg = f"Language detection failed: {e}"
            logger.error(error_msg)
            raise LanguageDetectionError(error_msg)
    
    def _detect_language_from_characters(self, text: str) -> Optional[str]:
        """Detect language based on character analysis."""
        if not text:
            return None
            
        # Unicode block detection
        scripts = {
            'latin': 0,
            'cyrillic': 0,
            'arabic': 0,
            'devanagari': 0,
            'han': 0
        }
        
        for char in text:
            code = ord(char)
            if 0x0041 <= code <= 0x024F:
                scripts['latin'] += 1
            elif 0x0400 <= code <= 0x04FF:
                scripts['cyrillic'] += 1
            elif 0x0600 <= code <= 0x06FF:
                scripts['arabic'] += 1
            elif 0x0900 <= code <= 0x097F:
                scripts['devanagari'] += 1
            elif 0x4E00 <= code <= 0x9FFF:
                scripts['han'] += 1
                
        # Find dominant script
        total = sum(scripts.values())
        if total == 0:
            return None
            
        dominant = max(scripts.items(), key=lambda x: x[1])
        if dominant[1] / total < 0.5:
            return None  # No clear majority
            
        # Map script to language (simplified)
        script_to_lang = {
            'latin': 'en',
            'cyrillic': 'ru',
            'arabic': 'ar',
            'devanagari': 'hi',
            'han': 'zh'
        }
        
        return script_to_lang.get(dominant[0])
    
    async def _detect_language_character_based(self, text: str) -> str:
        """Character-based language detection fallback."""
        # Try the new character detection method first
        detected = self._detect_language_from_characters(text)
        if detected:
            return detected
            
        # Fallback to simple approach
        text = text.lower()
        
        # Count Cyrillic characters and letters
        cyrillic_chars = sum(1 for c in text if 0x0400 <= ord(c) <= 0x04FF)
        latin_letters = sum(1 for c in text if 'a' <= c <= 'z')
        
        # Count actual letters to ignore punctuation and numbers
        letter_count = cyrillic_chars + latin_letters
        
        if letter_count == 0:
            return "en"
        
        # Calculate percentage of Cyrillic letters
        cyrillic_percentage = cyrillic_chars / letter_count if letter_count > 0 else 0
        is_russian = cyrillic_percentage > 0.25
        
        detected_lang = "ru" if is_russian else "en"
        logger.debug(f"Character-based detection: {detected_lang} (Cyrillic: {cyrillic_percentage:.2%})")
        
        return detected_lang
    
    def get_supported_languages(self) -> List[str]:
        """Return supported ISO language codes."""
        return list(LanguageCodeConverter.get_supported_languages('aya'))
    
    def is_available(self) -> bool:
        """Check if model is loaded and ready."""
        if not self._initialized or self.model is None:
            return False
        
        if self.use_gguf and LLAMA_CPP_AVAILABLE:
            # For GGUF models, only need the model to be loaded
            return True
        else:
            # For transformers models, need tokenizer and text_generator
            return (
                self.tokenizer is not None and
                self.text_generator is not None
            )
    
    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata."""
        info = {
            "name": self.model_name,
            "type": "aya",
            "model_path": self.model_path,
            "device": self.device,
            "max_length": self.max_length,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "available": self.is_available(),
            "model_size": self._get_model_size() if self.model else None
        }
        
        if self.use_gguf and LLAMA_CPP_AVAILABLE:
            info.update({
                "format": "GGUF",
                "gguf_filename": self.gguf_filename,
                "n_ctx": self.n_ctx,
                "n_gpu_layers": self.n_gpu_layers
            })
        else:
            info.update({
                "format": "transformers",
                "use_quantization": self.use_quantization,
                "quantization_type": "8-bit" if self.load_in_8bit else "4-bit" if self.use_quantization else "none",
                "torch_dtype": str(self.model.dtype) if self.model and hasattr(self.model, 'dtype') else None
            })
        
        return info
    
    def _get_model_size(self) -> Optional[str]:
        """Get approximate model size in memory."""
        try:
            if self.model is None:
                return None
            
            param_size = sum(p.numel() for p in self.model.parameters())
            
            # Approximate size calculation based on quantization
            if self.use_quantization:
                if self.load_in_8bit:
                    # 8-bit quantization
                    size_mb = param_size * 1 / (1024 ** 2)
                else:
                    # 4-bit quantization
                    size_mb = param_size * 0.5 / (1024 ** 2)
            elif self.device == "cuda":
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
            if self.text_generator is not None:
                del self.text_generator
                self.text_generator = None
            
            if self.model is not None:
                # GGUF models might need special cleanup
                if self.use_gguf and LLAMA_CPP_AVAILABLE and hasattr(self.model, 'close'):
                    self.model.close()
                del self.model
                self.model = None
            
            if self.tokenizer is not None:
                del self.tokenizer
                self.tokenizer = None
            
            # Clear memory cache
            clear_memory_cache()
            
            self._initialized = False
            logger.info(f"Aya Expanse model {self.model_name} cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during Aya Expanse model cleanup: {e}")
    
    def __del__(self):
        """Cleanup on deletion."""
        self.cleanup()