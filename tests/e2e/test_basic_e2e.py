"""Basic E2E test to verify models are cached and can be loaded."""

import os
import sys

# Add the e2e directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.service_manager import ServiceManager, MultiModelServiceConfig


def test_nllb_basic_health():
    """Test basic NLLB service startup with cached model."""
    manager = ServiceManager()
    
    try:
        config = MultiModelServiceConfig(
            api_key="test-api-key",
            models_to_load="nllb",
            log_level="INFO",
            custom_env={
                "MODELS_TO_LOAD": "nllb",
                "NLLB_MODEL": "facebook/nllb-200-distilled-600M",
                "MODEL_CACHE_DIR": os.path.expanduser("~/.cache/huggingface/transformers"),
                "HF_HOME": os.path.expanduser("~/.cache/huggingface"),
                "TRANSFORMERS_CACHE": os.path.expanduser("~/.cache/huggingface/transformers"),
            }
        )
        
        # Start service
        service_url = manager.start_multimodel_service(config, timeout=60)
        assert service_url is not None
        print(f"✓ Service started at {service_url}")
        
        # Check health
        import requests
        response = requests.get(f"{service_url}/health", timeout=10)
        print(f"✓ Health check status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Health data: {data}")
        
        assert response.status_code == 200
        
    finally:
        manager.cleanup()
        print("✓ Service cleaned up")


def test_aya_basic_health():
    """Test basic Aya service startup with cached model."""
    manager = ServiceManager()
    
    try:
        config = MultiModelServiceConfig(
            api_key="test-api-key",
            models_to_load="aya",
            log_level="INFO",
            custom_env={
                "MODELS_TO_LOAD": "aya",
                "AYA_MODEL": "CohereForAI/aya-expanse-8b",
                "MODEL_CACHE_DIR": os.path.expanduser("~/.cache/huggingface/transformers"),
                "HF_HOME": os.path.expanduser("~/.cache/huggingface"),
                "TRANSFORMERS_CACHE": os.path.expanduser("~/.cache/huggingface/transformers"),
                "HF_TOKEN": "test-hf-token-placeholder",
            }
        )
        
        # Start service
        service_url = manager.start_multimodel_service(config, timeout=60)
        assert service_url is not None
        print(f"✓ Service started at {service_url}")
        
        # Check health
        import requests
        response = requests.get(f"{service_url}/health", timeout=10)
        print(f"✓ Health check status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Health data: {data}")
        
        assert response.status_code == 200
        
    finally:
        manager.cleanup()
        print("✓ Service cleaned up")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])