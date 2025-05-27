"""
Comprehensive error handling and edge case tests.

Tests various error scenarios including:
- Invalid request data formats
- Missing required fields
- Network/model errors
- Malformed JSON
- Large input handling
- Unicode and special character edge cases
"""

import pytest
import json
from fastapi.testclient import TestClient
from app.main import app


class TestErrorHandling:
    """Test suite for error handling and edge cases."""

    def test_missing_required_fields(self, test_client, enhanced_mock_objects, api_key_header):
        """Test handling of missing required fields in request."""
        
        # Missing text field
        incomplete_data = {
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        response = test_client.post("/translate", json=incomplete_data, headers=api_key_header)
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data
        
        # Missing source_lang field
        incomplete_data = {
            "text": "Hello world",
            "target_lang": "fra_Latn"
        }
        response = test_client.post("/translate", json=incomplete_data, headers=api_key_header)
        assert response.status_code == 422
        
        # Missing target_lang field
        incomplete_data = {
            "text": "Hello world", 
            "source_lang": "eng_Latn"
        }
        response = test_client.post("/translate", json=incomplete_data, headers=api_key_header)
        assert response.status_code == 422

    def test_invalid_data_types(self, test_client, enhanced_mock_objects, api_key_header):
        """Test handling of invalid data types in request."""
        
        # Text field as integer
        invalid_data = {
            "text": 12345,
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        response = test_client.post("/translate", json=invalid_data, headers=api_key_header)
        assert response.status_code == 422
        
        # Language codes as integers
        invalid_data = {
            "text": "Hello world",
            "source_lang": 123,
            "target_lang": 456
        }
        response = test_client.post("/translate", json=invalid_data, headers=api_key_header)
        assert response.status_code == 422
        
        # Text field as boolean
        invalid_data = {
            "text": True,
            "source_lang": "eng_Latn", 
            "target_lang": "fra_Latn"
        }
        response = test_client.post("/translate", json=invalid_data, headers=api_key_header)
        assert response.status_code == 422

    def test_empty_and_null_values(self, test_client, enhanced_mock_objects, api_key_header):
        """Test handling of empty and null values."""
        
        # Empty text string
        empty_data = {
            "text": "",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        response = test_client.post("/translate", json=empty_data, headers=api_key_header)
        # Should either reject empty text or handle gracefully
        assert response.status_code in [400, 422, 200]
        
        # Null text value
        null_data = {
            "text": None,
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        response = test_client.post("/translate", json=null_data, headers=api_key_header)
        assert response.status_code == 422
        
        # Empty language codes
        empty_lang_data = {
            "text": "Hello world",
            "source_lang": "",
            "target_lang": ""
        }
        response = test_client.post("/translate", json=empty_lang_data, headers=api_key_header)
        assert response.status_code in [400, 422]

    def test_malformed_json(self, test_client, api_key_header):
        """Test handling of malformed JSON requests."""
        
        # Invalid JSON syntax
        malformed_json = '{"text": "Hello", "source_lang": "eng_Latn", "target_lang": "fra_Latn"'  # Missing closing brace
        
        response = test_client.post(
            "/translate",
            data=malformed_json,
            headers={**api_key_header, "Content-Type": "application/json"}
        )
        assert response.status_code == 422
        
        # Completely invalid JSON
        invalid_json = "not json at all"
        response = test_client.post(
            "/translate", 
            data=invalid_json,
            headers={**api_key_header, "Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_unsupported_language_codes(self, test_client, enhanced_mock_objects, api_key_header):
        """Test handling of unsupported or invalid language codes."""
        
        invalid_language_codes = [
            "invalid_lang",
            "xyz_Abcd", 
            "english",
            "fr",
            "123_456",
            "eng_Latn_Extra"
        ]
        
        for invalid_lang in invalid_language_codes:
            # Test invalid source language
            invalid_data = {
                "text": "Hello world",
                "source_lang": invalid_lang,
                "target_lang": "fra_Latn"
            }
            response = test_client.post("/translate", json=invalid_data, headers=api_key_header)
            # Should handle invalid language codes gracefully
            assert response.status_code in [400, 422, 500]
            
            # Test invalid target language
            invalid_data = {
                "text": "Hello world", 
                "source_lang": "eng_Latn",
                "target_lang": invalid_lang
            }
            response = test_client.post("/translate", json=invalid_data, headers=api_key_header)
            assert response.status_code in [400, 422, 500]

    def test_extremely_long_text(self, test_client, enhanced_mock_objects, api_key_header):
        """Test handling of extremely long input text."""
        
        # Very long text (10KB)
        long_text = "A" * 10000
        long_data = {
            "text": long_text,
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        response = test_client.post("/translate", json=long_data, headers=api_key_header)
        # Should either handle or reject gracefully with proper error
        assert response.status_code in [200, 400, 413, 422]
        
        if response.status_code == 200:
            data = response.json()
            assert "translated_text" in data
        else:
            data = response.json()
            assert "detail" in data

    def test_unicode_and_special_characters(self, test_client, enhanced_mock_objects, api_key_header):
        """Test handling of Unicode and special characters."""
        
        unicode_test_cases = [
            "Hello 🌍 World!",  # Emojis
            "こんにちは世界",  # Japanese
            "مرحبا بالعالم",  # Arabic
            "Здравствуй мир",  # Russian (Cyrillic)
            "Χαίρετε κόσμε",  # Greek
            "नमस्ते दुनिया",  # Hindi (Devanagari)
            "Test\n\t\r special chars",  # Control characters
            "Test with \"quotes\" and 'apostrophes'",  # Quotes
            "Test with <tags> & entities",  # HTML-like content
        ]
        
        for unicode_text in unicode_test_cases:
            unicode_data = {
                "text": unicode_text,
                "source_lang": "eng_Latn",
                "target_lang": "fra_Latn"
            }
            
            response = test_client.post("/translate", json=unicode_data, headers=api_key_header)
            # Should handle Unicode gracefully
            assert response.status_code in [200, 400]
            
            if response.status_code == 200:
                data = response.json()
                assert "translated_text" in data
                # Ensure response is valid JSON-encodable
                json.dumps(data)

    def test_same_source_target_language(self, test_client, enhanced_mock_objects, api_key_header):
        """Test behavior when source and target languages are the same."""
        
        same_lang_data = {
            "text": "Hello world",
            "source_lang": "eng_Latn",
            "target_lang": "eng_Latn"
        }
        
        response = test_client.post("/translate", json=same_lang_data, headers=api_key_header)
        # Should handle gracefully - either translate or return original
        assert response.status_code in [200, 400]
        
        if response.status_code == 200:
            data = response.json()
            assert "translated_text" in data

    def test_request_size_limits(self, test_client, enhanced_mock_objects, api_key_header):
        """Test request size limits and payload restrictions."""
        
        # Test with very large JSON payload
        large_payload = {
            "text": "Normal text",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn",
            "extra_large_field": "X" * 100000  # 100KB of extra data
        }
        
        response = test_client.post("/translate", json=large_payload, headers=api_key_header)
        # Should either ignore extra fields or handle large payloads
        assert response.status_code in [200, 400, 413, 422]

    def test_concurrent_error_scenarios(self, test_client, enhanced_mock_objects, api_key_header):
        """Test error handling under concurrent request scenarios."""
        import threading
        import time
        
        results = []
        
        def make_invalid_request():
            invalid_data = {
                "text": None,  # Invalid data
                "source_lang": "eng_Latn",
                "target_lang": "fra_Latn"
            }
            response = test_client.post("/translate", json=invalid_data, headers=api_key_header)
            results.append(response.status_code)
        
        # Create multiple threads making invalid requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_invalid_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All should return validation errors consistently
        for status_code in results:
            assert status_code == 422

    def test_http_method_not_allowed(self, test_client, api_key_header):
        """Test handling of unsupported HTTP methods."""
        
        request_data = {
            "text": "Hello world",
            "source_lang": "eng_Latn", 
            "target_lang": "fra_Latn"
        }
        
        # Test GET (should be 405 Method Not Allowed)
        response = test_client.get("/translate", headers=api_key_header)
        assert response.status_code == 405
        
        # Test PUT (should be 405 Method Not Allowed)  
        response = test_client.put("/translate", json=request_data, headers=api_key_header)
        assert response.status_code == 405
        
        # Test DELETE (should be 405 Method Not Allowed)
        response = test_client.delete("/translate", headers=api_key_header)
        assert response.status_code == 405

    def test_content_type_validation(self, test_client, api_key_header):
        """Test content type validation for requests."""
        
        # Test with form data instead of JSON
        form_data = "text=Hello&source_lang=eng_Latn&target_lang=fra_Latn"
        response = test_client.post(
            "/translate",
            data=form_data,
            headers={**api_key_header, "Content-Type": "application/x-www-form-urlencoded"}
        )
        # Should reject non-JSON content
        assert response.status_code in [415, 422]
        
        # Test with no content type
        response = test_client.post(
            "/translate",
            data='{"text": "Hello", "source_lang": "eng_Latn", "target_lang": "fra_Latn"}',
            headers=api_key_header
        )
        # May accept or reject based on FastAPI defaults
        assert response.status_code in [200, 415, 422]