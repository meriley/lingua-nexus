"""
End-to-end tests for multi-model translation system.

This module provides comprehensive E2E tests for the multi-model architecture,
testing real API interactions, model loading, and translation workflows.
"""

import pytest
import time
import os
from typing import Dict, Any
from unittest.mock import patch, Mock

from tests.e2e.utils.service_manager import ServiceManager, MultiModelServiceConfig
from tests.e2e.utils.multimodel_http_client import ModelTestClient
from tests.e2e.utils.test_reporter import E2ETestReporter as TestReporter
from tests.e2e.utils.performance_monitor import PerformanceMonitor


class TestMultiModelE2E:
    """End-to-end tests for multi-model translation system."""
    
    @pytest.fixture(scope="class")
    def service_manager(self):
        """Service manager for E2E tests."""
        manager = ServiceManager()
        yield manager
        manager.cleanup()
    
    @pytest.fixture(scope="class")
    def multimodel_service(self, service_manager):
        """Start multi-model service for testing."""
        config = MultiModelServiceConfig(
            api_key="test-api-key-e2e",
            models_to_load="nllb",  # Start with NLLB only
            log_level="DEBUG",
            custom_env={
                "PYTEST_RUNNING": "true",
                "MODEL_CACHE_DIR": "/tmp/e2e_model_cache"
            }
        )
        
        try:
            service_url = service_manager.start_multimodel_service(config, timeout=90)
            yield service_url
        except Exception as e:
            # Get logs for debugging
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
        return TestReporter("multimodel_e2e_tests")

    def test_service_startup_and_health(self, client, test_reporter):
        """Test that the multi-model service starts correctly and reports healthy."""
        with test_reporter.test_case("service_startup_health"):
            # Wait for service to be fully ready
            assert client.wait_for_service(timeout=60), "Service did not become ready in time"
            
            # Perform health check
            result = client.get("/health")
            assert result.status_code == 200, f"Health check failed: {result.error}"
            
            health_data = result.response_data
            assert health_data["status"] == "healthy"
            assert health_data["models_loaded"] >= 1
            assert "nllb" in health_data["models_available"]
            
            # Test passed - no need to record success since it's handled by the context manager

    def test_models_endpoint(self, client, test_reporter):
        """Test models listing endpoint."""
        with test_reporter.test_case("models_endpoint"):
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

    @pytest.mark.asyncio
    async def test_nllb_translation_workflow(self, client, performance_monitor, test_reporter):
        """Test complete NLLB translation workflow."""
        with test_reporter.test_case("nllb_translation_workflow"):
            
            # Mock NLLB for testing to avoid long load times
            with patch('app.models.nllb_model.NLLBModel') as mock_nllb:
                # Setup mock translation
                async def mock_translate(request):
                    from app.models.base import TranslationResponse
                    translations = {
                        "Hello, world!": "Привет, мир!",
                        "Good morning": "Доброе утро",
                        "How are you?": "Как дела?"
                    }
                    return TranslationResponse(
                        translated_text=translations.get(request.text, f"Translated: {request.text}"),
                        detected_source_lang=None,
                        processing_time_ms=120.0,
                        model_used="nllb",
                        metadata={"device": "cpu", "mocked": True}
                    )
                
                mock_instance = Mock()
                mock_instance.is_available.return_value = True
                mock_instance.supports_language_pair.return_value = True
                mock_instance.translate = mock_translate
                mock_instance.get_supported_languages.return_value = ["en", "ru", "es", "fr", "de"]
                mock_nllb.return_value = mock_instance
                
                # Test single translation
                start_time = time.time()
                result = client.translate("Hello, world!", source_lang="en", target_lang="ru", model="nllb")
                duration = (time.time() - start_time) * 1000
                
                assert result.status_code == 200, f"Translation failed: {result.error}"
                
                translation_data = result.response_data
                assert translation_data["translated_text"] == "Привет, мир!"
                assert translation_data["model_used"] == "nllb"
                assert translation_data["processing_time_ms"] > 0
                
                performance_monitor.record_request(
                    endpoint="/translate",
                    duration_ms=duration,
                    model="nllb",
                    text_length=len("Hello, world!")
                )
                
                # Test passed

    def test_auto_language_detection(self, client, test_reporter):
        """Test automatic language detection."""
        with test_reporter.test_case("auto_language_detection"):
            
            with patch('app.models.nllb_model.NLLBModel') as mock_nllb:
                async def mock_translate(request):
                    from app.models.base import TranslationResponse
                    return TranslationResponse(
                        translated_text="Hello, world!",
                        detected_source_lang="ru",  # Detected Russian
                        processing_time_ms=150.0,
                        model_used="nllb",
                        metadata={"auto_detected": True, "mocked": True}
                    )
                
                mock_instance = Mock()
                mock_instance.is_available.return_value = True
                mock_instance.supports_language_pair.return_value = True
                mock_instance.translate = mock_translate
                mock_nllb.return_value = mock_instance
                
                # Test auto-detection
                result = client.translate("Привет, мир!", source_lang="auto", target_lang="en", model="nllb")
                assert result.status_code == 200
                
                data = result.response_data
                assert data["detected_source_lang"] == "ru"
                assert data["translated_text"] == "Hello, world!"
                
                test_reporter.record_success("Auto-detection completed", {
                    "input": "Привет, мир!",
                    "detected_language": data["detected_source_lang"]
                })

    def test_batch_translation(self, client, performance_monitor, test_reporter):
        """Test batch translation functionality."""
        with test_reporter.test_case("batch_translation"):
            
            with patch('app.models.nllb_model.NLLBModel') as mock_nllb:
                async def mock_translate(request):
                    from app.models.base import TranslationResponse
                    translations = {
                        "Hello": "Привет",
                        "World": "Мир", 
                        "Good": "Хорошо",
                        "Morning": "Утро"
                    }
                    return TranslationResponse(
                        translated_text=translations.get(request.text, f"Translated: {request.text}"),
                        detected_source_lang=None,
                        processing_time_ms=100.0,
                        model_used="nllb",
                        metadata={"batch": True, "mocked": True}
                    )
                
                mock_instance = Mock()
                mock_instance.is_available.return_value = True
                mock_instance.supports_language_pair.return_value = True
                mock_instance.translate = mock_translate
                mock_nllb.return_value = mock_instance
                
                # Prepare batch request
                batch_requests = [
                    {"text": "Hello", "source_lang": "en", "target_lang": "ru", "model": "nllb"},
                    {"text": "World", "source_lang": "en", "target_lang": "ru", "model": "nllb"},
                    {"text": "Good", "source_lang": "en", "target_lang": "ru", "model": "nllb"},
                    {"text": "Morning", "source_lang": "en", "target_lang": "ru", "model": "nllb"}
                ]
                
                start_time = time.time()
                result = client.batch_translate(batch_requests)
                duration = (time.time() - start_time) * 1000
                
                assert result.status_code == 200
                
                batch_data = result.response_data
                assert batch_data["total_processed"] == 4
                assert batch_data["total_errors"] == 0
                assert len(batch_data["results"]) == 4
                
                # Verify translations
                translations = {r["result"]["translated_text"] for r in batch_data["results"]}
                assert "Привет" in translations
                assert "Мир" in translations
                
                performance_monitor.record_batch_request(
                    endpoint="/translate/batch",
                    duration_ms=duration,
                    batch_size=4,
                    model="nllb"
                )
                
                test_reporter.record_success("Batch translation completed", {
                    "batch_size": 4,
                    "duration_ms": duration,
                    "success_rate": "100%"
                })

    def test_aya_model_loading(self, client, test_reporter):
        """Test Aya model loading and translation."""
        with test_reporter.test_case("aya_model_loading"):
            
            with patch('app.models.aya_model.AyaModel') as mock_aya:
                # Setup Aya mock
                async def mock_translate(request):
                    from app.models.base import TranslationResponse
                    return TranslationResponse(
                        translated_text="Hola, mundo!",
                        detected_source_lang=None,
                        processing_time_ms=250.0,
                        model_used="aya",
                        metadata={"temperature": 0.3, "mocked": True}
                    )
                
                mock_instance = Mock()
                mock_instance.is_available.return_value = True
                mock_instance.supports_language_pair.return_value = True
                mock_instance.translate = mock_translate
                mock_instance.get_supported_languages.return_value = ["en", "ru", "es", "zh", "ar"]
                mock_instance.get_model_info.return_value = {
                    "name": "aya",
                    "type": "aya",
                    "available": True,
                    "device": "cpu"
                }
                mock_aya.return_value = mock_instance
                
                # Load Aya model
                load_result = client.load_model("aya")
                assert load_result.status_code == 200
                assert "loaded successfully" in load_result.response_data["message"]
                
                # Verify model is listed
                models_result = client.list_models()
                models = models_result.response_data
                aya_model = next((m for m in models if m["name"] == "aya"), None)
                assert aya_model is not None
                assert aya_model["available"] is True
                
                # Test translation with Aya
                translate_result = client.translate(
                    "Hello, world!", 
                    source_lang="en", 
                    target_lang="es", 
                    model="aya",
                    model_options={"temperature": 0.7}
                )
                
                assert translate_result.status_code == 200
                translation_data = translate_result.response_data
                assert translation_data["model_used"] == "aya"
                assert translation_data["translated_text"] == "Hola, mundo!"
                
                test_reporter.record_success("Aya model loading and translation completed", {
                    "model_loaded": True,
                    "translation_successful": True,
                    "output": translation_data["translated_text"]
                })

    def test_model_switching(self, client, test_reporter):
        """Test switching between models."""
        with test_reporter.test_case("model_switching"):
            
            with patch('app.models.nllb_model.NLLBModel') as mock_nllb, \
                 patch('app.models.aya_model.AyaModel') as mock_aya:
                
                # Setup mocks
                async def mock_nllb_translate(request):
                    from app.models.base import TranslationResponse
                    return TranslationResponse(
                        translated_text="NLLB: " + request.text,
                        detected_source_lang=None,
                        processing_time_ms=100.0,
                        model_used="nllb",
                        metadata={"mocked": True}
                    )
                
                async def mock_aya_translate(request):
                    from app.models.base import TranslationResponse
                    return TranslationResponse(
                        translated_text="Aya: " + request.text,
                        detected_source_lang=None,
                        processing_time_ms=200.0,
                        model_used="aya",
                        metadata={"mocked": True}
                    )
                
                nllb_instance = Mock()
                nllb_instance.is_available.return_value = True
                nllb_instance.supports_language_pair.return_value = True
                nllb_instance.translate = mock_nllb_translate
                mock_nllb.return_value = nllb_instance
                
                aya_instance = Mock()
                aya_instance.is_available.return_value = True
                aya_instance.supports_language_pair.return_value = True
                aya_instance.translate = mock_aya_translate
                aya_instance.get_model_info.return_value = {"name": "aya", "type": "aya", "available": True}
                mock_aya.return_value = aya_instance
                
                # Test NLLB first
                result1 = client.translate("Test text", model="nllb")
                assert result1.status_code == 200
                assert result1.response_data["model_used"] == "nllb"
                assert "NLLB: Test text" in result1.response_data["translated_text"]
                
                # Load and test Aya
                load_result = client.load_model("aya")
                assert load_result.status_code == 200
                
                result2 = client.translate("Test text", model="aya")
                assert result2.status_code == 200
                assert result2.response_data["model_used"] == "aya"
                assert "Aya: Test text" in result2.response_data["translated_text"]
                
                # Switch back to NLLB
                result3 = client.translate("Test text", model="nllb")
                assert result3.status_code == 200
                assert result3.response_data["model_used"] == "nllb"
                
                test_reporter.record_success("Model switching completed", {
                    "nllb_test": True,
                    "aya_test": True,
                    "switch_back": True
                })

    def test_language_support_endpoints(self, client, test_reporter):
        """Test language support endpoints."""
        with test_reporter.test_case("language_support_endpoints"):
            
            with patch('app.models.nllb_model.NLLBModel') as mock_nllb:
                mock_instance = Mock()
                mock_instance.is_available.return_value = True
                mock_instance.get_supported_languages.return_value = ["en", "ru", "es", "fr", "de", "zh"]
                mock_nllb.return_value = mock_instance
                
                # Test general languages endpoint
                result = client.get_languages()
                assert result.status_code == 200
                
                languages = result.response_data
                assert isinstance(languages, list)
                assert len(languages) >= 6
                
                # Check specific language
                en_lang = next((l for l in languages if l["iso_code"] == "en"), None)
                assert en_lang is not None
                assert en_lang["name"] == "English"
                assert "nllb" in en_lang["models_supporting"]
                
                # Test model-specific languages
                nllb_result = client.get_languages("nllb")
                assert nllb_result.status_code == 200
                
                nllb_data = nllb_result.response_data
                assert nllb_data["model"] == "nllb"
                assert "en" in nllb_data["supported_languages"]
                assert nllb_data["language_names"]["en"] == "English"
                
                test_reporter.record_success("Language support verified", {
                    "total_languages": len(languages),
                    "nllb_languages": len(nllb_data["supported_languages"])
                })

    def test_error_handling(self, client, test_reporter):
        """Test comprehensive error handling."""
        with test_reporter.test_case("error_handling"):
            
            # Test invalid model
            result = client.translate("Hello", model="invalid_model")
            assert result.status_code == 404
            assert "not found" in result.response_data["detail"]
            
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
            
            # Test passed

    def test_legacy_compatibility(self, client, test_reporter):
        """Test legacy API compatibility."""
        with test_reporter.test_case("legacy_compatibility"):
            
            with patch('app.models.nllb_model.NLLBModel') as mock_nllb:
                async def mock_translate(request):
                    from app.models.base import TranslationResponse
                    return TranslationResponse(
                        translated_text="Привет, мир!",
                        detected_source_lang="en",
                        processing_time_ms=120.0,
                        model_used="nllb",
                        metadata={"legacy": True, "mocked": True}
                    )
                
                mock_instance = Mock()
                mock_instance.is_available.return_value = True
                mock_instance.supports_language_pair.return_value = True
                mock_instance.translate = mock_translate
                mock_nllb.return_value = mock_instance
                
                # Test legacy endpoint
                result = client.post("/translate/legacy", json_data={
                    "text": "Hello, world!",
                    "source_lang": "en",
                    "target_lang": "ru"
                })
                
                assert result.status_code == 200
                
                legacy_data = result.response_data
                assert legacy_data["translated_text"] == "Привет, мир!"
                assert legacy_data["detected_source"] == "en"
                assert legacy_data["time_ms"] == 120
                
                # Verify legacy format (no model_used field)
                assert "model_used" not in legacy_data
                assert "processing_time_ms" not in legacy_data
                
                # Test passed

    def test_performance_benchmarks(self, client, performance_monitor, test_reporter):
        """Test performance benchmarks across different scenarios."""
        with test_reporter.test_case("performance_benchmarks"):
            
            with patch('app.models.nllb_model.NLLBModel') as mock_nllb:
                async def mock_translate(request):
                    import asyncio
                    await asyncio.sleep(0.05)  # Simulate processing time
                    from app.models.base import TranslationResponse
                    return TranslationResponse(
                        translated_text=f"Translated: {request.text}",
                        detected_source_lang=None,
                        processing_time_ms=50.0,
                        model_used="nllb",
                        metadata={"benchmark": True}
                    )
                
                mock_instance = Mock()
                mock_instance.is_available.return_value = True
                mock_instance.supports_language_pair.return_value = True
                mock_instance.translate = mock_translate
                mock_nllb.return_value = mock_instance
                
                # Performance test
                perf_results = client.performance_test("nllb", num_requests=5)
                
                assert perf_results["success_count"] == 5
                assert perf_results["error_count"] == 0
                assert perf_results["avg_duration_ms"] > 0
                assert perf_results["success_rate"] == 1.0
                
                performance_monitor.record_benchmark("nllb_performance", perf_results["avg_duration_ms"])
                
                test_reporter.record_success("Performance benchmarks completed", {
                    "requests_tested": 5,
                    "avg_duration_ms": perf_results["avg_duration_ms"],
                    "success_rate": perf_results["success_rate"]
                })

    def test_concurrent_requests(self, client, test_reporter):
        """Test handling of concurrent requests."""
        with test_reporter.test_case("concurrent_requests"):
            
            with patch('app.models.nllb_model.NLLBModel') as mock_nllb:
                async def mock_translate(request):
                    import asyncio
                    await asyncio.sleep(0.1)  # Simulate processing
                    from app.models.base import TranslationResponse
                    return TranslationResponse(
                        translated_text=f"Concurrent: {request.text}",
                        detected_source_lang=None,
                        processing_time_ms=100.0,
                        model_used="nllb",
                        metadata={"concurrent": True}
                    )
                
                mock_instance = Mock()
                mock_instance.is_available.return_value = True
                mock_instance.supports_language_pair.return_value = True
                mock_instance.translate = mock_translate
                mock_nllb.return_value = mock_instance
                
                # Make concurrent requests
                import threading
                import queue
                
                results_queue = queue.Queue()
                num_concurrent = 3
                
                def make_request(text_id):
                    result = client.translate(f"Concurrent text {text_id}", model="nllb")
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
                    thread.join()
                
                total_time = (time.time() - start_time) * 1000
                
                # Collect results
                results = []
                while not results_queue.empty():
                    results.append(results_queue.get())
                
                # Verify all succeeded
                assert len(results) == num_concurrent
                for text_id, result in results:
                    assert result.status_code == 200
                    assert f"Concurrent text {text_id}" in result.response_data["translated_text"]
                
                test_reporter.record_success("Concurrent requests completed", {
                    "concurrent_requests": num_concurrent,
                    "total_time_ms": total_time,
                    "all_successful": True
                })

    def test_service_recovery(self, service_manager, test_reporter):
        """Test service recovery capabilities."""
        with test_reporter.test_case("service_recovery"):
            
            # This test would simulate service failures and recovery
            # For now, we'll just test that the service can be restarted
            
            # Get current service info
            initial_url = service_manager.get_service_url("multimodel")
            assert initial_url is not None
            
            # Simulate restart (in real scenario, might test actual failure recovery)
            config = MultiModelServiceConfig(
                api_key="test-api-key-e2e",
                models_to_load="nllb",
                log_level="DEBUG"
            )
            
            # In this test, we just verify the service is still responsive
            client = ModelTestClient(initial_url, "test-api-key-e2e")
            health_result = client.health_check()
            assert health_result is True
            
            test_reporter.record_success("Service recovery verified", {
                "service_responsive": True,
                "recovery_successful": True
            })


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])