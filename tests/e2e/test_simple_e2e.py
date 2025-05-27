"""
Simple E2E test for verifying service startup without full model loading.
"""

import pytest
import sys
import os

# Add the e2e directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.service_manager import ServiceManager, MultiModelServiceConfig, ServiceConfig


class TestSimpleE2E:
    """Simple E2E tests that don't require full model loading."""
    
    def test_service_starts_without_models(self):
        """Test that the service can start and respond to basic health checks."""
        manager = ServiceManager()
        
        try:
            # Configure service with no models to load
            config = MultiModelServiceConfig(
                api_key="test-api-key-simple",
                models_to_load="",  # No models to load
                log_level="INFO",
                custom_env={
                    "PYTEST_RUNNING": "true",
                    "TESTING": "true"
                }
            )
            
            # Start service
            service_url = manager.start_multimodel_service(config, timeout=60)
            assert service_url is not None
            
            # Basic connectivity test
            import requests
            response = requests.get(f"{service_url}/health", timeout=10)
            assert response.status_code == 200
            
            # Should get "starting" status since no models are loaded
            health_data = response.json()
            assert health_data["status"] in ["starting", "healthy"]
            assert health_data["models_loaded"] == 0
            assert health_data["models_available"] == []
            
        finally:
            manager.cleanup()
    
    def test_regular_service_starts(self):
        """Test that the regular (non-multimodel) service starts quickly."""
        manager = ServiceManager()
        
        try:
            # Configure regular service
            config = ServiceConfig(
                api_key="test-api-key-regular",
                model_name="facebook/nllb-200-distilled-600M",
                cache_dir="/tmp/test_cache",
                log_level="INFO",
                custom_env={
                    "PYTEST_RUNNING": "true",
                    "TESTING": "true"
                }
            )
            
            # Start regular service (main.py, not main_multimodel.py)
            # Use longer timeout for model loading during startup
            service_url = manager.start_service(config, timeout=120)
            assert service_url is not None
            
            # Basic connectivity test
            import requests
            response = requests.get(f"{service_url}/health", timeout=10)
            assert response.status_code == 200
            
            health_data = response.json()
            assert health_data["status"] == "healthy"  # Regular service should be healthy immediately
            
        finally:
            manager.cleanup()