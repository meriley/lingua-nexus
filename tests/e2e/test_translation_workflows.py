"""E2E tests for complete translation workflow validation."""

import pytest
import time
from typing import Dict, Any, List

from .utils.http_client import E2EHttpClient


@pytest.mark.e2e
class TestTranslationWorkflows:
    """Test complete translation workflow scenarios end-to-end."""
    
    def test_complete_translation_request_response_cycle(self, e2e_client: E2EHttpClient, translation_test_data: List[Dict[str, Any]]):
        """Test end-to-end translation workflow from request to response."""
        # Test each translation scenario
        for test_case in translation_test_data:
            text = test_case["text"]
            source_lang = test_case["source_lang"]
            target_lang = test_case["target_lang"]
            
            # Make translation request
            response = e2e_client.translate(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang
            )
            
            # Verify successful response
            assert response.is_success, \
                f"Translation failed for '{text}' ({source_lang} -> {target_lang}): {response.text}"
            
            # Verify response structure
            assert response.json_data is not None, "Response should contain JSON data"
            
            response_data = response.json_data
            assert "translated_text" in response_data, "Response should contain translated_text"
            assert "detected_source" in response_data, "Response should contain detected_source"
            assert "time_ms" in response_data, "Response should contain time_ms"
            
            # Verify response content
            translated_text = response_data["translated_text"]
            assert isinstance(translated_text, str), "Translated text should be a string"
            assert len(translated_text) > 0, "Translated text should not be empty"
            assert translated_text != text, "Translation should differ from original text"
            
            # Verify detected source language
            assert response_data["detected_source"] == source_lang, "Detected source should match request"
            # Note: target_lang is not returned in the response, only the translation itself
            
            # Verify reasonable response time
            assert response.response_time < 10.0, \
                f"Translation took too long: {response.response_time}s"
    
    def test_multiple_language_pair_combinations(self, e2e_client: E2EHttpClient):
        """Test various language pair combinations."""
        language_pairs = [
            ("eng_Latn", "fra_Latn", "Hello world"),
            ("eng_Latn", "spa_Latn", "Good morning"),
            ("eng_Latn", "deu_Latn", "Thank you"),
            ("eng_Latn", "ita_Latn", "How are you?"),
            ("fra_Latn", "eng_Latn", "Bonjour"),
            ("spa_Latn", "eng_Latn", "Hola"),
        ]
        
        for source_lang, target_lang, text in language_pairs:
            response = e2e_client.translate(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang
            )
            
            assert response.is_success, \
                f"Failed to translate '{text}' from {source_lang} to {target_lang}: {response.text}"
            
            # Verify translation was performed
            if response.json_data:
                translated = response.json_data.get("translated_text", "")
                assert len(translated) > 0, f"Empty translation for {source_lang} -> {target_lang}"
    
    def test_unicode_text_handling_over_http(self, e2e_client: E2EHttpClient, unicode_test_data: List[Dict[str, Any]]):
        """Test Unicode and special character handling over HTTP."""
        for test_case in unicode_test_data:
            text = test_case["text"]
            source_lang = test_case["source_lang"]
            target_lang = test_case["target_lang"]
            
            response = e2e_client.translate(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang
            )
            
            # Should handle Unicode without HTTP errors
            assert response.status_code != 400, \
                f"Unicode text should not cause bad request: '{text}'"
            
            if response.is_success and response.json_data:
                translated = response.json_data.get("translated_text", "")
                
                # Verify Unicode preservation
                assert isinstance(translated, str), "Translation should remain as string"
                assert len(translated) > 0, "Unicode translation should not be empty"
                
                # Verify proper UTF-8 encoding over HTTP
                assert text.encode('utf-8').decode('utf-8') == text, "Original text should be valid UTF-8"
                assert translated.encode('utf-8').decode('utf-8') == translated, "Translation should be valid UTF-8"
    
    def test_large_text_translation_requests(self, e2e_client: E2EHttpClient):
        """Test translation of large text payloads."""
        # Test various text sizes
        text_sizes = [
            ("small", "Hello world. How are you today?"),
            ("medium", "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 10),
            ("large", "This is a longer text for testing large payload handling. " * 100),
            ("very_large", "Testing very large text translation capabilities. " * 500)
        ]
        
        for size_name, text in text_sizes:
            response = e2e_client.translate(
                text=text,
                source_lang="eng_Latn",
                target_lang="fra_Latn",
                timeout=60  # Longer timeout for large texts
            )
            
            # Should not fail due to size (within reasonable limits)
            assert response.status_code != 413, \
                f"Text size '{size_name}' should not be rejected as too large"
            
            if response.is_success:
                assert response.json_data is not None, f"Large text '{size_name}' should return JSON"
                translated = response.json_data.get("translated_text", "")
                assert len(translated) > 0, f"Large text '{size_name}' should produce translation"
                
                # Verify reasonable response time even for large texts
                assert response.response_time < 30.0, \
                    f"Large text '{size_name}' took too long: {response.response_time}s"
    
    def test_translation_response_format_validation(self, e2e_client: E2EHttpClient):
        """Test consistent translation response format."""
        test_requests = [
            {
                "text": "Hello",
                "source_lang": "eng_Latn",
                "target_lang": "fra_Latn"
            },
            {
                "text": "Good morning",
                "source_lang": "eng_Latn", 
                "target_lang": "spa_Latn"
            },
            {
                "text": "Thank you",
                "source_lang": "eng_Latn",
                "target_lang": "deu_Latn"
            }
        ]
        
        expected_fields = ["translated_text", "detected_source", "time_ms"]
        
        for request_data in test_requests:
            response = e2e_client.translate(**request_data)
            
            if response.is_success:
                assert response.json_data is not None, "Successful response should contain JSON"
                
                # Verify all required fields are present
                for field in expected_fields:
                    assert field in response.json_data, \
                        f"Response should contain '{field}' field"
                
                # Verify field types
                data = response.json_data
                assert isinstance(data["translated_text"], str), "translated_text should be string"
                assert isinstance(data["detected_source"], str), "detected_source should be string"
                assert isinstance(data["time_ms"], int), "time_ms should be integer"
                
                # Verify field values
                assert len(data["translated_text"]) > 0, "translated_text should not be empty"
                assert data["detected_source"] == request_data["source_lang"], "detected_source should match request source_lang"
                assert data["time_ms"] >= 0, "time_ms should be non-negative"
    
    def test_unsupported_language_error_handling(self, e2e_client: E2EHttpClient):
        """Test proper error handling for unsupported languages."""
        unsupported_language_tests = [
            {
                "text": "Hello",
                "source_lang": "invalid_lang",
                "target_lang": "fra_Latn"
            },
            {
                "text": "Hello", 
                "source_lang": "eng_Latn",
                "target_lang": "invalid_target"
            },
            {
                "text": "Hello",
                "source_lang": "xxx_Latn",  # Non-existent language code
                "target_lang": "yyy_Latn"
            }
        ]
        
        for test_case in unsupported_language_tests:
            response = e2e_client.translate(**test_case)
            
            # Should return error for unsupported languages
            assert response.is_client_error or response.is_server_error, \
                f"Unsupported language should return error: {test_case}"
            
            # Verify error response format
            if response.json_data:
                error_data = response.json_data
                has_error_info = any(
                    key in error_data 
                    for key in ["detail", "error", "message"]
                )
                assert has_error_info, "Error response should contain error information"
    
    def test_malformed_translation_requests(self, e2e_client: E2EHttpClient):
        """Test handling of malformed translation requests."""
        malformed_requests = [
            {},  # Empty request
            {"text": "Hello"},  # Missing language fields
            {"source_lang": "eng_Latn", "target_lang": "fra_Latn"},  # Missing text
            {"text": "", "source_lang": "eng_Latn", "target_lang": "fra_Latn"},  # Empty text
            {"text": None, "source_lang": "eng_Latn", "target_lang": "fra_Latn"},  # Null text
            {"text": "Hello", "source_lang": "", "target_lang": "fra_Latn"},  # Empty source
            {"text": "Hello", "source_lang": "eng_Latn", "target_lang": ""},  # Empty target
        ]
        
        for malformed_request in malformed_requests:
            response = e2e_client.post("/translate", json_data=malformed_request)
            
            # Should return client error for malformed requests
            assert response.is_client_error, \
                f"Malformed request should return 4xx error: {malformed_request}"
            
            # Verify error response contains useful information
            if response.json_data:
                error_data = response.json_data
                has_error_info = any(
                    key in error_data 
                    for key in ["detail", "error", "message"]
                )
                assert has_error_info, "Validation error should provide details"
    
    def test_translation_consistency_across_requests(self, e2e_client: E2EHttpClient):
        """Test that identical requests produce consistent results."""
        test_text = "Hello, how are you today?"
        source_lang = "eng_Latn"
        target_lang = "fra_Latn"
        
        # Make multiple identical requests
        responses = []
        for i in range(3):
            response = e2e_client.translate(
                text=test_text,
                source_lang=source_lang,
                target_lang=target_lang
            )
            assert response.is_success, f"Request {i} should succeed"
            responses.append(response)
        
        # Verify consistency
        translations = [r.json_data["translated_text"] for r in responses]
        
        # All translations should be identical (deterministic model behavior)
        first_translation = translations[0]
        for i, translation in enumerate(translations[1:], 1):
            assert translation == first_translation, \
                f"Translation {i} differs from first: '{translation}' vs '{first_translation}'"
    
    def test_concurrent_translation_requests(self, e2e_client: E2EHttpClient):
        """Test concurrent translation requests."""
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def make_translation_request(request_id):
            """Make a translation request and return result."""
            response = e2e_client.translate(
                text=f"Hello world {request_id}",
                source_lang="eng_Latn",
                target_lang="fra_Latn"
            )
            return {
                "request_id": request_id,
                "success": response.is_success,
                "status_code": response.status_code,
                "response_time": response.response_time,
                "translation": response.json_data.get("translated_text", "") if response.json_data else ""
            }
        
        # Execute concurrent requests
        num_requests = 5
        results = []
        
        with ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = [
                executor.submit(make_translation_request, i) 
                for i in range(num_requests)
            ]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Verify all requests succeeded
        assert len(results) == num_requests, "All requests should complete"
        
        for result in results:
            assert result["success"], \
                f"Request {result['request_id']} failed: {result['status_code']}"
            assert len(result["translation"]) > 0, \
                f"Request {result['request_id']} produced empty translation"
            assert result["response_time"] < 15.0, \
                f"Request {result['request_id']} took too long: {result['response_time']}s"
    
    def test_translation_with_special_formatting(self, e2e_client: E2EHttpClient):
        """Test translation of text with special formatting and punctuation."""
        special_texts = [
            "Hello, world!",
            "What's your name?",
            "I'm fine, thank you.",
            "This is a test... with ellipsis.",
            "Multiple sentences. Each with periods.",
            "Text with\nnewlines and\ttabs.",
            "Numbers: 123, 456.78, and percentages: 99%",
            "Email: test@example.com and URL: https://example.com"
        ]
        
        for text in special_texts:
            response = e2e_client.translate(
                text=text,
                source_lang="eng_Latn",
                target_lang="fra_Latn"
            )
            
            assert response.is_success, \
                f"Should handle special formatting in: '{text}'"
            
            if response.json_data:
                translated = response.json_data.get("translated_text", "")
                assert len(translated) > 0, f"Should translate formatted text: '{text}'"