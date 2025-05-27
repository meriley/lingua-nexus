"""E2E tests for API contract validation and HTTP protocol compliance."""

import pytest
import requests
import json
from typing import Dict, Any

from .utils.http_client import E2EHttpClient


@pytest.mark.e2e
@pytest.mark.e2e_foundation
class TestAPIContracts:
    """Test API specification compliance and HTTP protocol adherence."""
    
    def test_openapi_specification_compliance(self, e2e_client: E2EHttpClient):
        """Test OpenAPI schema validation and compliance."""
        # Get OpenAPI spec
        response = e2e_client.get("/openapi.json")
        
        assert response.is_success, f"Failed to get OpenAPI spec: {response.text}"
        assert response.json_data is not None, "OpenAPI spec should return JSON"
        
        openapi_spec = response.json_data
        
        # Validate basic OpenAPI structure
        assert "openapi" in openapi_spec, "Should have OpenAPI version"
        assert "info" in openapi_spec, "Should have info section"
        assert "paths" in openapi_spec, "Should have paths section"
        
        # Validate expected endpoints exist
        paths = openapi_spec["paths"]
        expected_endpoints = ["/health", "/translate", "/languages"]
        
        for endpoint in expected_endpoints:
            assert endpoint in paths, f"Endpoint {endpoint} should be documented"
        
        # Validate translate endpoint structure
        translate_path = paths.get("/translate", {})
        assert "post" in translate_path, "Translate should support POST method"
        
        post_spec = translate_path["post"]
        assert "requestBody" in post_spec, "POST should have request body spec"
        assert "responses" in post_spec, "POST should have response specs"
        
        # Validate response schemas
        responses = post_spec["responses"]
        assert "200" in responses, "Should document success response"
        assert "403" in responses or "422" in responses, "Should document error responses"
    
    def test_http_method_validation(self, e2e_client: E2EHttpClient):
        """Test proper HTTP method support and rejection."""
        # Test health endpoint - should support GET
        response = e2e_client.get("/health")
        assert response.is_success, "Health endpoint should support GET"
        
        # Test health endpoint - should not support POST
        response = e2e_client.post("/health")
        assert response.status_code == 405, "Health endpoint should reject POST with 405"
        
        # Test translate endpoint - should support POST
        translation_data = {
            "text": "Hello",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        response = e2e_client.post("/translate", json_data=translation_data)
        # Should either succeed or fail due to auth/validation, but not method error
        assert response.status_code != 405, "Translate endpoint should accept POST"
        
        # Test translate endpoint - should not support GET
        response = e2e_client.get("/translate")
        assert response.status_code == 405, "Translate endpoint should reject GET with 405"
        
        # Test languages endpoint - should support GET
        response = e2e_client.get("/languages")
        assert response.is_success, "Languages endpoint should support GET"
    
    def test_content_type_negotiation(self, e2e_client: E2EHttpClient):
        """Test application/json content type handling."""
        # Test with correct content type
        headers = {"Content-Type": "application/json"}
        translation_data = {
            "text": "Hello",
            "source_lang": "eng_Latn", 
            "target_lang": "fra_Latn"
        }
        
        response = e2e_client.post("/translate", json_data=translation_data, headers=headers)
        # Should not fail due to content type (may fail due to other reasons)
        assert response.status_code != 415, "Should accept application/json"
        
        # Test response content type
        if response.is_success:
            content_type = response.headers.get("content-type", "")
            assert "application/json" in content_type, "Response should be JSON"
        
        # Test health endpoint content type
        health_response = e2e_client.get("/health")
        if health_response.is_success:
            content_type = health_response.headers.get("content-type", "")
            assert "application/json" in content_type, "Health response should be JSON"
    
    def test_cors_headers_if_enabled(self, e2e_client: E2EHttpClient):
        """Test CORS configuration if enabled."""
        # Test preflight request
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,X-API-Key"
        }
        
        # Make OPTIONS request
        response = e2e_client.request("OPTIONS", "/translate", headers=headers)
        
        # CORS might or might not be enabled - test if present
        cors_headers = {
            "access-control-allow-origin",
            "access-control-allow-methods", 
            "access-control-allow-headers"
        }
        
        response_headers_lower = {k.lower(): v for k, v in response.headers.items()}
        
        if any(header in response_headers_lower for header in cors_headers):
            # CORS is enabled, validate proper configuration
            assert response.status_code == 200, "OPTIONS request should succeed"
            
            if "access-control-allow-origin" in response_headers_lower:
                origin = response_headers_lower["access-control-allow-origin"]
                assert origin in ["*", "http://localhost:3000"], f"Unexpected CORS origin: {origin}"
        else:
            # CORS not enabled is also valid
            pass
    
    def test_error_response_format_consistency(self, e2e_client: E2EHttpClient):
        """Test standard error response format across endpoints."""
        # Test 404 error format
        response = e2e_client.get("/nonexistent-endpoint")
        assert response.status_code == 404, "Should return 404 for non-existent endpoints"
        
        if response.json_data:
            # Check for consistent error format
            error_fields = {"detail", "error", "message"}
            has_error_field = any(field in response.json_data for field in error_fields)
            assert has_error_field, "Error response should have error information"
        
        # Test validation error format (invalid request body)
        invalid_translation_data = {
            "invalid_field": "value"
        }
        response = e2e_client.post("/translate", json_data=invalid_translation_data)
        
        if response.is_client_error and response.json_data:
            # Should have validation error details
            assert "detail" in response.json_data or "error" in response.json_data, \
                "Validation errors should provide details"
        
        # Test authentication error format (invalid API key)
        client_no_auth = E2EHttpClient(e2e_client.base_url)
        response = client_no_auth.post("/translate", json_data={
            "text": "Hello",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        })
        
        assert response.status_code == 403, "Should return 403 for invalid API key"
        
        if response.json_data:
            assert "detail" in response.json_data or "error" in response.json_data, \
                "Auth errors should provide details"
    
    def test_http_status_codes_compliance(self, e2e_client: E2EHttpClient):
        """Test proper HTTP status codes across all endpoints."""
        # Test successful responses
        health_response = e2e_client.get("/health")
        assert health_response.status_code == 200, "Health check should return 200"
        
        languages_response = e2e_client.get("/languages")
        assert languages_response.status_code == 200, "Languages should return 200"
        
        # Test valid translation request
        translation_data = {
            "text": "Hello",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        translation_response = e2e_client.post("/translate", json_data=translation_data)
        
        # Should be either 200 (success) or 4xx/5xx (expected errors)
        assert translation_response.status_code in [200, 400, 403, 422, 500], \
            f"Unexpected status code: {translation_response.status_code}"
        
        # Test method not allowed
        post_health_response = e2e_client.post("/health")
        assert post_health_response.status_code == 405, "Wrong method should return 405"
        
        # Test not found
        not_found_response = e2e_client.get("/not-found")
        assert not_found_response.status_code == 404, "Missing endpoint should return 404"
    
    def test_response_headers_consistency(self, e2e_client: E2EHttpClient):
        """Test consistent response headers across endpoints."""
        endpoints_to_test = [
            ("/health", "GET"),
            ("/languages", "GET"),
            ("/openapi.json", "GET")
        ]
        
        for endpoint, method in endpoints_to_test:
            if method == "GET":
                response = e2e_client.get(endpoint)
            else:
                response = e2e_client.request(method, endpoint)
            
            if response.is_success:
                # Check for standard headers
                headers = response.headers
                
                # Content-Type should be present for JSON responses
                assert "content-type" in headers, f"Missing Content-Type header for {endpoint}"
                
                # Server header might be present
                if "server" in headers:
                    server = headers["server"].lower()
                    assert "uvicorn" in server or "fastapi" in server or "python" in server, \
                        f"Unexpected server header: {headers['server']}"
    
    def test_request_validation_edge_cases(self, e2e_client: E2EHttpClient):
        """Test request validation edge cases and error handling."""
        # Test empty request body
        response = e2e_client.post("/translate", json_data={})
        assert response.is_client_error, "Empty request should be rejected"
        
        # Test malformed JSON (send raw data)
        response = e2e_client.request(
            "POST", 
            "/translate",
            headers={"Content-Type": "application/json"},
            data="invalid json"
        )
        assert response.is_client_error, "Malformed JSON should be rejected"
        
        # Test extremely large request
        large_text = "x" * 100000  # 100KB text
        large_request = {
            "text": large_text,
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        response = e2e_client.post("/translate", json_data=large_request, timeout=60)
        # Should either process or reject gracefully, not hang
        assert response.status_code != 0, "Should handle large requests without hanging"
    
    def test_api_versioning_consistency(self, e2e_client: E2EHttpClient):
        """Test API versioning and consistency."""
        # Check if API version is documented
        openapi_response = e2e_client.get("/openapi.json")
        
        if openapi_response.is_success and openapi_response.json_data:
            spec = openapi_response.json_data
            
            if "info" in spec and "version" in spec["info"]:
                version = spec["info"]["version"]
                assert isinstance(version, str), "API version should be a string"
                assert len(version) > 0, "API version should not be empty"
        
        # Test that all endpoints follow consistent patterns
        health_response = e2e_client.get("/health")
        languages_response = e2e_client.get("/languages")
        
        if health_response.is_success and languages_response.is_success:
            # Both should return JSON
            assert health_response.json_data is not None, "Health should return JSON"
            assert languages_response.json_data is not None, "Languages should return JSON"