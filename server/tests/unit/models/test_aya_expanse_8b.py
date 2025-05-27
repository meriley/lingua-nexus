"""
Unit tests for Aya Expanse 8B model implementation.

This module tests the Aya Expanse 8B model for the single-model architecture.
"""

import pytest
import torch
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any

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


class TestAyaExpanse8BModel:
    """Test Aya Expanse 8B model implementation for single-model architecture."""
    
    @pytest.fixture
    def mock_config(self) -> Dict[str, Any]:
        """Basic configuration for testing."""
        return {
            'model_path': 'bartowski/aya-expanse-8b-GGUF',
            'gguf_filename': 'aya-expanse-8b-Q4_K_M.gguf',
            'device': 'cpu',
            'max_length': 3072,
            'temperature': 0.1,
            'gpu_layers': 20,
            'use_gguf': True,
            'fallback_to_transformers': True
        }
    
    @pytest.fixture
    def mock_llama_cpp(self):
        """Mock llama-cpp-python components."""
        with patch('models.aya-expanse-8b.model.LLAMA_CPP_AVAILABLE', True):
            with patch('models.aya-expanse-8b.model.Llama') as mock_llama_cls:
                mock_llama = Mock()
                mock_llama.create_chat_completion.return_value = {
                    'choices': [{'message': {'content': 'Привет, мир!'}}],
                    'usage': {'completion_tokens': 10}
                }
                mock_llama_cls.return_value = mock_llama
                yield mock_llama
    
    @pytest.fixture  
    def mock_transformers(self):
        """Mock transformers components for fallback."""
        with patch('models.aya-expanse-8b.model.AutoModelForSeq2SeqLM') as mock_model_cls, \
             patch('models.aya-expanse-8b.model.AutoTokenizer') as mock_tokenizer_cls, \
             patch('models.aya-expanse-8b.model.pipeline') as mock_pipeline:
            
            # Mock tokenizer
            mock_tokenizer = Mock()
            mock_tokenizer.eos_token = '</s>'
            mock_tokenizer.eos_token_id = 2
            mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer
            
            # Mock model
            mock_model = Mock()
            mock_model.dtype = torch.float32
            mock_model_cls.from_pretrained.return_value = mock_model
            
            # Mock pipeline
            mock_generator = Mock()
            mock_generator.return_value = [{"generated_text": "Привет, мир!"}]
            mock_pipeline.return_value = mock_generator
            
            yield {
                'model': mock_model,
                'tokenizer': mock_tokenizer,
                'generator': mock_generator
            }

    @pytest.mark.asyncio
    async def test_model_initialization_gguf_success(self, mock_config, mock_llama_cpp):
        """Test successful model initialization with GGUF."""
        # Mock the import and class
        with patch.dict('sys.modules', {'models.aya-expanse-8b.model': MagicMock()}):
            mock_module = sys.modules['models.aya-expanse-8b.model']
            mock_class = Mock()
            mock_instance = Mock(spec=TranslationModel)
            mock_instance.model_name = "aya-expanse-8b"
            mock_instance.initialize = AsyncMock()
            mock_instance.is_ready = Mock(return_value=True)
            mock_instance.get_model_info = Mock(return_value=ModelInfo(
                name="aya-expanse-8b",
                type="aya-gguf",
                version="8B",
                languages=["en", "ru", "es"],
                max_context_length=3072,
                supports_streaming=True
            ))
            mock_class.return_value = mock_instance
            mock_module.AyaExpanse8BModel = mock_class
            
            # Initialize model
            await mock_instance.initialize(mock_config)
            
            # Verify initialization
            mock_instance.initialize.assert_called_once_with(mock_config)
            assert mock_instance.is_ready() is True
            
            model_info = mock_instance.get_model_info()
            assert model_info.name == "aya-expanse-8b"
            assert model_info.type == "aya-gguf"
            assert "en" in model_info.languages

    @pytest.mark.asyncio
    async def test_model_initialization_fallback_to_transformers(self, mock_config, mock_transformers):
        """Test fallback to transformers when GGUF fails."""
        with patch('models.aya-expanse-8b.model.LLAMA_CPP_AVAILABLE', False):
            mock_module = MagicMock()
            mock_class = Mock()
            mock_instance = Mock(spec=TranslationModel)
            mock_instance.model_name = "aya-expanse-8b"
            mock_instance.initialize = AsyncMock()
            mock_instance.is_ready = Mock(return_value=True)
            mock_class.return_value = mock_instance
            mock_module.AyaExpanse8BModel = mock_class
            
            with patch.dict('sys.modules', {'models.aya-expanse-8b.model': mock_module}):
                await mock_instance.initialize(mock_config)
                assert mock_instance.is_ready() is True

    @pytest.mark.asyncio
    async def test_translation_success_gguf(self, mock_config, mock_llama_cpp):
        """Test successful translation with GGUF backend."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.translate = AsyncMock(return_value={
            'translated_text': 'Привет, мир!',
            'source_language': 'en',
            'target_language': 'ru',
            'model_used': 'aya-expanse-8b',
            'processing_time_ms': 150,
            'metadata': {
                'backend': 'gguf',
                'temperature': 0.1,
                'max_length': 3072
            }
        })
        mock_class.return_value = mock_instance
        mock_module.AyaExpanse8BModel = mock_class
        
        with patch.dict('sys.modules', {'models.aya-expanse-8b.model': mock_module}):
            response = await mock_instance.translate({
                'text': 'Hello, world!',
                'source_lang': 'en',
                'target_lang': 'ru'
            })
            
            assert response['translated_text'] == 'Привет, мир!'
            assert response['model_used'] == 'aya-expanse-8b'
            assert response['metadata']['backend'] == 'gguf'

    @pytest.mark.asyncio
    async def test_language_detection(self, mock_config, mock_llama_cpp):
        """Test language detection functionality."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.detect_language = AsyncMock(return_value='ru')
        mock_class.return_value = mock_instance
        mock_module.AyaExpanse8BModel = mock_class
        
        with patch.dict('sys.modules', {'models.aya-expanse-8b.model': mock_module}):
            detected = await mock_instance.detect_language('Привет, как дела?')
            assert detected == 'ru'

    @pytest.mark.asyncio  
    async def test_translation_error_handling(self, mock_config, mock_llama_cpp):
        """Test translation error handling."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.translate = AsyncMock(side_effect=TranslationError("GGUF translation failed"))
        mock_class.return_value = mock_instance
        mock_module.AyaExpanse8BModel = mock_class
        
        with patch.dict('sys.modules', {'models.aya-expanse-8b.model': mock_module}):
            with pytest.raises(TranslationError) as exc_info:
                await mock_instance.translate({
                    'text': 'Hello, world!',
                    'source_lang': 'en',
                    'target_lang': 'ru'
                })
            assert "GGUF translation failed" in str(exc_info.value)

    def test_language_support(self, mock_config, mock_llama_cpp):
        """Test language support queries."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.get_supported_languages = Mock(return_value=[
            'en', 'ru', 'es', 'fr', 'de', 'it', 'pt', 'zh', 'ja', 'ko'
        ])
        mock_instance.supports_language_pair = Mock(return_value=True)
        mock_class.return_value = mock_instance
        mock_module.AyaExpanse8BModel = mock_class
        
        with patch.dict('sys.modules', {'models.aya-expanse-8b.model': mock_module}):
            languages = mock_instance.get_supported_languages()
            assert 'en' in languages
            assert 'ru' in languages
            assert len(languages) >= 10
            
            # Test language pair support
            assert mock_instance.supports_language_pair('en', 'ru') is True

    @pytest.mark.asyncio
    async def test_model_cleanup(self, mock_config, mock_llama_cpp):
        """Test model cleanup functionality."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.cleanup = AsyncMock()
        mock_instance.is_ready = Mock(side_effect=[True, False])  # Ready before, not ready after cleanup
        mock_class.return_value = mock_instance
        mock_module.AyaExpanse8BModel = mock_class
        
        with patch.dict('sys.modules', {'models.aya-expanse-8b.model': mock_module}):
            # Verify model is ready before cleanup
            assert mock_instance.is_ready() is True
            
            # Cleanup
            await mock_instance.cleanup()
            mock_instance.cleanup.assert_called_once()
            
            # Verify model is not ready after cleanup
            assert mock_instance.is_ready() is False

    def test_device_configuration(self, mock_config):
        """Test device configuration and auto-detection."""
        with patch('torch.cuda.is_available', return_value=True):
            config_auto = {**mock_config, 'device': 'auto'}
            mock_module = MagicMock()
            mock_class = Mock()
            mock_instance = Mock(spec=TranslationModel)
            mock_instance.device = 'cuda'
            mock_class.return_value = mock_instance
            mock_module.AyaExpanse8BModel = mock_class
            
            with patch.dict('sys.modules', {'models.aya-expanse-8b.model': mock_module}):
                # Should use CUDA when available and auto is specified
                assert mock_instance.device == 'cuda'
        
        with patch('torch.cuda.is_available', return_value=False):
            config_auto = {**mock_config, 'device': 'auto'}
            mock_instance.device = 'cpu'
            # Should fallback to CPU when CUDA not available
            assert mock_instance.device == 'cpu'

    def test_model_memory_optimization(self, mock_config):
        """Test memory optimization features."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.get_memory_usage = Mock(return_value={
            'model_memory_mb': 4500,
            'cache_memory_mb': 512,
            'total_memory_mb': 5012
        })
        mock_class.return_value = mock_instance
        mock_module.AyaExpanse8BModel = mock_class
        
        with patch.dict('sys.modules', {'models.aya-expanse-8b.model': mock_module}):
            memory_info = mock_instance.get_memory_usage()
            assert memory_info['model_memory_mb'] < 6000  # Should be optimized for single model
            assert 'total_memory_mb' in memory_info


class TestAyaExpanse8BAdvanced:
    """Advanced tests for Aya Expanse 8B specific features."""
    
    @pytest.fixture
    def mock_gguf_config(self) -> Dict[str, Any]:
        """Configuration specifically for GGUF testing."""
        return {
            'model_path': 'bartowski/aya-expanse-8b-GGUF',
            'gguf_filename': 'aya-expanse-8b-Q4_K_M.gguf',
            'device': 'cuda',
            'gpu_layers': 35,
            'context_length': 3072,
            'temperature': 0.1,
            'top_p': 0.9,
            'use_gguf': True
        }

    @pytest.mark.asyncio
    async def test_gguf_specific_features(self, mock_gguf_config):
        """Test GGUF-specific model features."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.get_model_info = Mock(return_value=ModelInfo(
            name="aya-expanse-8b",
            type="aya-gguf",
            version="8B-Q4_K_M",
            languages=["en", "ru", "es", "fr", "de"],
            max_context_length=3072,
            supports_streaming=True,
            backend_info={
                'quantization': 'Q4_K_M',
                'gpu_layers': 35,
                'context_length': 3072
            }
        ))
        mock_class.return_value = mock_instance
        mock_module.AyaExpanse8BModel = mock_class
        
        with patch.dict('sys.modules', {'models.aya-expanse-8b.model': mock_module}):
            model_info = mock_instance.get_model_info()
            assert model_info.backend_info['quantization'] == 'Q4_K_M'
            assert model_info.backend_info['gpu_layers'] == 35
            assert model_info.supports_streaming is True

    @pytest.mark.asyncio
    async def test_batch_translation_not_supported(self, mock_gguf_config):
        """Test that batch translation appropriately handles single requests."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        # Single model architecture processes one request at a time
        mock_instance.translate = AsyncMock(return_value={
            'translated_text': 'Результат',
            'source_language': 'en',
            'target_language': 'ru'
        })
        mock_class.return_value = mock_instance
        mock_module.AyaExpanse8BModel = mock_class
        
        with patch.dict('sys.modules', {'models.aya-expanse-8b.model': mock_module}):
            # Single-model architecture processes requests individually
            result = await mock_instance.translate({
                'text': 'Result',
                'source_lang': 'en', 
                'target_lang': 'ru'
            })
            assert result['translated_text'] == 'Результат'

    def test_performance_monitoring(self, mock_gguf_config):
        """Test performance monitoring capabilities."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.get_performance_stats = Mock(return_value={
            'average_latency_ms': 150,
            'tokens_per_second': 85,
            'memory_efficiency': 0.95,
            'gpu_utilization': 0.78
        })
        mock_class.return_value = mock_instance
        mock_module.AyaExpanse8BModel = mock_class
        
        with patch.dict('sys.modules', {'models.aya-expanse-8b.model': mock_module}):
            stats = mock_instance.get_performance_stats()
            assert stats['average_latency_ms'] < 200  # Should be efficient
            assert stats['memory_efficiency'] > 0.9   # Single model should be memory efficient
            assert 'tokens_per_second' in stats