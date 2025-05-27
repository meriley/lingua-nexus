"""
Test rate limiting functionality for the NLLB Translation API.

This module tests the SlowAPI rate limiting implementation with 10 requests/minute limit.
Tests cover both sequential and concurrent request scenarios to ensure proper
rate limit enforcement and error handling.
"""

import pytest
import time
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient


class TestRateLimiting:
    """Test cases for API rate limiting functionality."""
    
    def test_rate_limit_enforcement_sequential(self, test_client, enhanced_mock_objects, api_key_header):
        """Test basic rate limit enforcement - 10 requests/minute limit with sequential requests."""
        # Clear any existing rate limit state by resetting the storage
        try:
            # Try to clear the storage (implementation may vary)
            storage = test_client.app.state.limiter._storage
            if hasattr(storage, 'storage'):
                storage.storage.clear()
            elif hasattr(storage, '_storage'):
                storage._storage.clear()
        except Exception:
            # If clearing fails, we'll proceed with the test
            pass
        
        request_data = {
            "text": "Hello world",
            "source_lang": "eng_Latn",
            "target_lang": "rus_Cyrl"
        }
        
        successful_requests = 0
        rate_limited_requests = 0
        
        # Send 12 requests sequentially to test rate limiting
        for i in range(12):
            response = test_client.post(
                "/translate", 
                json=request_data, 
                headers=api_key_header
            )
            
            if response.status_code == 200:
                successful_requests += 1
                assert "translated_text" in response.json()
                assert response.json()["translated_text"].startswith("Translated:")
            elif response.status_code == 429:
                rate_limited_requests += 1
                assert "Rate limit exceeded" in response.json()["detail"]
            else:
                pytest.fail(f"Unexpected status code: {response.status_code}")
        
        # Should have exactly 10 successful requests and 2 rate-limited
        assert successful_requests == 10, f"Expected 10 successful requests, got {successful_requests}"
        assert rate_limited_requests == 2, f"Expected 2 rate-limited requests, got {rate_limited_requests}"
    
    def test_rate_limit_enforcement_concurrent(self, test_client, enhanced_mock_objects, api_key_header):
        """Test rate limiting with concurrent requests."""
        # Clear any existing rate limit state
        try:
            storage = test_client.app.state.limiter._storage
            if hasattr(storage, 'storage'):
                storage.storage.clear()
            elif hasattr(storage, '_storage'):
                storage._storage.clear()
        except Exception:
            pass
        
        request_data = {
            "text": "Concurrent test",
            "source_lang": "eng_Latn", 
            "target_lang": "rus_Cyrl"
        }
        
        def make_request():
            """Helper function to make a single request."""
            return test_client.post(
                "/translate",
                json=request_data,
                headers=api_key_header
            )
        
        # Use ThreadPoolExecutor to simulate concurrent requests
        with ThreadPoolExecutor(max_workers=15) as executor:
            # Submit 15 concurrent requests
            futures = [executor.submit(make_request) for _ in range(15)]
            responses = [future.result() for future in futures]
        
        # Analyze results
        successful_responses = [r for r in responses if r.status_code == 200]
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        other_responses = [r for r in responses if r.status_code not in [200, 429]]
        
        # Should have at most 10 successful requests (some might be rate limited)
        assert len(successful_responses) <= 10, f"Too many successful requests: {len(successful_responses)}"
        assert len(rate_limited_responses) >= 5, f"Expected at least 5 rate limited requests, got {len(rate_limited_responses)}"
        assert len(other_responses) == 0, f"Unexpected response codes: {[r.status_code for r in other_responses]}"
        
        # Verify successful responses have correct format
        for response in successful_responses:
            json_data = response.json()
            assert "translated_text" in json_data
            assert json_data["translated_text"].startswith("Translated:")
        
        # Verify rate limited responses have correct error message
        for response in rate_limited_responses:
            json_data = response.json()
            assert "Rate limit exceeded" in json_data["detail"]
    
    def test_rate_limit_per_client_isolation(self, test_client, enhanced_mock_objects):
        """Test that rate limits are properly isolated per client."""
        # Clear any existing rate limit state
        try:
            storage = test_client.app.state.limiter._storage
            if hasattr(storage, 'storage'):
                storage.storage.clear()
            elif hasattr(storage, '_storage'):
                storage._storage.clear()
        except Exception:
            pass
        
        # Create two different API keys
        api_key_1 = {"X-API-Key": "test_api_key_1"}
        api_key_2 = {"X-API-Key": "test_api_key_2"}
        
        # Mock different API keys for this test
        import app.main
        original_get_api_key = app.main.get_api_key
        
        async def mock_get_api_key(api_key_header: str):
            if api_key_header in ["test_api_key_1", "test_api_key_2"]:
                return api_key_header
            raise HTTPException(status_code=403, detail="Invalid API Key")
        
        app.main.get_api_key = mock_get_api_key
        
        try:
            request_data = {
                "text": "Rate limit isolation test",
                "source_lang": "eng_Latn",
                "target_lang": "rus_Cyrl"
            }
            
            # Send 10 requests with first API key - should all succeed
            client_1_responses = []
            for _ in range(10):
                response = test_client.post("/translate", json=request_data, headers=api_key_1)
                client_1_responses.append(response)
            
            # Send 10 requests with second API key - should also all succeed
            client_2_responses = []
            for _ in range(10):
                response = test_client.post("/translate", json=request_data, headers=api_key_2)
                client_2_responses.append(response)
            
            # All requests from both clients should succeed (rate limits are per client)
            for response in client_1_responses:
                assert response.status_code == 200, f"Client 1 request failed: {response.status_code}"
            
            for response in client_2_responses:
                assert response.status_code == 200, f"Client 2 request failed: {response.status_code}"
                
        finally:
            # Restore original function
            app.main.get_api_key = original_get_api_key
    
    def test_rate_limit_reset_behavior(self, test_client, enhanced_mock_objects, api_key_header):
        """Test rate limit reset behavior over time."""
        # Clear any existing rate limit state
        try:
            storage = test_client.app.state.limiter._storage
            if hasattr(storage, 'storage'):
                storage.storage.clear()
            elif hasattr(storage, '_storage'):
                storage._storage.clear()
        except Exception:
            pass
        
        request_data = {
            "text": "Rate limit reset test",
            "source_lang": "eng_Latn",
            "target_lang": "rus_Cyrl"
        }
        
        # Send 10 requests to reach the limit
        for _ in range(10):
            response = test_client.post("/translate", json=request_data, headers=api_key_header)
            assert response.status_code == 200
        
        # 11th request should be rate limited
        response = test_client.post("/translate", json=request_data, headers=api_key_header)
        assert response.status_code == 429
        
        # Note: In real scenarios, we would wait for the rate limit window to reset
        # For testing purposes, we can clear the limiter storage to simulate reset
        try:
            storage = test_client.app.state.limiter._storage
            if hasattr(storage, 'storage'):
                storage.storage.clear()
            elif hasattr(storage, '_storage'):
                storage._storage.clear()
        except Exception:
            pass
        
        # After reset, requests should work again
        response = test_client.post("/translate", json=request_data, headers=api_key_header)
        assert response.status_code == 200
        assert "translated_text" in response.json()
    
    def test_rate_limit_with_invalid_requests(self, test_client, enhanced_mock_objects, api_key_header):
        """Test that rate limiting applies even to requests that would fail validation."""
        # Clear any existing rate limit state
        try:
            storage = test_client.app.state.limiter._storage
            if hasattr(storage, 'storage'):
                storage.storage.clear()
            elif hasattr(storage, '_storage'):
                storage._storage.clear()
        except Exception:
            pass
        
        # Send 10 valid requests to reach rate limit
        valid_request = {
            "text": "Valid request",
            "source_lang": "eng_Latn",
            "target_lang": "rus_Cyrl"
        }
        
        for _ in range(10):
            response = test_client.post("/translate", json=valid_request, headers=api_key_header)
            assert response.status_code == 200
        
        # Now send an invalid request - should still be rate limited, not validation error
        invalid_request = {
            "text": "",  # Empty text should cause validation error
            "source_lang": "eng_Latn",
            "target_lang": "rus_Cyrl"
        }
        
        response = test_client.post("/translate", json=invalid_request, headers=api_key_header)
        # Should be rate limited (429) rather than validation error (422)
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]
    
    def test_rate_limit_error_response_format(self, test_client, enhanced_mock_objects, api_key_header):
        """Test that rate limit error responses have the correct format."""
        # Clear any existing rate limit state
        try:
            storage = test_client.app.state.limiter._storage
            if hasattr(storage, 'storage'):
                storage.storage.clear()
            elif hasattr(storage, '_storage'):
                storage._storage.clear()
        except Exception:
            pass
        
        request_data = {
            "text": "Rate limit format test",
            "source_lang": "eng_Latn",
            "target_lang": "rus_Cyrl"
        }
        
        # Exhaust rate limit
        for _ in range(10):
            test_client.post("/translate", json=request_data, headers=api_key_header)
        
        # Get rate limited response
        response = test_client.post("/translate", json=request_data, headers=api_key_header)
        
        assert response.status_code == 429
        
        json_data = response.json()
        assert "detail" in json_data
        assert isinstance(json_data["detail"], str)
        assert "Rate limit exceeded" in json_data["detail"]
        
        # Check that standard rate limiting headers might be present
        # Note: SlowAPI typically adds these headers
        headers = response.headers
        # Common rate limiting headers (may or may not be present depending on SlowAPI config)
        possible_headers = ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset", "Retry-After"]
        
        # At least verify the response is properly formatted JSON
        assert json_data is not None
        assert isinstance(json_data, dict)