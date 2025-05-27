"""
E2E tests for bidirectional translation workflows.
TASK-002: Comprehensive testing of bidirectional translation functionality.
"""

import pytest
import time
from typing import Dict, Any, List, Tuple

from tests.e2e.utils.http_client import E2EHttpClient


@pytest.mark.e2e
@pytest.mark.e2e_foundation
class TestBidirectionalTranslation:
    """Test suite for bidirectional translation workflows."""

    # Test data for bidirectional translation pairs
    BIDIRECTIONAL_TEST_PAIRS = [
        {
            "text_a": "Hello, how are you today?",
            "lang_a": "eng_Latn",
            "text_b": "Hola, ¿cómo estás hoy?",
            "lang_b": "spa_Latn",
            "keywords_a": ["hello", "how", "today"],
            "keywords_b": ["hola", "cómo", "hoy"]
        },
        {
            "text_a": "Good morning, have a nice day!",
            "lang_a": "eng_Latn", 
            "text_b": "Bonjour, bonne journée !",
            "lang_b": "fra_Latn",
            "keywords_a": ["good", "morning", "day"],
            "keywords_b": ["bonjour", "journée"]
        },
        {
            "text_a": "Thank you very much for your help.",
            "lang_a": "eng_Latn",
            "text_b": "Vielen Dank für Ihre Hilfe.",
            "lang_b": "deu_Latn",
            "keywords_a": ["thank", "very", "help"],
            "keywords_b": ["vielen", "dank", "hilfe"]
        },
        {
            "text_a": "The weather is beautiful today.",
            "lang_a": "eng_Latn",
            "text_b": "Погода сегодня прекрасная.",
            "lang_b": "rus_Cyrl",
            "keywords_a": ["weather", "beautiful", "today"],
            "keywords_b": ["погода", "сегодня", "прекрасная"]
        }
    ]

    def test_bidirectional_translation_basic_workflow(self, e2e_client: E2EHttpClient):
        """Test basic A→B→A bidirectional translation workflow."""
        original_text = "Hello, how are you today?"
        source_lang = "eng_Latn"
        target_lang = "spa_Latn"
        
        # Step 1: Translate A → B
        request_payload = {
            "text": original_text,
            "source_lang": source_lang,
            "target_lang": target_lang
        }
        
        response_ab = e2e_client.post("/translate", json_data=request_payload)
        assert response_ab.status_code == 200
        
        ab_data = response_ab.json()
        translated_text = ab_data["translated_text"]
        assert ab_data["detected_source"] == source_lang
        assert len(translated_text) > 0
        assert translated_text != original_text
        
        # Step 2: Translate B → A (reverse)
        reverse_payload = {
            "text": translated_text,
            "source_lang": target_lang,
            "target_lang": source_lang
        }
        
        response_ba = e2e_client.post("/translate", json_data=reverse_payload)
        assert response_ba.status_code == 200
        
        ba_data = response_ba.json()
        back_translated_text = ba_data["translated_text"]
        assert ba_data["detected_source"] == target_lang
        assert len(back_translated_text) > 0
        
        # Step 3: Verify semantic similarity (basic check)
        # Note: Perfect back-translation is not expected due to model limitations
        original_words = set(original_text.lower().split())
        back_words = set(back_translated_text.lower().split())
        
        # Should have some word overlap (allowing for translation variations)
        common_words = original_words.intersection(back_words)
        overlap_ratio = len(common_words) / len(original_words) if original_words else 0
        
        # Allow for reasonable variation in back-translation
        assert overlap_ratio >= 0.2, f"Too little overlap in back-translation: {overlap_ratio:.2f}"

    def test_bidirectional_translation_auto_detect_forward(self, e2e_client: E2EHttpClient):
        """Test bidirectional translation with auto-detect in forward direction."""
        # Start with auto-detect
        request_payload = {
            "text": "Привет, как дела?",
            "source_lang": "auto",
            "target_lang": "eng_Latn"
        }
        
        response = e2e_client.post("/translate", json_data=request_payload)
        assert response.status_code == 200
        
        data = response.json()
        translated_text = data["translated_text"]
        detected_lang = data["detected_source"]
        
        # Should detect Russian
        assert detected_lang == "rus_Cyrl"
        assert any(word in translated_text.lower() for word in ["hello", "hi", "hey", "greetings"])
        
        # Now translate back using detected language
        reverse_payload = {
            "text": translated_text,
            "source_lang": "eng_Latn",
            "target_lang": detected_lang
        }
        
        reverse_response = e2e_client.post("/translate", json_data=reverse_payload)
        assert reverse_response.status_code == 200
        
        reverse_data = reverse_response.json()
        assert len(reverse_data["translated_text"]) > 0

    def test_bidirectional_translation_language_swap_validation(self, e2e_client: E2EHttpClient):
        """Test that language swap operations are handled correctly."""
        test_pairs = [
            ("eng_Latn", "spa_Latn", "Hello world"),
            ("fra_Latn", "eng_Latn", "Bonjour le monde"),
            ("deu_Latn", "eng_Latn", "Hallo Welt"),
            ("rus_Cyrl", "eng_Latn", "Привет мир")
        ]
        
        for source_lang, target_lang, text in test_pairs:
            # Forward translation
            forward_payload = {
                "text": text,
                "source_lang": source_lang,
                "target_lang": target_lang
            }
            
            forward_response = e2e_client.post("/translate", json_data=forward_payload)
            assert forward_response.status_code == 200
            
            forward_data = forward_response.json()
            forward_translated = forward_data["translated_text"]
            
            # Swapped translation (reverse)
            swapped_payload = {
                "text": forward_translated,
                "source_lang": target_lang,
                "target_lang": source_lang
            }
            
            swapped_response = e2e_client.post("/translate", json_data=swapped_payload)
            assert swapped_response.status_code == 200
            
            swapped_data = swapped_response.json()
            assert len(swapped_data["translated_text"]) > 0
            assert swapped_data["detected_source"] == target_lang

    def test_bidirectional_translation_with_unicode_content(self, e2e_client: E2EHttpClient):
        """Test bidirectional translation with Unicode and special characters."""
        unicode_test_cases = [
            {
                "text": "Hello 👋 World 🌍 with émojis and àccents",
                "source": "eng_Latn",
                "target": "fra_Latn"
            },
            {
                "text": "Café naïve résumé with spëcial chars",
                "source": "eng_Latn",
                "target": "spa_Latn"
            },
            {
                "text": "测试文本 with 中文字符",
                "source": "zho_Hans",
                "target": "eng_Latn"
            }
        ]
        
        for test_case in unicode_test_cases:
            # Forward translation
            forward_payload = {
                "text": test_case["text"],
                "source_lang": test_case["source"],
                "target_lang": test_case["target"]
            }
            
            forward_response = e2e_client.post("/translate", json_data=forward_payload)
            assert forward_response.status_code == 200
            
            forward_data = forward_response.json()
            forward_translated = forward_data["translated_text"]
            
            # Verify Unicode handling
            assert len(forward_translated) > 0
            assert forward_translated != test_case["text"]
            
            # Reverse translation
            reverse_payload = {
                "text": forward_translated,
                "source_lang": test_case["target"],
                "target_lang": test_case["source"]
            }
            
            reverse_response = e2e_client.post("/translate", json_data=reverse_payload)
            assert reverse_response.status_code == 200
            
            reverse_data = reverse_response.json()
            assert len(reverse_data["translated_text"]) > 0

    def test_bidirectional_translation_consistency_check(self, e2e_client: E2EHttpClient):
        """Test consistency of bidirectional translations across multiple runs."""
        text = "This is a test sentence for consistency checking."
        source_lang = "eng_Latn"
        target_lang = "fra_Latn"
        
        translations = []
        
        # Perform same translation multiple times
        for i in range(3):
            payload = {
                "text": text,
                "source_lang": source_lang,
                "target_lang": target_lang
            }
            
            response = e2e_client.post("/translate", json_data=payload)
            assert response.status_code == 200
            
            data = response.json()
            translations.append(data["translated_text"])
            time.sleep(0.1)  # Small delay between requests
        
        # Check that translations are consistent (should be identical or very similar)
        first_translation = translations[0]
        for translation in translations[1:]:
            # Allow for minor variations but expect high similarity
            similarity_ratio = len(set(first_translation.split()) & set(translation.split())) / max(len(first_translation.split()), len(translation.split()))
            assert similarity_ratio >= 0.8, f"Translation consistency issue: {similarity_ratio:.2f}"

    def test_bidirectional_translation_error_validation(self, e2e_client: E2EHttpClient):
        """Test error handling in bidirectional translation scenarios."""
        # Test same source and target language
        same_lang_payload = {
            "text": "Hello world",
            "source_lang": "eng_Latn",
            "target_lang": "eng_Latn"
        }
        
        response = e2e_client.post("/translate", json_data=same_lang_payload)
        assert response.status_code == 400
        assert "Source and target languages cannot be the same" in response.json()["detail"]
        
        # Test invalid language codes in bidirectional context
        invalid_source_payload = {
            "text": "Hello world",
            "source_lang": "invalid_Latn",
            "target_lang": "spa_Latn"
        }
        
        response = e2e_client.post("/translate", json_data=invalid_source_payload)
        assert response.status_code == 400
        assert "Unsupported source language" in response.json()["detail"]
        
        # Test auto as target language (not allowed)
        auto_target_payload = {
            "text": "Hello world",
            "source_lang": "eng_Latn",
            "target_lang": "auto"
        }
        
        response = e2e_client.post("/translate", json_data=auto_target_payload)
        assert response.status_code == 400
        assert "Target language cannot be 'auto'" in response.json()["detail"]

    def test_bidirectional_translation_rtl_languages(self, e2e_client: E2EHttpClient):
        """Test bidirectional translation with RTL (right-to-left) languages."""
        rtl_test_cases = [
            {
                "text": "Hello, how are you?",
                "source": "eng_Latn",
                "target": "arb_Arab",
                "direction": "ltr_to_rtl"
            },
            {
                "text": "مرحبا، كيف حالك؟",
                "source": "arb_Arab", 
                "target": "eng_Latn",
                "direction": "rtl_to_ltr"
            }
        ]
        
        for test_case in rtl_test_cases:
            # Forward translation
            forward_payload = {
                "text": test_case["text"],
                "source_lang": test_case["source"],
                "target_lang": test_case["target"]
            }
            
            forward_response = e2e_client.post("/translate", json_data=forward_payload)
            assert forward_response.status_code == 200
            
            forward_data = forward_response.json()
            forward_translated = forward_data["translated_text"]
            assert len(forward_translated) > 0
            
            # Reverse translation
            reverse_payload = {
                "text": forward_translated,
                "source_lang": test_case["target"],
                "target_lang": test_case["source"]
            }
            
            reverse_response = e2e_client.post("/translate", json_data=reverse_payload)
            assert reverse_response.status_code == 200
            
            reverse_data = reverse_response.json()
            assert len(reverse_data["translated_text"]) > 0

    def test_bidirectional_translation_performance_timing(self, e2e_client: E2EHttpClient):
        """Test performance of bidirectional translation workflows."""
        text = "This is a test for measuring translation performance timing."
        source_lang = "eng_Latn"
        target_lang = "spa_Latn"
        
        # Time forward translation
        start_time = time.time()
        forward_payload = {
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang
        }
        
        forward_response = e2e_client.post("/translate", json_data=forward_payload)
        forward_end_time = time.time()
        
        assert forward_response.status_code == 200
        forward_time = forward_end_time - start_time
        
        forward_data = forward_response.json()
        translated_text = forward_data["translated_text"]
        
        # Time reverse translation
        reverse_start_time = time.time()
        reverse_payload = {
            "text": translated_text,
            "source_lang": target_lang,
            "target_lang": source_lang
        }
        
        reverse_response = e2e_client.post("/translate", json_data=reverse_payload)
        reverse_end_time = time.time()
        
        assert reverse_response.status_code == 200
        reverse_time = reverse_end_time - reverse_start_time
        
        # Performance assertions
        assert forward_time < 5.0, f"Forward translation took too long: {forward_time:.2f}s"
        assert reverse_time < 5.0, f"Reverse translation took too long: {reverse_time:.2f}s"
        
        # Total bidirectional workflow should complete under 10 seconds
        total_time = forward_time + reverse_time
        assert total_time < 10.0, f"Total bidirectional workflow took too long: {total_time:.2f}s"

    def test_bidirectional_translation_data_integrity(self, e2e_client: E2EHttpClient):
        """Test data integrity across bidirectional translation chains."""
        # Test with structured data-like content
        structured_texts = [
            "Name: John Doe, Age: 30, City: New York",
            "Email: test@example.com, Phone: +1-555-0123",
            "Date: 2024-01-15, Time: 14:30:00, Status: Active"
        ]
        
        for original_text in structured_texts:
            # Translate through multiple languages and back
            current_text = original_text
            current_lang = "eng_Latn"
            
            # Chain: English → Spanish → French → English
            language_chain = ["spa_Latn", "fra_Latn", "eng_Latn"]
            
            for target_lang in language_chain:
                payload = {
                    "text": current_text,
                    "source_lang": current_lang,
                    "target_lang": target_lang
                }
                
                response = e2e_client.post("/translate", json_data=payload)
                assert response.status_code == 200
                
                data = response.json()
                current_text = data["translated_text"]
                current_lang = target_lang
                
                # Verify each step produces valid output
                assert len(current_text) > 0
                assert data["detected_source"] == payload["source_lang"]
            
            # Final text should still contain some recognizable elements
            # (allowing for translation variations)
            assert len(current_text) > 0


@pytest.mark.e2e
@pytest.mark.e2e_performance
class TestBidirectionalTranslationPerformance:
    """Performance-focused tests for bidirectional translation."""

    def test_concurrent_bidirectional_translations(self, e2e_client: E2EHttpClient):
        """Test concurrent bidirectional translation requests."""
        import threading
        
        results = []
        
        def perform_bidirectional_translation(text_id: int):
            text = f"Test message number {text_id} for concurrent translation."
            
            try:
                # Forward translation
                forward_payload = {
                    "text": text,
                    "source_lang": "eng_Latn",
                    "target_lang": "spa_Latn"
                }
                
                start_time = time.time()
                forward_response = e2e_client.post("/translate", json_data=forward_payload)
                forward_data = forward_response.json()
                
                # Reverse translation
                reverse_payload = {
                    "text": forward_data["translated_text"],
                    "source_lang": "spa_Latn",
                    "target_lang": "eng_Latn"
                }
                
                reverse_response = e2e_client.post("/translate", json_data=reverse_payload)
                end_time = time.time()
                
                results.append({
                    'text_id': text_id,
                    'success': forward_response.status_code == 200 and reverse_response.status_code == 200,
                    'total_time': end_time - start_time,
                    'forward_status': forward_response.status_code,
                    'reverse_status': reverse_response.status_code
                })
                
            except Exception as e:
                results.append({
                    'text_id': text_id,
                    'success': False,
                    'error': str(e),
                    'total_time': None
                })
        
        # Start 3 concurrent bidirectional translation workflows
        threads = []
        for i in range(3):
            thread = threading.Thread(target=perform_bidirectional_translation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(results) == 3
        
        successful_results = [r for r in results if r['success']]
        assert len(successful_results) >= 2, "At least 2 out of 3 concurrent workflows should succeed"
        
        # Check performance of successful results
        for result in successful_results:
            if result['total_time']:
                assert result['total_time'] < 15.0, f"Concurrent bidirectional workflow took too long: {result['total_time']:.2f}s"

    def test_bidirectional_translation_memory_efficiency(self, e2e_client: E2EHttpClient):
        """Test memory efficiency of bidirectional translation workflows."""
        # Test with progressively larger texts
        base_text = "This is a test sentence for memory efficiency testing. "
        
        text_sizes = [1, 5, 10, 20]  # Multipliers for text length
        
        for multiplier in text_sizes:
            large_text = base_text * multiplier
            
            # Ensure text doesn't exceed API limits
            if len(large_text) > 4000:  # Leave buffer for 5000 char limit
                break
            
            # Perform bidirectional translation
            forward_payload = {
                "text": large_text,
                "source_lang": "eng_Latn",
                "target_lang": "fra_Latn"
            }
            
            forward_response = e2e_client.post("/translate", json_data=forward_payload)
            assert forward_response.status_code == 200
            
            forward_data = forward_response.json()
            
            # Reverse translation
            reverse_payload = {
                "text": forward_data["translated_text"],
                "source_lang": "fra_Latn",
                "target_lang": "eng_Latn"
            }
            
            reverse_response = e2e_client.post("/translate", json_data=reverse_payload)
            assert reverse_response.status_code == 200
            
            # Verify response times don't degrade significantly with size
            assert forward_data["time_ms"] < 10000  # 10 seconds max
            
            reverse_data = reverse_response.json()
            assert reverse_data["time_ms"] < 10000  # 10 seconds max