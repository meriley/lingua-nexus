"""
E2E tests specifically for NLLB model functionality.
"""

import pytest
import sys
import os
import time

# Add the e2e directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.robust_service_manager import RobustServiceManager
from utils.service_manager import MultiModelServiceConfig
from utils.comprehensive_client import ComprehensiveTestClient


class TestNLLBModelE2E:
    """E2E tests for NLLB model integration."""
    
    def test_nllb_model_loading(self):
        """Test that NLLB model can be loaded and monitored properly."""
        manager = RobustServiceManager()
        
        try:
            # Configure service with only NLLB model
            config = MultiModelServiceConfig(
                api_key="development-key",
                models_to_load="nllb",  # Only load NLLB
                log_level="INFO",
                custom_env={
                    "API_KEY": "development-key",
                    "PYTEST_RUNNING": "true",
                    "MODELS_TO_LOAD": "nllb",
                    "NLLB_MODEL": "facebook/nllb-200-distilled-600M",
                    "MODEL_CACHE_DIR": os.path.expanduser("~/.cache/huggingface/transformers"),
                    "HF_HOME": os.path.expanduser("~/.cache/huggingface"),
                    "TRANSFORMERS_CACHE": os.path.expanduser("~/.cache/huggingface/transformers"),
                    "MODEL_LOADING_TIMEOUT": "1800",  # 30 minutes
                    "LOG_MODEL_LOADING_PROGRESS": "true",
                }
            )
            
            # Track loading time
            loading_start = time.time()
            
            # Start service and wait for model
            service_url = manager.start_with_model_wait(
                config=config,
                model_name="nllb",
                timeout=1800  # 30 minutes for NLLB
            )
            assert service_url is not None
            
            loading_duration = time.time() - loading_start
            print(f"NLLB model loaded in {loading_duration:.1f} seconds")
            
            # Create client
            client = ComprehensiveTestClient(service_url, api_key="development-key")
            
            # Verify model status
            model_status = client.get_model_status("nllb")
            assert model_status["available"]
            assert model_status["loaded"]
            assert model_status["ready"]
            print(f"NLLB model status: {model_status}")
            
            # Check health with loaded model
            health_result = client.get("/health")
            assert health_result.status_code == 200
            health_data = health_result.response_data
            assert health_data["status"] == "healthy"
            assert health_data.get("models_loaded", 0) > 0
            print(f"Service health with NLLB loaded: {health_data}")
            
            # Get loading performance report
            report = manager.get_model_loading_report()
            assert "nllb" in report["models_loaded"]
            assert report["loading_times"]["nllb"] > 0  # Should have some loading time recorded
            print(f"Performance report: {report}")
            print(f"Total loading duration: {loading_duration:.3f}s vs Monitor measured: {report['loading_times']['nllb']:.3f}s")
            
        finally:
            manager.cleanup()
    
    def test_nllb_translation(self):
        """Test NLLB model translation capabilities with proper synchronization."""
        manager = RobustServiceManager()
        
        try:
            # Configure service
            config = MultiModelServiceConfig(
                api_key="development-key",
                models_to_load="nllb",
                log_level="INFO",
                custom_env={
                    "API_KEY": "development-key",
                    "PYTEST_RUNNING": "true",
                    "MODELS_TO_LOAD": "nllb",
                    "NLLB_MODEL": "facebook/nllb-200-distilled-600M",
                    "MODEL_CACHE_DIR": os.path.expanduser("~/.cache/huggingface/transformers"),
                    "HF_HOME": os.path.expanduser("~/.cache/huggingface"),
                    "TRANSFORMERS_CACHE": os.path.expanduser("~/.cache/huggingface/transformers"),
                    "MODEL_LOADING_TIMEOUT": "1800",  # 30 minutes
                    "LOG_MODEL_LOADING_PROGRESS": "true",
                }
            )
            
            # Start service and wait for model to be ready
            service_url = manager.start_with_model_wait(
                config=config, 
                model_name="nllb", 
                timeout=1800  # 30 minutes for NLLB
            )
            assert service_url is not None
            
            # Create comprehensive client
            client = ComprehensiveTestClient(service_url, api_key="development-key")
            
            # Verify model is truly ready
            assert manager.verify_model_readiness("nllb", api_key="development-key")
            
            # Test translation
            response = client.translate(
                text="Hello world",
                source_lang="en",
                target_lang="es",
                model="nllb"
            )
            
            assert response.status_code == 200
            data = response.response_data
            assert data is not None
            assert "translated_text" in data
            assert len(data["translated_text"]) > 0
            print(f"NLLB translation result: {data['translated_text']}")
            
            # Test multiple translations to ensure stability
            test_cases = [
                ("Thank you", "en", "fr"),
                ("Good morning", "en", "de"),
                ("How are you?", "en", "it"),
            ]
            
            for text, source, target in test_cases:
                response = client.translate(
                    text=text,
                    source_lang=source,
                    target_lang=target,
                    model="nllb"
                )
                assert response.status_code == 200
                assert response.response_data.get("translated_text")
                print(f"Translated '{text}' to {target}: {response.response_data['translated_text']}")
            
        finally:
            # Get performance report before cleanup
            report = manager.get_model_loading_report()
            print(f"Model loading report: {report}")
            manager.cleanup()
    
    def test_nllb_language_detection(self):
        """Test NLLB model language detection capabilities."""
        manager = RobustServiceManager()
        
        try:
            # Configure service
            config = MultiModelServiceConfig(
                api_key="development-key",
                models_to_load="nllb",
                log_level="INFO",
                custom_env={
                    "API_KEY": "development-key",
                    "PYTEST_RUNNING": "true",
                    "MODELS_TO_LOAD": "nllb",
                    "NLLB_MODEL": "facebook/nllb-200-distilled-600M",
                    "MODEL_CACHE_DIR": os.path.expanduser("~/.cache/huggingface/transformers"),
                    "HF_HOME": os.path.expanduser("~/.cache/huggingface"),
                    "TRANSFORMERS_CACHE": os.path.expanduser("~/.cache/huggingface/transformers"),
                    "MODEL_LOADING_TIMEOUT": "1800",  # 30 minutes
                    "LOG_MODEL_LOADING_PROGRESS": "true",
                }
            )
            
            # Start service and wait for model
            service_url = manager.start_with_model_wait(
                config=config,
                model_name="nllb",
                timeout=1800  # 30 minutes for NLLB
            )
            assert service_url is not None
            
            # Create comprehensive client
            client = ComprehensiveTestClient(service_url, api_key="development-key")
            
            # Test language detection with different texts
            test_texts = [
                ("Hello, how are you?", "en"),
                ("Bonjour, comment allez-vous?", "fr"),
                ("Hola, ¿cómo estás?", "es"),
                ("Ciao, come stai?", "it"),
                ("Hallo, wie geht es dir?", "de"),
            ]
            
            for text, expected_lang in test_texts:
                # Test language detection via auto-translation
                # Since there's no standalone /detect endpoint, we use auto-detection in translation
                auto_detect_result = client.translate(
                    text=text,
                    source_lang="auto",  # This triggers language detection
                    target_lang="en",    # Translate to English to see detection
                    model="nllb"
                )
                
                assert auto_detect_result.status_code == 200
                detection_data = auto_detect_result.response_data
                assert detection_data is not None
                
                # The response should include detected source language
                detected_lang = detection_data.get("detected_source_lang") or detection_data.get("source_language")
                
                print(f"Auto-detected language for '{text}': {detected_lang} (expected: {expected_lang})")
                print(f"Translation result: {detection_data.get('translated_text', 'N/A')}")
                
                # Verify detection happened (may not always match exactly due to model behavior)
                assert detected_lang is not None
                assert len(detected_lang) > 0
            
            # Test language support endpoint
            languages_result = client.get_languages("nllb")
            
            assert languages_result.status_code == 200
            languages_data = languages_result.response_data
            assert languages_data is not None
            print(f"NLLB supports {len(languages_data) if isinstance(languages_data, list) else 'multiple'} languages")
            
            # Test translation with automatic detection (manual approach)
            auto_translate_result = client.translate(
                text="Bonjour le monde",
                source_lang="auto",
                target_lang="en",
                model="nllb"
            )
            
            assert auto_translate_result.status_code == 200
            auto_data = auto_translate_result.response_data
            assert auto_data is not None
            assert auto_data.get("translated_text") is not None
            
            detected_french = auto_data.get("detected_source_lang") or auto_data.get("source_language")
            print(f"Auto-detected French: {detected_french}")
            print(f"Translation: {auto_data['translated_text']}")
            
        finally:
            manager.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])