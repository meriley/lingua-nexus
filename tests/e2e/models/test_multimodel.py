"""
Multi-Model Interaction E2E Test Suite

This module tests the interaction between NLLB and Aya models, including
model switching, concurrent requests, and resource sharing scenarios.
"""

import pytest
import sys
import os
import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

# Add the e2e directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.robust_service_manager import RobustServiceManager
from utils.service_manager import MultiModelServiceConfig
from utils.comprehensive_client import ComprehensiveTestClient


class TestMultiModelInteractions:
    """Test suite for multi-model interactions and resource management."""
    
    @staticmethod
    def get_language_codes_for_model(model_name, source="en", target="es"):
        """Get appropriate language codes for the given model."""
        if model_name == "nllb":
            # NLLB uses flores codes
            lang_map = {
                "en": "eng_Latn", "es": "spa_Latn", "fr": "fra_Latn", 
                "de": "deu_Latn", "it": "ita_Latn"
            }
            return lang_map.get(source, "eng_Latn"), lang_map.get(target, "spa_Latn")
        else:  # aya
            # Aya uses language names
            lang_map = {
                "en": "English", "es": "Spanish", "fr": "French",
                "de": "German", "it": "Italian"
            }
            return lang_map.get(source, "English"), lang_map.get(target, "Spanish")
    
    @pytest.fixture(scope="class")
    def multimodel_service(self):
        """Setup service with both NLLB and Aya models - RESOURCE INTENSIVE."""
        manager = RobustServiceManager()
        
        try:
            config = MultiModelServiceConfig(
                api_key="test-api-key-multimodel",
                models_to_load="nllb,aya",  # Load both models
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
                    "MODEL_LOADING_TIMEOUT": "3600",  # 60 minutes for both models
                    "LOG_MODEL_LOADING_PROGRESS": "true",
                    "PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:512",
                }
            )
            
            print("Starting multi-model service with both NLLB and Aya - this will take 60+ minutes...")
            loading_start = time.time()
            
            # Start service with both models
            service_url = manager.start_multimodel_with_progress(
                config=config,
                models=["nllb", "aya"],
                timeout=3600  # 60 minutes total
            )
            
            loading_duration = time.time() - loading_start
            print(f"Multi-model service ready in {loading_duration:.1f} seconds")
            
            client = ComprehensiveTestClient(service_url, api_key="test-api-key-multimodel")
            
            # Verify both models are ready
            assert manager.verify_model_readiness("nllb", api_key="test-api-key-multimodel")
            assert manager.verify_model_readiness("aya", api_key="test-api-key-multimodel")
            
            yield {"manager": manager, "client": client, "service_url": service_url}
            
        finally:
            manager.cleanup()
    
    def test_001_model_availability_verification(self, multimodel_service):
        """Verify both models are available and responsive."""
        client = multimodel_service["client"]
        
        # Check service health
        health_result = client.get("/health")
        assert health_result.status_code == 200, "Health check failed"
        
        health_data = health_result.response_data
        assert health_data["status"] == "healthy", f"Service not healthy: {health_data}"
        assert health_data.get("models_loaded", 0) >= 2, \
            f"Expected 2+ models loaded, got {health_data.get('models_loaded')}"
        
        # Check models endpoint
        models_result = client.get("/models")
        assert models_result.status_code == 200, "Models endpoint failed"
        
        models_data = models_result.response_data
        if isinstance(models_data, dict):
            available_models = list(models_data.keys())
        else:
            available_models = models_data
        
        assert "nllb" in available_models, f"NLLB not available: {available_models}"
        assert "aya" in available_models, f"Aya not available: {available_models}"
        
        print(f"✓ Multi-model verification: {health_data['models_loaded']} models loaded")
        print(f"✓ Available models: {available_models}")
    
    def test_002_sequential_model_switching(self, multimodel_service):
        """Test sequential requests switching between models."""
        client = multimodel_service["client"]
        
        # Test sequence: NLLB → Aya → NLLB → Aya
        test_sequence = [
            {"model": "nllb", "text": "Hello world from NLLB", "iteration": 1},
            {"model": "aya", "text": "Hello world from Aya", "iteration": 1},
            {"model": "nllb", "text": "Second NLLB translation", "iteration": 2}, 
            {"model": "aya", "text": "Second Aya translation", "iteration": 2},
            {"model": "nllb", "text": "Third NLLB translation", "iteration": 3},
            {"model": "aya", "text": "Third Aya translation", "iteration": 3}
        ]
        
        switch_times = []
        last_model = None
        
        for i, test_case in enumerate(test_sequence):
            print(f"Sequential test {i+1}: {test_case['model']} iteration {test_case['iteration']}")
            
            start_time = time.time()
            source_lang, target_lang = self.get_language_codes_for_model(test_case["model"])
                
            result = client.translate(
                text=test_case["text"],
                source_lang=source_lang,
                target_lang=target_lang,
                model=test_case["model"]
            )
            duration = time.time() - start_time
            
            assert result.status_code == 200, \
                f"Model switch to {test_case['model']} failed: {result.error}"
            
            data = result.response_data
            assert "translated_text" in data, f"Missing translation from {test_case['model']}"
            
            # Track switching times
            if last_model and last_model != test_case["model"]:
                switch_times.append(duration)
                print(f"  ✓ Switch from {last_model} to {test_case['model']}: {duration:.2f}s")
            else:
                print(f"  ✓ {test_case['model']} translation: {duration:.2f}s")
            
            last_model = test_case["model"]
        
        # Analyze switching performance
        if switch_times:
            avg_switch_time = sum(switch_times) / len(switch_times)
            max_switch_time = max(switch_times)
            print(f"✓ Model switching analysis: avg {avg_switch_time:.2f}s, max {max_switch_time:.2f}s")
            
            # Reasonable switching times (models should be kept in memory)
            assert avg_switch_time < 10.0, f"Average switch time too high: {avg_switch_time:.2f}s"
    
    def test_003_concurrent_same_model_requests(self, multimodel_service):
        """Test concurrent requests to the same model."""
        client = multimodel_service["client"]
        
        def translate_request(model_name, request_id):
            """Single translation request for concurrent testing."""
            text = f"Concurrent request {request_id} for {model_name}"
            
            start_time = time.time()
            result = client.translate(
                text=text,
                source_lang="eng_Latn",
                target_lang="spa_Latn", 
                model=model_name
            )
            duration = time.time() - start_time
            
            return {
                "request_id": request_id,
                "model": model_name,
                "duration": duration,
                "success": result.status_code == 200,
                "status_code": result.status_code,
                "error": result.error if result.status_code != 200 else None
            }
        
        # Test concurrent requests to NLLB
        print("Testing concurrent requests to NLLB...")
        nllb_results = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(translate_request, "nllb", i) 
                for i in range(5)
            ]
            
            for future in as_completed(futures):
                nllb_results.append(future.result())
        
        # Analyze NLLB concurrent performance
        nllb_successes = [r for r in nllb_results if r["success"]]
        nllb_failures = [r for r in nllb_results if not r["success"]]
        nllb_success_rate = len(nllb_successes) / len(nllb_results)
        
        assert nllb_success_rate >= 0.8, \
            f"NLLB concurrent success rate too low: {nllb_success_rate:.1%}"
        
        if nllb_successes:
            avg_nllb_duration = sum(r["duration"] for r in nllb_successes) / len(nllb_successes)
            print(f"✓ NLLB concurrent: {len(nllb_successes)}/{len(nllb_results)} successful, avg {avg_nllb_duration:.2f}s")
        
        # Test concurrent requests to Aya
        print("Testing concurrent requests to Aya...")
        aya_results = []
        with ThreadPoolExecutor(max_workers=2) as executor:  # Lower concurrency for 8B model
            futures = [
                executor.submit(translate_request, "aya", i)
                for i in range(3)  # Fewer requests for resource-intensive model
            ]
            
            for future in as_completed(futures):
                aya_results.append(future.result())
        
        # Analyze Aya concurrent performance
        aya_successes = [r for r in aya_results if r["success"]]
        aya_failures = [r for r in aya_results if not r["success"]]
        aya_success_rate = len(aya_successes) / len(aya_results)
        
        assert aya_success_rate >= 0.7, \
            f"Aya concurrent success rate too low: {aya_success_rate:.1%}"
        
        if aya_successes:
            avg_aya_duration = sum(r["duration"] for r in aya_successes) / len(aya_successes)
            print(f"✓ Aya concurrent: {len(aya_successes)}/{len(aya_results)} successful, avg {avg_aya_duration:.2f}s")
    
    def test_004_cross_model_concurrent_requests(self, multimodel_service):
        """Test concurrent requests across different models."""
        client = multimodel_service["client"]
        
        def mixed_translate_request(request_id):
            """Translation request that alternates between models."""
            model_name = "nllb" if request_id % 2 == 0 else "aya"
            text = f"Cross-model request {request_id} using {model_name}"
            
            start_time = time.time()
            result = client.translate(
                text=text,
                source_lang="eng_Latn",
                target_lang="spa_Latn",
                model=model_name
            )
            duration = time.time() - start_time
            
            return {
                "request_id": request_id,
                "model": model_name,
                "duration": duration,
                "success": result.status_code == 200,
                "status_code": result.status_code,
                "response_size": len(result.response_data.get("translated_text", "")) if result.status_code == 200 else 0
            }
        
        print("Testing cross-model concurrent requests...")
        
        # Execute mixed concurrent requests
        mixed_results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(mixed_translate_request, i)
                for i in range(8)  # 4 NLLB + 4 Aya requests
            ]
            
            for future in as_completed(futures):
                mixed_results.append(future.result())
        
        # Analyze cross-model performance
        nllb_mixed = [r for r in mixed_results if r["model"] == "nllb"]
        aya_mixed = [r for r in mixed_results if r["model"] == "aya"]
        
        total_successes = len([r for r in mixed_results if r["success"]])
        total_requests = len(mixed_results)
        overall_success_rate = total_successes / total_requests
        
        assert overall_success_rate >= 0.75, \
            f"Cross-model success rate too low: {overall_success_rate:.1%}"
        
        print(f"✓ Cross-model concurrent: {total_successes}/{total_requests} successful")
        print(f"  NLLB requests: {len([r for r in nllb_mixed if r['success']])}/{len(nllb_mixed)}")
        print(f"  Aya requests: {len([r for r in aya_mixed if r['success']])}/{len(aya_mixed)}")
    
    def test_005_model_comparison_same_input(self, multimodel_service):
        """Compare translation quality between models for same inputs."""
        client = multimodel_service["client"]
        
        comparison_texts = [
            "Technology is transforming our world rapidly.",
            "Education empowers individuals and communities globally.",
            "Healthcare innovations save millions of lives annually.",
            "Environmental protection requires international cooperation.",
            "Cultural diversity enriches human civilization."
        ]
        
        comparisons = []
        
        for text in comparison_texts:
            print(f"Comparing models for: '{text[:30]}...'")
            
            # Get NLLB translation
            nllb_start = time.time()
            nllb_result = client.translate(
                text=text,
                source_lang="eng_Latn",
                target_lang="spa_Latn",
                model="nllb"
            )
            nllb_duration = time.time() - nllb_start
            
            # Get Aya translation
            aya_start = time.time()
            aya_result = client.translate(
                text=text,
                source_lang="eng_Latn", 
                target_lang="spa_Latn",
                model="aya"
            )
            aya_duration = time.time() - aya_start
            
            comparison = {
                "input_text": text,
                "nllb": {
                    "success": nllb_result.status_code == 200,
                    "translation": nllb_result.response_data.get("translated_text", "") if nllb_result.status_code == 200 else None,
                    "duration": nllb_duration
                },
                "aya": {
                    "success": aya_result.status_code == 200,
                    "translation": aya_result.response_data.get("translated_text", "") if aya_result.status_code == 200 else None,
                    "duration": aya_duration
                }
            }
            
            comparisons.append(comparison)
            
            # Log comparison results
            if comparison["nllb"]["success"] and comparison["aya"]["success"]:
                print(f"  NLLB ({nllb_duration:.2f}s): {comparison['nllb']['translation']}")
                print(f"  Aya  ({aya_duration:.2f}s): {comparison['aya']['translation']}")
                
                # Basic quality check - translations should be different between models
                if comparison["nllb"]["translation"] != comparison["aya"]["translation"]:
                    print("  ✓ Models produce different translations (expected)")
                else:
                    print("  ⚠ Models produced identical translations")
            else:
                print(f"  ⚠ Translation failures - NLLB: {comparison['nllb']['success']}, Aya: {comparison['aya']['success']}")
        
        # Analyze comparison results
        successful_comparisons = [
            c for c in comparisons 
            if c["nllb"]["success"] and c["aya"]["success"]
        ]
        
        comparison_success_rate = len(successful_comparisons) / len(comparisons)
        assert comparison_success_rate >= 0.8, \
            f"Model comparison success rate too low: {comparison_success_rate:.1%}"
        
        if successful_comparisons:
            avg_nllb_time = sum(c["nllb"]["duration"] for c in successful_comparisons) / len(successful_comparisons)
            avg_aya_time = sum(c["aya"]["duration"] for c in successful_comparisons) / len(successful_comparisons)
            
            print(f"✓ Model comparison: {len(successful_comparisons)}/{len(comparisons)} successful")
            print(f"  Average NLLB time: {avg_nllb_time:.2f}s")
            print(f"  Average Aya time: {avg_aya_time:.2f}s")
        
        # Save comparison results
        comparison_file = "/tmp/model_comparison_results.json"
        with open(comparison_file, "w") as f:
            json.dump(comparisons, f, indent=2)
        print(f"✓ Comparison results saved to {comparison_file}")
    
    def test_006_resource_sharing_stability(self, multimodel_service):
        """Test resource sharing stability between models under load."""
        client = multimodel_service["client"]
        
        def sustained_mixed_load(duration_seconds=60):
            """Run sustained mixed load across both models."""
            end_time = time.time() + duration_seconds
            results = []
            request_count = 0
            
            while time.time() < end_time:
                request_count += 1
                model_name = "nllb" if request_count % 3 != 0 else "aya"  # 2:1 ratio favoring NLLB
                text = f"Resource sharing test {request_count} using {model_name}"
                
                start_time = time.time()
                result = client.translate(
                    text=text,
                    source_lang="eng_Latn",
                    target_lang="spa_Latn",
                    model=model_name
                )
                duration = time.time() - start_time
                
                results.append({
                    "request_id": request_count,
                    "model": model_name,
                    "success": result.status_code == 200,
                    "duration": duration,
                    "timestamp": time.time()
                })
                
                # Brief pause to simulate realistic usage
                time.sleep(0.5)
            
            return results
        
        print("Testing resource sharing stability (60 seconds of mixed load)...")
        
        stability_results = sustained_mixed_load(60)
        
        # Analyze resource sharing results
        total_requests = len(stability_results)
        successful_requests = len([r for r in stability_results if r["success"]])
        nllb_requests = [r for r in stability_results if r["model"] == "nllb"]
        aya_requests = [r for r in stability_results if r["model"] == "aya"]
        
        success_rate = successful_requests / total_requests
        nllb_success_rate = len([r for r in nllb_requests if r["success"]]) / len(nllb_requests) if nllb_requests else 0
        aya_success_rate = len([r for r in aya_requests if r["success"]]) / len(aya_requests) if aya_requests else 0
        
        assert success_rate >= 0.8, f"Resource sharing success rate too low: {success_rate:.1%}"
        assert nllb_success_rate >= 0.85, f"NLLB success rate under load too low: {nllb_success_rate:.1%}"
        assert aya_success_rate >= 0.7, f"Aya success rate under load too low: {aya_success_rate:.1%}"
        
        print(f"✓ Resource sharing stability: {successful_requests}/{total_requests} successful")
        print(f"  NLLB performance: {len([r for r in nllb_requests if r['success']])}/{len(nllb_requests)} ({nllb_success_rate:.1%})")
        print(f"  Aya performance: {len([r for r in aya_requests if r['success']])}/{len(aya_requests)} ({aya_success_rate:.1%})")
        
        # Check for performance degradation over time
        if successful_requests >= 10:
            first_half = [r for r in stability_results[:len(stability_results)//2] if r["success"]]
            second_half = [r for r in stability_results[len(stability_results)//2:] if r["success"]]
            
            if first_half and second_half:
                first_half_avg = sum(r["duration"] for r in first_half) / len(first_half)
                second_half_avg = sum(r["duration"] for r in second_half) / len(second_half)
                degradation = (second_half_avg - first_half_avg) / first_half_avg
                
                print(f"  Performance change over time: {degradation:+.1%}")
                
                # Allow for some performance variation but not significant degradation
                assert degradation < 0.5, f"Performance degraded too much over time: {degradation:+.1%}"
    
    def test_007_memory_pressure_recovery(self, multimodel_service):
        """Test recovery from memory pressure scenarios."""
        client = multimodel_service["client"]
        
        # Create memory pressure with large batch requests
        large_texts = [
            "Memory pressure test with substantial text content. " * 50,  # ~2500 chars
            "Testing system resilience under resource constraints. " * 75,  # ~4000 chars
            "Evaluating recovery mechanisms during high memory usage. " * 100  # ~5500 chars
        ]
        
        pressure_results = []
        
        print("Creating memory pressure with large batch requests...")
        
        # Send large requests to both models simultaneously
        for i, text in enumerate(large_texts):
            print(f"Memory pressure test {i+1}/3 (text length: {len(text)} chars)")
            
            # Send to both models in quick succession
            nllb_result = client.translate(
                text=text,
                source_lang="eng_Latn",
                target_lang="spa_Latn",
                model="nllb"
            )
            
            aya_result = client.translate(
                text=text,
                source_lang="eng_Latn",
                target_lang="fra_Latn",
                model="aya"
            )
            
            pressure_results.extend([
                {"model": "nllb", "success": nllb_result.status_code == 200, "text_length": len(text)},
                {"model": "aya", "success": aya_result.status_code == 200, "text_length": len(text)}
            ])
        
        # Test recovery with normal requests
        print("Testing recovery with normal-sized requests...")
        
        recovery_results = []
        for i in range(6):  # 3 requests per model
            model_name = "nllb" if i % 2 == 0 else "aya"
            recovery_text = f"Recovery test {i+1} for {model_name}"
            
            result = client.translate(
                text=recovery_text,
                source_lang="eng_Latn",
                target_lang="spa_Latn",
                model=model_name
            )
            
            recovery_results.append({
                "model": model_name,
                "success": result.status_code == 200
            })
        
        # Analyze memory pressure and recovery
        pressure_successes = len([r for r in pressure_results if r["success"]])
        pressure_rate = pressure_successes / len(pressure_results)
        
        recovery_successes = len([r for r in recovery_results if r["success"]])
        recovery_rate = recovery_successes / len(recovery_results)
        
        # Memory pressure may cause some failures, but recovery should be good
        assert recovery_rate >= 0.8, f"Recovery rate too low: {recovery_rate:.1%}"
        
        print(f"✓ Memory pressure handling: {pressure_successes}/{len(pressure_results)} pressure tests successful")
        print(f"✓ Recovery verification: {recovery_successes}/{len(recovery_results)} recovery tests successful")
        
        # Verify both models are still responsive
        final_nllb = client.translate("Final NLLB test", "eng_Latn", "spa_Latn", "nllb")
        final_aya = client.translate("Final Aya test", "eng_Latn", "spa_Latn", "aya")
        
        assert final_nllb.status_code == 200, "NLLB not responsive after memory pressure"
        assert final_aya.status_code == 200, "Aya not responsive after memory pressure"
        
        print("✓ Both models remain responsive after memory pressure testing")
    
    def test_008_comprehensive_multimodel_benchmark(self, multimodel_service):
        """Comprehensive benchmark of multi-model system performance."""
        client = multimodel_service["client"]
        
        benchmark_scenarios = [
            {
                "name": "Sequential Light Load",
                "description": "Alternating light requests between models",
                "requests": [
                    {"model": "nllb", "text": "Light load test 1"},
                    {"model": "aya", "text": "Light load test 2"}, 
                    {"model": "nllb", "text": "Light load test 3"},
                    {"model": "aya", "text": "Light load test 4"}
                ]
            },
            {
                "name": "NLLB Heavy Load",
                "description": "Multiple consecutive NLLB requests",
                "requests": [
                    {"model": "nllb", "text": f"NLLB heavy load test {i}"} 
                    for i in range(1, 6)
                ]
            },
            {
                "name": "Aya Focused Test",
                "description": "Multiple Aya requests with varying complexity",
                "requests": [
                    {"model": "aya", "text": "Simple Aya test"},
                    {"model": "aya", "text": "Complex technological advancement discussion for Aya evaluation"},
                    {"model": "aya", "text": "Medium complexity Aya translation request"}
                ]
            }
        ]
        
        benchmark_results = {
            "test_timestamp": time.time(),
            "scenarios": []
        }
        
        for scenario in benchmark_scenarios:
            print(f"Running benchmark scenario: {scenario['name']}")
            
            scenario_start = time.time()
            scenario_results = []
            
            for req in scenario["requests"]:
                start_time = time.time()
                result = client.translate(
                    text=req["text"],
                    source_lang="eng_Latn",
                    target_lang="spa_Latn",
                    model=req["model"]
                )
                duration = time.time() - start_time
                
                scenario_results.append({
                    "model": req["model"],
                    "success": result.status_code == 200,
                    "duration": duration,
                    "text_length": len(req["text"])
                })
            
            scenario_duration = time.time() - scenario_start
            successful_requests = len([r for r in scenario_results if r["success"]])
            
            scenario_summary = {
                "name": scenario["name"],
                "description": scenario["description"],
                "total_requests": len(scenario_results),
                "successful_requests": successful_requests,
                "success_rate": successful_requests / len(scenario_results),
                "total_duration": scenario_duration,
                "avg_request_duration": sum(r["duration"] for r in scenario_results) / len(scenario_results),
                "results": scenario_results
            }
            
            benchmark_results["scenarios"].append(scenario_summary)
            
            print(f"  ✓ {scenario['name']}: {successful_requests}/{len(scenario_results)} successful, " +
                  f"{scenario_summary['avg_request_duration']:.2f}s avg")
        
        # Overall benchmark analysis
        total_requests = sum(s["total_requests"] for s in benchmark_results["scenarios"])
        total_successful = sum(s["successful_requests"] for s in benchmark_results["scenarios"])
        overall_success_rate = total_successful / total_requests
        
        assert overall_success_rate >= 0.8, \
            f"Overall benchmark success rate too low: {overall_success_rate:.1%}"
        
        # Save comprehensive benchmark results
        benchmark_file = "/tmp/multimodel_benchmark_results.json"
        with open(benchmark_file, "w") as f:
            json.dump(benchmark_results, f, indent=2)
        
        print(f"✓ Multi-model benchmark completed: {total_successful}/{total_requests} successful")
        print(f"  Overall success rate: {overall_success_rate:.1%}")
        print(f"  Results saved to: {benchmark_file}")
        
        print("✓ Multi-model interaction test suite PASSED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])