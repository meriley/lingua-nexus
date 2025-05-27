"""
E2E tests specifically for Aya model functionality.
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


class TestAyaModelE2E:
    """E2E tests for Aya model integration."""
    
    def test_aya_model_loading(self):
        """Test that Aya model can be loaded and monitored properly."""
        manager = RobustServiceManager()
        
        try:
            # Configure service with only Aya model
            config = MultiModelServiceConfig(
                api_key="test-api-key-aya",
                models_to_load="aya",  # Only load Aya
                log_level="INFO",
                custom_env={
                    "PYTEST_RUNNING": "true",
                    "MODELS_TO_LOAD": "aya",
                    "AYA_MODEL": "CohereForAI/aya-expanse-8b",
                    "MODEL_CACHE_DIR": os.path.expanduser("~/.cache/huggingface/transformers"),
                    "HF_HOME": os.path.expanduser("~/.cache/huggingface"),
                    "TRANSFORMERS_CACHE": os.path.expanduser("~/.cache/huggingface/transformers"),
                    "HF_TOKEN": os.environ.get("HF_TOKEN", "test-hf-token-placeholder"),
                    "MODEL_LOADING_TIMEOUT": "3600",  # 60 minutes for 8B model
                    "LOG_MODEL_LOADING_PROGRESS": "true",
                    "PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:512",  # Memory optimization
                }
            )
            
            # Track loading time
            loading_start = time.time()
            
            # Start service and wait for model
            service_url = manager.start_with_model_wait(
                config=config,
                model_name="aya",
                timeout=3600  # 60 minutes for Aya 8B
            )
            assert service_url is not None
            
            loading_duration = time.time() - loading_start
            print(f"Aya model loaded in {loading_duration:.1f} seconds")
            
            # Create client
            client = ComprehensiveTestClient(service_url, api_key="test-api-key-aya")
            
            # Verify model status
            model_status = client.get_model_status("aya")
            assert model_status["available"]
            assert model_status["loaded"]
            assert model_status["ready"]
            print(f"Aya model status: {model_status}")
            
            # Check health with loaded model
            health_result = client.get("/health")
            assert health_result.status_code == 200
            health_data = health_result.response_data
            assert health_data["status"] == "healthy"
            assert health_data.get("models_loaded", 0) > 0
            print(f"Service health with Aya loaded: {health_data}")
            
            # Get loading performance report
            report = manager.get_model_loading_report()
            assert "aya" in report["models_loaded"]
            assert report["loading_times"]["aya"] == loading_duration
            print(f"Performance report: {report}")
            
        finally:
            manager.cleanup()
    
    def test_aya_translation(self):
        """Test Aya model translation capabilities - NO SKIPPING."""
        manager = RobustServiceManager()
        
        try:
            # Configure and start service
            config = MultiModelServiceConfig(
                api_key="test-api-key-aya-translate",
                models_to_load="aya",
                log_level="INFO",
                custom_env={
                    "PYTEST_RUNNING": "true",
                    "MODELS_TO_LOAD": "aya",
                    "AYA_MODEL": "CohereForAI/aya-expanse-8b",
                    "MODEL_CACHE_DIR": os.path.expanduser("~/.cache/huggingface/transformers"),
                    "HF_HOME": os.path.expanduser("~/.cache/huggingface"),
                    "TRANSFORMERS_CACHE": os.path.expanduser("~/.cache/huggingface/transformers"),
                    "HF_TOKEN": os.environ.get("HF_TOKEN", "test-hf-token-placeholder"),
                    "MODEL_LOADING_TIMEOUT": "3600",  # 60 minutes for 8B model
                    "LOG_MODEL_LOADING_PROGRESS": "true",
                    "PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:512",  # Memory optimization
                }
            )
            
            # Track loading time
            loading_start = time.time()
            
            # Start service and wait for model - THIS IS REQUIRED, NOT OPTIONAL
            service_url = manager.start_with_model_wait(
                config=config,
                model_name="aya",
                timeout=3600  # 60 minutes for Aya 8B model
            )
            assert service_url is not None
            
            loading_duration = time.time() - loading_start
            print(f"Aya model ready after {loading_duration:.1f} seconds - proceeding with tests")
            
            # Create comprehensive client
            client = ComprehensiveTestClient(service_url, api_key="test-api-key-aya-translate")
            
            # Verify model is truly ready
            assert manager.verify_model_readiness("aya", api_key="test-api-key-aya-translate")
            
            # Test translation capabilities
            test_cases = [
                # English to French
                ("Hello, how are you?", "eng_Latn", "fra_Latn"),
                # English to Spanish
                ("Good morning, have a nice day!", "eng_Latn", "spa_Latn"),
                # English to German
                ("The weather is beautiful today.", "eng_Latn", "deu_Latn"),
                # Multilingual test - French to Spanish
                ("Bonjour, comment allez-vous?", "fra_Latn", "spa_Latn"),
                # Long text handling
                ("Artificial intelligence and machine learning are transforming the way we interact with technology. These advanced systems can process vast amounts of data, recognize patterns, and make predictions with increasing accuracy.", "eng_Latn", "fra_Latn"),
            ]
            
            for text, source_lang, target_lang in test_cases:
                print(f"\nTesting: '{text[:50]}...' from {source_lang} to {target_lang}")
                
                response = client.translate(
                    text=text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    model="aya"
                )
                
                assert response.status_code == 200
                data = response.response_data
                assert data is not None
                assert "translated_text" in data
                assert len(data["translated_text"]) > 0
                
                print(f"Translation result: {data['translated_text']}")
                
                # Record translation performance
                manager.performance_tracker.record_translation(
                    model_name="aya",
                    text_length=len(text),
                    duration_ms=response.duration_ms,
                    success=True
                )
            
            # Test batch translation
            batch_requests = [
                {"text": "Hello", "source_lang": "eng_Latn", "target_lang": "spa_Latn", "model": "aya"},
                {"text": "Goodbye", "source_lang": "eng_Latn", "target_lang": "fra_Latn", "model": "aya"},
                {"text": "Thank you", "source_lang": "eng_Latn", "target_lang": "deu_Latn", "model": "aya"},
            ]
            
            batch_result = client.batch_translate_with_retry(batch_requests)
            assert batch_result.status_code == 200
            print(f"Batch translation completed successfully")
            
            # Test memory stability with repeated requests
            print("\nTesting memory stability...")
            stability_result = client.verify_model_persistence("aya", test_text="Memory test")
            assert stability_result["all_successful"]
            print("Memory stability test passed")
            
        finally:
            # Get comprehensive performance report
            report = manager.get_model_loading_report()
            print(f"\nFinal performance report: {report}")
            manager.cleanup()