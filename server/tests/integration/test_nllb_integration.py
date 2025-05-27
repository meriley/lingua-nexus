"""
Integration tests specifically for NLLB model.

This module tests the complete integration of the NLLB model
with the single-model server architecture, including transformers-specific
functionality and multilingual translation capabilities.
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


class TestNLLBIntegration:
    """Test NLLB model integration."""
    
    @pytest.fixture
    def mock_nllb_model(self):
        """Create mock NLLB model."""
        mock = AsyncMock()
        mock.model_name = "nllb"
        mock.model_type = "transformers"
        mock.initialize = AsyncMock()
        mock.cleanup = AsyncMock()
        mock.health_check = AsyncMock(return_value=True)
        
        # Model info with NLLB-specific characteristics
        mock.get_model_info.return_value = ModelInfo(
            name="nllb",
            version="1.0.0",
            supported_languages=[
                "en", "ru", "es", "fr", "de", "zh", "ja", "ko", "ar", "hi",
                "pt", "it", "nl", "tr", "pl", "sv", "da", "no", "fi", "el",
                "he", "th", "vi", "id", "ms", "tl", "sw", "am", "yo", "zu"
            ],
            max_tokens=1024,
            memory_requirements="2.5 GB RAM",
            description="NLLB-200 distilled 600M multilingual translation model"
        )
        
        # Translation behavior - simulates NLLB's strong multilingual performance
        async def mock_translate(text, source_lang, target_lang):
            translations = {
                ("Hello, world!", "en", "ru"): "Привет, мир!",
                ("Hello, world!", "en", "es"): "¡Hola, mundo!",
                ("Hello, world!", "en", "fr"): "Bonjour le monde!",
                ("Hello, world!", "en", "de"): "Hallo Welt!",
                ("Hello, world!", "en", "zh"): "你好世界！",
                ("Hello, world!", "en", "ar"): "مرحبا بالعالم!",
                ("Hello, world!", "en", "hi"): "नमस्ते दुनिया!",
                ("Hello, world!", "en", "ja"): "こんにちは世界！",
                # Reverse translations
                ("Привет, мир!", "ru", "en"): "Hello, world!",
                ("¡Hola, mundo!", "es", "en"): "Hello, world!",
                # Cross-language (non-English) translations
                ("Bonjour le monde!", "fr", "es"): "¡Hola mundo!",
                ("Привет", "ru", "de"): "Hallo",
                # Long text handling
                ("This is a longer text that tests the model's ability to handle sentences with multiple clauses and complex grammatical structures.", "en", "ru"):
                    "Это более длинный текст, который проверяет способность модели обрабатывать предложения с несколькими клаузулами и сложными грамматическими структурами."
            }
            return translations.get((text, source_lang, target_lang), f"[NLLB:{target_lang}] {text}")
        
        mock.translate = mock_translate
        
        # Language detection with character-based detection
        async def mock_detect_language(text):
            # NLLB-style language detection based on character patterns
            if any(char in text for char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"):
                return "ru"
            elif any(char in text for char in "áéíóúüñ"):
                return "es"
            elif any(char in text for char in "àâäçèéêëîïôöùûüÿ"):
                return "fr"
            elif any(char in text for char in "äöüß"):
                return "de"
            elif any(char in text for char in "一-鿿"):
                return "zh"
            elif any(char in text for char in "぀-ゟ゠-ヿ"):
                return "ja"
            elif any(char in text for char in "؀-ۿ"):
                return "ar"
            elif any(char in text for char in "ऀ-ॿ"):
                return "hi"
            else:
                return "en"
        
        mock._detect_language = mock_detect_language
        return mock
    
    @pytest.fixture
    def nllb_server(self, mock_nllb_model):
        """Create server with NLLB model."""
        server = Mock(spec=SingleModelServer)
        server.model_name = "nllb"
        server.model = mock_nllb_model
        server.is_ready.return_value = True
        server.get_model_info = AsyncMock(return_value=mock_nllb_model.get_model_info())
        server.translate = AsyncMock(side_effect=mock_nllb_model.translate)
        server.health_check = AsyncMock(return_value=True)
        return server
    
    @pytest.fixture
    def nllb_client(self, nllb_server):
        """Create test client for NLLB model."""
        with patch.dict(os.environ, {"LINGUA_NEXUS_MODEL": "nllb", "TESTING": "true"}):
            app = create_app()
            with patch('app.single_model_main.server', nllb_server):
                return TestClient(app)
    
    def test_nllb_model_info(self, nllb_client):
        """Test NLLB model information endpoint."""
        headers = {"X-API-Key": "development-key"}
        response = nllb_client.get("/model/info", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify NLLB-specific information
        assert data["name"] == "nllb"
        assert data["type"] == "transformers"
        assert "multilingual" in data["capabilities"]
        assert "distilled" in data["capabilities"]
        assert data["model_size"] == "1.2 GB"
        assert data["memory_usage"] == "2.5 GB"
        assert "facebook/nllb-200-distilled-600M" in data["model_path"]
        
        # Verify extensive language support (NLLB supports 200+ languages)
        supported_langs = data["supported_languages"]
        assert len(supported_langs) >= 30  # Comprehensive language coverage
        
        # Check for major language families
        assert "en" in supported_langs  # English
        assert "zh" in supported_langs  # Chinese
        assert "ar" in supported_langs  # Arabic
        assert "hi" in supported_langs  # Hindi
        assert "es" in supported_langs  # Spanish
        assert "fr" in supported_langs  # French
        assert "ru" in supported_langs  # Russian
        assert "ja" in supported_langs  # Japanese
        assert "ko" in supported_langs  # Korean
        assert "pt" in supported_langs  # Portuguese
        
        # Check for African languages (NLLB strength)
        assert "sw" in supported_langs  # Swahili
        assert "yo" in supported_langs  # Yoruba
        assert "zu" in supported_langs  # Zulu
    
    def test_nllb_multilingual_translation(self, nllb_client):
        """Test NLLB's multilingual translation capabilities."""
        headers = {"X-API-Key": "development-key"}
        
        # Test various language pairs
        test_cases = [
            ("Hello, world!", "en", "ru", "Привет, мир!"),
            ("Hello, world!", "en", "es", "¡Hola, mundo!"),
            ("Hello, world!", "en", "fr", "Bonjour le monde!"),
            ("Hello, world!", "en", "de", "Hallo Welt!"),
            ("Hello, world!", "en", "zh", "你好世界！"),
            ("Hello, world!", "en", "ar", "مرحبا بالعالم!"),
            ("Hello, world!", "en", "hi", "नमस्ते दुनिया!"),
            ("Hello, world!", "en", "ja", "こんにちは世界！")
        ]
        
        for text, source, target, expected in test_cases:
            translation_data = {
                "text": text,
                "source_lang": source,
                "target_lang": target
            }
            
            response = nllb_client.post("/translate", json=translation_data, headers=headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["translated_text"] == expected
            assert data["source_lang"] == source
            assert data["target_lang"] == target
            assert data["model_name"] == "nllb"
    
    def test_nllb_reverse_translation(self, nllb_client):
        """Test NLLB's bidirectional translation capabilities."""
        headers = {"X-API-Key": "development-key"}
        
        # Test reverse translation (non-English to English)
        test_cases = [
            ("Привет, мир!", "ru", "en", "Hello, world!"),
            ("¡Hola, mundo!", "es", "en", "Hello, world!")
        ]
        
        for text, source, target, expected in test_cases:
            translation_data = {
                "text": text,
                "source_lang": source,
                "target_lang": target
            }
            
            response = nllb_client.post("/translate", json=translation_data, headers=headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["translated_text"] == expected
    
    def test_nllb_cross_language_translation(self, nllb_client):
        """Test NLLB's direct cross-language translation (bypassing English)."""
        headers = {"X-API-Key": "development-key"}
        
        # Test non-English to non-English translation
        test_cases = [
            ("Bonjour le monde!", "fr", "es", "¡Hola mundo!"),
            ("Привет", "ru", "de", "Hallo")
        ]
        
        for text, source, target, expected in test_cases:
            translation_data = {
                "text": text,
                "source_lang": source,
                "target_lang": target
            }
            
            response = nllb_client.post("/translate", json=translation_data, headers=headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["translated_text"] == expected
    
    def test_nllb_long_text_handling(self, nllb_client):
        """Test NLLB's handling of longer texts."""
        headers = {"X-API-Key": "development-key"}
        
        # Test complex sentence structure
        long_text = "This is a longer text that tests the model's ability to handle sentences with multiple clauses and complex grammatical structures."
        translation_data = {
            "text": long_text,
            "source_lang": "en",
            "target_lang": "ru"
        }
        
        response = nllb_client.post("/translate", json=translation_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        # Verify we get a proper Russian translation
        expected_russian = "Это более длинный текст, который проверяет способность модели обрабатывать предложения с несколькими клаузулами и сложными грамматическими структурами."
        assert data["translated_text"] == expected_russian
        assert data["processing_time_ms"] >= 0
    
    def test_nllb_language_detection(self, nllb_client):
        """Test NLLB's character-based language detection."""
        headers = {"X-API-Key": "development-key"}
        
        # Test language detection for various scripts
        test_cases = [
            ("Hello world", "en"),
            ("Привет мир", "ru"),     # Cyrillic
            ("¡Hola mundo!", "es"),        # Spanish with accents
            ("Bonjour le monde", "fr"),     # French
            ("Guten Tag", "de"),           # German
        ]
        
        for text, expected_lang in test_cases:
            response = nllb_client.post(f"/detect?text={text}", headers=headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["detected_language"] == expected_lang
            assert data["model"] == "nllb"
    
    def test_nllb_health_check_transformers_specific(self, nllb_client):
        """Test health check with transformers-specific considerations."""
        response = nllb_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["model_name"] == "nllb"
        
        # Check transformers-specific model info
        model_info = data["model_info"]
        assert model_info["type"] == "transformers"
        assert "architecture" in model_info or model_info.get("architecture") == "transformer"
        assert "distilled" in model_info.get("capabilities", [])
    
    @pytest.mark.asyncio
    async def test_nllb_server_lifecycle_with_transformers(self):
        """Test server lifecycle with transformers model considerations."""
        with patch('models.nllb.model.NLLBModel') as mock_model_class:
            # Setup mock that simulates transformers loading behavior
            mock_model = Mock()
            mock_model.model_name = "nllb"
            mock_model.initialize = AsyncMock()
            mock_model.cleanup = AsyncMock()
            mock_model.health_check = AsyncMock(return_value=True)
            mock_model.get_model_info.return_value = ModelInfo(
                name="nllb",
                version="1.0.0",
                supported_languages=["en", "ru", "es"],
                max_tokens=1024,
                memory_requirements="2.5 GB RAM",
                description="NLLB multilingual translation model"
            )
            mock_model_class.return_value = mock_model
            
            server = SingleModelServer("nllb")
            
            # Test initialization (transformers models load faster than GGUF)
            await server.startup()
            assert server.is_ready()
            mock_model.initialize.assert_called_once()
            
            # Test that model is properly loaded
            assert server.model == mock_model
            assert server.model_name == "nllb"
            
            # Test cleanup (important for transformers memory management)
            await server.shutdown()
            mock_model.cleanup.assert_called_once()
            assert not server.is_ready()
    
    def test_nllb_performance_characteristics(self, nllb_client):
        """Test performance characteristics expected for NLLB model."""
        headers = {"X-API-Key": "development-key"}
        
        # Test translation request
        translation_data = {
            "text": "Hello, world!",
            "source_lang": "en",
            "target_lang": "ru"
        }
        
        response = nllb_client.post("/translate", json=translation_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that processing time is reported
        assert "processing_time_ms" in data
        assert data["processing_time_ms"] >= 0
        
        # Model name should be correctly reported
        assert data["model_name"] == "nllb"
    
    def test_nllb_error_handling(self, nllb_client, nllb_server):
        """Test error handling specific to NLLB model."""
        headers = {"X-API-Key": "development-key"}
        
        # Test when model is not ready
        nllb_server.is_ready.return_value = False
        
        translation_data = {
            "text": "Hello, world!",
            "source_lang": "en",
            "target_lang": "ru"
        }
        
        response = nllb_client.post("/translate", json=translation_data, headers=headers)
        assert response.status_code == 503
        assert "not ready" in response.json()["detail"]
        
        # Test translation error
        nllb_server.is_ready.return_value = True
        nllb_server.translate = AsyncMock(side_effect=TranslationError("Transformers model error", "nllb"))
        
        response = nllb_client.post("/translate", json=translation_data, headers=headers)
        assert response.status_code == 500
        assert "Transformers model error" in response.json()["detail"]
    
    def test_nllb_memory_efficiency_verification(self, nllb_server):
        """Test memory efficiency aspects of single NLLB instance."""
        # Verify single model instance
        assert nllb_server.model_name == "nllb"
        assert hasattr(nllb_server, 'model')
        
        # Should not have multiple models
        assert not hasattr(nllb_server, 'models')
        assert not hasattr(nllb_server, 'model_registry')
        
        # Model info should reflect efficient memory usage
        model_info = nllb_server.model.get_model_info()
        assert model_info.memory_usage == "2.5 GB"  # More efficient than Aya
        assert model_info.model_size == "1.2 GB"   # Smaller than Aya
    
    def test_nllb_distilled_model_characteristics(self, nllb_client):
        """Test characteristics specific to NLLB distilled model."""
        headers = {"X-API-Key": "development-key"}
        response = nllb_client.get("/model/info", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify distilled model characteristics
        assert "distilled" in data["capabilities"]
        assert "600M" in data["model_path"]  # facebook/nllb-200-distilled-600M
        
        # Distilled models should be smaller and faster
        assert "1.2 GB" in data["model_size"]  # Smaller than full models
        assert "2.5 GB" in data["memory_usage"]  # Efficient memory usage


class TestNLLBLoadingAndConfiguration:
    """Test NLLB specific loading and configuration."""
    
    @pytest.mark.asyncio
    async def test_nllb_model_loading(self):
        """Test NLLB model loading through server."""
        with patch('models.nllb.model.NLLBModel') as mock_model_class:
            mock_instance = Mock()
            mock_model_class.return_value = mock_instance
            
            server = SingleModelServer("nllb")
            model = await server._load_model("nllb")
            
            assert model == mock_instance
            mock_model_class.assert_called_once()
    
    def test_nllb_environment_configuration(self):
        """Test NLLB-specific environment configuration."""
        with patch.dict(os.environ, {"LINGUA_NEXUS_MODEL": "nllb"}):
            with patch('app.single_model_main.SingleModelServer') as mock_server_class:
                create_app()
                mock_server_class.assert_called_with("nllb")
    
    def test_nllb_default_configuration(self):
        """Test NLLB as default model configuration."""
        with patch.dict(os.environ, {}, clear=True):  # No LINGUA_NEXUS_MODEL set
            with patch('app.single_model_main.SingleModelServer') as mock_server_class:
                create_app()
                mock_server_class.assert_called_with("nllb")  # Should default to NLLB
    
    def test_nllb_application_title_and_description(self):
        """Test application metadata for NLLB model."""
        with patch.dict(os.environ, {"LINGUA_NEXUS_MODEL": "nllb"}):
            app = create_app()
            assert "Nllb" in app.title
            assert "nllb" in app.description


class TestNLLBAPICompatibilityAndPerformance:
    """Test NLLB API compatibility and performance characteristics."""
    
    def test_nllb_api_compatibility_verification(self, nllb_client):
        """Test API compatibility for NLLB model."""
        headers = {"X-API-Key": "development-key"}
        
        # Test health endpoint
        response = nllb_client.get("/health")
        assert response.status_code == 200
        
        # Test model info endpoint
        response = nllb_client.get("/model/info", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert all(field in data for field in ["name", "version", "type", "supported_languages"])
        
        # Test translation endpoint
        translation_data = {
            "text": "Hello",
            "source_lang": "en",
            "target_lang": "ru"
        }
        response = nllb_client.post("/translate", json=translation_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert all(field in data for field in ["translated_text", "source_lang", "target_lang", "model_name"])
        
        # Test language detection endpoint
        response = nllb_client.post("/detect?text=Hello world", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert all(field in data for field in ["detected_language", "text", "model"])
    
    def test_nllb_comprehensive_language_support(self, nllb_client):
        """Test NLLB's comprehensive language support."""
        headers = {"X-API-Key": "development-key"}
        response = nllb_client.get("/model/info", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        supported_langs = data["supported_languages"]
        
        # Test major language families are supported
        language_families = {
            "Germanic": ["en", "de", "nl", "sv", "da", "no"],
            "Romance": ["es", "fr", "pt", "it"],
            "Slavic": ["ru", "pl"],
            "Sino-Tibetan": ["zh"],
            "Semitic": ["ar", "he"],
            "Indo-Aryan": ["hi"],
            "Japonic": ["ja"],
            "Koreanic": ["ko"],
            "Niger-Congo": ["sw", "yo", "zu"],  # NLLB's strength in African languages
            "Austronesian": ["id", "ms", "tl"]
        }
        
        for family, languages in language_families.items():
            family_supported = [lang for lang in languages if lang in supported_langs]
            assert len(family_supported) > 0, f"No {family} languages supported"
    
    def test_nllb_translation_quality_patterns(self, nllb_client):
        """Test translation quality patterns specific to NLLB."""
        headers = {"X-API-Key": "development-key"}
        
        # Test that NLLB provides consistent translation formats
        test_cases = [
            ("Hello", "en", "ru"),
            ("World", "en", "es"),
            ("Peace", "en", "fr")
        ]
        
        for text, source, target in test_cases:
            translation_data = {
                "text": text,
                "source_lang": source,
                "target_lang": target
            }
            
            response = nllb_client.post("/translate", json=translation_data, headers=headers)
            assert response.status_code == 200
            
            data = response.json()
            # NLLB should provide non-empty translations
            assert len(data["translated_text"]) > 0
            # Should not just return the input text
            assert data["translated_text"] != text
            # Should include model name
            assert data["model_name"] == "nllb"
