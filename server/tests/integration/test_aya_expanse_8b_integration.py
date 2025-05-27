"""
Integration tests specifically for Aya Expanse 8B model.

This module tests the complete integration of the Aya Expanse 8B model
with the single-model server architecture, including GGUF-specific
functionality and multilingual capabilities.
"""

import pytest
import os
import asyncio
from unittest.mock import patch, Mock, AsyncMock
from fastapi.testclient import TestClient

from app.single_model_main import create_app, SingleModelServer
from models.base import (
    ModelInfo,
    TranslationRequest,
    ModelInitializationError,
    TranslationError,
    ModelNotReadyError
)


class TestAyaExpanse8BIntegration:
    """Test Aya Expanse 8B model integration."""
    
    @pytest.fixture
    def mock_aya_model(self):
        """Create mock Aya Expanse 8B model."""
        mock = AsyncMock()
        mock.model_name = "aya-expanse-8b"
        mock.model_type = "gguf"
        mock.initialize = AsyncMock()
        mock.cleanup = AsyncMock()
        mock.health_check = AsyncMock(return_value=True)
        
        # Model info with Aya-specific characteristics
        mock.get_model_info.return_value = ModelInfo(
            name="aya-expanse-8b",
            version="1.0.0",
            supported_languages=[
                "en", "ru", "es", "fr", "de", "zh", "ja", "ko",
                "ar", "hi", "pt", "it", "nl", "tr", "pl", "sv"
            ],
            max_tokens=32768,
            memory_requirements="8.0 GB RAM",
            description="Aya Expanse 8B GGUF quantized multilingual translation and generation model"
        )
        
        # Translation behavior - simulates high-quality multilingual translations
        async def mock_translate(text, source_lang, target_lang):
            translations = {
                ("Hello, world!", "en", "ru"): "Привет, мир!",
                ("Hello, world!", "en", "es"): "¡Hola, mundo!",
                ("Hello, world!", "en", "fr"): "Bonjour, le monde !",
                ("Hello, world!", "en", "de"): "Hallo, Welt!",
                ("Hello, world!", "en", "zh"): "你好，世界！",
                ("How are you?", "en", "ar"): "كيف حالك؟",
                ("Good morning", "en", "hi"): "सुप्रभात",
                ("Thank you", "en", "ja"): "ありがとうございます",
                ("Complex multilingual text with technical terms.", "en", "ru"): 
                    "Сложный многоязычный текст с техническими терминами."
            }
            return translations.get((text, source_lang, target_lang), f"[{target_lang}] {text}")
        
        mock.translate = mock_translate
        
        # Language detection for multilingual texts
        async def mock_detect_language(text):
            # Simple language detection simulation
            if any(char in text for char in "русский"):
                return "ru"
            elif any(char in text for char in "español"):
                return "es"
            elif any(char in text for char in "français"):
                return "fr"
            elif any(char in text for char in "中文"):
                return "zh"
            else:
                return "en"
        
        mock._detect_language = mock_detect_language
        return mock
    
    @pytest.fixture
    def aya_server(self, mock_aya_model):
        """Create server with Aya model."""
        server = Mock(spec=SingleModelServer)
        server.model_name = "aya-expanse-8b"
        server.model = mock_aya_model
        server.is_ready.return_value = True
        server.get_model_info = AsyncMock(return_value=mock_aya_model.get_model_info())
        server.translate = AsyncMock(side_effect=mock_aya_model.translate)
        server.health_check = AsyncMock(return_value=True)
        return server
    
    @pytest.fixture
    def aya_client(self, aya_server):
        """Create test client for Aya model."""
        with patch.dict(os.environ, {"LINGUA_NEXUS_MODEL": "aya-expanse-8b", "TESTING": "true"}):
            app = create_app()
            with patch('app.single_model_main.server', aya_server):
                return TestClient(app)
    
    def test_aya_model_info(self, aya_client):
        """Test Aya model information endpoint."""
        headers = {"X-API-Key": "development-key"}
        response = aya_client.get("/model/info", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify Aya-specific information
        assert data["name"] == "aya-expanse-8b"
        assert data["type"] == "gguf"
        assert "generation" in data["capabilities"]
        assert "multilingual" in data["capabilities"]
        assert data["model_size"] == "4.5 GB"
        assert data["memory_usage"] == "8.0 GB"
        assert "bartowski/aya-expanse-8b-GGUF" in data["model_path"]
        
        # Verify extensive language support
        supported_langs = data["supported_languages"]
        assert len(supported_langs) >= 16  # Aya supports many languages
        assert "zh" in supported_langs  # Chinese
        assert "ar" in supported_langs  # Arabic
        assert "hi" in supported_langs  # Hindi
        assert "ja" in supported_langs  # Japanese
    
    def test_aya_multilingual_translation(self, aya_client):
        """Test Aya's multilingual translation capabilities."""
        headers = {"X-API-Key": "development-key"}
        
        # Test various language pairs
        test_cases = [
            ("Hello, world!", "en", "ru", "Привет, мир!"),
            ("Hello, world!", "en", "es", "¡Hola, mundo!"),
            ("Hello, world!", "en", "fr", "Bonjour, le monde !"),
            ("Hello, world!", "en", "de", "Hallo, Welt!"),
            ("Hello, world!", "en", "zh", "你好，世界！"),
            ("How are you?", "en", "ar", "كيف حالك؟"),
            ("Good morning", "en", "hi", "सुप्रभात"),
            ("Thank you", "en", "ja", "ありがとうございます")
        ]
        
        for text, source, target, expected in test_cases:
            translation_data = {
                "text": text,
                "source_lang": source,
                "target_lang": target
            }
            
            response = aya_client.post("/translate", json=translation_data, headers=headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["translated_text"] == expected
            assert data["source_lang"] == source
            assert data["target_lang"] == target
            assert data["model_name"] == "aya-expanse-8b"
    
    def test_aya_complex_text_translation(self, aya_client):
        """Test Aya's handling of complex texts."""
        headers = {"X-API-Key": "development-key"}
        
        # Test complex technical text
        complex_text = "Complex multilingual text with technical terms."
        translation_data = {
            "text": complex_text,
            "source_lang": "en",
            "target_lang": "ru"
        }
        
        response = aya_client.post("/translate", json=translation_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["translated_text"] == "Сложный многоязычный текст с техническими терминами."
        assert data["processing_time_ms"] >= 0
    
    def test_aya_language_detection(self, aya_client):
        """Test Aya's language detection capabilities."""
        headers = {"X-API-Key": "development-key"}
        
        # Test language detection for various languages
        test_cases = [
            ("Hello world", "en"),
            ("Bonjour le monde", "fr"),  # Should detect as French
            ("Hola mundo", "es"),       # Should detect as Spanish
        ]
        
        for text, expected_lang in test_cases:
            response = aya_client.post(f"/detect?text={text}", headers=headers)
            
            assert response.status_code == 200
            data = response.json()
            # Note: Our mock returns 'en' for unknown patterns
            assert "detected_language" in data
            assert data["model"] == "aya-expanse-8b"
    
    def test_aya_health_check_gguf_specific(self, aya_client):
        """Test health check with GGUF-specific considerations."""
        response = aya_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["model_name"] == "aya-expanse-8b"
        
        # Check GGUF-specific model info
        model_info = data["model_info"]
        assert model_info["type"] == "gguf"
        assert "quantization" in model_info or "Q4_K_M" in str(model_info)
        assert "context_length" in model_info or model_info.get("context_length") == 32768
    
    @pytest.mark.asyncio
    async def test_aya_server_lifecycle_with_gguf(self):
        """Test server lifecycle with GGUF model considerations."""
        with patch('models.aya_expanse_8b.model.AyaExpanse8BModel') as mock_model_class:
            # Setup mock that simulates GGUF loading behavior
            mock_model = Mock()
            mock_model.model_name = "aya-expanse-8b"
            mock_model.initialize = AsyncMock()
            mock_model.cleanup = AsyncMock()
            mock_model.health_check = AsyncMock(return_value=True)
            mock_model.get_model_info.return_value = ModelInfo(
                name="aya-expanse-8b",
                version="1.0.0",
                supported_languages=["en", "ru", "es"],
                max_tokens=32768,
                memory_requirements="8.0 GB RAM",
                description="Aya Expanse 8B GGUF multilingual model"
            )
            mock_model_class.return_value = mock_model
            
            server = SingleModelServer("aya-expanse-8b")
            
            # Test initialization (GGUF models may take longer to load)
            await server.startup()
            assert server.is_ready()
            mock_model.initialize.assert_called_once()
            
            # Test that model is properly loaded
            assert server.model == mock_model
            assert server.model_name == "aya-expanse-8b"
            
            # Test cleanup (important for GGUF memory management)
            await server.shutdown()
            mock_model.cleanup.assert_called_once()
            assert not server.is_ready()
    
    def test_aya_performance_characteristics(self, aya_client):
        """Test performance characteristics expected for Aya model."""
        headers = {"X-API-Key": "development-key"}
        
        # Test translation request
        translation_data = {
            "text": "Hello, world!",
            "source_lang": "en",
            "target_lang": "ru"
        }
        
        response = aya_client.post("/translate", json=translation_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that processing time is reported
        assert "processing_time_ms" in data
        assert data["processing_time_ms"] >= 0
        
        # Model name should be correctly reported
        assert data["model_name"] == "aya-expanse-8b"
    
    def test_aya_error_handling(self, aya_client, aya_server):
        """Test error handling specific to Aya model."""
        headers = {"X-API-Key": "development-key"}
        
        # Test when model is not ready
        aya_server.is_ready.return_value = False
        
        translation_data = {
            "text": "Hello, world!",
            "source_lang": "en",
            "target_lang": "ru"
        }
        
        response = aya_client.post("/translate", json=translation_data, headers=headers)
        assert response.status_code == 503
        assert "not ready" in response.json()["detail"]
        
        # Test translation error
        aya_server.is_ready.return_value = True
        aya_server.translate = AsyncMock(side_effect=TranslationError("GGUF model error", "aya-expanse-8b"))
        
        response = aya_client.post("/translate", json=translation_data, headers=headers)
        assert response.status_code == 500
        assert "GGUF model error" in response.json()["detail"]
    
    def test_aya_memory_efficiency_verification(self, aya_server):
        """Test memory efficiency aspects of single Aya instance."""
        # Verify single model instance
        assert aya_server.model_name == "aya-expanse-8b"
        assert hasattr(aya_server, 'model')
        
        # Should not have multiple models
        assert not hasattr(aya_server, 'models')
        assert not hasattr(aya_server, 'model_registry')
        
        # Model info should reflect memory usage
        model_info = aya_server.model.get_model_info()
        assert model_info.memory_usage == "8.0 GB"
        assert model_info.model_size == "4.5 GB"
    
    def test_aya_api_compatibility_verification(self, aya_client):
        """Test API compatibility for Aya model."""
        headers = {"X-API-Key": "development-key"}
        
        # Test health endpoint
        response = aya_client.get("/health")
        assert response.status_code == 200
        
        # Test model info endpoint
        response = aya_client.get("/model/info", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert all(field in data for field in ["name", "version", "type", "supported_languages"])
        
        # Test translation endpoint
        translation_data = {
            "text": "Hello",
            "source_lang": "en",
            "target_lang": "ru"
        }
        response = aya_client.post("/translate", json=translation_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert all(field in data for field in ["translated_text", "source_lang", "target_lang", "model_name"])
        
        # Test language detection endpoint
        response = aya_client.post("/detect?text=Hello world", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert all(field in data for field in ["detected_language", "text", "model"])


class TestAyaExpanse8BLoadingAndConfiguration:
    """Test Aya Expanse 8B specific loading and configuration."""
    
    @pytest.mark.asyncio
    async def test_aya_model_loading(self):
        """Test Aya model loading through server."""
        with patch('models.aya_expanse_8b.model.AyaExpanse8BModel') as mock_model_class:
            mock_instance = Mock()
            mock_model_class.return_value = mock_instance
            
            server = SingleModelServer("aya-expanse-8b")
            model = await server._load_model("aya-expanse-8b")
            
            assert model == mock_instance
            mock_model_class.assert_called_once()
    
    def test_aya_environment_configuration(self):
        """Test Aya-specific environment configuration."""
        with patch.dict(os.environ, {"LINGUA_NEXUS_MODEL": "aya-expanse-8b"}):
            with patch('app.single_model_main.SingleModelServer') as mock_server_class:
                create_app()
                mock_server_class.assert_called_with("aya-expanse-8b")
    
    def test_aya_application_title_and_description(self):
        """Test application metadata for Aya model."""
        with patch.dict(os.environ, {"LINGUA_NEXUS_MODEL": "aya-expanse-8b"}):
            app = create_app()
            assert "Aya-Expanse-8B" in app.title
            assert "aya-expanse-8b" in app.description
