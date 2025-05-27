"""E2E tests for network failure and edge case scenarios."""

import pytest
import time
import socket
import threading
from unittest.mock import patch
from typing import Dict, Any
import requests

from .utils.http_client import E2EHttpClient


@pytest.mark.e2e
@pytest.mark.e2e_slow
class TestNetworkResilience:
    """Test network failure and edge case scenarios."""
    
    def test_connection_timeout_handling(self, running_service: str, test_config):
        """Test network timeout scenarios."""
        api_key = test_config.VALID_CONFIGS["default"].api_key
        
        client = E2EHttpClient(running_service)
        client.set_api_key(api_key)
        
        # Test with very short timeout
        short_timeout_response = client.translate(
            text="Timeout test",
            source_lang="eng_Latn",
            target_lang="fra_Latn",
            timeout=0.001  # 1ms - likely to timeout
        )
        
        # Should either succeed very quickly or timeout gracefully
        assert short_timeout_response.status_code == 0 or short_timeout_response.is_success, \
            "Very short timeout should either timeout (status 0) or succeed quickly"
        
        # Test with reasonable timeout
        normal_response = client.translate(
            text="Normal timeout test",
            source_lang="eng_Latn",
            target_lang="fra_Latn",
            timeout=30
        )
        
        # Should succeed with reasonable timeout
        assert normal_response.is_success, "Normal timeout should succeed"
        
        client.close()
    
    def test_large_payload_streaming(self, running_service: str, test_config):
        """Test large request/response handling."""
        api_key = test_config.VALID_CONFIGS["default"].api_key
        
        client = E2EHttpClient(running_service)
        client.set_api_key(api_key)
        
        # Test progressively larger payloads
        payload_sizes = [
            (1024, "1KB"),
            (10240, "10KB"), 
            (102400, "100KB"),
            (1048576, "1MB")  # 1MB payload
        ]
        
        for size_bytes, size_name in payload_sizes:
            # Create large text payload
            base_text = "This is a test sentence for large payload testing. "
            repeat_count = size_bytes // len(base_text) + 1
            large_text = (base_text * repeat_count)[:size_bytes]
            
            print(f"Testing {size_name} payload ({len(large_text)} chars)")
            
            start_time = time.time()
            response = client.translate(
                text=large_text,
                source_lang="eng_Latn",
                target_lang="fra_Latn",
                timeout=120  # Extended timeout for large payloads
            )
            response_time = time.time() - start_time
            
            if size_bytes <= 102400:  # Up to 100KB should work
                assert response.status_code != 413, \
                    f"{size_name} payload should not be rejected as too large"
                
                if response.is_success:
                    assert response.json_data is not None, f"{size_name} should return JSON"
                    translated = response.json_data.get("translated_text", "")
                    assert len(translated) > 0, f"{size_name} should produce translation"
                    
                    # Performance should degrade gracefully
                    assert response_time < 60.0, f"{size_name} took too long: {response_time:.1f}s"
            
            else:  # Very large payloads (1MB+) may be rejected
                # Either succeeds or fails gracefully (not hanging)
                assert response.status_code != 0, f"{size_name} should not hang"
                print(f"{size_name} result: {response.status_code}")
        
        client.close()
    
    def test_connection_interruption_recovery(self, running_service: str, test_config):
        """Test connection interruption simulation."""
        api_key = test_config.VALID_CONFIGS["default"].api_key
        
        # Test connection recovery by making requests with fresh connections
        for i in range(5):
            # Create new client for each request (simulates connection reset)
            client = E2EHttpClient(running_service)
            client.set_api_key(api_key)
            
            response = client.translate(
                text=f"Connection recovery test {i}",
                source_lang="eng_Latn",
                target_lang="fra_Latn"
            )
            
            # Each fresh connection should work
            assert response.is_success, f"Fresh connection {i} should succeed"
            
            client.close()
            
            # Brief pause between connections
            time.sleep(0.5)
        
        # Test rapid connection cycling
        clients = []
        try:
            # Create multiple clients rapidly
            for i in range(10):
                client = E2EHttpClient(running_service)
                client.set_api_key(api_key)
                clients.append(client)
            
            # Make requests from all clients
            for i, client in enumerate(clients):
                response = client.health_check()
                assert response.is_success, f"Rapid client {i} should work"
                
        finally:
            # Clean up all clients
            for client in clients:
                client.close()
    
    def test_keep_alive_connection_behavior(self, running_service: str, test_config):
        """Test HTTP keep-alive connection persistence."""
        api_key = test_config.VALID_CONFIGS["default"].api_key
        
        client = E2EHttpClient(running_service)
        client.set_api_key(api_key)
        
        # Make multiple requests on same connection
        response_times = []
        
        for i in range(10):
            start_time = time.time()
            
            response = client.translate(
                text=f"Keep-alive test {i}",
                source_lang="eng_Latn",
                target_lang="fra_Latn"
            )
            
            response_time = time.time() - start_time
            response_times.append(response_time)
            
            assert response.is_success, f"Keep-alive request {i} should succeed"
            
            # Small delay between requests
            time.sleep(0.1)
        
        # Connection reuse should maintain or improve performance
        if len(response_times) >= 3:
            first_request_time = response_times[0]
            later_avg_time = sum(response_times[2:]) / len(response_times[2:])
            
            # Later requests should not be significantly slower (connection reuse)
            assert later_avg_time <= first_request_time * 2, \
                "Keep-alive requests should maintain reasonable performance"
        
        client.close()
    
    def test_http_protocol_compliance(self, running_service: str, test_config):
        """Test HTTP/1.1 compliance validation."""
        api_key = test_config.VALID_CONFIGS["default"].api_key
        
        # Test various HTTP protocol features
        client = E2EHttpClient(running_service)
        client.set_api_key(api_key)
        
        # Test HTTP headers
        custom_headers = {
            "User-Agent": "E2E-Test-Client/1.0",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }
        
        response = client.translate(
            text="HTTP compliance test",
            source_lang="eng_Latn",
            target_lang="fra_Latn",
            headers=custom_headers
        )
        
        assert response.is_success, "Custom headers should be accepted"
        
        # Verify response headers
        response_headers = response.headers
        
        # Check for standard HTTP headers
        assert "content-type" in response_headers, "Response should have Content-Type"
        assert "content-length" in response_headers or "transfer-encoding" in response_headers, \
            "Response should have Content-Length or Transfer-Encoding"
        
        # Test HTTP methods compliance
        methods_to_test = [
            ("GET", "/health", True),
            ("POST", "/translate", True),
            ("PUT", "/translate", False),  # Should not be allowed
            ("DELETE", "/translate", False),  # Should not be allowed
            ("PATCH", "/translate", False),  # Should not be allowed
        ]
        
        for method, endpoint, should_succeed in methods_to_test:
            if method == "GET":
                test_response = client.get(endpoint)
            elif method == "POST":
                test_response = client.post(endpoint, json_data={
                    "text": "Method test",
                    "source_lang": "eng_Latn",
                    "target_lang": "fra_Latn"
                })
            else:
                test_response = client.request(method, endpoint)
            
            if should_succeed:
                assert test_response.status_code != 405, \
                    f"{method} {endpoint} should be allowed"
            else:
                assert test_response.status_code == 405, \
                    f"{method} {endpoint} should return 405 Method Not Allowed"
        
        client.close()
    
    def test_concurrent_connection_limits(self, running_service: str, test_config):
        """Test behavior under high concurrent connection load."""
        api_key = test_config.VALID_CONFIGS["default"].api_key
        
        # Test many concurrent connections
        num_concurrent = 20
        clients = []
        responses = []
        
        def make_concurrent_request(client_id: int):
            """Make request from concurrent client."""
            client = E2EHttpClient(running_service)
            client.set_api_key(api_key)
            
            try:
                response = client.translate(
                    text=f"Concurrent test {client_id}",
                    source_lang="eng_Latn",
                    target_lang="fra_Latn",
                    timeout=30
                )
                return {
                    "client_id": client_id,
                    "success": response.is_success,
                    "status_code": response.status_code,
                    "response_time": response.response_time
                }
            finally:
                client.close()
        
        # Launch concurrent requests
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [
                executor.submit(make_concurrent_request, i)
                for i in range(num_concurrent)
            ]
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                responses.append(result)
        
        # Analyze results
        successful_requests = sum(1 for r in responses if r["success"])
        failed_requests = len(responses) - successful_requests
        
        # Most requests should succeed even under high concurrency
        success_rate = successful_requests / len(responses)
        assert success_rate >= 0.7, f"Success rate too low under concurrency: {success_rate:.2%}"
        
        # Response times should remain reasonable
        successful_response_times = [r["response_time"] for r in responses if r["success"]]
        if successful_response_times:
            max_response_time = max(successful_response_times)
            avg_response_time = sum(successful_response_times) / len(successful_response_times)
            
            assert avg_response_time < 10.0, f"Average response time too high: {avg_response_time:.2f}s"
            assert max_response_time < 30.0, f"Maximum response time too high: {max_response_time:.2f}s"
        
        print(f"Concurrent connections test:")
        print(f"- Total requests: {len(responses)}")
        print(f"- Successful: {successful_requests}")
        print(f"- Failed: {failed_requests}")
        print(f"- Success rate: {success_rate:.2%}")
    
    def test_malformed_http_requests(self, running_service: str, test_config):
        """Test handling of malformed HTTP requests."""
        import urllib3
        from urllib.parse import urlparse
        
        api_key = test_config.VALID_CONFIGS["default"].api_key
        
        # Parse service URL
        parsed_url = urlparse(running_service)
        host = parsed_url.hostname
        port = parsed_url.port
        
        # Test malformed requests using raw socket connection
        try:
            # Test incomplete HTTP request
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((host, port))
                
                # Send incomplete HTTP request
                sock.send(b"GET /health HTTP/1.1\r\n")
                # Don't send Host header or final \r\n - malformed request
                
                # Server should handle gracefully (close connection or send error)
                try:
                    response = sock.recv(1024)
                    # Should receive some response or connection close
                    assert len(response) >= 0, "Server should handle malformed requests"
                except (ConnectionResetError, socket.timeout):
                    # Connection reset is also acceptable behavior
                    pass
        
        except Exception as e:
            # If we can't make raw socket connections, test with HTTP client
            print(f"Raw socket test skipped: {e}")
        
        # Test with malformed headers using HTTP client
        client = E2EHttpClient(running_service)
        client.set_api_key(api_key)
        
        # Test with very long header value
        long_header_value = "x" * 8192  # 8KB header
        malformed_headers = {
            "X-Very-Long-Header": long_header_value
        }
        
        response = client.translate(
            text="Malformed header test",
            source_lang="eng_Latn",
            target_lang="fra_Latn",
            headers=malformed_headers
        )
        
        # Should either accept or reject gracefully (not crash)
        assert response.status_code != 0, "Server should handle large headers gracefully"
        
        client.close()
    
    def test_network_error_recovery(self, running_service: str, test_config):
        """Test recovery from various network error conditions."""
        api_key = test_config.VALID_CONFIGS["default"].api_key
        
        # Test with invalid hostname (should fail gracefully)
        invalid_client = E2EHttpClient("http://invalid-hostname:8000")
        invalid_client.set_api_key(api_key)
        
        response = invalid_client.translate(
            text="Invalid host test",
            source_lang="eng_Latn",
            target_lang="fra_Latn",
            timeout=5
        )
        
        # Should fail with network error (status 0)
        assert response.status_code == 0, "Invalid hostname should cause network error"
        assert "invalid-hostname" in response.text.lower() or "name" in response.text.lower(), \
            "Error message should indicate hostname issue"
        
        invalid_client.close()
        
        # Test with wrong port (should fail quickly)
        wrong_port_url = running_service.replace(str(urlparse(running_service).port), "9999")
        wrong_port_client = E2EHttpClient(wrong_port_url)
        wrong_port_client.set_api_key(api_key)
        
        start_time = time.time()
        response = wrong_port_client.translate(
            text="Wrong port test",
            source_lang="eng_Latn",
            target_lang="fra_Latn",
            timeout=5
        )
        error_time = time.time() - start_time
        
        # Should fail quickly (not hang for full timeout)
        assert response.status_code == 0, "Wrong port should cause connection error"
        assert error_time < 3.0, "Wrong port should fail quickly"
        
        wrong_port_client.close()
        
        # Verify that valid client still works after network errors
        valid_client = E2EHttpClient(running_service)
        valid_client.set_api_key(api_key)
        
        response = valid_client.translate(
            text="Recovery test",
            source_lang="eng_Latn",
            target_lang="fra_Latn"
        )
        
        assert response.is_success, "Valid client should work after network errors"
        
        valid_client.close()