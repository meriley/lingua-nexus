"""
Simplified Multi-Model Interaction E2E Test Suite - TASK-009 Implementation

This module tests the essential interaction between NLLB and Aya models, including
model switching, concurrent requests, and resource sharing scenarios.
"""

import pytest
import time
import os
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from tests.e2e.utils.comprehensive_client import ComprehensiveTestClient
from tests.e2e.utils.robust_service_manager import RobustServiceManager
from tests.e2e.utils.service_manager import MultiModelServiceConfig


class TestMultiModelSimplified:
    """Simplified test suite for multi-model interactions and resource management."""
    
    @staticmethod
    def get_language_codes_for_model(model_name):
        """Get appropriate language codes for the given model."""
        if model_name == "nllb":
            return "eng_Latn", "spa_Latn"  # NLLB uses flores codes
        else:  # aya
            return "English", "Spanish"    # Aya uses language names
    
    @classmethod
    def setup_class(cls):
        """Setup service with both NLLB and Aya models."""
        cls.service_manager = RobustServiceManager()
        
        # Create service configuration for both models
        config = MultiModelServiceConfig(
            api_key="test-api-key-multimodel-simplified",
            models_to_load="nllb,aya",
            log_level="INFO",
            custom_env={
                "PYTEST_RUNNING": "true",
                "MODELS_TO_LOAD": "nllb,aya",
                "NLLB_MODEL": "facebook/nllb-200-distilled-600M",
                "AYA_MODEL": "CohereForAI/aya-expanse-8b",
                "MODEL_CACHE_DIR": os.path.expanduser("~/.cache/huggingface/transformers"),
                "HF_HOME": os.path.expanduser("~/.cache/huggingface"),
                "TRANSFORMERS_CACHE": os.path.expanduser("~/.cache/huggingface/transformers"),
                "HF_TOKEN": os.environ.get("HF_TOKEN", "test-hf-token-placeholder"),
                "MODEL_LOADING_TIMEOUT": "3600",
                "LOG_MODEL_LOADING_PROGRESS": "true",
                "PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:512",
            }
        )
        
        print("Starting multi-model service with both NLLB and Aya...")
        print("This will take significant time to load both models...")
        
        # Start service with both models
        service_url = cls.service_manager.start_multimodel_with_progress(
            config=config,
            models=["nllb", "aya"],
            timeout=3600  # 60 minutes total
        )
        
        # Initialize client
        cls.client = ComprehensiveTestClient(service_url, "test-api-key-multimodel-simplified")
        
        print("Multi-model service setup complete!")
        
    @classmethod
    def teardown_class(cls):
        """Clean up test environment."""
        cls.service_manager.cleanup()

    def test_001_both_models_available_and_responsive(self):
        """Test 1: Verify both models are available and responsive."""
        print("Testing model availability and responsiveness...")
        
        # Check service health
        health = self.client.get_health()
        assert health["status"] == "healthy", f"Service not healthy: {health}"
        
        # Verify both models are loaded
        models_loaded = health.get("models_loaded", 0)
        assert models_loaded >= 2, f"Expected 2+ models loaded, got {models_loaded}"
        
        models = health.get("models", [])
        model_names = [model["name"] for model in models]
        
        assert "nllb" in model_names, f"NLLB not available: {model_names}"
        assert "aya" in model_names, f"Aya not available: {model_names}"
        
        print(f"✓ Multi-model verification: {models_loaded} models loaded")
        print(f"✓ Available models: {model_names}")

    def test_002_sequential_model_switching(self):
        """Test 2: Validate sequential requests switching between models."""
        print("Testing sequential model switching...")
        
        # Test sequence: NLLB → Aya → NLLB → Aya
        test_sequence = [
            {"model": "nllb", "text": "Hello from NLLB model"},
            {"model": "aya", "text": "Hello from Aya model"},
            {"model": "nllb", "text": "Second NLLB request"},
            {"model": "aya", "text": "Second Aya request"},
        ]
        
        switch_count = 0
        last_model = None
        
        for i, test_case in enumerate(test_sequence):
            print(f"  Sequential test {i+1}: {test_case['model']}")
            
            source_lang, target_lang = self.get_language_codes_for_model(test_case["model"])
            
            start_time = time.time()
            result = self.client.translate(
                text=test_case["text"],
                source_lang=source_lang,
                target_lang=target_lang,
                model=test_case["model"]
            )
            duration = time.time() - start_time
            
            assert result.status_code == 200, \
                f"Model {test_case['model']} failed: {result.error}"
            
            data = result.response_data
            translated_text = data.get("translated_text", "")
            assert len(translated_text) > 0, f"Empty translation from {test_case['model']}"
            
            if last_model and last_model != test_case["model"]:
                switch_count += 1
                print(f"    ✓ Switch from {last_model} to {test_case['model']}: {duration:.2f}s")
            else:
                print(f"    ✓ {test_case['model']} translation: {duration:.2f}s")
            
            last_model = test_case["model"]
            
            # Add small delay for stability
            time.sleep(2)
        
        assert switch_count >= 1, "No model switches occurred"
        print(f"✓ Sequential model switching: {switch_count} successful switches")

    def test_003_concurrent_requests_same_model(self):
        """Test 3: Validate concurrent requests to the same model."""
        print("Testing concurrent requests to same model...")
        
        def translate_concurrent(model_name, request_id):
            """Single translation request for concurrency testing."""
            text = f"Concurrent test {request_id} for {model_name}"
            source_lang, target_lang = self.get_language_codes_for_model(model_name)
            
            start_time = time.time()
            result = self.client.translate(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                model=model_name
            )
            duration = time.time() - start_time
            
            return {
                "request_id": request_id,
                "model": model_name,
                "success": result.status_code == 200,
                "duration": duration,
                "status_code": result.status_code
            }
        
        # Test concurrent NLLB requests
        print("  Testing concurrent NLLB requests...")
        nllb_results = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(translate_concurrent, "nllb", i)
                for i in range(1, 4)  # 3 concurrent requests
            ]
            for future in as_completed(futures):
                nllb_results.append(future.result())
        
        nllb_successes = len([r for r in nllb_results if r["success"]])
        nllb_success_rate = nllb_successes / len(nllb_results)
        
        assert nllb_success_rate >= 0.66, \
            f"NLLB concurrent success rate too low: {nllb_success_rate:.1%}"
        
        print(f"    ✓ NLLB concurrent: {nllb_successes}/{len(nllb_results)} successful")
        
        # Test concurrent Aya requests (fewer due to resource requirements)
        print("  Testing concurrent Aya requests...")
        aya_results = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(translate_concurrent, "aya", i)
                for i in range(1, 3)  # 2 concurrent requests
            ]
            for future in as_completed(futures):
                aya_results.append(future.result())
        
        aya_successes = len([r for r in aya_results if r["success"]])
        aya_success_rate = aya_successes / len(aya_results)
        
        assert aya_success_rate >= 0.5, \
            f"Aya concurrent success rate too low: {aya_success_rate:.1%}"
        
        print(f"    ✓ Aya concurrent: {aya_successes}/{len(aya_results)} successful")

    def test_004_cross_model_concurrent_requests(self):
        """Test 4: Validate concurrent requests across different models."""
        print("Testing cross-model concurrent requests...")
        
        def mixed_translate_request(request_id):
            """Translation request alternating between models."""
            model_name = "nllb" if request_id % 2 == 0 else "aya"
            text = f"Cross-model request {request_id} using {model_name}"
            source_lang, target_lang = self.get_language_codes_for_model(model_name)
            
            start_time = time.time()
            result = self.client.translate(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                model=model_name
            )
            duration = time.time() - start_time
            
            return {
                "request_id": request_id,
                "model": model_name,
                "success": result.status_code == 200,
                "duration": duration
            }
        
        # Execute mixed concurrent requests
        mixed_results = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(mixed_translate_request, i)
                for i in range(1, 5)  # 2 NLLB + 2 Aya requests
            ]
            for future in as_completed(futures):
                mixed_results.append(future.result())
        
        # Analyze results
        total_successes = len([r for r in mixed_results if r["success"]])
        success_rate = total_successes / len(mixed_results)
        
        nllb_results = [r for r in mixed_results if r["model"] == "nllb"]
        aya_results = [r for r in mixed_results if r["model"] == "aya"]
        
        assert success_rate >= 0.5, \
            f"Cross-model success rate too low: {success_rate:.1%}"
        
        print(f"✓ Cross-model concurrent: {total_successes}/{len(mixed_results)} successful")
        print(f"  NLLB results: {len([r for r in nllb_results if r['success']])}/{len(nllb_results)}")
        print(f"  Aya results: {len([r for r in aya_results if r['success']])}/{len(aya_results)}")

    def test_005_model_comparison_same_input(self):
        """Test 5: Compare translations between models for same inputs."""
        print("Testing model comparison for same inputs...")
        
        comparison_texts = [
            "Technology is transforming our world.",
            "Education empowers people globally.",
            "Science advances human knowledge."
        ]
        
        comparisons = []
        
        for text in comparison_texts:
            print(f"  Comparing models for: '{text}'")
            
            # Get NLLB translation
            nllb_source, nllb_target = self.get_language_codes_for_model("nllb")
            nllb_result = self.client.translate(
                text=text,
                source_lang=nllb_source,
                target_lang=nllb_target,
                model="nllb"
            )
            
            # Small delay between requests
            time.sleep(2)
            
            # Get Aya translation  
            aya_source, aya_target = self.get_language_codes_for_model("aya")
            aya_result = self.client.translate(
                text=text,
                source_lang=aya_source,
                target_lang=aya_target,
                model="aya"
            )
            
            comparison = {
                "input_text": text,
                "nllb_success": nllb_result.status_code == 200,
                "aya_success": aya_result.status_code == 200,
                "nllb_translation": nllb_result.response_data.get("translated_text", "") if nllb_result.status_code == 200 else None,
                "aya_translation": aya_result.response_data.get("translated_text", "") if aya_result.status_code == 200 else None
            }
            
            comparisons.append(comparison)
            
            if comparison["nllb_success"] and comparison["aya_success"]:
                print(f"    NLLB: {comparison['nllb_translation']}")
                print(f"    Aya:  {comparison['aya_translation']}")
                
                # Check if translations are different (expected)
                if comparison["nllb_translation"] != comparison["aya_translation"]:
                    print("    ✓ Models produce different translations")
                else:
                    print("    ⚠ Models produced identical translations")
            else:
                print(f"    ⚠ Translation failures - NLLB: {comparison['nllb_success']}, Aya: {comparison['aya_success']}")
            
            # Rate limiting delay
            time.sleep(3)
        
        # Analyze comparison results
        successful_comparisons = [
            c for c in comparisons 
            if c["nllb_success"] and c["aya_success"]
        ]
        
        comparison_success_rate = len(successful_comparisons) / len(comparisons)
        assert comparison_success_rate >= 0.66, \
            f"Model comparison success rate too low: {comparison_success_rate:.1%}"
        
        print(f"✓ Model comparison: {len(successful_comparisons)}/{len(comparisons)} successful")

    def test_006_resource_sharing_basic_test(self):
        """Test 6: Basic resource sharing test between models."""
        print("Testing basic resource sharing...")
        
        # Alternate between models multiple times to test resource sharing
        resource_tests = [
            {"model": "nllb", "text": "Resource test 1 NLLB"},
            {"model": "aya", "text": "Resource test 1 Aya"},
            {"model": "nllb", "text": "Resource test 2 NLLB"},
            {"model": "aya", "text": "Resource test 2 Aya"},
            {"model": "nllb", "text": "Resource test 3 NLLB"},
            {"model": "aya", "text": "Resource test 3 Aya"},
        ]
        
        results = []
        
        for i, test in enumerate(resource_tests):
            print(f"  Resource test {i+1}: {test['model']}")
            
            source_lang, target_lang = self.get_language_codes_for_model(test["model"])
            
            start_time = time.time()
            result = self.client.translate(
                text=test["text"],
                source_lang=source_lang,
                target_lang=target_lang,
                model=test["model"]
            )
            duration = time.time() - start_time
            
            success = result.status_code == 200
            results.append({
                "model": test["model"],
                "success": success,
                "duration": duration
            })
            
            if success:
                print(f"    ✓ {test['model']}: {duration:.2f}s")
            else:
                print(f"    ✗ {test['model']}: Failed with {result.status_code}")
            
            # Brief pause between requests
            time.sleep(2)
        
        # Analyze resource sharing results
        successful_results = [r for r in results if r["success"]]
        success_rate = len(successful_results) / len(results)
        
        assert success_rate >= 0.66, \
            f"Resource sharing success rate too low: {success_rate:.1%}"
        
        nllb_results = [r for r in results if r["model"] == "nllb"]
        aya_results = [r for r in results if r["model"] == "aya"]
        
        nllb_successes = len([r for r in nllb_results if r["success"]])
        aya_successes = len([r for r in aya_results if r["success"]])
        
        print(f"✓ Resource sharing: {len(successful_results)}/{len(results)} successful")
        print(f"  NLLB: {nllb_successes}/{len(nllb_results)} successful")
        print(f"  Aya: {aya_successes}/{len(aya_results)} successful")

    def test_007_final_multimodel_health_check(self):
        """Test 7: Final health check to ensure both models remain responsive."""
        print("Performing final multi-model health check...")
        
        # Check service health
        health = self.client.get_health()
        assert health["status"] == "healthy", f"Service not healthy after tests: {health}"
        
        models = health.get("models", [])
        model_statuses = {model["name"]: model["status"] for model in models}
        
        assert "nllb" in model_statuses, "NLLB model missing from health response"
        assert "aya" in model_statuses, "Aya model missing from health response"
        assert model_statuses["nllb"] == "loaded", f"NLLB not loaded: {model_statuses['nllb']}"
        assert model_statuses["aya"] == "loaded", f"Aya not loaded: {model_statuses['aya']}"
        
        print(f"  ✓ Service status: {health['status']}")
        print(f"  ✓ NLLB status: {model_statuses['nllb']}")
        print(f"  ✓ Aya status: {model_statuses['aya']}")
        
        # Final translation test for each model
        nllb_source, nllb_target = self.get_language_codes_for_model("nllb")
        final_nllb = self.client.translate(
            text="Final NLLB test",
            source_lang=nllb_source,
            target_lang=nllb_target,
            model="nllb"
        )
        
        aya_source, aya_target = self.get_language_codes_for_model("aya") 
        final_aya = self.client.translate(
            text="Final Aya test",
            source_lang=aya_source,
            target_lang=aya_target,
            model="aya"
        )
        
        assert final_nllb.status_code == 200, f"NLLB final test failed: {final_nllb.status_code}"
        assert final_aya.status_code == 200, f"Aya final test failed: {final_aya.status_code}"
        
        print("  ✓ Final NLLB translation successful")
        print("  ✓ Final Aya translation successful")
        print("✓ Multi-model interaction test suite COMPLETED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])