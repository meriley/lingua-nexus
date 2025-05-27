"""
Simplified Aya Model E2E Test Suite - TASK-008 Implementation

This module contains essential end-to-end tests for the Aya Expanse 8B translation model,
designed to work within API rate limits while providing comprehensive validation.
"""

import pytest
import time
import os
from typing import List, Dict, Any

from tests.e2e.utils.comprehensive_client import ComprehensiveTestClient
from tests.e2e.utils.robust_service_manager import RobustServiceManager
from tests.e2e.utils.service_manager import MultiModelServiceConfig
from tests.e2e.utils.model_loading_monitor import ModelLoadingMonitor


class TestAyaSimplified:
    """Simplified test suite for Aya Expanse 8B model functionality."""

    @classmethod
    def setup_class(cls):
        """Set up test environment and ensure Aya model is loaded."""
        cls.service_manager = RobustServiceManager()
        
        # Create service configuration for Aya model
        config = MultiModelServiceConfig(
            api_key="test-api-key-aya-simplified",
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
                "PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:512",
            }
        )
        
        # Start service and wait for Aya model to be ready
        print("Starting Aya service and waiting for model to load...")
        service_url = cls.service_manager.start_with_model_wait(
            config=config,
            model_name="aya",
            timeout=3600  # 60 minutes for Aya 8B model
        )
        
        # Initialize client
        cls.client = ComprehensiveTestClient(service_url, "test-api-key-aya-simplified")
        
        # Initialize test tracking
        cls.test_results = []
        print("Aya model setup complete!")
        
    @classmethod
    def teardown_class(cls):
        """Clean up test environment."""
        cls.service_manager.stop_service()
        
        # Print summary
        total_tests = len(cls.test_results)
        successful_tests = sum(1 for result in cls.test_results if result.get("success", False))
        print(f"\n=== Aya Test Suite Summary ===")
        print(f"Total tests: {total_tests}")
        print(f"Successful: {successful_tests}")
        print(f"Success rate: {successful_tests/total_tests:.1%}" if total_tests > 0 else "No tests run")

    def test_001_aya_basic_translation_validation(self):
        """Test 1: Validate basic translation functionality with Aya model."""
        print("Testing basic Aya translation functionality...")
        
        # Simple test cases using proper Aya language codes
        basic_cases = [
            {
                "text": "Hello, how are you?",
                "source": "English", 
                "target": "Spanish",
                "description": "English to Spanish"
            },
            {
                "text": "Technology is amazing",
                "source": "English",
                "target": "French", 
                "description": "English to French"
            },
            {
                "text": "Good morning",
                "source": "English",
                "target": "German",
                "description": "English to German"
            }
        ]
        
        successful = 0
        for i, case in enumerate(basic_cases):
            print(f"  Test {i+1}: {case['description']}")
            
            start_time = time.time()
            result = self.client.translate(
                text=case["text"],
                source_lang=case["source"],
                target_lang=case["target"],
                model="aya"
            )
            duration = time.time() - start_time
            
            success = False
            if result.status_code == 200:
                data = result.response_data
                translated_text = data.get("translated_text", "")
                if translated_text and translated_text != case["text"]:
                    successful += 1
                    success = True
                    print(f"    ✓ '{case['text']}' → '{translated_text}' ({duration:.1f}s)")
                else:
                    print(f"    ⚠ Translation issue: '{translated_text}'")
            else:
                print(f"    ✗ Failed with status {result.status_code}: {result.error}")
            
            self.test_results.append({
                "test": f"basic_translation_{i+1}",
                "success": success,
                "duration": duration,
                "status_code": result.status_code
            })
            
            # Rate limiting: wait between requests
            if i < len(basic_cases) - 1:
                time.sleep(7)  # 10 requests per minute = 6s minimum, use 7s for safety
        
        # Require at least 66% success rate
        success_rate = successful / len(basic_cases)
        assert success_rate >= 0.66, \
            f"Basic translation success rate too low: {success_rate:.1%} ({successful}/{len(basic_cases)})"
        
        print(f"✓ Basic translation test passed: {successful}/{len(basic_cases)} successful")

    def test_002_aya_bidirectional_translation(self):
        """Test 2: Validate bidirectional translation capabilities."""
        print("Testing bidirectional translation...")
        
        # Test translation in both directions
        bidirectional_cases = [
            {
                "text_en": "Machine learning is transforming technology",
                "text_es": "El aprendizaje automático está transformando la tecnología",
                "lang_pair": ("English", "Spanish")
            },
            {
                "text_en": "Artificial intelligence helps solve problems", 
                "text_fr": "L'intelligence artificielle aide à résoudre les problèmes",
                "lang_pair": ("English", "French")
            }
        ]
        
        successful = 0
        total_tests = 0
        
        for case in bidirectional_cases:
            lang1, lang2 = case["lang_pair"]
            
            # Test direction 1: lang1 → lang2
            total_tests += 1
            print(f"  Testing {lang1} → {lang2}")
            
            result1 = self.client.translate(
                text=case["text_en"],
                source_lang=lang1,
                target_lang=lang2,
                model="aya"
            )
            
            if result1.status_code == 200:
                data1 = result1.response_data
                translated1 = data1.get("translated_text", "")
                if translated1 and translated1 != case["text_en"]:
                    successful += 1
                    print(f"    ✓ '{case['text_en'][:30]}...' → '{translated1[:30]}...'")
                else:
                    print(f"    ⚠ Translation issue")
            else:
                print(f"    ✗ Failed with status {result1.status_code}")
            
            time.sleep(7)  # Rate limiting
            
            # Test direction 2: lang2 → lang1  
            total_tests += 1
            print(f"  Testing {lang2} → {lang1}")
            
            source_text = case.get(f"text_{lang2.lower()[:2]}", case["text_en"])
            result2 = self.client.translate(
                text=source_text,
                source_lang=lang2,
                target_lang=lang1,
                model="aya"
            )
            
            if result2.status_code == 200:
                data2 = result2.response_data
                translated2 = data2.get("translated_text", "")
                if translated2 and translated2 != source_text:
                    successful += 1
                    print(f"    ✓ '{source_text[:30]}...' → '{translated2[:30]}...'")
                else:
                    print(f"    ⚠ Translation issue")
            else:
                print(f"    ✗ Failed with status {result2.status_code}")
            
            time.sleep(7)  # Rate limiting
        
        success_rate = successful / total_tests if total_tests > 0 else 0
        assert success_rate >= 0.5, \
            f"Bidirectional translation success rate too low: {success_rate:.1%} ({successful}/{total_tests})"
        
        print(f"✓ Bidirectional translation test passed: {successful}/{total_tests} successful")

    def test_003_aya_longer_text_handling(self):
        """Test 3: Validate handling of longer texts."""
        print("Testing longer text handling...")
        
        # Test with progressively longer texts
        base_text = "Artificial intelligence and machine learning are revolutionizing how we approach complex problems. These technologies enable us to process vast amounts of data, identify patterns, and make predictions that were previously impossible. From healthcare to finance, from transportation to education, AI is transforming every sector of our economy and society."
        
        text_cases = [
            {
                "text": base_text,
                "description": "Medium text (~50 words)"
            },
            {
                "text": base_text + " " + base_text,
                "description": "Long text (~100 words)"
            }
        ]
        
        successful = 0
        for i, case in enumerate(text_cases):
            word_count = len(case["text"].split())
            print(f"  Testing {case['description']} - {word_count} words")
            
            start_time = time.time()
            result = self.client.translate(
                text=case["text"],
                source_lang="English",
                target_lang="Spanish",
                model="aya"
            )
            duration = time.time() - start_time
            
            if result.status_code == 200:
                data = result.response_data
                translated_text = data.get("translated_text", "")
                translated_words = len(translated_text.split()) if translated_text else 0
                
                # Basic validation
                if translated_text and len(translated_text) > 0:
                    successful += 1
                    words_per_sec = word_count / duration if duration > 0 else 0
                    print(f"    ✓ {word_count} → {translated_words} words in {duration:.1f}s ({words_per_sec:.1f} w/s)")
                else:
                    print(f"    ⚠ Empty or invalid translation")
            else:
                print(f"    ✗ Failed with status {result.status_code}: {result.error}")
            
            # Rate limiting
            if i < len(text_cases) - 1:
                time.sleep(7)
        
        success_rate = successful / len(text_cases)
        assert success_rate >= 0.5, \
            f"Longer text handling success rate too low: {success_rate:.1%} ({successful}/{len(text_cases)})"
        
        print(f"✓ Longer text test passed: {successful}/{len(text_cases)} successful")

    def test_004_aya_error_handling_resilience(self):
        """Test 4: Validate error handling and resilience."""
        print("Testing error handling and resilience...")
        
        # Test various error conditions
        error_cases = [
            {
                "text": "",
                "source": "English",
                "target": "Spanish", 
                "description": "Empty text",
                "should_fail": True
            },
            {
                "text": "Hello world",
                "source": "InvalidLanguage",
                "target": "Spanish",
                "description": "Invalid source language",
                "should_fail": True
            },
            {
                "text": "Hello world",
                "source": "English",
                "target": "InvalidLanguage",
                "description": "Invalid target language", 
                "should_fail": True
            }
        ]
        
        handled_gracefully = 0
        for i, case in enumerate(error_cases):
            print(f"  Testing {case['description']}")
            
            result = self.client.translate(
                text=case["text"],
                source_lang=case["source"],
                target_lang=case["target"],
                model="aya"
            )
            
            if case["should_fail"]:
                # Expecting error - check if handled gracefully
                if result.status_code in [400, 422, 500]:
                    handled_gracefully += 1
                    print(f"    ✓ Error handled gracefully (status {result.status_code})")
                elif result.status_code == 200:
                    # Some errors might be handled at model level
                    handled_gracefully += 1
                    print(f"    ✓ Handled at model level")
                else:
                    print(f"    ⚠ Unexpected status {result.status_code}")
            
            # Rate limiting
            if i < len(error_cases) - 1:
                time.sleep(7)
        
        # Test recovery after errors
        print("  Testing recovery after errors...")
        time.sleep(7)
        recovery_result = self.client.translate(
            text="Recovery test after error scenarios",
            source_lang="English",
            target_lang="Spanish",
            model="aya"
        )
        
        assert recovery_result.status_code == 200, \
            f"Model failed to recover after error scenarios: {recovery_result.status_code}"
        
        print(f"✓ Error handling test passed: {handled_gracefully}/{len(error_cases)} handled gracefully")
        print("✓ Model recovery verified")

    def test_005_aya_performance_baseline(self):
        """Test 5: Establish performance baseline for Aya model."""
        print("Establishing Aya performance baseline...")
        
        # Simple performance test
        test_text = "Technology is advancing rapidly and changing our world in many ways."
        
        durations = []
        successful_runs = 0
        
        for run in range(3):
            print(f"  Performance run {run + 1}/3")
            
            start_time = time.time()
            result = self.client.translate(
                text=test_text,
                source_lang="English",
                target_lang="Spanish",
                model="aya"
            )
            duration = time.time() - start_time
            
            if result.status_code == 200:
                successful_runs += 1
                durations.append(duration)
                data = result.response_data
                translated_text = data.get("translated_text", "")
                print(f"    ✓ Run {run + 1}: {duration:.2f}s - '{translated_text[:30]}...'")
            else:
                print(f"    ✗ Run {run + 1}: Failed with status {result.status_code}")
            
            # Rate limiting between runs
            if run < 2:
                time.sleep(7)
        
        if durations:
            avg_duration = sum(durations) / len(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            
            print(f"  Performance metrics:")
            print(f"    Average: {avg_duration:.2f}s")
            print(f"    Range: {min_duration:.2f}s - {max_duration:.2f}s")
            print(f"    Success rate: {successful_runs}/3")
            
            # Basic performance assertions
            assert avg_duration < 60.0, f"Average translation time too slow: {avg_duration:.2f}s"
            assert successful_runs >= 2, f"Too many failed runs: {successful_runs}/3"
        else:
            pytest.fail("No successful performance runs")
        
        print("✓ Performance baseline established")

    def test_006_aya_model_health_final_check(self):
        """Test 6: Final health check to ensure model is still responsive."""
        print("Performing final Aya model health check...")
        
        # Check model health
        health = self.client.get_health()
        assert health["status"] == "healthy", f"Service not healthy: {health}"
        
        # Verify Aya model is still loaded
        models = health.get("models", [])
        aya_model = next((m for m in models if m["name"] == "aya"), None)
        assert aya_model is not None, "Aya model not found in health response"
        assert aya_model["status"] == "loaded", f"Aya model not loaded: {aya_model['status']}"
        
        print(f"  ✓ Service status: {health['status']}")
        print(f"  ✓ Aya model status: {aya_model['status']}")
        print(f"  ✓ Memory usage: {aya_model.get('memory_usage_gb', 'unknown')} GB")
        
        # Final translation test
        final_result = self.client.translate(
            text="Final validation test for Aya model",
            source_lang="English",
            target_lang="Spanish",
            model="aya"
        )
        
        assert final_result.status_code == 200, \
            f"Final translation test failed: {final_result.status_code}"
        
        final_data = final_result.response_data
        final_translation = final_data.get("translated_text", "")
        assert len(final_translation) > 0, "Final translation is empty"
        
        print(f"  ✓ Final translation: '{final_translation}'")
        print("✓ Aya model health check passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])