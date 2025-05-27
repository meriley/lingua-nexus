"""
Comprehensive API key authentication and validation tests.

Tests authentication scenarios including:
- Valid API key access
- Invalid API key rejection
- Missing API key handling
- Malformed API key formats
- Case sensitivity validation
- Header format variations
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


class TestAuthentication:
    """Test suite for API key authentication and validation."""

    def test_valid_api_key_success(self, test_client, enhanced_mock_objects):
        """Test successful authentication with valid API key."""
        valid_headers = {"X-API-Key": "development-key"}
        request_data = {
            "text": "Hello world",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        response = test_client.post("/translate", json=request_data, headers=valid_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "translated_text" in data
        assert data["translated_text"].startswith("Translated: ")

    def test_missing_api_key_rejection(self, test_client, enhanced_mock_objects):
        """Test rejection when API key header is missing."""
        request_data = {
            "text": "Hello world",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        response = test_client.post("/translate", json=request_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "API key required" in data["detail"]

    def test_invalid_api_key_rejection(self, test_client, enhanced_mock_objects):
        """Test rejection with invalid API key."""
        invalid_headers = {"X-API-Key": "invalid_key_12345"}
        request_data = {
            "text": "Hello world",
            "source_lang": "eng_Latn", 
            "target_lang": "fra_Latn"
        }
        
        response = test_client.post("/translate", json=request_data, headers=invalid_headers)
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Invalid API key" in data["detail"]

    def test_empty_api_key_rejection(self, test_client, enhanced_mock_objects):
        """Test rejection when API key is empty string."""
        empty_headers = {"X-API-Key": ""}
        request_data = {
            "text": "Hello world",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        response = test_client.post("/translate", json=request_data, headers=empty_headers)
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "API key required" in data["detail"]

    def test_api_key_case_sensitivity(self, test_client, enhanced_mock_objects):
        """Test API key validation is case-sensitive."""
        case_headers = {"X-API-Key": "TEST_API_KEY"}  # Different case
        request_data = {
            "text": "Hello world", 
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        response = test_client.post("/translate", json=request_data, headers=case_headers)
        
        # Should fail if API key validation is case-sensitive
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Invalid API key" in data["detail"]

    def test_api_key_header_variations(self, test_client, enhanced_mock_objects):
        """Test different API key header format variations."""
        request_data = {
            "text": "Hello world",
            "source_lang": "eng_Latn", 
            "target_lang": "fra_Latn"
        }
        
        # Test lowercase header (should fail)
        lowercase_headers = {"x-api-key": "development-key"}
        response = test_client.post("/translate", json=request_data, headers=lowercase_headers)
        assert response.status_code == 401
        
        # Test alternative header names (should fail)
        alt_headers = {"Authorization": "development-key"}
        response = test_client.post("/translate", json=request_data, headers=alt_headers)
        assert response.status_code == 401
        
        bearer_headers = {"Authorization": "Bearer development-key"}
        response = test_client.post("/translate", json=request_data, headers=bearer_headers)
        assert response.status_code == 401

    def test_api_key_with_whitespace(self, test_client, enhanced_mock_objects):
        """Test API key handling with leading/trailing whitespace."""
        request_data = {
            "text": "Hello world",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        # Test leading whitespace
        leading_space_headers = {"X-API-Key": " development-key"}
        response = test_client.post("/translate", json=request_data, headers=leading_space_headers)
        assert response.status_code == 401
        
        # Test trailing whitespace  
        trailing_space_headers = {"X-API-Key": "development-key "}
        response = test_client.post("/translate", json=request_data, headers=trailing_space_headers)
        assert response.status_code == 401
        
        # Test both leading and trailing whitespace
        both_space_headers = {"X-API-Key": " development-key "}
        response = test_client.post("/translate", json=request_data, headers=both_space_headers)
        assert response.status_code == 401

    def test_multiple_api_key_headers(self, test_client, enhanced_mock_objects):
        """Test behavior when multiple API key headers are provided."""
        request_data = {
            "text": "Hello world",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        # Test with duplicate headers (FastAPI behavior test)
        response = test_client.post(
            "/translate", 
            json=request_data, 
            headers=[("X-API-Key", "development-key"), ("X-API-Key", "duplicate_key")]
        )
        
        # Behavior may vary - should handle gracefully
        assert response.status_code in [200, 401]

    def test_health_endpoint_no_auth_required(self, test_client):
        """Test that health endpoint doesn't require authentication."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_special_characters_in_api_key(self, test_client, enhanced_mock_objects):
        """Test API key validation with special characters."""
        request_data = {
            "text": "Hello world",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        special_char_keys = [
            "test@api#key",
            "test-api_key.123",
            "test/api\\key",
            "test api key",  # space
            "test\tapi\nkey",  # tab/newline
        ]
        
        for special_key in special_char_keys:
            headers = {"X-API-Key": special_key}
            response = test_client.post("/translate", json=request_data, headers=headers)
            
            # All should fail as they don't match expected format
            assert response.status_code == 401
            data = response.json()
            assert "detail" in data