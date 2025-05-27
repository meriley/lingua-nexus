"""
Integration tests for multi-model translation API.

This module tests the complete multi-model API functionality including
model loading, translation endpoints, and model management.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock

# Import the multi-model app
from app.main_multimodel import app, model_registry
from app.models.registry import ModelRegistry


class TestMultiModelAPI:
    """Test multi-model API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_registry(self):
        """Mock model registry for testing."""
        with patch('app.main_multimodel.model_registry') as mock_reg:
            mock_reg.list_available_models.return_value = ['nllb', 'aya']
            mock_reg.get_model.return_value = Mock()
            mock_reg.get_model_info.return_value = {
                'name': 'test_model',
                'type': 'nllb',
                'available': True,
                'device': 'cpu',
                'model_size': '1.2 GB'
            }
            yield mock_reg
    
    def test_health_endpoint_no_registry(self, client):
        """Test health endpoint when registry is not initialized."""
        with patch('app.main_multimodel.model_registry', None):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "starting"
            assert data["models_loaded"] == 0
    
    def test_health_endpoint_with_models(self, client, mock_registry):
        """Test health endpoint with loaded models."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["models_loaded"] == 2
        assert "nllb" in data["models_available"]
        assert "aya" in data["models_available"]
    
    def test_models_list_endpoint(self, client, mock_registry):
        """Test models listing endpoint."""
        # Mock model with get_supported_languages method
        mock_model = Mock()
        mock_model.get_supported_languages.return_value = ['en', 'ru', 'es']
        mock_registry.get_model.return_value = mock_model
        
        headers = {"X-API-Key": "development-key"}
        response = client.get("/models", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # nllb and aya
        assert data[0]["name"] in ["nllb", "aya"]
        assert data[0]["available"] is True
    
    def test_models_list_unauthorized(self, client):
        """Test models listing without API key."""
        response = client.get("/models")
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_load_model_endpoint(self, client, mock_registry):
        """Test model loading endpoint."""
        mock_registry.load_model = AsyncMock()
        
        headers = {"X-API-Key": "development-key"}
        response = client.post("/models/aya/load", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "loaded successfully" in data["message"]
    
    def test_unload_model_endpoint(self, client, mock_registry):
        """Test model unloading endpoint."""
        headers = {"X-API-Key": "development-key"}
        response = client.delete("/models/aya", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "unloaded successfully" in data["message"]
    
    def test_languages_endpoint(self, client, mock_registry):
        """Test supported languages endpoint."""
        # Mock model behavior
        mock_model = Mock()
        mock_model.is_available.return_value = True
        mock_model.get_supported_languages.return_value = ['en', 'ru', 'es']
        mock_registry.get_model.return_value = mock_model
        
        headers = {"X-API-Key": "development-key"}
        response = client.get("/languages", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3  # At least en, ru, es
        
        # Check language info structure
        lang_info = next((lang for lang in data if lang["iso_code"] == "en"), None)
        assert lang_info is not None
        assert lang_info["name"] == "English"
        assert len(lang_info["models_supporting"]) == 2  # Both models
    
    def test_model_languages_endpoint(self, client, mock_registry):
        """Test model-specific languages endpoint."""
        mock_model = Mock()
        mock_model.is_available.return_value = True
        mock_model.get_supported_languages.return_value = ['en', 'ru', 'es', 'fr']
        mock_registry.get_model.return_value = mock_model
        
        headers = {"X-API-Key": "development-key"}
        response = client.get("/languages/nllb", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "nllb"
        assert "en" in data["supported_languages"]
        assert data["language_names"]["en"] == "English"
    
    @pytest.mark.asyncio
    async def test_translate_endpoint(self, client, mock_registry):
        """Test translation endpoint."""
        # Mock model and translation
        mock_model = Mock()
        mock_model.is_available.return_value = True
        mock_model.supports_language_pair.return_value = True
        
        # Mock async translate method
        async def mock_translate(request):
            from app.models.base import TranslationResponse
            return TranslationResponse(
                translated_text="Привет, мир!",
                detected_source_lang=None,
                processing_time_ms=150.5,
                model_used="nllb",
                metadata={"device": "cpu"}
            )
        
        mock_model.translate = mock_translate
        mock_registry.get_model.return_value = mock_model
        
        headers = {"X-API-Key": "development-key"}
        translation_data = {
            "text": "Hello, world!",
            "source_lang": "en",
            "target_lang": "ru",
            "model": "nllb"
        }
        
        response = client.post("/translate", json=translation_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["translated_text"] == "Привет, мир!"
        assert data["model_used"] == "nllb"
        assert data["processing_time_ms"] == 150.5
    
    def test_translate_invalid_model(self, client, mock_registry):
        """Test translation with invalid model."""
        mock_registry.get_model.side_effect = ValueError("Model not found")
        
        headers = {"X-API-Key": "development-key"}
        translation_data = {
            "text": "Hello, world!",
            "source_lang": "en",
            "target_lang": "ru",
            "model": "invalid_model"
        }
        
        response = client.post("/translate", json=translation_data, headers=headers)
        assert response.status_code == 404
    
    def test_translate_unsupported_language_pair(self, client, mock_registry):
        """Test translation with unsupported language pair."""
        mock_model = Mock()
        mock_model.is_available.return_value = True
        mock_model.supports_language_pair.return_value = False
        mock_registry.get_model.return_value = mock_model
        
        headers = {"X-API-Key": "development-key"}
        translation_data = {
            "text": "Hello, world!",
            "source_lang": "en",
            "target_lang": "zz",  # Unsupported language
            "model": "nllb"
        }
        
        response = client.post("/translate", json=translation_data, headers=headers)
        assert response.status_code == 400
        assert "does not support" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_batch_translate_endpoint(self, client, mock_registry):
        """Test batch translation endpoint."""
        # Setup mock model
        mock_model = Mock()
        mock_model.is_available.return_value = True
        mock_model.supports_language_pair.return_value = True
        
        async def mock_translate(request):
            from app.models.base import TranslationResponse
            return TranslationResponse(
                translated_text=f"Translated: {request.text}",
                detected_source_lang=None,
                processing_time_ms=100.0,
                model_used="nllb",
                metadata={}
            )
        
        mock_model.translate = mock_translate
        mock_registry.get_model.return_value = mock_model
        
        headers = {"X-API-Key": "development-key"}
        batch_data = [
            {
                "text": "Hello",
                "source_lang": "en",
                "target_lang": "ru",
                "model": "nllb"
            },
            {
                "text": "World",
                "source_lang": "en",
                "target_lang": "ru",
                "model": "nllb"
            }
        ]
        
        response = client.post("/translate/batch", json=batch_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_processed"] == 2
        assert data["total_errors"] == 0
        assert len(data["results"]) == 2
    
    def test_batch_translate_too_large(self, client, mock_registry):
        """Test batch translation with too many requests."""
        headers = {"X-API-Key": "development-key"}
        batch_data = [{"text": f"Text {i}", "target_lang": "ru", "model": "nllb"} 
                      for i in range(11)]  # Exceed limit of 10
        
        response = client.post("/translate/batch", json=batch_data, headers=headers)
        assert response.status_code == 400
        assert "cannot exceed 10" in response.json()["detail"]
    
    def test_legacy_translate_endpoint(self, client, mock_registry):
        """Test legacy translation endpoint for backward compatibility."""
        # Mock model
        mock_model = Mock()
        mock_model.is_available.return_value = True
        mock_model.supports_language_pair.return_value = True
        
        async def mock_translate(request):
            from app.models.base import TranslationResponse
            return TranslationResponse(
                translated_text="Привет",
                detected_source_lang="en",
                processing_time_ms=120.0,
                model_used="nllb",
                metadata={}
            )
        
        mock_model.translate = mock_translate
        mock_registry.get_model.return_value = mock_model
        
        headers = {"X-API-Key": "development-key"}
        legacy_data = {
            "text": "Hello",
            "source_lang": "en",
            "target_lang": "ru"
        }
        
        response = client.post("/translate/legacy", json=legacy_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["translated_text"] == "Привет"
        assert data["detected_source"] == "en"
        assert data["time_ms"] == 120


class TestModelRegistryIntegration:
    """Test model registry integration."""
    
    @pytest.mark.asyncio
    async def test_registry_model_loading(self):
        """Test async model loading through registry."""
        registry = ModelRegistry()
        
        # Mock the model classes to avoid actual loading
        with patch('app.models.nllb_model.NLLBModel') as mock_nllb:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_instance.model_name = "nllb"
            mock_nllb.return_value = mock_instance
            
            await registry.load_model("nllb")
            
            assert "nllb" in registry
            assert registry.get_model("nllb") == mock_instance
    
    @pytest.mark.asyncio
    async def test_registry_concurrent_loading(self):
        """Test concurrent model loading."""
        registry = ModelRegistry()
        
        with patch('app.models.nllb_model.NLLBModel') as mock_nllb:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_instance.model_name = "nllb"
            mock_nllb.return_value = mock_instance
            
            # Start multiple loading tasks concurrently
            tasks = [
                registry.load_model("nllb"),
                registry.load_model("nllb"),
                registry.load_model("nllb")
            ]
            
            await asyncio.gather(*tasks)
            
            # Should only create one instance
            assert mock_nllb.call_count == 1
            assert "nllb" in registry
    
    def test_registry_cleanup(self):
        """Test registry cleanup functionality."""
        registry = ModelRegistry()
        
        # Add mock model
        mock_model = Mock()
        mock_model.cleanup = Mock()
        registry.register_model("test_model", mock_model)
        
        assert len(registry) == 1
        
        # Test cleanup
        registry.cleanup_all()
        
        assert len(registry) == 0
        mock_model.cleanup.assert_called_once()
    
    def test_registry_default_configs(self):
        """Test default configuration loading."""
        registry = ModelRegistry()
        
        nllb_config = registry._get_default_config("nllb")
        assert nllb_config["model_path"] == "facebook/nllb-200-distilled-600M"
        assert nllb_config["device"] == "auto"
        
        aya_config = registry._get_default_config("aya")
        assert aya_config["model_path"] == "CohereForAI/aya-expanse-8b"
        assert aya_config["use_quantization"] is True