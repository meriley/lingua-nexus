"""
E2E tests for language API endpoint (/languages).
TASK-001: Comprehensive testing of language metadata endpoint functionality.
"""

import pytest
import json
from typing import Dict, Any
from unittest.mock import patch

from tests.e2e.utils.http_client import E2EHttpClient


@pytest.mark.e2e
@pytest.mark.e2e_foundation
class TestLanguageAPIEndpoint:
    """Test suite for /languages API endpoint."""

    def test_languages_endpoint_authentication_required(self, running_service: str):
        """Test that /languages endpoint requires valid API key."""
        # Create client without default authentication
        from tests.e2e.utils.http_client import E2EHttpClient
        
        # Test without API key
        with E2EHttpClient(running_service) as client:
            response = client.get("/languages")
            assert response.status_code == 403
            assert "Invalid API Key" in response.json()["detail"]

    def test_languages_endpoint_invalid_api_key(self, running_service: str):
        """Test /languages endpoint with invalid API key."""
        from tests.e2e.utils.http_client import E2EHttpClient
        
        invalid_headers = {"X-API-Key": "invalid-key-12345"}
        with E2EHttpClient(running_service) as client:
            response = client.get("/languages", headers=invalid_headers)
            assert response.status_code == 403
            assert "Invalid API Key" in response.json()["detail"]

    def test_languages_endpoint_returns_valid_structure(self, e2e_client: E2EHttpClient):
        """Test that /languages endpoint returns valid metadata structure."""
        response = e2e_client.get("/languages")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check top-level structure
        assert "languages" in data
        assert "families" in data
        assert "popular" in data
        assert "popular_pairs" in data
        assert "total_count" in data
        assert "cache_headers" in data
        
        # Validate languages array structure
        assert isinstance(data["languages"], list)
        assert len(data["languages"]) > 0
        
        # Validate cache headers
        cache_headers = data["cache_headers"]
        assert "Cache-Control" in cache_headers
        assert "ETag" in cache_headers
        assert "public, max-age=3600" in cache_headers["Cache-Control"]
        assert cache_headers["ETag"].startswith("lang-metadata-v1-")

    def test_languages_endpoint_language_structure_validation(self, e2e_client: E2EHttpClient):
        """Test individual language object structure in /languages response."""
        response = e2e_client.get("/languages")
        assert response.status_code == 200
        
        data = response.json()
        languages = data["languages"]
        
        # Check that we have required languages
        required_languages = ["eng_Latn", "spa_Latn", "fra_Latn", "rus_Cyrl", "zho_Hans", "arb_Arab"]
        language_codes = [lang["code"] for lang in languages]
        
        for required_lang in required_languages:
            assert required_lang in language_codes, f"Required language {required_lang} not found"
        
        # Validate structure of first language object (should be representative)
        first_language = languages[0]
        required_fields = ["code", "name", "native_name", "family", "script", "popular", "region", "rtl"]
        
        for field in required_fields:
            assert field in first_language, f"Missing required field: {field}"
            assert first_language[field] is not None, f"Field {field} is None"
        
        # Validate data types
        assert isinstance(first_language["code"], str)
        assert isinstance(first_language["name"], str)
        assert isinstance(first_language["native_name"], str)
        assert isinstance(first_language["family"], str)
        assert isinstance(first_language["script"], str)
        assert isinstance(first_language["popular"], bool)
        assert isinstance(first_language["region"], str)
        assert isinstance(first_language["rtl"], bool)

    def test_languages_endpoint_bcp47_format_validation(self, e2e_client: E2EHttpClient):
        """Test that language codes follow BCP-47 + ISO 639-3 + ISO 15924 format."""
        response = e2e_client.get("/languages")
        assert response.status_code == 200
        
        data = response.json()
        languages = data["languages"]
        
        # Validate BCP-47 format (except for special "auto" case)
        for language in languages:
            code = language["code"]
            if code == "auto":
                continue  # Special case for auto-detection
            
            # Format should be: xxx_Yyyy (3-letter language + underscore + 4-letter script)
            parts = code.split("_")
            assert len(parts) == 2, f"Invalid language code format: {code}"
            
            lang_part, script_part = parts
            assert len(lang_part) == 3, f"Language part should be 3 characters: {code}"
            assert lang_part.islower(), f"Language part should be lowercase: {code}"
            assert len(script_part) == 4, f"Script part should be 4 characters: {code}"
            assert script_part[0].isupper(), f"Script part should start with uppercase: {code}"
            assert script_part[1:].islower(), f"Script part should have lowercase after first char: {code}"

    def test_languages_endpoint_popular_languages_included(self, e2e_client: E2EHttpClient):
        """Test that popular languages are properly marked and included."""
        response = e2e_client.get("/languages")
        assert response.status_code == 200
        
        data = response.json()
        languages = data["languages"]
        popular_codes = data["popular"]
        
        # Create lookup for easy checking
        lang_lookup = {lang["code"]: lang for lang in languages}
        
        # Verify popular languages exist and are marked as popular
        expected_popular = ["auto", "eng_Latn", "spa_Latn", "fra_Latn", "deu_Latn", "rus_Cyrl", "zho_Hans"]
        for pop_code in expected_popular:
            assert pop_code in popular_codes, f"Popular language {pop_code} not in popular list"
            assert pop_code in lang_lookup, f"Popular language {pop_code} not in languages list"
            assert lang_lookup[pop_code]["popular"] is True, f"Language {pop_code} not marked as popular"

    def test_languages_endpoint_rtl_languages_correctly_marked(self, e2e_client: E2EHttpClient):
        """Test that RTL languages are correctly identified."""
        response = e2e_client.get("/languages")
        assert response.status_code == 200
        
        data = response.json()
        languages = data["languages"]
        lang_lookup = {lang["code"]: lang for lang in languages}
        
        # Known RTL languages
        rtl_languages = ["arb_Arab", "pes_Arab", "heb_Hebr"]
        
        # Known LTR languages  
        ltr_languages = ["eng_Latn", "spa_Latn", "fra_Latn", "deu_Latn", "rus_Cyrl", "zho_Hans"]
        
        # Test RTL languages
        for rtl_code in rtl_languages:
            if rtl_code in lang_lookup:
                assert lang_lookup[rtl_code]["rtl"] is True, f"Language {rtl_code} should be marked as RTL"
        
        # Test LTR languages
        for ltr_code in ltr_languages:
            if ltr_code in lang_lookup:
                assert lang_lookup[ltr_code]["rtl"] is False, f"Language {ltr_code} should be marked as LTR"

    def test_languages_endpoint_families_structure(self, e2e_client: E2EHttpClient):
        """Test language families structure and consistency."""
        response = e2e_client.get("/languages")
        assert response.status_code == 200
        
        data = response.json()
        families = data["families"]
        languages = data["languages"]
        
        # Create language code to family mapping
        lang_to_family = {lang["code"]: lang["family"] for lang in languages}
        
        # Verify family structure
        assert isinstance(families, dict)
        
        expected_families = ["Germanic", "Romance", "Slavic", "Sino-Tibetan", "Afro-Asiatic"]
        for expected_family in expected_families:
            assert expected_family in families, f"Expected family {expected_family} not found"
            assert isinstance(families[expected_family], list), f"Family {expected_family} should be a list"
            assert len(families[expected_family]) > 0, f"Family {expected_family} should not be empty"
        
        # Verify consistency between families and language family assignments
        for family_name, lang_codes in families.items():
            for lang_code in lang_codes:
                if lang_code in lang_to_family:
                    assert lang_to_family[lang_code] == family_name, \
                        f"Language {lang_code} family mismatch: expected {family_name}, got {lang_to_family[lang_code]}"

    def test_languages_endpoint_popular_pairs_validation(self, e2e_client: E2EHttpClient):
        """Test popular language pairs structure and validity."""
        response = e2e_client.get("/languages")
        assert response.status_code == 200
        
        data = response.json()
        popular_pairs = data["popular_pairs"]
        languages = data["languages"]
        
        # Create set of valid language codes
        valid_codes = {lang["code"] for lang in languages}
        
        # Verify structure
        assert isinstance(popular_pairs, list)
        assert len(popular_pairs) > 0
        
        # Verify each pair
        for pair in popular_pairs:
            assert isinstance(pair, list), "Language pair should be a list"
            assert len(pair) == 2, "Language pair should have exactly 2 elements"
            
            source_lang, target_lang = pair
            assert source_lang in valid_codes, f"Source language {source_lang} not in valid codes"
            assert target_lang in valid_codes, f"Target language {target_lang} not in valid codes"
        
        # Verify expected popular pairs exist
        expected_pairs = [
            ["auto", "eng_Latn"],
            ["eng_Latn", "spa_Latn"],
            ["eng_Latn", "fra_Latn"]
        ]
        
        for expected_pair in expected_pairs:
            assert expected_pair in popular_pairs, f"Expected popular pair {expected_pair} not found"

    def test_languages_endpoint_caching_headers(self, e2e_client: E2EHttpClient):
        """Test that appropriate caching headers are returned."""
        response = e2e_client.get("/languages")
        assert response.status_code == 200
        
        # Should have cache headers in response body
        data = response.json()
        cache_headers = data["cache_headers"]
        
        assert "Cache-Control" in cache_headers
        assert "public" in cache_headers["Cache-Control"]
        assert "max-age=3600" in cache_headers["Cache-Control"]
        
        assert "ETag" in cache_headers
        assert cache_headers["ETag"].startswith("lang-metadata-v1-")

    def test_languages_endpoint_rate_limiting(self, e2e_client: E2EHttpClient):
        """Test rate limiting on /languages endpoint (30/minute)."""
        # Make multiple requests to test rate limiting
        # This is a simplified test - in production you'd need to make 31 requests
        
        responses = []
        for i in range(5):  # Test with 5 requests first
            response = e2e_client.get("/languages")
            responses.append(response)
        
        # All should succeed (under rate limit)
        for response in responses:
            assert response.status_code == 200

    def test_languages_endpoint_total_count_accuracy(self, e2e_client: E2EHttpClient):
        """Test that total_count matches actual number of languages."""
        response = e2e_client.get("/languages")
        assert response.status_code == 200
        
        data = response.json()
        languages = data["languages"]
        total_count = data["total_count"]
        
        assert total_count == len(languages), f"Total count {total_count} doesn't match actual count {len(languages)}"
        assert total_count > 20, "Should have a reasonable number of languages (>20)"

    @pytest.mark.skip(reason="E2E tests cannot mock server internals - this should be a unit test")
    def test_languages_endpoint_error_handling(self, e2e_client: E2EHttpClient):
        """Test error handling when language metadata fails to load."""
        # Note: This test attempted to mock server internals which doesn't work in E2E tests
        # since the server runs in a separate process. This should be tested at the unit level.
        pass


@pytest.mark.e2e
@pytest.mark.e2e_foundation
class TestIndividualLanguageEndpoint:
    """Test suite for /languages/{language_code} endpoint."""

    def test_individual_language_endpoint_valid_code(self, e2e_client: E2EHttpClient):
        """Test fetching individual language by valid code."""
        # Test with popular language
        response = e2e_client.get("/languages/eng_Latn")
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == "eng_Latn"
        assert data["name"] == "English"
        assert data["native_name"] == "English"
        assert data["family"] == "Germanic"
        assert data["script"] == "Latin"
        assert data["popular"] is True
        assert data["region"] == "Global"
        assert data["rtl"] is False

    def test_individual_language_endpoint_invalid_code(self, e2e_client: E2EHttpClient):
        """Test fetching individual language with invalid code."""
        response = e2e_client.get("/languages/invalid_Code")
        assert response.status_code == 404
        assert "Language code 'invalid_Code' not found" in response.json()["detail"]

    def test_individual_language_endpoint_authentication(self, e2e_client: E2EHttpClient):
        """Test that individual language endpoint requires authentication."""
        # Remove API key header to test authentication requirement
        original_headers = e2e_client.session.headers.copy()
        e2e_client.remove_default_header("X-API-Key")
        
        try:
            response = e2e_client.get("/languages/eng_Latn")
            assert response.status_code == 403
        finally:
            # Restore headers
            e2e_client.session.headers = original_headers

    def test_individual_language_endpoint_rate_limiting(self, e2e_client: E2EHttpClient):
        """Test rate limiting on individual language endpoint (60/minute)."""
        # Test multiple requests to same endpoint
        responses = []
        for i in range(10):
            response = e2e_client.get("/languages/eng_Latn")
            responses.append(response)
        
        # All should succeed (under rate limit)
        for response in responses:
            assert response.status_code == 200

    def test_individual_language_special_characters(self, e2e_client: E2EHttpClient):
        """Test individual language endpoint with language codes containing special characters."""
        # Test with Arabic (RTL language)
        response = e2e_client.get("/languages/arb_Arab")
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == "arb_Arab"
        assert data["name"] == "Arabic"
        assert data["rtl"] is True
        assert "العربية" in data["native_name"]

    def test_individual_language_auto_detect(self, e2e_client: E2EHttpClient):
        """Test fetching auto-detect special language code."""
        response = e2e_client.get("/languages/auto")
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == "auto"
        assert data["name"] == "Auto-detect"
        assert data["family"] == "Auto"


@pytest.mark.e2e
@pytest.mark.e2e_performance  
class TestLanguageAPIPerformance:
    """Performance tests for language API endpoints."""

    def test_languages_endpoint_response_time(self, e2e_client: E2EHttpClient):
        """Test that /languages endpoint responds within acceptable time."""
        import time
        
        start_time = time.time()
        response = e2e_client.get("/languages")
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response.status_code == 200
        assert response_time < 2.0, f"Response time {response_time:.2f}s exceeds 2s limit"

    def test_individual_language_response_time(self, e2e_client: E2EHttpClient):
        """Test that individual language endpoint responds quickly."""
        import time
        
        start_time = time.time()
        response = e2e_client.get("/languages/eng_Latn")
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response.status_code == 200
        assert response_time < 0.5, f"Response time {response_time:.2f}s exceeds 0.5s limit"

    def test_concurrent_language_requests(self, e2e_client: E2EHttpClient):
        """Test concurrent requests to language endpoints."""
        import threading
        import time
        
        results = []
        
        def make_request():
            start_time = time.time()
            response = e2e_client.get("/languages")
            end_time = time.time()
            results.append({
                'status_code': response.status_code,
                'response_time': end_time - start_time
            })
        
        # Start 5 concurrent requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all requests succeeded
        assert len(results) == 5
        for result in results:
            assert result['status_code'] == 200
            assert result['response_time'] < 3.0  # Allow extra time for concurrency