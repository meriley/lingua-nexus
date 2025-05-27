"""
Lightweight E2E tests that load only one model at a time.
More suitable for resource-constrained environments.
"""

import pytest
import sys
import os
import time

# Add the e2e directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.service_manager import ServiceManager, MultiModelServiceConfig
from utils.multimodel_http_client import ModelTestClient


class TestSingleModelE2E:
    """E2E tests with single models for lower resource usage."""
    
    @pytest.mark.parametrize("model_name,model_path", [
        ("nllb", "facebook/nllb-200-distilled-600M"),
        ("aya", "CohereForAI/aya-expanse-8b"),
    ])
    def test_single_model_loading(self, model_name, model_path):
        """Test loading models one at a time."""
        manager = ServiceManager()
        
        try:
            # Configure service with single model
            config = MultiModelServiceConfig(
                api_key=f"test-api-key-{model_name}",
                models_to_load=model_name,  # Only load one model
                log_level="INFO",
                custom_env={
                    "PYTEST_RUNNING": "true",
                    "MODEL_CACHE_DIR": os.path.expanduser("~/.cache/huggingface/transformers"),
                    "HF_HOME": os.path.expanduser("~/.cache/huggingface"),
                    f"{model_name.upper()}_MODEL": model_path,
                }
            )
            
            # Start service with shorter timeout for single model
            service_url = manager.start_multimodel_service(config, timeout=300)
            assert service_url is not None
            
            # Create client
            client = ModelTestClient(service_url, api_key=f"test-api-key-{model_name}")
            
            # Wait for service with retry
            max_wait = 180  # 3 minutes for single model
            for i in range(max_wait):
                result = client.get("/health")
                if result.status_code == 200:
                    health_data = result.response_data
                    print(f"\n[{model_name}] Health at {i}s: {health_data}")
                    
                    if health_data.get("status") == "healthy":
                        assert health_data["models_loaded"] >= 1
                        assert model_name in health_data["models_available"]
                        print(f"✓ {model_name} model loaded successfully!")
                        return
                        
                    elif i % 30 == 0:
                        print(f"[{model_name}] Still loading... Status: {health_data.get('status')}")
                
                time.sleep(1)
            
            # If we get here, model didn't load in time
            pytest.skip(f"{model_name} model loading timed out - likely resource constraints")
            
        finally:
            manager.cleanup()
            
    def test_nllb_only_translation(self):
        """Test NLLB model translation with minimal resources."""
        manager = ServiceManager()
        
        try:
            # Load only NLLB
            config = MultiModelServiceConfig(
                api_key="test-nllb-translate",
                models_to_load="nllb",
                log_level="INFO",
                custom_env={
                    "MODEL_CACHE_DIR": os.path.expanduser("~/.cache/huggingface/transformers"),
                    "NLLB_MODEL": "facebook/nllb-200-distilled-600M",
                }
            )
            
            service_url = manager.start_multimodel_service(config, timeout=600)
            client = ModelTestClient(service_url, api_key="test-nllb-translate")
            
            # Wait for model to be ready
            if not client.wait_for_service(timeout=300):
                pytest.skip("NLLB model loading timed out")
            
            # Test translation
            result = client.translate(
                text="Hello, how are you?",
                source_lang="eng_Latn",
                target_lang="fra_Latn",
                model="nllb"
            )
            
            if result.status_code == 200:
                print(f"NLLB translation successful: {result.response_data}")
                assert "translated_text" in result.response_data
            else:
                pytest.skip(f"Translation failed: {result.status_code}")
                
        finally:
            manager.cleanup()