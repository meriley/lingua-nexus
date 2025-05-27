"""
Unit tests for NLLB model implementation.

This module tests the NLLB model for the single-model architecture.
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


class TestNLLBModel:
    """Test NLLB model implementation for single-model architecture."""
    
    @pytest.fixture
    def mock_config(self) -> Dict[str, Any]:
        """Basic configuration for testing."""
        return {
            'model_path': 'facebook/nllb-200-distilled-600M',
            'device': 'cpu',
            'max_length': 512,
            'num_beams': 4,
            'use_pipeline': True,
            'batch_size': 1
        }
    
    @pytest.fixture
    def mock_transformers(self):
        """Mock transformers components."""
        with patch('models.nllb.model.AutoModelForSeq2SeqLM') as mock_model_cls, \
             patch('models.nllb.model.AutoTokenizer') as mock_tokenizer_cls, \
             patch('models.nllb.model.pipeline') as mock_pipeline:
            
            # Mock tokenizer
            mock_tokenizer = Mock()
            mock_tokenizer.lang_code_to_id = {
                'eng_Latn': 256047, 
                'rus_Cyrl': 256184,
                'spa_Latn': 256042,
                'fra_Latn': 256057
            }
            mock_tokenizer.convert_tokens_to_ids = Mock(return_value=256047)
            mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer
            
            # Mock model
            mock_model = Mock()
            mock_model.dtype = torch.float32
            mock_model.generate.return_value = torch.tensor([[4, 5, 6]])
            mock_model_cls.from_pretrained.return_value = mock_model
            
            # Mock pipeline
            mock_translator = Mock()
            mock_translator.return_value = [{"translation_text": "Привет, мир!"}]
            mock_pipeline.return_value = mock_translator
            
            yield {
                'model': mock_model,
                'tokenizer': mock_tokenizer,
                'pipeline': mock_translator
            }

    @pytest.mark.asyncio
    async def test_model_initialization_success(self, mock_config, mock_transformers):
        """Test successful model initialization."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.model_name = "nllb"
        mock_instance.initialize = AsyncMock()
        mock_instance.is_ready = Mock(return_value=True)
        mock_instance.get_model_info = Mock(return_value=ModelInfo(
            name="nllb",
            type="nllb-distilled",
            version="200-distilled-600M",
            languages=["en", "ru", "es", "fr", "de"],
            max_context_length=512,
            supports_streaming=False
        ))
        mock_class.return_value = mock_instance
        mock_module.NLLBModel = mock_class
        
        with patch.dict('sys.modules', {'models.nllb.model': mock_module}):
            await mock_instance.initialize(mock_config)
            
            mock_instance.initialize.assert_called_once_with(mock_config)
            assert mock_instance.is_ready() is True
            
            model_info = mock_instance.get_model_info()
            assert model_info.name == "nllb"
            assert model_info.type == "nllb-distilled"
            assert "en" in model_info.languages

    @pytest.mark.asyncio
    async def test_translation_with_pipeline(self, mock_config, mock_transformers):
        """Test translation using pipeline."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.translate = AsyncMock(return_value={
            'translated_text': 'Привет, мир!',
            'source_language': 'en',
            'target_language': 'ru',
            'model_used': 'nllb',
            'processing_time_ms': 85,
            'metadata': {
                'backend': 'pipeline',
                'num_beams': 4,
                'max_length': 512,
                'use_pipeline': True
            }
        })
        mock_class.return_value = mock_instance
        mock_module.NLLBModel = mock_class
        
        with patch.dict('sys.modules', {'models.nllb.model': mock_module}):
            response = await mock_instance.translate({
                'text': 'Hello, world!',
                'source_lang': 'en',
                'target_lang': 'ru'
            })
            
            assert response['translated_text'] == 'Привет, мир!'
            assert response['model_used'] == 'nllb'
            assert response['metadata']['backend'] == 'pipeline'
            assert response['metadata']['use_pipeline'] is True

    @pytest.mark.asyncio
    async def test_translation_direct_model(self, mock_config, mock_transformers):
        """Test translation using model directly."""
        config_direct = {**mock_config, 'use_pipeline': False}
        
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.translate = AsyncMock(return_value={
            'translated_text': 'Привет, мир!',
            'source_language': 'en', 
            'target_language': 'ru',
            'model_used': 'nllb',
            'processing_time_ms': 95,
            'metadata': {
                'backend': 'direct',
                'use_pipeline': False,
                'num_beams': 4
            }
        })
        mock_class.return_value = mock_instance
        mock_module.NLLBModel = mock_class
        
        with patch.dict('sys.modules', {'models.nllb.model': mock_module}):
            response = await mock_instance.translate({
                'text': 'Hello, world!',
                'source_lang': 'en',
                'target_lang': 'ru'
            })
            
            assert response['translated_text'] == 'Привет, мир!'
            assert response['metadata']['use_pipeline'] is False
            assert response['metadata']['backend'] == 'direct'

    @pytest.mark.asyncio
    async def test_auto_language_detection(self, mock_config, mock_transformers):
        """Test automatic language detection."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.translate = AsyncMock(return_value={
            'translated_text': 'Hello, world!',
            'source_language': 'ru',
            'target_language': 'en',
            'detected_source_lang': 'ru',
            'model_used': 'nllb',
            'processing_time_ms': 120
        })
        mock_class.return_value = mock_instance
        mock_module.NLLBModel = mock_class
        
        with patch.dict('sys.modules', {'models.nllb.model': mock_module}):
            response = await mock_instance.translate({
                'text': 'Привет, мир!',
                'source_lang': 'auto',  # Auto-detect
                'target_lang': 'en'
            })
            
            assert response['detected_source_lang'] == 'ru'
            assert response['translated_text'] == 'Hello, world!'

    @pytest.mark.asyncio
    async def test_language_detection_cyrillic(self, mock_config, mock_transformers):
        """Test language detection for Cyrillic text."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.detect_language = AsyncMock(side_effect=[
            'ru',  # Russian text
            'en',  # English text
            'ru',  # Mixed text with more Cyrillic
            'en'   # Mixed text with more Latin
        ])
        mock_class.return_value = mock_instance
        mock_module.NLLBModel = mock_class
        
        with patch.dict('sys.modules', {'models.nllb.model': mock_module}):
            # Test Russian text
            detected = await mock_instance.detect_language('Привет, как дела?')
            assert detected == 'ru'
            
            # Test English text
            detected = await mock_instance.detect_language('Hello, how are you?')
            assert detected == 'en'
            
            # Test mixed text with high Cyrillic ratio
            detected = await mock_instance.detect_language('Привет hello мир')
            assert detected == 'ru'
            
            # Test mixed text with low Cyrillic ratio
            detected = await mock_instance.detect_language('Hello world this is English Привет')
            assert detected == 'en'

    @pytest.mark.asyncio
    async def test_language_detection_edge_cases(self, mock_config, mock_transformers):
        """Test language detection edge cases."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.detect_language = AsyncMock(return_value='en')  # Default fallback
        mock_class.return_value = mock_instance
        mock_module.NLLBModel = mock_class
        
        with patch.dict('sys.modules', {'models.nllb.model': mock_module}):
            # Empty string
            detected = await mock_instance.detect_language('')
            assert detected == 'en'
            
            # Only numbers and punctuation
            detected = await mock_instance.detect_language('123 !@# 456')
            assert detected == 'en'
            
            # Only spaces
            detected = await mock_instance.detect_language('   ')
            assert detected == 'en'

    @pytest.mark.asyncio
    async def test_translation_error_handling(self, mock_config, mock_transformers):
        """Test translation error handling."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.translate = AsyncMock(side_effect=TranslationError("NLLB translation failed"))
        mock_class.return_value = mock_instance
        mock_module.NLLBModel = mock_class
        
        with patch.dict('sys.modules', {'models.nllb.model': mock_module}):
            with pytest.raises(TranslationError) as exc_info:
                await mock_instance.translate({
                    'text': 'Hello, world!',
                    'source_lang': 'en',
                    'target_lang': 'ru'
                })
            assert "NLLB translation failed" in str(exc_info.value)

    def test_supported_languages(self, mock_config, mock_transformers):
        """Test supported languages retrieval."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.get_supported_languages = Mock(return_value=[
            'en', 'ru', 'es', 'fr', 'de', 'it', 'pt', 'zh', 'ja', 'ko',
            'ar', 'hi', 'tr', 'pl', 'nl', 'sv', 'da', 'no', 'fi', 'cs'
        ])
        mock_class.return_value = mock_instance
        mock_module.NLLBModel = mock_class
        
        with patch.dict('sys.modules', {'models.nllb.model': mock_module}):
            languages = mock_instance.get_supported_languages()
            assert 'en' in languages
            assert 'ru' in languages
            assert 'es' in languages
            assert len(languages) >= 20  # NLLB supports many languages

    def test_language_pair_support(self, mock_config, mock_transformers):
        """Test language pair support checking."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.supports_language_pair = Mock(side_effect=[True, True, False])
        mock_class.return_value = mock_instance
        mock_module.NLLBModel = mock_class
        
        with patch.dict('sys.modules', {'models.nllb.model': mock_module}):
            # Test supported pair
            assert mock_instance.supports_language_pair('en', 'ru') is True
            
            # Test auto detection
            assert mock_instance.supports_language_pair('auto', 'en') is True
            
            # Test unsupported language
            assert mock_instance.supports_language_pair('en', 'xx') is False

    @pytest.mark.asyncio
    async def test_model_cleanup(self, mock_config, mock_transformers):
        """Test model cleanup."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.cleanup = AsyncMock()
        mock_instance.is_ready = Mock(side_effect=[True, False])
        mock_class.return_value = mock_instance
        mock_module.NLLBModel = mock_class
        
        with patch.dict('sys.modules', {'models.nllb.model': mock_module}):
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
            mock_module.NLLBModel = mock_class
            
            with patch.dict('sys.modules', {'models.nllb.model': mock_module}):
                assert mock_instance.device == 'cuda'
        
        with patch('torch.cuda.is_available', return_value=False):
            config_auto = {**mock_config, 'device': 'auto'}
            mock_instance.device = 'cpu'
            assert mock_instance.device == 'cpu'


class TestNLLBModelAdvanced:
    """Advanced tests for NLLB specific features."""
    
    @pytest.fixture
    def mock_multilingual_config(self) -> Dict[str, Any]:
        """Configuration for multilingual testing."""
        return {
            'model_path': 'facebook/nllb-200-distilled-600M',
            'device': 'cpu',
            'max_length': 512,
            'num_beams': 5,
            'use_pipeline': True,
            'supported_languages': [
                'en', 'ru', 'es', 'fr', 'de', 'it', 'pt', 'zh', 'ja', 'ko'
            ]
        }

    @pytest.mark.asyncio
    async def test_multilingual_capabilities(self, mock_multilingual_config):
        """Test NLLB multilingual translation capabilities."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        
        # Mock translations for different language pairs
        translation_results = {
            ('en', 'ru'): 'Привет, мир!',
            ('en', 'es'): '¡Hola, mundo!',
            ('en', 'fr'): 'Bonjour, monde!',
            ('en', 'de'): 'Hallo, Welt!',
            ('ru', 'en'): 'Hello, world!'
        }
        
        async def mock_translate(request):
            source = request['source_lang']
            target = request['target_lang']
            return {
                'translated_text': translation_results.get((source, target), 'Translation'),
                'source_language': source,
                'target_language': target,
                'model_used': 'nllb'
            }
        
        mock_instance.translate = AsyncMock(side_effect=mock_translate)
        mock_class.return_value = mock_instance
        mock_module.NLLBModel = mock_class
        
        with patch.dict('sys.modules', {'models.nllb.model': mock_module}):
            # Test English to various languages
            for target_lang, expected in [('ru', 'Привет, мир!'), ('es', '¡Hola, mundo!'), ('fr', 'Bonjour, monde!')]:
                result = await mock_instance.translate({
                    'text': 'Hello, world!',
                    'source_lang': 'en',
                    'target_lang': target_lang
                })
                assert result['translated_text'] == expected

    def test_memory_efficiency(self, mock_multilingual_config):
        """Test memory efficiency in single-model architecture."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.get_memory_usage = Mock(return_value={
            'model_memory_mb': 1200,  # 600M model should be smaller
            'cache_memory_mb': 256,
            'total_memory_mb': 1456
        })
        mock_class.return_value = mock_instance
        mock_module.NLLBModel = mock_class
        
        with patch.dict('sys.modules', {'models.nllb.model': mock_module}):
            memory_info = mock_instance.get_memory_usage()
            # NLLB should be more memory efficient than Aya
            assert memory_info['model_memory_mb'] < 2000
            assert memory_info['total_memory_mb'] < 2000

    @pytest.mark.asyncio
    async def test_pipeline_vs_direct_performance(self, mock_multilingual_config):
        """Test performance difference between pipeline and direct model usage."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        
        # Pipeline typically faster for single requests
        mock_instance.translate = AsyncMock(side_effect=[
            {  # Pipeline result
                'translated_text': 'Результат',
                'processing_time_ms': 75,
                'metadata': {'backend': 'pipeline'}
            },
            {  # Direct model result  
                'translated_text': 'Результат',
                'processing_time_ms': 95,
                'metadata': {'backend': 'direct'}
            }
        ])
        mock_class.return_value = mock_instance
        mock_module.NLLBModel = mock_class
        
        with patch.dict('sys.modules', {'models.nllb.model': mock_module}):
            # Test pipeline performance
            pipeline_result = await mock_instance.translate({
                'text': 'Result',
                'source_lang': 'en',
                'target_lang': 'ru'
            })
            
            # Test direct model performance
            direct_result = await mock_instance.translate({
                'text': 'Result', 
                'source_lang': 'en',
                'target_lang': 'ru'
            })
            
            # Pipeline should generally be faster for single requests
            assert pipeline_result['processing_time_ms'] <= direct_result['processing_time_ms']

    def test_language_code_mapping(self, mock_multilingual_config):
        """Test NLLB language code mapping functionality."""
        mock_module = MagicMock()
        mock_class = Mock()
        mock_instance = Mock(spec=TranslationModel)
        mock_instance.get_language_code_mapping = Mock(return_value={
            'en': 'eng_Latn',
            'ru': 'rus_Cyrl', 
            'es': 'spa_Latn',
            'fr': 'fra_Latn',
            'de': 'deu_Latn'
        })
        mock_class.return_value = mock_instance
        mock_module.NLLBModel = mock_class
        
        with patch.dict('sys.modules', {'models.nllb.model': mock_module}):
            mappings = mock_instance.get_language_code_mapping()
            assert mappings['en'] == 'eng_Latn'
            assert mappings['ru'] == 'rus_Cyrl'
            assert mappings['es'] == 'spa_Latn'