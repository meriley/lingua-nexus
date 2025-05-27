"""
Integration tests for single-model translation API.

This module tests the complete single-model API functionality including
model loading, translation endpoints, and health checks for individual models.
Tests are designed to validate the new single-model-per-instance architecture.
"""

import pytest
import asyncio
import os
import time
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock

# Import the single-model app
from app.single_model_main import create_app, SingleModelServer
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


class TestSingleModelAPI:
    """Test single-model API endpoints."""
    
    @pytest.fixture
    def mock_model(self):
        """Create mock translation model."""
        mock = AsyncMock(spec=TranslationModel)
        mock.model_name = "test-model"
        mock.initialize = AsyncMock()
        mock.cleanup = AsyncMock()
        mock.health_check = AsyncMock(return_value=True)
        mock.get_model_info.return_value = ModelInfo(
            name="test-model",
            version="1.0.0",
            supported_languages=["en", "ru", "es"],
            max_tokens=4096,
            memory_requirements="1.0 GB RAM",
            description="Test translation model"
        )
        mock.translate = AsyncMock(return_value="Тестовый перевод")
        return mock
    
    @pytest.fixture
    def mock_server(self, mock_model):
        """Create mock server with initialized model."""
        server = Mock(spec=SingleModelServer)
        server.model_name = "test-model"
        server.model = mock_model
        server.is_ready.return_value = True
        server.get_model_info = AsyncMock(return_value=mock_model.get_model_info())
        server.translate = AsyncMock(return_value="Тестовый перевод")
        server.health_check = AsyncMock(return_value=True)
        return server
    
    @pytest.fixture
    def client(self, mock_server):
        """Create test client with mocked server."""
        with patch.dict(os.environ, {"LINGUA_NEXUS_MODEL": "test-model", "TESTING": "true"}):
            app = create_app()
            with patch('app.single_model_main.server', mock_server):
                return TestClient(app)
    
    def test_health_endpoint_healthy(self, client, mock_server):
        """Test health endpoint when model is healthy."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["model_name"] == "test-model"
        assert "model_info" in data
        assert "timestamp" in data
    
    def test_health_endpoint_unhealthy(self, client):
        """Test health endpoint when server is not initialized."""
        with patch('app.single_model_main.server', None):
            response = client.get("/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["model_name"] == "unknown"
            assert "Server not initialized" in data["details"]
    
    def test_health_endpoint_model_not_ready(self, client, mock_server):
        """Test health endpoint when model is not ready."""
        mock_server.is_ready.return_value = False
        mock_server.health_check = AsyncMock(return_value=False)
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "not responding" in data["details"]
    
    def test_model_info_endpoint(self, client, mock_server):
        """Test model info endpoint."""
        headers = {"X-API-Key": "development-key"}
        response = client.get("/model/info", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-model"
        assert data["version"] == "1.0.0"
        assert data["type"] == "test"
        assert "en" in data["supported_languages"]
        assert "translation" in data["capabilities"]
        assert data["device"] == "cpu"
    
    def test_model_info_unauthorized(self, client):
        """Test model info endpoint without API key."""
        response = client.get("/model/info")
        assert response.status_code == 403
    
    def test_model_info_invalid_key(self, client):
        """Test model info endpoint with invalid API key."""
        headers = {"X-API-Key": "invalid-key"}
        response = client.get("/model/info", headers=headers)
        assert response.status_code == 403
    
    def test_model_info_not_ready(self, client, mock_server):
        """Test model info endpoint when model is not ready."""
        mock_server.is_ready.return_value = False
        
        headers = {"X-API-Key": "development-key"}
        response = client.get("/model/info", headers=headers)
        assert response.status_code == 503
        assert "not ready" in response.json()["detail"]
    
    def test_translate_endpoint(self, client, mock_server):
        """Test translation endpoint."""
        headers = {"X-API-Key": "development-key"}
        translation_data = {
            "text": "Hello, world!",
            "source_lang": "en",
            "target_lang": "ru"
        }
        
        response = client.post("/translate", json=translation_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["translated_text"] == "Тестовый перевод"
        assert data["source_lang"] == "en"
        assert data["target_lang"] == "ru"
        assert data["model_name"] == "test-model"
        assert "processing_time_ms" in data
        assert data["processing_time_ms"] >= 0
    
    def test_translate_unauthorized(self, client):
        """Test translation endpoint without API key."""
        translation_data = {
            "text": "Hello, world!",
            "source_lang": "en",
            "target_lang": "ru"
        }
        
        response = client.post("/translate", json=translation_data)
        assert response.status_code == 403
    
    def test_translate_invalid_request(self, client):
        """Test translation endpoint with invalid request data."""
        headers = {"X-API-Key": "development-key"}
        invalid_data = {
            "text": "",  # Empty text should fail validation
            "source_lang": "en",
            "target_lang": "ru"
        }
        
        response = client.post("/translate", json=invalid_data, headers=headers)
        assert response.status_code == 422  # Validation error
    
    def test_translate_model_not_ready(self, client, mock_server):
        """Test translation endpoint when model is not ready."""
        mock_server.is_ready.return_value = False
        
        headers = {"X-API-Key": "development-key"}
        translation_data = {
            "text": "Hello, world!",
            "source_lang": "en",
            "target_lang": "ru"
        }
        
        response = client.post("/translate", json=translation_data, headers=headers)
        assert response.status_code == 503
        assert "not ready" in response.json()["detail"]
    
    def test_translate_model_error(self, client, mock_server):
        """Test translation endpoint when model raises error."""
        mock_server.translate = AsyncMock(side_effect=TranslationError("Translation failed", "test-model"))
        
        headers = {"X-API-Key": "development-key"}
        translation_data = {
            "text": "Hello, world!",
            "source_lang": "en",
            "target_lang": "ru"
        }
        
        response = client.post("/translate", json=translation_data, headers=headers)
        assert response.status_code == 500
        assert "Translation failed" in response.json()["detail"]
    
    def test_detect_language_endpoint(self, client, mock_server):
        """Test language detection endpoint."""
        headers = {"X-API-Key": "development-key"}
        
        # Mock language detection
        mock_server.model._detect_language = AsyncMock(return_value="en")
        
        response = client.post("/detect?text=Hello world", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["detected_language"] == "en"
        assert data["text"] == "Hello world"
        assert data["model"] == "test-model"
        assert "confidence" in data
    
    def test_detect_language_unauthorized(self, client):
        """Test language detection endpoint without API key."""
        response = client.post("/detect?text=Hello world")
        assert response.status_code == 403
    
    def test_detect_language_model_not_ready(self, client, mock_server):
        """Test language detection when model is not ready."""
        mock_server.is_ready.return_value = False
        
        headers = {"X-API-Key": "development-key"}
        response = client.post("/detect?text=Hello world", headers=headers)
        assert response.status_code == 503
        assert "not ready" in response.json()["detail"]


class TestSingleModelServerIntegration:
    """Test single-model server integration."""
    
    @pytest.fixture
    def mock_model_class(self):
        """Mock model class for testing."""
        class MockModelClass:
            def __init__(self):
                self.model_name = "test-model"
                self._initialized = False
            
            async def initialize(self):
                self._initialized = True
            
            async def cleanup(self):
                self._initialized = False
            
            async def health_check(self):
                return self._initialized
            
            def get_model_info(self):
                return ModelInfo(
                    name="test-model",
                    version="1.0.0",
                    supported_languages=["en", "ru"],
                    max_tokens=4096,
                    memory_requirements="1.0 GB RAM",
                    description="Test translation model"
                )
            
            async def translate(self, text, source_lang, target_lang):
                if not self._initialized:
                    raise ModelNotReadyError("Model not ready", "test-model")
                return f"Translated: {text}"
        
        return MockModelClass
    
    @pytest.mark.asyncio
    async def test_server_lifecycle(self, mock_model_class):
        """Test complete server lifecycle."""
        with patch('app.single_model_main.SingleModelServer._load_model', return_value=mock_model_class()):
            server = SingleModelServer("test-model")
            
            # Test startup
            assert not server.is_ready()
            await server.startup()
            assert server.is_ready()
            
            # Test model info
            model_info = await server.get_model_info()
            assert model_info.name == "test-model"
            
            # Test translation
            result = await server.translate("Hello", "en", "ru")
            assert "Translated: Hello" in result
            
            # Test health check
            is_healthy = await server.health_check()
            assert is_healthy
            
            # Test shutdown
            await server.shutdown()
            assert not server.is_ready()
    
    @pytest.mark.asyncio
    async def test_server_model_loading_error(self):
        """Test server behavior when model loading fails."""
        server = SingleModelServer("invalid-model")
        
        with pytest.raises(ModelInitializationError):
            await server.startup()
        
        assert not server.is_ready()
    
    @pytest.mark.asyncio
    async def test_server_operations_when_not_ready(self):
        """Test server operations when model is not ready."""
        server = SingleModelServer("test-model")
        
        # All operations should raise ModelNotReadyError
        with pytest.raises(ModelNotReadyError):
            await server.get_model_info()
        
        with pytest.raises(ModelNotReadyError):
            await server.translate("Hello", "en", "ru")
        
        # Health check should return False
        is_healthy = await server.health_check()
        assert not is_healthy
    
    @pytest.mark.asyncio
    async def test_supported_model_loading(self):
        """Test loading of supported models."""
        server = SingleModelServer("test-model")
        
        # Test aya-expanse-8b loading
        with patch('models.aya_expanse_8b.model.AyaExpanse8BModel') as mock_aya:
            mock_instance = Mock()
            mock_aya.return_value = mock_instance
            
            model = await server._load_model("aya-expanse-8b")
            assert model == mock_instance
            mock_aya.assert_called_once()
        
        # Test nllb loading
        with patch('models.nllb.model.NLLBModel') as mock_nllb:
            mock_instance = Mock()
            mock_nllb.return_value = mock_instance
            
            model = await server._load_model("nllb")
            assert model == mock_instance
            mock_nllb.assert_called_once()
        
        # Test unknown model
        with pytest.raises(ValueError, match="Unknown model"):
            await server._load_model("unknown-model")


class TestModelSpecificIntegration:
    """Test model-specific integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_aya_expanse_8b_integration(self):
        """Test Aya Expanse 8B model integration."""
        with patch.dict(os.environ, {"LINGUA_NEXUS_MODEL": "aya-expanse-8b"}):
            with patch('models.aya_expanse_8b.model.AyaExpanse8BModel') as mock_model_class:
                # Setup mock model
                mock_model = Mock()
                mock_model.model_name = "aya-expanse-8b"
                mock_model.initialize = AsyncMock()
                mock_model.cleanup = AsyncMock()
                mock_model.health_check = AsyncMock(return_value=True)
                mock_model.get_model_info.return_value = ModelInfo(
                    name="aya-expanse-8b",
                    version="1.0.0",
                    supported_languages=["en", "ru", "es", "fr", "de"],
                    max_tokens=8192,
                    memory_requirements="8.0 GB RAM",
                    description="Aya Expanse 8B GGUF multilingual translation model"
                )
                mock_model.translate = AsyncMock(return_value="Hola, mundo!")
                mock_model_class.return_value = mock_model
                
                # Test server initialization
                server = SingleModelServer("aya-expanse-8b")
                await server.startup()
                
                assert server.is_ready()
                assert server.model_name == "aya-expanse-8b"
                
                # Test model info
                model_info = await server.get_model_info()
                assert model_info.name == "aya-expanse-8b"
                assert model_info.type == "gguf"
                assert "generation" in model_info.capabilities
                
                # Test translation
                result = await server.translate("Hello, world!", "en", "es")
                assert result == "Hola, mundo!"
                
                await server.shutdown()
    
    @pytest.mark.asyncio
    async def test_nllb_integration(self):
        """Test NLLB model integration."""
        with patch.dict(os.environ, {"LINGUA_NEXUS_MODEL": "nllb"}):
            with patch('models.nllb.model.NLLBModel') as mock_model_class:
                # Setup mock model
                mock_model = Mock()
                mock_model.model_name = "nllb"
                mock_model.initialize = AsyncMock()
                mock_model.cleanup = AsyncMock()
                mock_model.health_check = AsyncMock(return_value=True)
                mock_model.get_model_info.return_value = ModelInfo(
                    name="nllb",
                    version="1.0.0",
                    supported_languages=["en", "ru", "es", "fr", "de", "zh"],
                    max_tokens=1024,
                    memory_requirements="2.5 GB RAM",
                    description="NLLB multilingual translation model"
                )
                mock_model.translate = AsyncMock(return_value="Привет, мир!")
                mock_model_class.return_value = mock_model
                
                # Test server initialization
                server = SingleModelServer("nllb")
                await server.startup()
                
                assert server.is_ready()
                assert server.model_name == "nllb"
                
                # Test model info
                model_info = await server.get_model_info()
                assert model_info.name == "nllb"
                assert model_info.type == "transformers"
                assert "translation" in model_info.capabilities
                
                # Test translation
                result = await server.translate("Hello, world!", "en", "ru")
                assert result == "Привет, мир!"
                
                await server.shutdown()


class TestAPICompatibility:
    """Test API compatibility and architectural constraints."""
    
    def test_single_instance_constraint(self, mock_server):
        """Test that server enforces single-model-per-instance constraint."""
        # Server should only have one model
        assert mock_server.model_name == "test-model"
        assert hasattr(mock_server, 'model')
        
        # Should not have multi-model registry
        assert not hasattr(mock_server, 'models')
        assert not hasattr(mock_server, 'registry')
    
    def test_api_response_format_compatibility(self, client):
        """Test API response format for backward compatibility."""
        headers = {"X-API-Key": "development-key"}
        
        # Test health check format
        response = client.get("/health")
        data = response.json()
        required_health_fields = ["status", "model_name", "timestamp"]
        for field in required_health_fields:
            assert field in data
        
        # Test model info format
        response = client.get("/model/info", headers=headers)
        data = response.json()
        required_info_fields = ["name", "version", "type", "supported_languages", "capabilities"]
        for field in required_info_fields:
            assert field in data
        
        # Test translation format
        translation_data = {
            "text": "Hello",
            "source_lang": "en",
            "target_lang": "ru"
        }
        response = client.post("/translate", json=translation_data, headers=headers)
        data = response.json()
        required_translation_fields = ["translated_text", "source_lang", "target_lang", "model_name", "processing_time_ms"]
        for field in required_translation_fields:
            assert field in data
    
    def test_environment_configuration(self):
        """Test environment-based model selection."""
        # Test default model
        with patch.dict(os.environ, {}, clear=True):
            with patch('app.single_model_main.SingleModelServer') as mock_server_class:
                create_app()
                mock_server_class.assert_called_with("nllb")  # Default
        
        # Test custom model
        with patch.dict(os.environ, {"LINGUA_NEXUS_MODEL": "aya-expanse-8b"}):
            with patch('app.single_model_main.SingleModelServer') as mock_server_class:
                create_app()
                mock_server_class.assert_called_with("aya-expanse-8b")
    
    def test_memory_efficiency_pattern(self, mock_server):
        """Test memory efficiency constraints of single-model architecture."""
        # Single model should be more memory efficient
        assert mock_server.model_name  # Has specific model name
        assert hasattr(mock_server, 'model')  # Has single model instance
        
        # Should not have multiple models loaded
        assert not hasattr(mock_server, 'models_list')
        assert not hasattr(mock_server, 'model_registry')
    
    def test_operational_simplicity_pattern(self, client):
        """Test operational simplicity of single-model architecture."""
        headers = {"X-API-Key": "development-key"}
        
        # Health check should be simple
        response = client.get("/health")
        assert response.status_code == 200
        
        # Model info should be straightforward
        response = client.get("/model/info", headers=headers)
        assert response.status_code == 200
        
        # Translation should be direct
        translation_data = {
            "text": "Hello",
            "source_lang": "en",
            "target_lang": "ru"
        }
        response = client.post("/translate", json=translation_data, headers=headers)
        assert response.status_code == 200
        
        # No complex model management endpoints
        response = client.post("/models/load/test", headers=headers)
        assert response.status_code == 404  # Should not exist
        
        response = client.get("/models", headers=headers)
        assert response.status_code == 404  # Should not exist
