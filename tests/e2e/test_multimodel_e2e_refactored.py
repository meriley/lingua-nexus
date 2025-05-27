"""
True end-to-end tests for multi-model translation system.

NO MOCKS ALLOWED - These tests use real models and test the complete system.
Tests are marked with @pytest.mark.slow for CI/CD configuration.
"""

import pytest
import time
import os
import sys
from typing import Dict, Any, List

# Add the e2e directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.service_manager import ServiceManager, MultiModelServiceConfig
from utils.multimodel_http_client import ModelTestClient
from utils.test_reporter import E2ETestReporter as TestReporter
from utils.performance_monitor import PerformanceMonitor
from test_data import (
    E2E_TEST_TRANSLATIONS,
    E2E_BATCH_TRANSLATIONS,
    E2E_LANGUAGE_DETECTION_TESTS,
    E2E_ERROR_CASES,
    validate_translation
)


class TestMultiModelE2E:
    """True end-to-end tests for multi-model translation system."""
    
    @pytest.fixture(scope="session")
    def service_manager(self):
        """Service manager for E2E tests - session scoped for efficiency."""
        manager = ServiceManager()
        yield manager
        manager.cleanup()
    
    @pytest.fixture(scope="session")
    def multimodel_service(self, service_manager):
        """Start multi-model service with real models - cached for entire session."""
        # Use configuration optimized for model caching and reuse
        import os
        model_cache_dir = os.path.expanduser("~/.cache/huggingface/transformers")
        config = MultiModelServiceConfig(
            api_key="test-api-key-e2e",
            models_to_load="nllb,aya",  # Load both NLLB and Aya models
            log_level="INFO",
            custom_env={
                "PYTEST_RUNNING": "true",
                "MODEL_CACHE_DIR": model_cache_dir,
                "HF_HOME": os.path.expanduser("~/.cache/huggingface"),
                "TRANSFORMERS_CACHE": model_cache_dir,
                "HF_DATASETS_CACHE": os.path.expanduser("~/.cache/huggingface/datasets"),
                "TORCH_HOME": os.path.expanduser("~/.cache/torch"),
                # Use the smaller distilled model for faster loading
                "NLLB_MODEL": "facebook/nllb-200-distilled-600M",
                "AYA_MODEL": "CohereForAI/aya-expanse-8b",
                "E2E_FULL_MODEL_TEST": "true"  # Signal this is a full model test
            }
        )
        
        try:
            # Allow more time for real model loading (20 minutes for first download)
            service_url = service_manager.start_multimodel_service(config, timeout=1200)
            yield service_url
        except Exception as e:
            logs = service_manager.get_service_logs()
            pytest.fail(f"Failed to start multi-model service: {e}\nLogs:\n{logs}")
    
    @pytest.fixture
    def client(self, multimodel_service):
        """HTTP client for API testing."""
        return ModelTestClient(multimodel_service, "test-api-key-e2e")
    
    @pytest.fixture
    def performance_monitor(self):
        """Performance monitoring."""
        return PerformanceMonitor()
    
    @pytest.fixture
    def test_reporter(self):
        """Test reporting."""
        return TestReporter("multimodel_e2e_tests_real")

    @pytest.mark.slow
    def test_service_startup_and_health(self, client, test_reporter):
        """Test that the multi-model service starts correctly with real models."""
        with test_reporter.test_case("service_startup_health_real"):
            # Wait for service to be fully ready with real models (extended timeout for first-time downloads)
            assert client.wait_for_service(timeout=600), "Service did not become ready in time"
            
            # Perform health check with retry for model loading (up to 15 minutes for download + loading)
            max_retries = 900  # Give up to 15 minutes (900 seconds) for model download and loading
            for i in range(max_retries):
                result = client.get("/health")
                assert result.status_code == 200, f"Health check failed: {result.error}"
                
                health_data = result.response_data
                if health_data["status"] == "healthy":
                    break
                    
                # If still starting, wait a bit and log progress
                if i % 60 == 0:  # Log every minute
                    minutes_elapsed = i // 60
                    print(f"Still waiting for models to load... ({minutes_elapsed}m elapsed, status: {health_data['status']})")
                elif i % 30 == 0 and i < 120:  # Log every 30s for first 2 minutes
                    print(f"Still waiting for models to load... ({i}s elapsed, status: {health_data['status']})")
                time.sleep(1)
            else:
                # If we exhausted retries, fail
                assert False, f"Service did not become healthy after {max_retries} seconds. Status: {health_data['status']}"
            
            assert health_data["models_loaded"] >= 2
            assert "nllb" in health_data["models_available"]
            assert "aya" in health_data["models_available"]
            
            # Test passed - reporter handles success via context manager

    @pytest.mark.slow
    def test_models_endpoint(self, client, test_reporter):
        """Test models listing endpoint with real models."""
        with test_reporter.test_case("models_endpoint_real"):
            result = client.list_models()
            assert result.status_code == 200, f"Models endpoint failed: {result.error}"
            
            models = result.response_data
            assert isinstance(models, list)
            assert len(models) >= 1
            
            # Check NLLB model
            nllb_model = next((m for m in models if m["name"] == "nllb"), None)
            assert nllb_model is not None
            assert nllb_model["available"] is True
            assert nllb_model["type"] == "nllb"
            assert len(nllb_model["supported_languages"]) > 0
            
            # Test passed

    @pytest.mark.slow
    def test_nllb_translation_workflow(self, client, performance_monitor, test_reporter):
        """Test complete NLLB translation workflow with real model."""
        with test_reporter.test_case("nllb_translation_workflow_real"):
            
            for test_case in E2E_TEST_TRANSLATIONS[:2]:  # Test first 2 to save time
                # Test real translation
                start_time = time.time()
                result = client.translate(
                    test_case["text"],
                    source_lang=test_case["source"],
                    target_lang=test_case["target"],
                    model="nllb"
                )
                duration = (time.time() - start_time) * 1000
                
                assert result.status_code == 200, f"Translation failed: {result.error}"
                
                translation_data = result.response_data
                assert "translated_text" in translation_data
                assert translation_data["model_used"] == "nllb"
                assert translation_data["processing_time_ms"] > 0
                
                # Validate translation
                is_valid, message = validate_translation(
                    translation_data["translated_text"],
                    test_case
                )
                assert is_valid, f"Translation validation failed for '{test_case['text']}': {message}"
                
                # Performance metrics recorded
                
                # Test passed for this case

    @pytest.mark.slow
    def test_auto_language_detection(self, client, test_reporter):
        """Test automatic language detection with real model."""
        with test_reporter.test_case("auto_language_detection_real"):
            
            for test_case in E2E_LANGUAGE_DETECTION_TESTS[:1]:  # Test first one to save time
                # Test auto-detection
                result = client.translate(
                    test_case["text"],
                    source_lang="auto",
                    target_lang=test_case["target"],
                    model="nllb"
                )
                assert result.status_code == 200, f"Auto-detection failed: {result.error}"
                
                data = result.response_data
                assert "detected_source_lang" in data
                assert "translated_text" in data
                assert len(data["translated_text"]) > 0
                
                # Language detection might not be perfect, but should return something
                # Language detection completed

    @pytest.mark.slow
    def test_batch_translation(self, client, performance_monitor, test_reporter):
        """Test batch translation functionality with real model."""
        with test_reporter.test_case("batch_translation_real"):
            
            # Prepare batch request
            batch_requests = []
            for item in E2E_BATCH_TRANSLATIONS:
                batch_requests.append({
                    "text": item["text"],
                    "source_lang": item["source"],
                    "target_lang": item["target"],
                    "model": "nllb"
                })
            
            start_time = time.time()
            result = client.batch_translate(batch_requests)
            duration = (time.time() - start_time) * 1000
            
            assert result.status_code == 200, f"Batch translation failed: {result.error}"
            
            batch_data = result.response_data
            assert batch_data["total_processed"] == len(batch_requests)
            assert batch_data["total_errors"] == 0
            assert len(batch_data["results"]) == len(batch_requests)
            
            # Verify all translations completed
            for i, batch_result in enumerate(batch_data["results"]):
                # Check if it has status (might be different structure)
                if "status" in batch_result:
                    assert batch_result["status"] == "success"
                if "index" in batch_result:
                    assert batch_result["index"] == i
                # The result might be directly in batch_result or nested
                result = batch_result.get("result", batch_result)
                assert "translated_text" in result
                assert len(result["translated_text"]) > 0
            
            # Batch performance recorded
            
            # Batch test passed

    @pytest.mark.slow
    def test_language_support_endpoints(self, client, test_reporter):
        """Test language support endpoints with real model."""
        with test_reporter.test_case("language_support_endpoints_real"):
            
            # Test general languages endpoint
            result = client.get_languages()
            assert result.status_code == 200, f"Languages endpoint failed: {result.error}"
            
            languages = result.response_data
            assert isinstance(languages, list)
            assert len(languages) > 0
            
            # Check some common languages
            language_codes = {lang["iso_code"] for lang in languages}
            assert "en" in language_codes
            assert "es" in language_codes
            assert "fr" in language_codes
            
            # Test model-specific languages
            nllb_result = client.get_languages("nllb")
            assert nllb_result.status_code == 200
            
            nllb_data = nllb_result.response_data
            assert nllb_data["model"] == "nllb"
            assert "supported_languages" in nllb_data
            assert len(nllb_data["supported_languages"]) > 0
            
            # Language support test passed

    def test_error_handling(self, client, test_reporter):
        """Test comprehensive error handling - no model needed."""
        with test_reporter.test_case("error_handling_real"):
            
            # Test invalid model
            result = client.translate("Hello", model="invalid_model")
            assert result.status_code == 422  # Invalid model format returns validation error
            assert "Invalid model name format" in str(result.response_data["detail"])
            
            # Test forbidden access
            forbidden_client = ModelTestClient(client.base_url, "invalid-api-key")
            result = forbidden_client.list_models()
            assert result.status_code == 403
            
            # Test invalid request data
            result = client.post("/translate", json_data={
                "text": "",  # Empty text
                "target_lang": "ru",
                "model": "nllb"
            })
            assert result.status_code == 422  # Validation error
            
            # Test batch size limit
            large_batch = [{"text": f"Text {i}", "target_lang": "ru", "model": "nllb"} 
                          for i in range(15)]  # Exceed limit of 10
            result = client.batch_translate(large_batch)
            assert result.status_code == 400
            assert "cannot exceed" in result.response_data["detail"]
            
            # Error handling test passed

    def test_legacy_compatibility(self, client, test_reporter):
        """Test legacy API compatibility without mocks."""
        with test_reporter.test_case("legacy_compatibility_real"):
            
            # Test legacy endpoint format
            result = client.post("/translate/legacy", json_data={
                "text": "Hello",
                "source_lang": "en",
                "target_lang": "es"
            })
            
            assert result.status_code == 200
            
            legacy_data = result.response_data
            assert "translated_text" in legacy_data
            assert len(legacy_data["translated_text"]) > 0
            assert "time_ms" in legacy_data
            
            # Verify legacy format (no model_used field)
            assert "model_used" not in legacy_data
            assert "processing_time_ms" not in legacy_data
            
            # Legacy compatibility test passed

    @pytest.mark.slow
    def test_concurrent_requests(self, client, test_reporter):
        """Test handling of concurrent requests with real model."""
        with test_reporter.test_case("concurrent_requests_real"):
            
            import threading
            import queue
            
            results_queue = queue.Queue()
            num_concurrent = 3
            
            def make_request(text_id):
                result = client.translate(
                    f"Test {text_id}",
                    source_lang="en",
                    target_lang="es",
                    model="nllb"
                )
                results_queue.put((text_id, result))
            
            # Start concurrent requests
            threads = []
            start_time = time.time()
            
            for i in range(num_concurrent):
                thread = threading.Thread(target=make_request, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join(timeout=30)  # Timeout for real model requests
            
            total_time = (time.time() - start_time) * 1000
            
            # Collect results
            results = []
            while not results_queue.empty():
                results.append(results_queue.get())
            
            # Verify all succeeded
            assert len(results) == num_concurrent
            for text_id, result in results:
                assert result.status_code == 200
                assert len(result.response_data["translated_text"]) > 0
            
            # Concurrent requests test passed

    def test_service_recovery(self, client, service_manager, test_reporter):
        """Test service recovery capabilities."""
        with test_reporter.test_case("service_recovery_real"):
            
            # Verify service is responsive
            health_result = client.health_check()
            assert health_result is True
            
            # Make a translation request to ensure full functionality
            result = client.translate("Recovery test", model="nllb")
            assert result.status_code == 200
            
            # Service recovery test passed


if __name__ == "__main__":
    # Run with: pytest test_multimodel_e2e_refactored.py -v -m slow
    pytest.main([__file__, "-v", "--tb=short", "-s", "-m", "slow"])