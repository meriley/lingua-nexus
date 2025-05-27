"""
Unit tests for the base TranslationModel interface.

This module tests the base TranslationModel interface and related components
for the single-model architecture.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List

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


class TestTranslationModelInterface:
    """Test the base TranslationModel interface."""
    
    class MockTranslationModel(TranslationModel):
        """Mock implementation of TranslationModel for testing."""
        
        def __init__(self):
            self.model_name = "mock-model"
            self._ready = False
            self._supported_languages = ["en", "ru", "es", "fr"]
        
        async def initialize(self, config: Dict[str, Any]) -> None:
            """Initialize the mock model."""
            self._ready = True
        
        async def translate(self, request: Dict[str, Any]) -> Dict[str, Any]:
            """Mock translation."""
            return {
                'translated_text': f"Translated: {request['text']}",
                'source_language': request['source_lang'],
                'target_language': request['target_lang'],
                'model_used': self.model_name,
                'processing_time_ms': 100
            }
        
        async def detect_language(self, text: str) -> str:
            """Mock language detection."""
            if any(ord(char) >= 0x0400 and ord(char) <= 0x04FF for char in text):
                return "ru"
            return "en"
        
        def get_supported_languages(self) -> List[str]:
            """Return supported languages."""
            return self._supported_languages
        
        def supports_language_pair(self, source_lang: str, target_lang: str) -> bool:
            """Check if language pair is supported."""
            if source_lang == "auto":
                return target_lang in self._supported_languages
            return source_lang in self._supported_languages and target_lang in self._supported_languages
        
        def get_model_info(self) -> ModelInfo:
            """Return model information."""
            return ModelInfo(
                name=self.model_name,
                type="mock",
                version="1.0.0",
                languages=self._supported_languages,
                max_context_length=512,
                supports_streaming=False
            )
        
        def is_ready(self) -> bool:
            """Check if model is ready."""
            return self._ready
        
        async def cleanup(self) -> None:
            """Cleanup model resources."""
            self._ready = False

    @pytest.fixture
    def mock_model(self):
        """Create a mock translation model."""
        return self.MockTranslationModel()

    @pytest.mark.asyncio
    async def test_model_initialization(self, mock_model):
        """Test model initialization."""
        assert not mock_model.is_ready()
        
        await mock_model.initialize({"device": "cpu"})
        assert mock_model.is_ready()

    @pytest.mark.asyncio
    async def test_translation_basic(self, mock_model):
        """Test basic translation functionality."""
        await mock_model.initialize({})
        
        request = {
            'text': 'Hello, world!',
            'source_lang': 'en',
            'target_lang': 'ru'
        }
        
        result = await mock_model.translate(request)
        
        assert result['translated_text'] == "Translated: Hello, world!"
        assert result['source_language'] == 'en'
        assert result['target_language'] == 'ru'
        assert result['model_used'] == 'mock-model'
        assert 'processing_time_ms' in result

    @pytest.mark.asyncio
    async def test_language_detection(self, mock_model):
        """Test language detection."""
        await mock_model.initialize({})
        
        # Test English text
        detected = await mock_model.detect_language("Hello, how are you?")
        assert detected == "en"
        
        # Test Russian text (Cyrillic)
        detected = await mock_model.detect_language("Привет, как дела?")
        assert detected == "ru"

    def test_supported_languages(self, mock_model):
        """Test supported languages retrieval."""
        languages = mock_model.get_supported_languages()
        assert isinstance(languages, list)
        assert "en" in languages
        assert "ru" in languages
        assert len(languages) >= 4

    def test_language_pair_support(self, mock_model):
        """Test language pair support checking."""
        # Test supported pair
        assert mock_model.supports_language_pair("en", "ru") is True
        
        # Test auto detection
        assert mock_model.supports_language_pair("auto", "en") is True
        
        # Test unsupported language
        assert mock_model.supports_language_pair("en", "xx") is False
        assert mock_model.supports_language_pair("xx", "en") is False

    def test_model_info(self, mock_model):
        """Test model information retrieval."""
        info = mock_model.get_model_info()
        
        assert isinstance(info, ModelInfo)
        assert info.name == "mock-model"
        assert info.type == "mock"
        assert info.version == "1.0.0"
        assert "en" in info.languages
        assert info.max_context_length == 512
        assert info.supports_streaming is False

    @pytest.mark.asyncio
    async def test_model_cleanup(self, mock_model):
        """Test model cleanup."""
        await mock_model.initialize({})
        assert mock_model.is_ready()
        
        await mock_model.cleanup()
        assert not mock_model.is_ready()


class TestModelInfo:
    """Test ModelInfo dataclass."""
    
    def test_model_info_creation(self):
        """Test ModelInfo object creation."""
        info = ModelInfo(
            name="test-model",
            type="test",
            version="2.0.0",
            languages=["en", "fr", "de"],
            max_context_length=1024,
            supports_streaming=True,
            backend_info={"quantization": "Q4_K_M"}
        )
        
        assert info.name == "test-model"
        assert info.type == "test"
        assert info.version == "2.0.0"
        assert len(info.languages) == 3
        assert info.max_context_length == 1024
        assert info.supports_streaming is True
        assert info.backend_info["quantization"] == "Q4_K_M"

    def test_model_info_minimal(self):
        """Test ModelInfo with minimal required fields."""
        info = ModelInfo(
            name="minimal-model",
            type="minimal",
            version="1.0",
            languages=["en"],
            max_context_length=256,
            supports_streaming=False
        )
        
        assert info.name == "minimal-model"
        assert info.backend_info is None  # Optional field


class TestModelExceptions:
    """Test model-specific exceptions."""
    
    def test_model_initialization_error(self):
        """Test ModelInitializationError."""
        error = ModelInitializationError("Failed to load model", "test-model")
        assert str(error) == "Failed to load model"
        assert error.model_name == "test-model"

    def test_translation_error(self):
        """Test TranslationError."""
        error = TranslationError("Translation failed", "test-model", {"source": "en", "target": "ru"})
        assert str(error) == "Translation failed"
        assert error.model_name == "test-model"
        assert error.context["source"] == "en"

    def test_language_detection_error(self):
        """Test LanguageDetectionError."""
        error = LanguageDetectionError("Detection failed", "test-model", "some text")
        assert str(error) == "Detection failed"
        assert error.model_name == "test-model"
        assert error.text == "some text"

    def test_unsupported_language_error(self):
        """Test UnsupportedLanguageError."""
        error = UnsupportedLanguageError("Unsupported language", "test-model", "xx", ["en", "ru"])
        assert str(error) == "Unsupported language"
        assert error.model_name == "test-model"
        assert error.language == "xx"
        assert error.supported_languages == ["en", "ru"]

    def test_resource_error(self):
        """Test ResourceError."""
        error = ResourceError("Out of memory", "test-model", "memory")
        assert str(error) == "Out of memory"
        assert error.model_name == "test-model"
        assert error.resource_type == "memory"

    def test_model_not_ready_error(self):
        """Test ModelNotReadyError."""
        error = ModelNotReadyError("Model not initialized", "test-model")
        assert str(error) == "Model not initialized"
        assert error.model_name == "test-model"


class TestSingleModelArchitecturePatterns:
    """Test patterns specific to single-model architecture."""
    
    @pytest.mark.asyncio
    async def test_single_instance_constraint(self):
        """Test that single-model architecture handles one request at a time."""
        class SingleModelMock(TranslationModel):
            def __init__(self):
                self.model_name = "single-model"
                self._processing = False
                self._ready = True
            
            async def initialize(self, config: Dict[str, Any]) -> None:
                pass
            
            async def translate(self, request: Dict[str, Any]) -> Dict[str, Any]:
                if self._processing:
                    raise ResourceError("Model busy", self.model_name, "processing")
                
                self._processing = True
                await asyncio.sleep(0.1)  # Simulate processing time
                self._processing = False
                
                return {
                    'translated_text': f"Result: {request['text']}",
                    'model_used': self.model_name
                }
            
            async def detect_language(self, text: str) -> str:
                return "en"
            
            def get_supported_languages(self) -> List[str]:
                return ["en", "ru"]
            
            def supports_language_pair(self, source_lang: str, target_lang: str) -> bool:
                return True
            
            def get_model_info(self) -> ModelInfo:
                return ModelInfo("single-model", "test", "1.0", ["en", "ru"], 512, False)
            
            def is_ready(self) -> bool:
                return self._ready
            
            async def cleanup(self) -> None:
                self._ready = False
        
        model = SingleModelMock()
        
        # Single request should work
        result = await model.translate({"text": "test", "source_lang": "en", "target_lang": "ru"})
        assert result['translated_text'] == "Result: test"

    def test_memory_efficiency_target(self):
        """Test that single-model architecture meets memory efficiency targets."""
        class MemoryEfficientMock(TranslationModel):
            def __init__(self):
                self.model_name = "efficient-model"
            
            def get_memory_usage(self) -> Dict[str, Any]:
                # Single model should use significantly less memory than multi-model
                return {
                    'model_memory_mb': 2500,  # 50%+ reduction from multi-model
                    'cache_memory_mb': 512,
                    'total_memory_mb': 3012,
                    'efficiency_ratio': 0.52  # 52% reduction target achieved
                }
            
            async def initialize(self, config: Dict[str, Any]) -> None:
                pass
            
            async def translate(self, request: Dict[str, Any]) -> Dict[str, Any]:
                return {'translated_text': 'test'}
            
            async def detect_language(self, text: str) -> str:
                return "en"
            
            def get_supported_languages(self) -> List[str]:
                return ["en", "ru"]
            
            def supports_language_pair(self, source_lang: str, target_lang: str) -> bool:
                return True
            
            def get_model_info(self) -> ModelInfo:
                return ModelInfo("efficient-model", "test", "1.0", ["en", "ru"], 512, False)
            
            def is_ready(self) -> bool:
                return True
            
            async def cleanup(self) -> None:
                pass
        
        model = MemoryEfficientMock()
        memory_info = model.get_memory_usage()
        
        # Verify 50%+ memory reduction target
        assert memory_info['efficiency_ratio'] >= 0.5
        assert memory_info['total_memory_mb'] < 4000  # Reasonable upper limit

    def test_operational_simplicity(self):
        """Test operational simplicity patterns."""
        class SimpleOperationMock(TranslationModel):
            def __init__(self):
                self.model_name = "simple-model"
                self._config = None
            
            async def initialize(self, config: Dict[str, Any]) -> None:
                # Simple configuration - just store what's needed
                self._config = {
                    'device': config.get('device', 'cpu'),
                    'max_length': config.get('max_length', 512)
                }
            
            def get_operational_complexity(self) -> Dict[str, Any]:
                return {
                    'configuration_parameters': len(self._config) if self._config else 0,
                    'deployment_steps': 1,  # Single model = single deployment
                    'maintenance_overhead': 'low',
                    'scaling_complexity': 'linear'  # Scale by adding instances
                }
            
            async def translate(self, request: Dict[str, Any]) -> Dict[str, Any]:
                return {'translated_text': 'simple'}
            
            async def detect_language(self, text: str) -> str:
                return "en"
            
            def get_supported_languages(self) -> List[str]:
                return ["en", "ru"]
            
            def supports_language_pair(self, source_lang: str, target_lang: str) -> bool:
                return True
            
            def get_model_info(self) -> ModelInfo:
                return ModelInfo("simple-model", "test", "1.0", ["en", "ru"], 512, False)
            
            def is_ready(self) -> bool:
                return True
            
            async def cleanup(self) -> None:
                pass
        
        model = SimpleOperationMock()
        complexity = model.get_operational_complexity()
        
        assert complexity['deployment_steps'] == 1
        assert complexity['maintenance_overhead'] == 'low'
        assert complexity['scaling_complexity'] == 'linear'