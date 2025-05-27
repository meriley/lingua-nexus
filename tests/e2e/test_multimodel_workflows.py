"""
End-to-end tests for multi-model translation workflows.

This module tests the complete multi-model translation system including
API endpoints, model loading, translation workflows, and error scenarios.
"""

import pytest
import asyncio
import time
import requests
from typing import Dict, Any, List
from unittest.mock import patch, Mock

from tests.e2e.utils.http_client import E2EHttpClient as HTTPClient
from tests.e2e.utils.service_manager import ServiceManager
from tests.e2e.utils.test_reporter import E2ETestReporter as TestReporter
from tests.e2e.utils.performance_monitor import PerformanceMonitor


class TestMultiModelWorkflows:
    """Test complete multi-model translation workflows."""
    
    @pytest.fixture(scope="class")
    def service_manager(self):
        """Set up multi-model service for testing."""
        manager = ServiceManager()
        
        # Start multi-model service with test configuration
        config = {
            "MODELS_TO_LOAD": "nllb",  # Start with NLLB only
            "API_KEY": "test-api-key-multimodel",
            "LOG_LEVEL": "DEBUG"
        }
        
        manager.start_multimodel_service(config)
        yield manager
        manager.cleanup()
    
    @pytest.fixture
    def http_client(self, service_manager):
        """HTTP client for API requests."""
        base_url = service_manager.get_service_url("multimodel")
        return HTTPClient(
            base_url=base_url,
            default_headers={"X-API-Key": "test-api-key-multimodel"}
        )
    
    @pytest.fixture
    def performance_monitor(self):
        """Performance monitoring for E2E tests."""
        return PerformanceMonitor()
    
    @pytest.fixture
    def test_reporter(self):
        """Test result reporting."""
        return TestReporter("multimodel_e2e")

    def test_service_startup_and_health(self, http_client, test_reporter):
        """Test multi-model service startup and health check."""
        with test_reporter.test_case("service_startup_health"):
            # Wait for service to be ready
            max_retries = 30
            for attempt in range(max_retries):
                try:
                    response = http_client.get("/health")
                    if response.status_code == 200:
                        break
                    time.sleep(1)
                except requests.exceptions.ConnectionError:
                    if attempt == max_retries - 1:
                        pytest.fail("Service failed to start within timeout")
                    time.sleep(1)
            
            # Verify health response
            health_data = response.json()
            assert health_data["status"] == "healthy"
            assert health_data["models_loaded"] >= 1
            assert "nllb" in health_data["models_available"]
            
            test_reporter.record_success("Service started successfully", health_data)

    def test_model_management_workflow(self, http_client, test_reporter):
        """Test complete model management workflow."""
        with test_reporter.test_case("model_management_workflow"):
            
            # 1. List initial models
            response = http_client.get("/models")
            assert response.status_code == 200
            
            initial_models = response.json()
            assert len(initial_models) >= 1
            nllb_model = next((m for m in initial_models if m["name"] == "nllb"), None)
            assert nllb_model is not None
            assert nllb_model["available"] is True
            
            # 2. Mock Aya model loading (since we can't load real model in tests)
            with patch('app.models.aya_model.AyaModel') as mock_aya:
                mock_instance = Mock()
                mock_instance.is_available.return_value = True
                mock_instance.model_name = "aya"
                mock_instance.get_supported_languages.return_value = ["en", "ru", "es"]
                mock_instance.get_model_info.return_value = {
                    "name": "aya",
                    "type": "aya", 
                    "available": True,
                    "device": "cpu"
                }
                mock_aya.return_value = mock_instance
                
                # Load Aya model
                response = http_client.post("/models/aya/load")
                assert response.status_code == 200
                assert "loaded successfully" in response.json()["message"]
            
            # 3. Verify both models are available
            response = http_client.get("/models")
            models = response.json()
            model_names = [m["name"] for m in models]
            assert "nllb" in model_names
            
            # 4. Test model-specific language support
            response = http_client.get("/languages/nllb")
            assert response.status_code == 200
            
            nllb_langs = response.json()
            assert nllb_langs["model"] == "nllb"
            assert "en" in nllb_langs["supported_languages"]
            assert "ru" in nllb_langs["supported_languages"]
            
            test_reporter.record_success("Model management workflow completed")

    def test_translation_workflow_nllb(self, http_client, performance_monitor, test_reporter):
        """Test complete translation workflow with NLLB model."""
        with test_reporter.test_case("translation_workflow_nllb"):
            
            # Mock NLLB model for testing
            with patch('app.models.nllb_model.NLLBModel') as mock_nllb:
                # Setup mock translation response
                async def mock_translate(request):
                    from app.models.base import TranslationResponse
                    return TranslationResponse(
                        translated_text="Привет, мир!",
                        detected_source_lang=None,
                        processing_time_ms=150.0,
                        model_used="nllb",
                        metadata={"device": "cpu", "use_pipeline": True}
                    )
                
                mock_instance = Mock()
                mock_instance.is_available.return_value = True
                mock_instance.supports_language_pair.return_value = True
                mock_instance.translate = mock_translate
                mock_nllb.return_value = mock_instance
                
                # Test single translation
                translation_data = {
                    "text": "Hello, world!",
                    "source_lang": "en",
                    "target_lang": "ru",
                    "model": "nllb"
                }
                
                start_time = time.time()
                response = http_client.post("/translate", json_data=translation_data)
                end_time = time.time()
                
                assert response.status_code == 200
                
                result = response.json()
                assert result["translated_text"] == "Привет, мир!"
                assert result["model_used"] == "nllb"
                assert result["processing_time_ms"] > 0
                
                # Record performance metrics
                performance_monitor.record_request(
                    endpoint="/translate",
                    duration_ms=(end_time - start_time) * 1000,
                    model="nllb",
                    text_length=len(translation_data["text"])
                )
                
                test_reporter.record_success("NLLB translation completed", {
                    "input": translation_data["text"],
                    "output": result["translated_text"],
                    "processing_time": result["processing_time_ms"]
                })

    def test_translation_workflow_aya(self, http_client, performance_monitor, test_reporter):
        """Test complete translation workflow with Aya Expanse model."""
        with test_reporter.test_case("translation_workflow_aya"):
            
            # Mock Aya model for testing
            with patch('app.models.aya_model.AyaModel') as mock_aya:
                # Setup mock translation response
                async def mock_translate(request):
                    from app.models.base import TranslationResponse
                    return TranslationResponse(
                        translated_text="Hola, mundo!",
                        detected_source_lang=None,
                        processing_time_ms=200.0,
                        model_used="aya",
                        metadata={
                            "device": "cpu",
                            "temperature": 0.3,
                            "use_quantization": False
                        }
                    )
                
                mock_instance = Mock()
                mock_instance.is_available.return_value = True
                mock_instance.supports_language_pair.return_value = True
                mock_instance.translate = mock_translate
                mock_aya.return_value = mock_instance
                
                # First load the model
                response = http_client.post("/models/aya/load")
                assert response.status_code == 200
                
                # Test translation with custom options
                translation_data = {
                    "text": "Hello, world!",
                    "source_lang": "en",
                    "target_lang": "es",
                    "model": "aya",
                    "model_options": {
                        "temperature": 0.5,
                        "max_new_tokens": 100
                    }
                }
                
                start_time = time.time()
                response = http_client.post("/translate", json_data=translation_data)
                end_time = time.time()
                
                assert response.status_code == 200
                
                result = response.json()
                assert result["translated_text"] == "Hola, mundo!"
                assert result["model_used"] == "aya"
                assert result["metadata"]["temperature"] == 0.3
                
                # Record performance metrics
                performance_monitor.record_request(
                    endpoint="/translate",
                    duration_ms=(end_time - start_time) * 1000,
                    model="aya",
                    text_length=len(translation_data["text"])
                )
                
                test_reporter.record_success("Aya translation completed", {
                    "input": translation_data["text"],
                    "output": result["translated_text"],
                    "model_options": translation_data["model_options"]
                })

    def test_auto_language_detection_workflow(self, http_client, test_reporter):
        """Test automatic language detection workflow."""
        with test_reporter.test_case("auto_language_detection"):
            
            with patch('app.models.nllb_model.NLLBModel') as mock_nllb:
                # Setup mock for auto-detection
                async def mock_translate(request):
                    from app.models.base import TranslationResponse
                    return TranslationResponse(
                        translated_text="Hello, world!",
                        detected_source_lang="ru",  # Detected Russian
                        processing_time_ms=180.0,
                        model_used="nllb",
                        metadata={"auto_detected": True}
                    )
                
                mock_instance = Mock()
                mock_instance.is_available.return_value = True
                mock_instance.supports_language_pair.return_value = True
                mock_instance.translate = mock_translate
                mock_nllb.return_value = mock_instance
                
                # Test auto-detection
                translation_data = {
                    "text": "Привет, мир!",
                    "source_lang": "auto",
                    "target_lang": "en",
                    "model": "nllb"
                }
                
                response = http_client.post("/translate", json_data=translation_data)
                assert response.status_code == 200
                
                result = response.json()
                assert result["detected_source_lang"] == "ru"
                assert result["translated_text"] == "Hello, world!"
                
                test_reporter.record_success("Auto-detection completed", {
                    "input": translation_data["text"],
                    "detected_language": result["detected_source_lang"],
                    "output": result["translated_text"]
                })

    def test_batch_translation_workflow(self, http_client, performance_monitor, test_reporter):
        """Test batch translation workflow."""
        with test_reporter.test_case("batch_translation"):
            
            with patch('app.models.nllb_model.NLLBModel') as mock_nllb:
                # Setup mock for batch translation
                async def mock_translate(request):
                    from app.models.base import TranslationResponse
                    translations = {
                        "Hello": "Привет",
                        "World": "Мир",
                        "Good morning": "Доброе утро"
                    }
                    return TranslationResponse(
                        translated_text=translations.get(request.text, f"Translated: {request.text}"),
                        detected_source_lang=None,
                        processing_time_ms=120.0,
                        model_used="nllb",
                        metadata={"batch_processing": True}
                    )
                
                mock_instance = Mock()
                mock_instance.is_available.return_value = True
                mock_instance.supports_language_pair.return_value = True
                mock_instance.translate = mock_translate
                mock_nllb.return_value = mock_instance
                
                # Test batch translation
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
                    },
                    {
                        "text": "Good morning",
                        "source_lang": "en",
                        "target_lang": "ru",
                        "model": "nllb"
                    }
                ]
                
                start_time = time.time()
                response = http_client.post("/translate/batch", json_data=batch_data)
                end_time = time.time()
                
                assert response.status_code == 200
                
                result = response.json()
                assert result["total_processed"] == 3
                assert result["total_errors"] == 0
                assert len(result["results"]) == 3
                
                # Verify each translation
                translations = {r["result"]["translated_text"] for r in result["results"]}
                assert "Привет" in translations
                assert "Мир" in translations
                assert "Доброе утро" in translations
                
                # Record performance metrics
                performance_monitor.record_batch_request(
                    endpoint="/translate/batch",
                    duration_ms=(end_time - start_time) * 1000,
                    batch_size=len(batch_data),
                    model="nllb"
                )
                
                test_reporter.record_success("Batch translation completed", {
                    "batch_size": len(batch_data),
                    "processing_time": (end_time - start_time) * 1000,
                    "results": len(result["results"])
                })

    def test_language_support_workflow(self, http_client, test_reporter):
        """Test language support discovery workflow."""
        with test_reporter.test_case("language_support_workflow"):
            
            # Mock models for language support testing
            with patch('app.models.nllb_model.NLLBModel') as mock_nllb, \
                 patch('app.models.aya_model.AyaModel') as mock_aya:
                
                # Setup NLLB mock
                nllb_instance = Mock()
                nllb_instance.is_available.return_value = True
                nllb_instance.get_supported_languages.return_value = ["en", "ru", "es", "fr", "de"]
                mock_nllb.return_value = nllb_instance
                
                # Setup Aya mock
                aya_instance = Mock()
                aya_instance.is_available.return_value = True
                aya_instance.get_supported_languages.return_value = ["en", "ru", "es", "zh", "ar"]
                mock_aya.return_value = aya_instance
                
                # Load Aya model
                response = http_client.post("/models/aya/load")
                assert response.status_code == 200
                
                # 1. Test global language support
                response = http_client.get("/languages")
                assert response.status_code == 200
                
                languages = response.json()
                assert len(languages) >= 5  # At least en, ru, es, fr, de, zh, ar
                
                # Find English language info
                en_info = next((lang for lang in languages if lang["iso_code"] == "en"), None)
                assert en_info is not None
                assert en_info["name"] == "English"
                assert len(en_info["models_supporting"]) == 2  # Both NLLB and Aya
                
                # 2. Test model-specific language support
                response = http_client.get("/languages/nllb")
                assert response.status_code == 200
                
                nllb_langs = response.json()
                assert "fr" in nllb_langs["supported_languages"]
                assert "de" in nllb_langs["supported_languages"]
                
                response = http_client.get("/languages/aya")
                assert response.status_code == 200
                
                aya_langs = response.json()
                assert "zh" in aya_langs["supported_languages"]
                assert "ar" in aya_langs["supported_languages"]
                
                test_reporter.record_success("Language support workflow completed", {
                    "total_languages": len(languages),
                    "nllb_languages": len(nllb_langs["supported_languages"]),
                    "aya_languages": len(aya_langs["supported_languages"])
                })

    def test_error_handling_workflows(self, http_client, test_reporter):
        """Test error handling in various scenarios."""
        with test_reporter.test_case("error_handling_workflows"):
            
            # 1. Test invalid model
            translation_data = {
                "text": "Hello, world!",
                "source_lang": "en",
                "target_lang": "ru",
                "model": "invalid_model"
            }
            
            response = http_client.post("/translate", json_data=translation_data)
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]
            
            # 2. Test unsupported language pair
            with patch('app.models.nllb_model.NLLBModel') as mock_nllb:
                mock_instance = Mock()
                mock_instance.is_available.return_value = True
                mock_instance.supports_language_pair.return_value = False
                mock_nllb.return_value = mock_instance
                
                translation_data = {
                    "text": "Hello",
                    "source_lang": "en", 
                    "target_lang": "xx",  # Unsupported
                    "model": "nllb"
                }
                
                response = http_client.post("/translate", json_data=translation_data)
                assert response.status_code == 400
                assert "does not support" in response.json()["detail"]
            
            # 3. Test invalid request format
            invalid_data = {
                "text": "",  # Empty text
                "target_lang": "ru",
                "model": "nllb"
            }
            
            response = http_client.post("/translate", json_data=invalid_data)
            assert response.status_code == 422  # Validation error
            
            # 4. Test forbidden access
            response = http_client.get("/models", headers={})  # No API key
            assert response.status_code == 403
            
            # 5. Test batch size limit
            large_batch = [{"text": f"Text {i}", "target_lang": "ru", "model": "nllb"} 
                          for i in range(15)]  # Exceed limit
            
            response = http_client.post("/translate/batch", json_data=large_batch)
            assert response.status_code == 400
            assert "cannot exceed" in response.json()["detail"]
            
            test_reporter.record_success("Error handling tests completed")

    def test_legacy_compatibility_workflow(self, http_client, test_reporter):
        """Test legacy API compatibility."""
        with test_reporter.test_case("legacy_compatibility"):
            
            with patch('app.models.nllb_model.NLLBModel') as mock_nllb:
                # Setup mock for legacy compatibility
                async def mock_translate(request):
                    from app.models.base import TranslationResponse
                    return TranslationResponse(
                        translated_text="Привет, мир!",
                        detected_source_lang="en",
                        processing_time_ms=130.0,
                        model_used="nllb",
                        metadata={"legacy_mode": True}
                    )
                
                mock_instance = Mock()
                mock_instance.is_available.return_value = True
                mock_instance.supports_language_pair.return_value = True
                mock_instance.translate = mock_translate
                mock_nllb.return_value = mock_instance
                
                # Test legacy endpoint format
                legacy_data = {
                    "text": "Hello, world!",
                    "source_lang": "en",
                    "target_lang": "ru"
                }
                
                response = http_client.post("/translate/legacy", json_data=legacy_data)
                assert response.status_code == 200
                
                result = response.json()
                assert result["translated_text"] == "Привет, мир!"
                assert result["detected_source"] == "en"
                assert result["time_ms"] == 130
                
                # Verify legacy format (no model_used field, different field names)
                assert "model_used" not in result
                assert "processing_time_ms" not in result
                assert "time_ms" in result
                
                test_reporter.record_success("Legacy compatibility verified", {
                    "legacy_format": True,
                    "backward_compatible": True
                })

    def test_performance_benchmarks(self, http_client, performance_monitor, test_reporter):
        """Test performance benchmarks across models."""
        with test_reporter.test_case("performance_benchmarks"):
            
            # Mock both models for performance comparison
            with patch('app.models.nllb_model.NLLBModel') as mock_nllb, \
                 patch('app.models.aya_model.AyaModel') as mock_aya:
                
                # Setup NLLB mock (faster)
                async def mock_nllb_translate(request):
                    await asyncio.sleep(0.1)  # Simulate processing time
                    from app.models.base import TranslationResponse
                    return TranslationResponse(
                        translated_text="NLLB: " + request.text,
                        detected_source_lang=None,
                        processing_time_ms=100.0,
                        model_used="nllb",
                        metadata={"simulated": True}
                    )
                
                nllb_instance = Mock()
                nllb_instance.is_available.return_value = True
                nllb_instance.supports_language_pair.return_value = True
                nllb_instance.translate = mock_nllb_translate
                mock_nllb.return_value = nllb_instance
                
                # Setup Aya mock (slower but more capable)
                async def mock_aya_translate(request):
                    await asyncio.sleep(0.2)  # Simulate longer processing
                    from app.models.base import TranslationResponse
                    return TranslationResponse(
                        translated_text="Aya: " + request.text,
                        detected_source_lang=None,
                        processing_time_ms=200.0,
                        model_used="aya",
                        metadata={"simulated": True}
                    )
                
                aya_instance = Mock()
                aya_instance.is_available.return_value = True
                aya_instance.supports_language_pair.return_value = True
                aya_instance.translate = mock_aya_translate
                mock_aya.return_value = aya_instance
                
                # Load Aya model
                response = http_client.post("/models/aya/load")
                assert response.status_code == 200
                
                # Benchmark NLLB
                nllb_times = []
                for i in range(3):
                    start_time = time.time()
                    response = http_client.post("/translate", json_data={
                        "text": f"Test text {i}",
                        "source_lang": "en",
                        "target_lang": "ru", 
                        "model": "nllb"
                    })
                    end_time = time.time()
                    
                    assert response.status_code == 200
                    nllb_times.append((end_time - start_time) * 1000)
                
                # Benchmark Aya
                aya_times = []
                for i in range(3):
                    start_time = time.time()
                    response = http_client.post("/translate", json_data={
                        "text": f"Test text {i}",
                        "source_lang": "en",
                        "target_lang": "ru",
                        "model": "aya"
                    })
                    end_time = time.time()
                    
                    assert response.status_code == 200
                    aya_times.append((end_time - start_time) * 1000)
                
                # Record performance comparison
                avg_nllb_time = sum(nllb_times) / len(nllb_times)
                avg_aya_time = sum(aya_times) / len(aya_times)
                
                performance_monitor.record_benchmark("nllb_avg_time", avg_nllb_time)
                performance_monitor.record_benchmark("aya_avg_time", avg_aya_time)
                
                test_reporter.record_success("Performance benchmarks completed", {
                    "nllb_avg_time_ms": avg_nllb_time,
                    "aya_avg_time_ms": avg_aya_time,
                    "performance_ratio": avg_aya_time / avg_nllb_time
                })

    def test_concurrent_requests_workflow(self, http_client, performance_monitor, test_reporter):
        """Test concurrent translation requests."""
        with test_reporter.test_case("concurrent_requests"):
            
            with patch('app.models.nllb_model.NLLBModel') as mock_nllb:
                # Setup mock for concurrent testing
                async def mock_translate(request):
                    await asyncio.sleep(0.1)  # Simulate processing
                    from app.models.base import TranslationResponse
                    return TranslationResponse(
                        translated_text=f"Translated: {request.text}",
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
                
                # Create concurrent requests
                import threading
                import queue
                
                results_queue = queue.Queue()
                num_concurrent = 5
                
                def make_request(text_id):
                    try:
                        response = http_client.post("/translate", json_data={
                            "text": f"Concurrent text {text_id}",
                            "source_lang": "en",
                            "target_lang": "ru",
                            "model": "nllb"
                        })
                        results_queue.put((text_id, response.status_code, response.json()))
                    except Exception as e:
                        results_queue.put((text_id, 500, str(e)))
                
                # Start concurrent requests
                threads = []
                start_time = time.time()
                
                for i in range(num_concurrent):
                    thread = threading.Thread(target=make_request, args=(i,))
                    threads.append(thread)
                    thread.start()
                
                # Wait for all to complete
                for thread in threads:
                    thread.join()
                
                end_time = time.time()
                
                # Collect results
                results = []
                while not results_queue.empty():
                    results.append(results_queue.get())
                
                # Verify all requests succeeded
                assert len(results) == num_concurrent
                for text_id, status_code, response_data in results:
                    assert status_code == 200
                    if isinstance(response_data, dict):
                        assert f"Concurrent text {text_id}" in response_data["translated_text"]
                
                total_time = (end_time - start_time) * 1000
                performance_monitor.record_concurrent_test(
                    concurrent_requests=num_concurrent,
                    total_time_ms=total_time,
                    avg_time_per_request=total_time / num_concurrent
                )
                
                test_reporter.record_success("Concurrent requests completed", {
                    "concurrent_requests": num_concurrent,
                    "total_time_ms": total_time,
                    "success_rate": "100%"
                })

    def test_model_switching_workflow(self, http_client, test_reporter):
        """Test dynamic model switching during operation."""
        with test_reporter.test_case("model_switching"):
            
            with patch('app.models.nllb_model.NLLBModel') as mock_nllb, \
                 patch('app.models.aya_model.AyaModel') as mock_aya:
                
                # Setup mocks
                nllb_instance = Mock()
                nllb_instance.is_available.return_value = True
                nllb_instance.supports_language_pair.return_value = True
                
                async def mock_nllb_translate(request):
                    from app.models.base import TranslationResponse
                    return TranslationResponse(
                        translated_text="NLLB result",
                        detected_source_lang=None,
                        processing_time_ms=100.0,
                        model_used="nllb",
                        metadata={}
                    )
                
                nllb_instance.translate = mock_nllb_translate
                mock_nllb.return_value = nllb_instance
                
                aya_instance = Mock()
                aya_instance.is_available.return_value = True
                aya_instance.supports_language_pair.return_value = True
                
                async def mock_aya_translate(request):
                    from app.models.base import TranslationResponse
                    return TranslationResponse(
                        translated_text="Aya result",
                        detected_source_lang=None,
                        processing_time_ms=200.0,
                        model_used="aya",
                        metadata={}
                    )
                
                aya_instance.translate = mock_aya_translate
                mock_aya.return_value = aya_instance
                
                # 1. Translate with NLLB
                response = http_client.post("/translate", json_data={
                    "text": "Test text",
                    "source_lang": "en",
                    "target_lang": "ru",
                    "model": "nllb"
                })
                assert response.status_code == 200
                assert response.json()["model_used"] == "nllb"
                
                # 2. Load Aya model
                response = http_client.post("/models/aya/load")
                assert response.status_code == 200
                
                # 3. Switch to Aya model
                response = http_client.post("/translate", json_data={
                    "text": "Test text",
                    "source_lang": "en",
                    "target_lang": "ru",
                    "model": "aya"
                })
                assert response.status_code == 200
                assert response.json()["model_used"] == "aya"
                
                # 4. Switch back to NLLB
                response = http_client.post("/translate", json_data={
                    "text": "Test text",
                    "source_lang": "en",
                    "target_lang": "ru",
                    "model": "nllb"
                })
                assert response.status_code == 200
                assert response.json()["model_used"] == "nllb"
                
                # 5. Unload Aya model
                response = http_client.delete("/models/aya")
                assert response.status_code == 200
                
                # 6. Verify Aya is no longer available
                response = http_client.post("/translate", json_data={
                    "text": "Test text",
                    "source_lang": "en",
                    "target_lang": "ru",
                    "model": "aya"
                })
                assert response.status_code == 404
                
                test_reporter.record_success("Model switching workflow completed", {
                    "models_tested": ["nllb", "aya"],
                    "switching_successful": True,
                    "cleanup_successful": True
                })


class TestMultiModelIntegration:
    """Integration tests for multi-model system components."""
    
    def test_language_code_conversion_e2e(self, test_reporter):
        """Test language code conversion across the system."""
        with test_reporter.test_case("language_code_conversion_e2e"):
            from app.utils.language_codes import LanguageCodeConverter
            
            # Test conversion chain: ISO -> NLLB -> ISO
            iso_code = "en"
            nllb_code = LanguageCodeConverter.to_model_code(iso_code, "nllb")
            back_to_iso = LanguageCodeConverter.from_model_code(nllb_code, "nllb")
            
            assert nllb_code == "eng_Latn"
            assert back_to_iso == iso_code
            
            # Test conversion chain: ISO -> Aya -> ISO
            aya_code = LanguageCodeConverter.to_model_code(iso_code, "aya")
            back_to_iso_aya = LanguageCodeConverter.from_model_code(aya_code, "aya")
            
            assert aya_code == "English"
            assert back_to_iso_aya == iso_code
            
            # Test normalization
            normalized = LanguageCodeConverter.normalize_language_code("English", "nllb")
            assert normalized == "eng_Latn"
            
            test_reporter.record_success("Language code conversion verified")
    
    def test_model_registry_e2e(self, test_reporter):
        """Test model registry functionality end-to-end."""
        with test_reporter.test_case("model_registry_e2e"):
            from app.models.registry import ModelRegistry
            
            registry = ModelRegistry()
            
            # Test factory registration
            assert "nllb" in registry._model_factories
            assert "aya" in registry._model_factories
            
            # Test default configurations
            nllb_config = registry._get_default_config("nllb")
            assert nllb_config["model_path"] == "facebook/nllb-200-distilled-600M"
            
            aya_config = registry._get_default_config("aya")
            assert aya_config["model_path"] == "CohereForAI/aya-expanse-8b"
            assert aya_config["use_quantization"] is True
            
            test_reporter.record_success("Model registry verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])