"""
E2E tests for language swap functionality.
TASK-007: Comprehensive testing of bidirectional language swapping across platforms.
"""

import pytest
import time
from typing import Dict, Any, List

from tests.e2e.utils.http_client import E2EHttpClient


@pytest.mark.e2e
@pytest.mark.e2e_foundation
class TestLanguageSwapFunctionality:
    """Test suite for language swap functionality across platforms."""

    def test_basic_language_swap_workflow(self, e2e_client: E2EHttpClient):
        """Test basic language swap functionality in translation workflow."""
        # Initial translation: English → Spanish
        original_text = "Hello, how are you today?"
        
        forward_payload = {
            "text": original_text,
            "source_lang": "eng_Latn",
            "target_lang": "spa_Latn"
        }
        
        forward_response = e2e_client.post("/translate", json_data=forward_payload)
        assert forward_response.status_code == 200
        
        forward_result = forward_response.json()
        spanish_text = forward_result["translated_text"]
        
        # Language swap: Spanish → English (reverse direction)
        swap_payload = {
            "text": spanish_text,
            "source_lang": "spa_Latn",  # Previously target
            "target_lang": "eng_Latn"   # Previously source
        }
        
        swap_response = e2e_client.post("/translate", json_data=swap_payload)
        assert swap_response.status_code == 200
        
        swap_result = swap_response.json()
        back_to_english = swap_result["translated_text"]
        
        # Verify swap functionality works
        assert len(spanish_text) > 0, "Forward translation should produce text"
        assert len(back_to_english) > 0, "Swapped translation should produce text"
        assert spanish_text != back_to_english, "Forward and swapped translations should be different"
        
        # Verify semantic similarity (basic check)
        original_words = set(original_text.lower().split())
        back_words = set(back_to_english.lower().split())
        common_words = original_words.intersection(back_words)
        
        # Should have some semantic overlap
        overlap_ratio = len(common_words) / len(original_words) if original_words else 0
        assert overlap_ratio >= 0.2, f"Language swap should preserve meaning: overlap {overlap_ratio:.2f}"

    def test_language_swap_with_auto_detect_restrictions(self, e2e_client: E2EHttpClient):
        """Test language swap restrictions when auto-detect is involved."""
        # Test that auto-detect cannot be used as target language
        auto_target_payload = {
            "text": "Hello world",
            "source_lang": "eng_Latn",
            "target_lang": "auto"
        }
        
        response = e2e_client.post("/translate", json_data=auto_target_payload)
        assert response.status_code == 400
        assert "Target language cannot be 'auto'" in response.json()["detail"]
        
        # Test valid auto-detect usage (source only)
        auto_source_payload = {
            "text": "Привет мир",  # Russian text for auto-detection
            "source_lang": "auto",
            "target_lang": "eng_Latn"
        }
        
        response = e2e_client.post("/translate", json_data=auto_source_payload)
        assert response.status_code == 200
        
        result = response.json()
        assert result["detected_source"] == "rus_Cyrl"  # Should detect Russian
        
        # Test that we can swap from detected language
        swap_payload = {
            "text": result["translated_text"],
            "source_lang": "eng_Latn",
            "target_lang": result["detected_source"]  # Use detected language as target
        }
        
        swap_response = e2e_client.post("/translate", json_data=swap_payload)
        assert swap_response.status_code == 200

    def test_language_swap_with_rtl_languages(self, e2e_client: E2EHttpClient):
        """Test language swap functionality with RTL (right-to-left) languages."""
        rtl_swap_test_cases = [
            {
                "text": "Hello, welcome to our website",
                "forward_source": "eng_Latn",
                "forward_target": "arb_Arab",
                "description": "English to Arabic swap"
            },
            {
                "text": "Good morning, how can I help you?",
                "forward_source": "eng_Latn", 
                "forward_target": "heb_Hebr",
                "description": "English to Hebrew swap"
            }
        ]
        
        for test_case in rtl_swap_test_cases:
            # Forward translation to RTL language
            forward_payload = {
                "text": test_case["text"],
                "source_lang": test_case["forward_source"],
                "target_lang": test_case["forward_target"]
            }
            
            forward_response = e2e_client.post("/translate", json_data=forward_payload)
            
            if forward_response.status_code == 200:  # Language may not be supported
                forward_result = forward_response.json()
                rtl_text = forward_result["translated_text"]
                
                # Language swap back to LTR
                swap_payload = {
                    "text": rtl_text,
                    "source_lang": test_case["forward_target"],
                    "target_lang": test_case["forward_source"]
                }
                
                swap_response = e2e_client.post("/translate", json_data=swap_payload)
                assert swap_response.status_code == 200
                
                swap_result = swap_response.json()
                ltr_text = swap_result["translated_text"]
                
                # Verify swap completed successfully
                assert len(rtl_text) > 0, f"RTL translation should produce text for {test_case['description']}"
                assert len(ltr_text) > 0, f"LTR swap back should produce text for {test_case['description']}"

    def test_language_swap_preserves_text_formatting(self, e2e_client: E2EHttpClient):
        """Test that language swap preserves text formatting and special characters."""
        formatting_test_cases = [
            {
                "text": "Hello! How are you? I'm fine, thanks.",
                "source": "eng_Latn",
                "target": "spa_Latn",
                "description": "Punctuation preservation"
            },
            {
                "text": "Visit https://example.com for more info.",
                "source": "eng_Latn",
                "target": "fra_Latn", 
                "description": "URL preservation"
            },
            {
                "text": "Call +1-555-0123 or email test@example.com",
                "source": "eng_Latn",
                "target": "deu_Latn",
                "description": "Contact info preservation"
            },
            {
                "text": "Price: $19.99 (was $29.99)",
                "source": "eng_Latn",
                "target": "spa_Latn",
                "description": "Numeric formatting preservation"
            }
        ]
        
        for test_case in formatting_test_cases:
            # Forward translation
            forward_payload = {
                "text": test_case["text"],
                "source_lang": test_case["source"],
                "target_lang": test_case["target"]
            }
            
            forward_response = e2e_client.post("/translate", json_data=forward_payload)
            assert forward_response.status_code == 200
            
            forward_result = forward_response.json()
            translated_text = forward_result["translated_text"]
            
            # Language swap back
            swap_payload = {
                "text": translated_text,
                "source_lang": test_case["target"],
                "target_lang": test_case["source"]
            }
            
            swap_response = e2e_client.post("/translate", json_data=swap_payload)
            assert swap_response.status_code == 200
            
            swap_result = swap_response.json()
            back_translated = swap_result["translated_text"]
            
            # Check that special formatting elements are preserved somewhat
            # Note: Perfect preservation is not expected, but some elements should remain
            original_has_url = "http" in test_case["text"]
            original_has_email = "@" in test_case["text"]
            original_has_phone = "555" in test_case["text"]
            original_has_price = "$" in test_case["text"]
            
            if original_has_url:
                # URL might be preserved in some form
                assert "http" in translated_text or "example" in translated_text, \
                    f"URL elements should be somewhat preserved in {test_case['description']}"
            
            if original_has_email:
                # Email might be preserved
                assert "@" in translated_text or "example" in translated_text, \
                    f"Email elements should be somewhat preserved in {test_case['description']}"

    def test_language_swap_chain_consistency(self, e2e_client: E2EHttpClient):
        """Test consistency of language swap chains (A→B→C→A)."""
        # Test a chain of swaps: English → Spanish → French → English
        original_text = "This is a test of translation chain consistency."
        
        # Step 1: English → Spanish
        step1_payload = {
            "text": original_text,
            "source_lang": "eng_Latn",
            "target_lang": "spa_Latn"
        }
        
        step1_response = e2e_client.post("/translate", json_data=step1_payload)
        assert step1_response.status_code == 200
        step1_result = step1_response.json()
        spanish_text = step1_result["translated_text"]
        
        # Step 2: Spanish → French (language swap)
        step2_payload = {
            "text": spanish_text,
            "source_lang": "spa_Latn",
            "target_lang": "fra_Latn"
        }
        
        step2_response = e2e_client.post("/translate", json_data=step2_payload)
        assert step2_response.status_code == 200
        step2_result = step2_response.json()
        french_text = step2_result["translated_text"]
        
        # Step 3: French → English (complete the chain)
        step3_payload = {
            "text": french_text,
            "source_lang": "fra_Latn",
            "target_lang": "eng_Latn"
        }
        
        step3_response = e2e_client.post("/translate", json_data=step3_payload)
        assert step3_response.status_code == 200
        step3_result = step3_response.json()
        final_english = step3_result["translated_text"]
        
        # Verify chain consistency
        assert len(spanish_text) > 0, "Spanish translation should produce text"
        assert len(french_text) > 0, "French translation should produce text"
        assert len(final_english) > 0, "Final English translation should produce text"
        
        # All texts should be different (no pass-through)
        texts = [original_text, spanish_text, french_text, final_english]
        for i, text1 in enumerate(texts):
            for j, text2 in enumerate(texts):
                if i != j:
                    assert text1 != text2, f"Translation step {i} and {j} should produce different texts"
        
        # Final result should have some semantic similarity to original
        original_words = set(original_text.lower().split())
        final_words = set(final_english.lower().split())
        common_words = original_words.intersection(final_words)
        overlap_ratio = len(common_words) / len(original_words) if original_words else 0
        
        # Allow for significant degradation in chain translation
        assert overlap_ratio >= 0.1, f"Translation chain should preserve some meaning: overlap {overlap_ratio:.2f}"

    def test_language_swap_performance_timing(self, e2e_client: E2EHttpClient):
        """Test performance of language swap operations."""
        test_text = "This is a performance test for language swap functionality."
        
        # Test multiple swap operations with timing
        swap_operations = [
            ("eng_Latn", "spa_Latn"),
            ("spa_Latn", "fra_Latn"),
            ("fra_Latn", "deu_Latn"),
            ("deu_Latn", "eng_Latn")
        ]
        
        current_text = test_text
        total_time = 0
        
        for source_lang, target_lang in swap_operations:
            start_time = time.time()
            
            payload = {
                "text": current_text,
                "source_lang": source_lang,
                "target_lang": target_lang
            }
            
            response = e2e_client.post("/translate", json_data=payload)
            end_time = time.time()
            
            operation_time = end_time - start_time
            total_time += operation_time
            
            assert response.status_code == 200, f"Swap operation {source_lang}→{target_lang} should succeed"
            
            result = response.json()
            current_text = result["translated_text"]
            
            # Each operation should complete within reasonable time
            assert operation_time < 5.0, f"Swap operation {source_lang}→{target_lang} took too long: {operation_time:.2f}s"
            
            # Verify timing information in response
            assert "time_ms" in result, "Response should include timing information"
            assert result["time_ms"] > 0, "Timing should be positive"
        
        # Total chain should complete within reasonable time
        assert total_time < 15.0, f"Complete language swap chain took too long: {total_time:.2f}s"

    def test_language_swap_with_identical_languages_error(self, e2e_client: E2EHttpClient):
        """Test error handling when trying to swap to the same language."""
        # Test identical language error
        same_lang_payload = {
            "text": "Hello world",
            "source_lang": "eng_Latn",
            "target_lang": "eng_Latn"
        }
        
        response = e2e_client.post("/translate", json_data=same_lang_payload)
        assert response.status_code == 400
        assert "Source and target languages cannot be the same" in response.json()["detail"]
        
        # Test with different language codes for the same language (if any exist)
        # Most NLLB codes are unique, but verify the check works properly


@pytest.mark.e2e
@pytest.mark.e2e_foundation
class TestLanguageSwapIntegration:
    """Test suite for language swap integration across different scenarios."""

    def test_language_swap_with_unicode_content(self, e2e_client: E2EHttpClient):
        """Test language swap with Unicode and special characters."""
        unicode_test_cases = [
            {
                "text": "Hello 👋 World 🌍 with emojis!",
                "source": "eng_Latn",
                "target": "spa_Latn",
                "description": "Emoji handling"
            },
            {
                "text": "Café naïve résumé with accents",
                "source": "eng_Latn",
                "target": "fra_Latn",
                "description": "Accent preservation"
            },
            {
                "text": "Price: €29.99 → $34.50",
                "source": "eng_Latn",
                "target": "deu_Latn",
                "description": "Currency symbols"
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
            
            forward_result = forward_response.json()
            translated_text = forward_result["translated_text"]
            
            # Language swap back
            swap_payload = {
                "text": translated_text,
                "source_lang": test_case["target"],
                "target_lang": test_case["source"]
            }
            
            swap_response = e2e_client.post("/translate", json_data=swap_payload)
            assert swap_response.status_code == 200
            
            swap_result = swap_response.json()
            
            # Verify Unicode handling doesn't break the swap
            assert len(translated_text) > 0, f"Forward translation should work with Unicode: {test_case['description']}"
            assert len(swap_result["translated_text"]) > 0, f"Swap should work with Unicode: {test_case['description']}"

    def test_language_swap_error_recovery(self, e2e_client: E2EHttpClient):
        """Test error recovery scenarios in language swap workflows."""
        # Test recovery from invalid intermediate language
        original_text = "This is a test of error recovery in language swap."
        
        # Valid first translation
        step1_payload = {
            "text": original_text,
            "source_lang": "eng_Latn",
            "target_lang": "spa_Latn"
        }
        
        step1_response = e2e_client.post("/translate", json_data=step1_payload)
        assert step1_response.status_code == 200
        
        step1_result = step1_response.json()
        spanish_text = step1_result["translated_text"]
        
        # Try invalid swap (invalid target language)
        invalid_swap_payload = {
            "text": spanish_text,
            "source_lang": "spa_Latn",
            "target_lang": "invalid_Lang"
        }
        
        invalid_response = e2e_client.post("/translate", json_data=invalid_swap_payload)
        assert invalid_response.status_code == 400
        
        # Recover with valid swap
        valid_swap_payload = {
            "text": spanish_text,
            "source_lang": "spa_Latn",
            "target_lang": "fra_Latn"
        }
        
        valid_response = e2e_client.post("/translate", json_data=valid_swap_payload)
        assert valid_response.status_code == 200
        
        # Should successfully complete after error
        valid_result = valid_response.json()
        assert len(valid_result["translated_text"]) > 0

    def test_language_swap_with_long_text(self, e2e_client: E2EHttpClient):
        """Test language swap functionality with longer text content."""
        # Create longer test text
        base_text = "This is a comprehensive test of the language swap functionality with longer content. "
        long_text = base_text * 10  # Repeat to create longer text
        
        # Ensure we don't exceed API limits
        if len(long_text) > 4000:
            long_text = long_text[:4000]
        
        # Forward translation
        forward_payload = {
            "text": long_text,
            "source_lang": "eng_Latn",
            "target_lang": "spa_Latn"
        }
        
        forward_response = e2e_client.post("/translate", json_data=forward_payload)
        assert forward_response.status_code == 200
        
        forward_result = forward_response.json()
        spanish_text = forward_result["translated_text"]
        
        # Language swap back
        swap_payload = {
            "text": spanish_text,
            "source_lang": "spa_Latn",
            "target_lang": "eng_Latn"
        }
        
        swap_response = e2e_client.post("/translate", json_data=swap_payload)
        assert swap_response.status_code == 200
        
        swap_result = swap_response.json()
        back_translated = swap_result["translated_text"]
        
        # Verify long text handling
        assert len(spanish_text) > 0, "Long text forward translation should work"
        assert len(back_translated) > 0, "Long text swap should work"
        
        # Check that response times are reasonable even for longer text
        assert forward_result["time_ms"] < 10000, "Long text translation should complete within 10 seconds"
        assert swap_result["time_ms"] < 10000, "Long text swap should complete within 10 seconds"

    def test_language_swap_concurrent_operations(self, e2e_client: E2EHttpClient):
        """Test concurrent language swap operations."""
        import threading
        
        results = []
        
        def perform_language_swap(swap_id: int):
            try:
                # Forward translation
                forward_payload = {
                    "text": f"Concurrent swap test {swap_id}",
                    "source_lang": "eng_Latn",
                    "target_lang": "spa_Latn"
                }
                
                forward_response = e2e_client.post("/translate", json_data=forward_payload)
                forward_data = forward_response.json()
                
                # Language swap
                swap_payload = {
                    "text": forward_data["translated_text"],
                    "source_lang": "spa_Latn",
                    "target_lang": "fra_Latn"
                }
                
                swap_response = e2e_client.post("/translate", json_data=swap_payload)
                
                results.append({
                    "swap_id": swap_id,
                    "forward_success": forward_response.status_code == 200,
                    "swap_success": swap_response.status_code == 200,
                    "overall_success": forward_response.status_code == 200 and swap_response.status_code == 200
                })
                
            except Exception as e:
                results.append({
                    "swap_id": swap_id,
                    "error": str(e),
                    "overall_success": False
                })
        
        # Start concurrent swap operations
        threads = []
        for i in range(3):
            thread = threading.Thread(target=perform_language_swap, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(results) == 3, "Should have 3 concurrent swap results"
        
        successful_swaps = [r for r in results if r["overall_success"]]
        assert len(successful_swaps) >= 2, "At least 2 out of 3 concurrent swaps should succeed"