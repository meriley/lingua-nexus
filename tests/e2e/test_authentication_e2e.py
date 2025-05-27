"""E2E tests for authentication over real HTTP connections."""

import pytest
import threading
import time
from typing import Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

from .utils.http_client import E2EHttpClient, E2EHttpClientPool
from .utils.service_manager import ServiceConfig


@pytest.mark.e2e
@pytest.mark.e2e_foundation  
class TestAuthenticationE2E:
    """Test end-to-end authentication scenarios over real HTTP."""
    
    def test_valid_api_key_authentication(self, running_service: str, test_config):
        """Test that valid API key allows access to protected endpoints."""
        valid_api_key = test_config.VALID_CONFIGS["default"].api_key
        
        # Test with valid API key
        client = E2EHttpClient(running_service)
        client.set_api_key(valid_api_key)
        
        # Test protected endpoint access
        translation_response = client.translate(
            text="Hello",
            source_lang="eng_Latn",
            target_lang="fra_Latn"
        )
        
        # Should not be rejected due to authentication
        assert translation_response.status_code != 403, "Valid API key should not return 403"
        
        # Test languages endpoint (might not require auth)
        languages_response = client.get_supported_languages()
        assert languages_response.is_success, "Languages endpoint should be accessible"
        
        # Test health endpoint (typically doesn't require auth)
        health_response = client.health_check()
        assert health_response.is_success, "Health endpoint should be accessible"
    
    def test_invalid_api_key_rejection(self, running_service: str):
        """Test that invalid API key returns 403 Forbidden."""
        invalid_api_key = "invalid-key-12345"
        
        client = E2EHttpClient(running_service)
        client.set_api_key(invalid_api_key)
        
        # Test translation endpoint with invalid key
        translation_response = client.translate(
            text="Hello",
            source_lang="eng_Latn",
            target_lang="fra_Latn"
        )
        
        assert translation_response.status_code == 403, \
            f"Invalid API key should return 403, got {translation_response.status_code}"
        
        # Verify error message is informative
        if translation_response.json_data:
            error_info = translation_response.json_data
            assert "detail" in error_info or "error" in error_info, \
                "Error response should contain details"
    
    def test_missing_api_key_handling(self, running_service: str):
        """Test that missing API key returns 403 Forbidden."""
        client = E2EHttpClient(running_service)
        # Intentionally don't set API key
        
        # Test translation endpoint without API key
        translation_response = client.translate(
            text="Hello",
            source_lang="eng_Latn",
            target_lang="fra_Latn"
        )
        
        assert translation_response.status_code == 403, \
            f"Missing API key should return 403, got {translation_response.status_code}"
        
        # Verify error response format
        if translation_response.json_data:
            error_info = translation_response.json_data
            assert "detail" in error_info or "error" in error_info, \
                "Missing auth error should provide details"
    
    def test_api_key_header_case_sensitivity(self, running_service: str, test_config):
        """Test X-API-Key header case sensitivity and variations."""
        valid_api_key = test_config.VALID_CONFIGS["default"].api_key
        
        # Test different header case variations
        header_variations = [
            "X-API-Key",
            "x-api-key", 
            "X-Api-Key",
            "X-API-KEY"
        ]
        
        for header_name in header_variations:
            client = E2EHttpClient(running_service)
            client.set_default_header(header_name, valid_api_key)
            
            translation_response = client.translate(
                text="Hello",
                source_lang="eng_Latn",
                target_lang="fra_Latn"
            )
            
            # HTTP headers are case-insensitive, so all should work
            assert translation_response.status_code != 403, \
                f"Header '{header_name}' should be accepted (case-insensitive)"
    
    def test_multiple_simultaneous_authenticated_clients(self, running_service: str, test_config):
        """Test concurrent authentication with multiple clients."""
        valid_api_key = test_config.VALID_CONFIGS["default"].api_key
        num_clients = 5
        
        # Create multiple clients with authentication
        with E2EHttpClientPool(running_service, pool_size=num_clients) as client_pool:
            client_pool.set_api_key_for_all(valid_api_key)
            
            clients = client_pool.get_all_clients()
            
            def make_authenticated_request(client, request_id):
                """Make an authenticated request and return result."""
                response = client.translate(
                    text=f"Hello {request_id}",
                    source_lang="eng_Latn", 
                    target_lang="fra_Latn"
                )
                return {
                    "client_id": request_id,
                    "status_code": response.status_code,
                    "response_time": response.response_time,
                    "success": response.status_code != 403
                }
            
            # Execute concurrent requests
            results = []
            with ThreadPoolExecutor(max_workers=num_clients) as executor:
                futures = [
                    executor.submit(make_authenticated_request, client, i) 
                    for i, client in enumerate(clients)
                ]
                
                for future in as_completed(futures):
                    results.append(future.result())
            
            # Verify all requests were authenticated successfully
            assert len(results) == num_clients, "All requests should complete"
            
            for result in results:
                assert result["success"], \
                    f"Client {result['client_id']} failed authentication: {result['status_code']}"
                assert result["response_time"] < 10.0, \
                    f"Client {result['client_id']} took too long: {result['response_time']}s"
    
    def test_api_key_with_special_characters(self, running_service: str, e2e_service_manager, test_config):
        """Test API key handling with special characters."""
        # Test with various special characters in API key
        special_api_keys = [
            "test-key-with-dashes-123",
            "test_key_with_underscores_456", 
            "testkeywithoutspecialchars789",
            "test.key.with.dots.000",
            "test+key+with+plus+111"
        ]
        
        # Since we can't easily change the server's expected API key,
        # we'll test that these keys are properly transmitted and rejected
        for special_key in special_api_keys:
            client = E2EHttpClient(running_service)
            client.set_api_key(special_key)
            
            translation_response = client.translate(
                text="Hello",
                source_lang="eng_Latn",
                target_lang="fra_Latn"
            )
            
            # These should be rejected (since they're not the valid key)
            # but the rejection should be due to invalid key, not malformed request
            assert translation_response.status_code == 403, \
                f"Special character key '{special_key}' should be properly handled and rejected"
            
            # Verify the request was properly formed (not 400 Bad Request)
            assert translation_response.status_code != 400, \
                f"Special character key '{special_key}' should not cause malformed request"
    
    def test_authentication_isolation_between_clients(self, running_service: str, test_config):
        """Test that authentication is properly isolated between different clients."""
        valid_api_key = test_config.VALID_CONFIGS["default"].api_key
        invalid_api_key = "invalid-key-99999"
        
        # Create two clients with different API keys
        client_valid = E2EHttpClient(running_service)
        client_invalid = E2EHttpClient(running_service)
        
        client_valid.set_api_key(valid_api_key)
        client_invalid.set_api_key(invalid_api_key)
        
        # Test that valid client works
        valid_response = client_valid.translate(
            text="Hello",
            source_lang="eng_Latn",
            target_lang="fra_Latn"
        )
        assert valid_response.status_code != 403, "Valid client should be authenticated"
        
        # Test that invalid client is rejected
        invalid_response = client_invalid.translate(
            text="Hello",
            source_lang="eng_Latn",
            target_lang="fra_Latn"
        )
        assert invalid_response.status_code == 403, "Invalid client should be rejected"
        
        # Test that valid client still works after invalid client request
        valid_response2 = client_valid.translate(
            text="Goodbye",
            source_lang="eng_Latn",
            target_lang="fra_Latn"
        )
        assert valid_response2.status_code != 403, "Valid client should remain authenticated"
    
    def test_authentication_with_session_persistence(self, running_service: str, test_config):
        """Test authentication behavior with persistent HTTP sessions."""
        valid_api_key = test_config.VALID_CONFIGS["default"].api_key
        
        client = E2EHttpClient(running_service)
        client.set_api_key(valid_api_key)
        
        # Make multiple requests with the same client/session
        for i in range(5):
            response = client.translate(
                text=f"Hello {i}",
                source_lang="eng_Latn",
                target_lang="fra_Latn"
            )
            
            assert response.status_code != 403, \
                f"Request {i} should remain authenticated in same session"
            
            # Small delay between requests
            time.sleep(0.1)
    
    def test_authentication_error_message_quality(self, running_service: str):
        """Test that authentication error messages are helpful and consistent."""
        test_cases = [
            {
                "name": "missing_header",
                "setup": lambda client: None,  # Don't set any auth header
                "expected_status": 403
            },
            {
                "name": "empty_api_key",
                "setup": lambda client: client.set_api_key(""),
                "expected_status": 403
            },
            {
                "name": "invalid_api_key",
                "setup": lambda client: client.set_api_key("definitely-invalid-key"),
                "expected_status": 403
            }
        ]
        
        for test_case in test_cases:
            client = E2EHttpClient(running_service)
            
            # Setup the test condition
            if test_case["setup"]:
                test_case["setup"](client)
            
            # Make request
            response = client.translate(
                text="Hello",
                source_lang="eng_Latn",
                target_lang="fra_Latn"
            )
            
            # Verify status code
            assert response.status_code == test_case["expected_status"], \
                f"Test '{test_case['name']}' should return {test_case['expected_status']}"
            
            # Verify error message quality
            if response.json_data:
                error_data = response.json_data
                
                # Should have some error information
                has_error_info = any(
                    key in error_data 
                    for key in ["detail", "error", "message"]
                )
                assert has_error_info, \
                    f"Test '{test_case['name']}' should provide error details"
                
                # Error message should be non-empty string
                for key in ["detail", "error", "message"]:
                    if key in error_data:
                        assert isinstance(error_data[key], str), \
                            f"Error {key} should be string"
                        assert len(error_data[key]) > 0, \
                            f"Error {key} should not be empty"