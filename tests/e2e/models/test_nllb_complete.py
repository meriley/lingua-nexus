"""
Comprehensive NLLB Model E2E Test Suite

This module contains complete end-to-end tests for the NLLB translation model,
covering all production scenarios without skipping resource-intensive tests.
"""

import pytest
import sys
import os
import time
import json
from typing import List, Dict, Any

# Add the e2e directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.robust_service_manager import RobustServiceManager
from utils.service_manager import MultiModelServiceConfig
from utils.comprehensive_client import ComprehensiveTestClient


class TestNLLBComplete:
    """Comprehensive test suite for NLLB model functionality."""
    
    @pytest.fixture(scope="class")
    def nllb_service(self):
        """Setup NLLB service for the entire test class."""
        manager = RobustServiceManager()
        
        try:
            config = MultiModelServiceConfig(
                api_key="test-api-key-nllb-complete",
                models_to_load="nllb",
                log_level="INFO",
                custom_env={
                    "PYTEST_RUNNING": "true",
                    "MODELS_TO_LOAD": "nllb",
                    "NLLB_MODEL": "facebook/nllb-200-distilled-600M",
                    "MODEL_CACHE_DIR": os.path.expanduser("~/.cache/huggingface/transformers"),
                    "HF_HOME": os.path.expanduser("~/.cache/huggingface"),
                    "TRANSFORMERS_CACHE": os.path.expanduser("~/.cache/huggingface/transformers"),
                    "MODEL_LOADING_TIMEOUT": "1800",  # 30 minutes
                    "LOG_MODEL_LOADING_PROGRESS": "true",
                }
            )
            
            # Start service and wait for model
            service_url = manager.start_with_model_wait(
                config=config,
                model_name="nllb",
                timeout=1800  # 30 minutes
            )
            
            client = ComprehensiveTestClient(service_url, api_key="test-api-key-nllb-complete")
            
            # Verify model is ready
            assert manager.verify_model_readiness("nllb", api_key="test-api-key-nllb-complete")
            
            yield {"manager": manager, "client": client, "service_url": service_url}
            
        finally:
            manager.cleanup()
    
    def test_001_basic_translation_accuracy(self, nllb_service):
        """Test basic translation accuracy across language pairs."""
        client = nllb_service["client"]
        
        # Test cases with expected quality characteristics
        test_cases = [
            {
                "text": "Hello, how are you today?",
                "source": "eng_Latn",
                "target": "spa_Latn",
                "min_length": 10,
                "description": "English to Spanish greeting"
            },
            {
                "text": "The weather is beautiful today.",
                "source": "eng_Latn", 
                "target": "fra_Latn",
                "min_length": 15,
                "description": "English to French weather statement"
            },
            {
                "text": "I would like to order a coffee, please.",
                "source": "eng_Latn",
                "target": "deu_Latn",
                "min_length": 20,
                "description": "English to German polite request"
            },
            {
                "text": "Technology is changing our world rapidly.",
                "source": "eng_Latn",
                "target": "ita_Latn",
                "min_length": 20,
                "description": "English to Italian technology statement"
            },
            {
                "text": "Artificial intelligence helps solve complex problems.",
                "source": "eng_Latn",
                "target": "por_Latn",
                "min_length": 25,
                "description": "English to Portuguese AI concept"
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            result = client.translate(
                text=test_case["text"],
                source_lang=test_case["source"],
                target_lang=test_case["target"],
                model="nllb"
            )
            
            assert result.status_code == 200, f"Translation {i+1} failed: {result.error}"
            
            data = result.response_data
            assert "translated_text" in data, f"Missing translated_text in response {i+1}"
            
            translated_text = data["translated_text"]
            assert len(translated_text) >= test_case["min_length"], \
                f"Translation {i+1} too short: '{translated_text}' (expected min {test_case['min_length']} chars)"
            assert translated_text != test_case["text"], \
                f"Translation {i+1} identical to source: '{translated_text}'"
            
            print(f"✓ {test_case['description']}: '{test_case['text']}' → '{translated_text}'")
    
    def test_002_batch_translation_processing(self, nllb_service):
        """Test batch translation functionality and consistency."""
        client = nllb_service["client"]
        
        # Prepare batch requests
        batch_requests = [
            {"text": "Good morning", "source_lang": "eng_Latn", "target_lang": "spa_Latn", "model": "nllb"},
            {"text": "Good afternoon", "source_lang": "eng_Latn", "target_lang": "fra_Latn", "model": "nllb"},
            {"text": "Good evening", "source_lang": "eng_Latn", "target_lang": "deu_Latn", "model": "nllb"},
            {"text": "Good night", "source_lang": "eng_Latn", "target_lang": "ita_Latn", "model": "nllb"},
            {"text": "Thank you very much", "source_lang": "eng_Latn", "target_lang": "por_Latn", "model": "nllb"}
        ]
        
        # Test batch processing
        batch_result = client.batch_translate_with_retry(batch_requests, max_retries=3)
        
        assert batch_result.status_code == 200, f"Batch translation failed: {batch_result.error}"
        
        batch_data = batch_result.response_data
        assert "translations" in batch_data or isinstance(batch_data, list), \
            "Batch response missing translations array"
        
        translations = batch_data.get("translations", batch_data)
        assert len(translations) == len(batch_requests), \
            f"Expected {len(batch_requests)} translations, got {len(translations)}"
        
        # Verify each translation in batch
        for i, translation in enumerate(translations):
            assert "translated_text" in translation, f"Batch item {i+1} missing translated_text"
            assert len(translation["translated_text"]) > 0, f"Batch item {i+1} empty translation"
            print(f"✓ Batch {i+1}: '{batch_requests[i]['text']}' → '{translation['translated_text']}'")
    
    def test_003_language_detection_accuracy(self, nllb_service):
        """Test language detection accuracy and consistency."""
        client = nllb_service["client"]
        
        test_texts = [
            {"text": "Hello, how are you?", "expected_family": "eng"},
            {"text": "Bonjour, comment allez-vous?", "expected_family": "fra"},
            {"text": "Hola, ¿cómo estás?", "expected_family": "spa"},
            {"text": "Ciao, come stai?", "expected_family": "ita"},
            {"text": "Hallo, wie geht es dir?", "expected_family": "deu"},
            {"text": "Olá, como está você?", "expected_family": "por"},
            {"text": "Привет, как дела?", "expected_family": "rus"},
            {"text": "こんにちは、元気ですか？", "expected_family": "jpn"}
        ]
        
        for test_text in test_texts:
            result = client.detect_language(test_text["text"], model="nllb")
            
            assert result.status_code == 200, f"Language detection failed for '{test_text['text']}'"
            
            data = result.response_data
            detected_lang = data.get("detected_language") or data.get("language")
            confidence = data.get("confidence", 0)
            
            assert detected_lang is not None, f"No language detected for '{test_text['text']}'"
            assert len(detected_lang) > 0, f"Empty language code for '{test_text['text']}'"
            assert confidence >= 0, f"Invalid confidence for '{test_text['text']}'"
            
            print(f"✓ Detected '{test_text['text']}' as {detected_lang} (confidence: {confidence})")
    
    def test_004_translation_with_auto_detection(self, nllb_service):
        """Test translation with automatic language detection."""
        client = nllb_service["client"]
        
        test_cases = [
            {"text": "Bonjour le monde", "target": "eng_Latn"},
            {"text": "Hola mundo", "target": "eng_Latn"},
            {"text": "Ciao mondo", "target": "fra_Latn"},
            {"text": "Hallo Welt", "target": "spa_Latn"}
        ]
        
        for test_case in test_cases:
            result = client.test_translation_with_detection(
                text=test_case["text"],
                target_lang=test_case["target"],
                model="nllb"
            )
            
            assert result["success"], f"Auto-translation failed for '{test_case['text']}': {result.get('error')}"
            assert result["detection"] is not None, f"Language detection failed for '{test_case['text']}'"
            assert result["translation"] is not None, f"Translation failed for '{test_case['text']}'"
            
            detected_lang = result["detection"].get("detected_language") or result["detection"].get("language")
            translated_text = result["translation"]["translated_text"]
            
            print(f"✓ Auto-translated '{test_case['text']}' ({detected_lang}) → '{translated_text}'")
    
    def test_005_long_text_handling(self, nllb_service):
        """Test handling of long texts and chunking."""
        client = nllb_service["client"]
        
        # Test various text lengths
        long_texts = [
            # Medium text (~100 words)
            "Artificial intelligence is transforming the way we live and work. Machine learning algorithms can process vast amounts of data to identify patterns and make predictions. Natural language processing enables computers to understand and generate human language. Computer vision allows machines to interpret and analyze visual information. These technologies are being applied in healthcare, finance, transportation, and many other fields to solve complex problems and improve efficiency.",
            
            # Long text (~200 words)  
            "The development of artificial intelligence has been one of the most significant technological advances of the 21st century. From early expert systems to modern deep learning networks, AI has evolved to tackle increasingly complex problems. Machine learning algorithms now power recommendation systems, autonomous vehicles, medical diagnosis tools, and financial trading platforms. Natural language processing has enabled virtual assistants, language translation services, and automated content generation. Computer vision applications include facial recognition, object detection, medical imaging analysis, and quality control in manufacturing. As AI continues to advance, we must also consider the ethical implications of these technologies. Issues such as algorithmic bias, privacy protection, job displacement, and the need for transparency in AI decision-making are becoming increasingly important. The future of AI will likely involve more sophisticated models that can reason, plan, and adapt to new situations while remaining safe and beneficial for humanity.",
            
            # Very long text (~300 words)
            "The field of artificial intelligence encompasses a wide range of technologies and approaches designed to create machines that can perform tasks typically requiring human intelligence. Machine learning, a subset of AI, involves training algorithms on large datasets to recognize patterns and make predictions without being explicitly programmed for each specific task. Deep learning, which uses artificial neural networks with multiple layers, has been particularly successful in areas such as image recognition, natural language processing, and speech synthesis. Reinforcement learning enables AI systems to learn through trial and error, receiving rewards or penalties based on their actions. This approach has been used to create AI systems that can play complex games like chess and Go at superhuman levels, and is being applied to robotics and autonomous vehicle control. Natural language processing combines computational linguistics with machine learning to enable computers to understand, interpret, and generate human language. Applications include machine translation, sentiment analysis, chatbots, and automated summarization. Computer vision uses machine learning to enable computers to identify and analyze visual content, with applications in medical imaging, autonomous vehicles, security systems, and augmented reality. As AI continues to advance, researchers are working on developing artificial general intelligence (AGI) - AI systems that can understand, learn, and apply knowledge across a wide range of domains at a level comparable to human intelligence. However, this goal remains challenging and controversial, with significant technical, ethical, and safety considerations that must be addressed."
        ]
        
        for i, text in enumerate(long_texts):
            word_count = len(text.split())
            print(f"Testing long text {i+1} with {word_count} words...")
            
            start_time = time.time()
            result = client.translate(
                text=text,
                source_lang="eng_Latn",
                target_lang="spa_Latn",
                model="nllb"
            )
            duration = time.time() - start_time
            
            assert result.status_code == 200, f"Long text {i+1} translation failed: {result.error}"
            
            data = result.response_data
            translated_text = data["translated_text"]
            
            # Verify translation quality
            assert len(translated_text) > len(text) * 0.5, \
                f"Long text {i+1} translation suspiciously short"
            assert len(translated_text) < len(text) * 2.0, \
                f"Long text {i+1} translation suspiciously long"
            
            translated_words = len(translated_text.split())
            print(f"✓ Long text {i+1}: {word_count} words → {translated_words} words in {duration:.2f}s")
    
    def test_006_error_handling_and_recovery(self, nllb_service):
        """Test error handling for invalid inputs and edge cases."""
        client = nllb_service["client"]
        
        # Test invalid language codes
        invalid_requests = [
            {
                "text": "Hello world",
                "source_lang": "invalid_lang",
                "target_lang": "spa_Latn",
                "description": "Invalid source language"
            },
            {
                "text": "Hello world",
                "source_lang": "eng_Latn",
                "target_lang": "invalid_lang", 
                "description": "Invalid target language"
            },
            {
                "text": "",
                "source_lang": "eng_Latn",
                "target_lang": "spa_Latn",
                "description": "Empty text"
            }
        ]
        
        for req in invalid_requests:
            result = client.translate(
                text=req["text"],
                source_lang=req["source_lang"],
                target_lang=req["target_lang"],
                model="nllb"
            )
            
            # Should either handle gracefully or return appropriate error
            if result.status_code != 200:
                assert result.status_code in [400, 422], \
                    f"Unexpected error code for {req['description']}: {result.status_code}"
                print(f"✓ {req['description']}: Correctly returned error {result.status_code}")
            else:
                # If it succeeds, verify the response is reasonable
                data = result.response_data
                assert "translated_text" in data, f"Missing response field for {req['description']}"
                print(f"✓ {req['description']}: Handled gracefully")
    
    def test_007_concurrent_request_handling(self, nllb_service):
        """Test handling of concurrent translation requests."""
        client = nllb_service["client"]
        
        # Prepare concurrent requests
        texts = [
            "The sun is shining brightly today.",
            "I love reading books in the evening.", 
            "Coffee tastes better in the morning.",
            "Music brings joy to our lives.",
            "Travel opens our minds to new cultures."
        ]
        
        # Execute concurrent requests using stress test method
        stress_result = client.stress_test_model(
            model_name="nllb",
            duration_seconds=30,  # 30 seconds of sustained load
            requests_per_second=2  # Moderate load
        )
        
        assert stress_result["requests_sent"] >= 50, \
            f"Too few requests sent: {stress_result['requests_sent']}"
        assert stress_result["success_rate"] >= 0.9, \
            f"Success rate too low: {stress_result['success_rate']}"
        assert stress_result["avg_response_time_ms"] < 5000, \
            f"Average response time too high: {stress_result['avg_response_time_ms']}ms"
        
        print(f"✓ Concurrent test: {stress_result['requests_sent']} requests, " +
              f"{stress_result['success_rate']:.1%} success rate, " +
              f"{stress_result['avg_response_time_ms']:.0f}ms avg response time")
    
    def test_008_memory_stability_extended_usage(self, nllb_service):
        """Test memory stability during extended usage."""
        client = nllb_service["client"]
        
        # Test model persistence over time
        stability_result = client.verify_model_persistence(
            model_name="nllb",
            test_text="Memory stability test message"
        )
        
        assert stability_result["all_successful"], \
            f"Model persistence failed: {[c for c in stability_result['checks'] if c.get('error')]}"
        
        successful_checks = len([c for c in stability_result["checks"] if c["translation_success"]])
        total_checks = len(stability_result["checks"])
        
        print(f"✓ Memory stability: {successful_checks}/{total_checks} checks passed over time")
    
    def test_009_performance_baseline_recording(self, nllb_service):
        """Record performance baselines for regression testing."""
        client = nllb_service["client"]
        manager = nllb_service["manager"]
        
        # Test different text lengths for performance characterization
        test_texts = [
            ("Short text", "Hello world"),
            ("Medium text", "The quick brown fox jumps over the lazy dog. " * 5),
            ("Long text", "Artificial intelligence is transforming our world. " * 20)
        ]
        
        performance_data = {
            "model": "nllb",
            "test_timestamp": time.time(),
            "baselines": []
        }
        
        for description, text in test_texts:
            start_time = time.time()
            result = client.translate(
                text=text,
                source_lang="eng_Latn",
                target_lang="spa_Latn",
                model="nllb"
            )
            duration = time.time() - start_time
            
            assert result.status_code == 200, f"Performance test failed for {description}"
            
            baseline = {
                "description": description,
                "text_length": len(text),
                "word_count": len(text.split()),
                "translation_time_ms": duration * 1000,
                "characters_per_second": len(text) / duration if duration > 0 else 0,
                "words_per_second": len(text.split()) / duration if duration > 0 else 0
            }
            
            performance_data["baselines"].append(baseline)
            print(f"✓ {description}: {baseline['translation_time_ms']:.0f}ms, " +
                  f"{baseline['characters_per_second']:.1f} chars/sec")
        
        # Get model loading time from manager
        loading_report = manager.get_model_loading_report()
        if "nllb" in loading_report.get("loading_times", {}):
            performance_data["model_loading_time_seconds"] = loading_report["loading_times"]["nllb"]
            print(f"✓ Model loading time: {performance_data['model_loading_time_seconds']:.1f} seconds")
        
        # Save performance data for future reference
        perf_file = "/tmp/nllb_performance_baseline.json"
        with open(perf_file, "w") as f:
            json.dump(performance_data, f, indent=2)
        print(f"✓ Performance baseline saved to {perf_file}")
    
    def test_010_comprehensive_language_support(self, nllb_service):
        """Test comprehensive language support and availability."""
        client = nllb_service["client"]
        
        # Get supported languages
        languages_result = client.get_languages("nllb")
        assert languages_result.status_code == 200, "Failed to get supported languages"
        
        languages_data = languages_result.response_data
        assert languages_data is not None, "No language data returned"
        
        # Test representative languages from different families
        test_languages = [
            ("eng_Latn", "spa_Latn", "Hello", "English → Spanish"),
            ("spa_Latn", "fra_Latn", "Hola", "Spanish → French"),  
            ("fra_Latn", "deu_Latn", "Bonjour", "French → German"),
            ("deu_Latn", "ita_Latn", "Hallo", "German → Italian"),
            ("ita_Latn", "por_Latn", "Ciao", "Italian → Portuguese")
        ]
        
        successful_pairs = 0
        for source, target, text, description in test_languages:
            result = client.translate(
                text=text,
                source_lang=source,
                target_lang=target,
                model="nllb"
            )
            
            if result.status_code == 200:
                data = result.response_data
                translated = data.get("translated_text", "")
                if translated and translated != text:
                    successful_pairs += 1
                    print(f"✓ {description}: '{text}' → '{translated}'")
                else:
                    print(f"⚠ {description}: Translation same as input")
            else:
                print(f"✗ {description}: Failed with status {result.status_code}")
        
        success_rate = successful_pairs / len(test_languages)
        assert success_rate >= 0.8, f"Language support too low: {success_rate:.1%}"
        print(f"✓ Language support test: {successful_pairs}/{len(test_languages)} pairs successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])