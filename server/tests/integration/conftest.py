"""
Integration test configuration.

This conftest.py provides test fixtures specifically for integration tests
of the single-model architecture without heavy dependencies.
"""

import os
import sys
import pytest
from unittest.mock import Mock, AsyncMock

# Set testing environment variable
os.environ["TESTING"] = "true"
os.environ.setdefault("API_KEY", "development-key")

# Add the app directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Lightweight imports that don't trigger heavy dependencies
try:
    from models.base import (
        TranslationModel,
        ModelInfo,
        TranslationRequest,
        TranslationResponse,
        HealthCheckResponse,
        ModelInitializationError,
        TranslationError,
        ModelNotReadyError
    )
except ImportError as e:
    # If models.base isn't available, create minimal mocks
    class ModelInfo:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        
        def dict(self):
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    class TranslationRequest:
        def __init__(self, text: str, source_lang: str, target_lang: str):
            self.text = text
            self.source_lang = source_lang
            self.target_lang = target_lang
    
    class TranslationResponse:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class HealthCheckResponse:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class TranslationModel:
        pass
    
    class ModelInitializationError(Exception):
        pass
    
    class TranslationError(Exception):
        pass
    
    class ModelNotReadyError(Exception):
        pass


@pytest.fixture
def mock_model_info():
    """Create a mock ModelInfo object."""
    return ModelInfo(
        name="test-model",
        version="1.0.0",
        supported_languages=["en", "ru", "es"],
        max_tokens=4096,
        memory_requirements="1.0 GB RAM",
        description="Test translation model"
    )


@pytest.fixture
def mock_translation_model(mock_model_info):
    """Create a mock TranslationModel."""
    mock = AsyncMock(spec=TranslationModel)
    mock.model_name = "test-model"
    mock.initialize = AsyncMock()
    mock.cleanup = AsyncMock()
    mock.health_check = AsyncMock(return_value=True)
    mock.get_model_info.return_value = mock_model_info
    mock.translate = AsyncMock(return_value="Test translation")
    return mock


@pytest.fixture
def mock_server(mock_translation_model):
    """Create a mock SingleModelServer."""
    from unittest.mock import Mock
    
    server = Mock()
    server.model_name = "test-model"
    server.model = mock_translation_model
    server.is_ready.return_value = True
    server.get_model_info = AsyncMock(return_value=mock_translation_model.get_model_info())
    server.translate = AsyncMock(return_value="Test translation")
    server.health_check = AsyncMock(return_value=True)
    return server


@pytest.fixture
def api_headers():
    """Provide API headers for testing."""
    return {"X-API-Key": "development-key"}


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ["TESTING"] = "true"
    os.environ["API_KEY"] = "development-key"
    os.environ.setdefault("LINGUA_NEXUS_MODEL", "nllb")
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# Mock classes for testing
class MockTranslationModel:
    """Mock translation model for testing."""
    
    def __init__(self, model_name="test-model"):
        self.model_name = model_name
        self._initialized = False
    
    async def initialize(self):
        """Mock initialization."""
        self._initialized = True
    
    async def cleanup(self):
        """Mock cleanup."""
        self._initialized = False
    
    async def health_check(self):
        """Mock health check."""
        return self._initialized
    
    def get_model_info(self):
        """Mock model info."""
        return ModelInfo(
            name=self.model_name,
            version="1.0.0",
            supported_languages=["en", "ru", "es"],
            max_tokens=4096,
            memory_requirements="1.0 GB RAM",
            description=f"{self.model_name} test translation model"
        )
    
    async def translate(self, text, source_lang, target_lang):
        """Mock translation."""
        if not self._initialized:
            raise ModelNotReadyError("Model not ready", self.model_name)
        return f"Translated: {text}"
