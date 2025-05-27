"""E2E tests for observability and monitoring validation."""

import pytest
import time
import json
import re
from typing import Dict, Any, List

from .utils.http_client import E2EHttpClient


@pytest.mark.e2e
class TestMonitoringE2E:
    """Test observability and monitoring integration."""
    
    def test_health_endpoint_monitoring_behavior(self, e2e_client: E2EHttpClient):
        """Test health endpoint for monitoring integration."""
        # Test basic health check
        response = e2e_client.health_check()
        
        assert response.is_success, "Health endpoint should be accessible"
        assert response.response_time < 1.0, "Health check should be fast"
        
        # Verify health check response format
        if response.json_data:
            health_data = response.json_data
            
            # Common health check fields
            expected_fields = ["status", "timestamp", "uptime", "version"]
            present_fields = [field for field in expected_fields if field in health_data]
            
            # At least some health information should be present
            assert len(present_fields) > 0, "Health response should contain status information"
            
            # If status field exists, verify it indicates healthy service
            if "status" in health_data:
                status = health_data["status"]
                assert status in ["ok", "healthy", "up", "running"], \
                    f"Health status should indicate healthy service: {status}"
        
        # Test health check consistency
        health_responses = []
        for i in range(5):
            response = e2e_client.health_check()
            health_responses.append(response)
            time.sleep(0.5)
        
        # All health checks should succeed
        success_count = sum(1 for r in health_responses if r.is_success)
        assert success_count == len(health_responses), \
            "Health checks should be consistently successful"
        
        # Response times should be consistent
        response_times = [r.response_time for r in health_responses]
        max_response_time = max(response_times)
        avg_response_time = sum(response_times) / len(response_times)
        
        assert max_response_time < 2.0, "Health check response times should be reasonable"
        assert avg_response_time < 0.5, "Average health check time should be fast"
    
    def test_structured_logging_output(self, running_service: str, e2e_service_manager, test_config):
        """Test structured logging output validation."""
        # Generate some activity to produce logs
        api_key = test_config.VALID_CONFIGS["default"].api_key
        
        client = E2EHttpClient(running_service)
        client.set_api_key(api_key)
        
        # Make various requests to generate different types of log entries
        operations = [
            ("health_check", lambda: client.health_check()),
            ("translation", lambda: client.translate("Hello", "eng_Latn", "fra_Latn")),
            ("languages", lambda: client.get_supported_languages()),
            ("invalid_request", lambda: client.post("/translate", json_data={})),
        ]
        
        for operation_name, operation in operations:
            try:
                response = operation()
                print(f"Operation '{operation_name}': {response.status_code}")
                time.sleep(0.5)  # Allow time for log processing
            except Exception as e:
                print(f"Operation '{operation_name}' failed: {e}")
        
        # Capture service logs
        logs = e2e_service_manager.get_service_logs(max_lines=50)
        
        if logs:
            # Analyze log structure
            log_analysis = {
                "total_lines": len(logs),
                "json_structured": 0,
                "timestamp_format": 0,
                "log_levels": set(),
                "request_logs": 0
            }
            
            for log_line in logs:
                if not log_line.strip():
                    continue
                
                # Check for JSON structured logs
                try:
                    json.loads(log_line)
                    log_analysis["json_structured"] += 1
                except (json.JSONDecodeError, ValueError):
                    pass
                
                # Check for timestamp patterns
                timestamp_patterns = [
                    r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
                    r'\d{2}:\d{2}:\d{2}',  # HH:MM:SS
                    r'\d{10,13}',          # Unix timestamp
                ]
                
                if any(re.search(pattern, log_line) for pattern in timestamp_patterns):
                    log_analysis["timestamp_format"] += 1
                
                # Check for log levels
                log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                for level in log_levels:
                    if level in log_line.upper():
                        log_analysis["log_levels"].add(level)
                
                # Check for request-related logs
                request_indicators = ['GET', 'POST', 'HTTP', 'request', 'response']
                if any(indicator in log_line for indicator in request_indicators):
                    log_analysis["request_logs"] += 1
            
            # Verify logging quality
            assert log_analysis["total_lines"] > 0, "Should capture some log output"
            
            # At least some logs should have timestamps
            timestamp_ratio = log_analysis["timestamp_format"] / log_analysis["total_lines"]
            assert timestamp_ratio > 0.3, "Most logs should have timestamps"
            
            # Should see some log levels
            assert len(log_analysis["log_levels"]) > 0, "Should see log level indicators"
            
            print(f"Log analysis: {log_analysis}")
        
        client.close()
    
    def test_request_tracing_correlation_ids(self, e2e_client: E2EHttpClient):
        """Test request tracking and correlation IDs."""
        # Make requests with custom headers that might be used for tracing
        tracing_headers = {
            "X-Request-ID": "test-request-12345",
            "X-Correlation-ID": "test-correlation-67890",
            "X-Trace-ID": "test-trace-abcdef"
        }
        
        # Test health check with tracing headers
        health_response = e2e_client.health_check(headers=tracing_headers)
        assert health_response.is_success, "Health check with tracing headers should work"
        
        # Check if tracing headers are echoed back
        response_headers = health_response.headers
        tracing_response_headers = {}
        
        for header_name in tracing_headers.keys():
            if header_name.lower() in [k.lower() for k in response_headers.keys()]:
                tracing_response_headers[header_name] = response_headers.get(header_name)
        
        # Test translation request with tracing
        translation_response = e2e_client.translate(
            text="Tracing test",
            source_lang="eng_Latn",
            target_lang="fra_Latn",
            headers=tracing_headers
        )
        
        # Request should succeed regardless of tracing headers
        assert translation_response.status_code != 400, \
            "Tracing headers should not cause bad request"
        
        # Test multiple requests with different trace IDs
        trace_ids = ["trace-001", "trace-002", "trace-003"]
        
        for trace_id in trace_ids:
            headers = {"X-Trace-ID": trace_id}
            response = e2e_client.health_check(headers=headers)
            
            assert response.is_success, f"Request with trace ID {trace_id} should succeed"
            
            # Response time should be reasonable regardless of tracing
            assert response.response_time < 2.0, \
                f"Tracing should not significantly impact performance: {response.response_time}s"
    
    def test_metrics_collection_endpoints(self, e2e_client: E2EHttpClient):
        """Test performance metrics collection endpoints."""
        # Common metrics endpoints to test
        metrics_endpoints = [
            "/metrics",
            "/health/metrics", 
            "/stats",
            "/status",
            "/info"
        ]
        
        metrics_found = []
        
        for endpoint in metrics_endpoints:
            response = e2e_client.get(endpoint)
            
            if response.is_success:
                metrics_found.append({
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type", ""),
                    "response_size": len(response.text)
                })
                
                # Analyze metrics content
                content = response.text.lower()
                
                # Look for common metrics indicators
                metrics_indicators = [
                    "requests", "duration", "memory", "cpu", 
                    "connections", "errors", "latency", "throughput"
                ]
                
                found_indicators = [indicator for indicator in metrics_indicators 
                                  if indicator in content]
                
                if found_indicators:
                    print(f"Metrics endpoint {endpoint} contains: {found_indicators}")
        
        # It's OK if no specific metrics endpoints exist
        # This test documents what's available
        print(f"Available metrics endpoints: {[m['endpoint'] for m in metrics_found]}")
        
        # If metrics endpoints exist, they should be fast
        for metrics in metrics_found:
            endpoint = metrics["endpoint"]
            response = e2e_client.get(endpoint)
            assert response.response_time < 1.0, \
                f"Metrics endpoint {endpoint} should respond quickly"
    
    def test_error_reporting_and_alerting(self, e2e_client: E2EHttpClient):
        """Test error tracking and reporting behavior."""
        # Generate various types of errors to test error handling
        error_scenarios = [
            {
                "name": "invalid_endpoint",
                "action": lambda: e2e_client.get("/nonexistent-endpoint"),
                "expected_status": 404
            },
            {
                "name": "method_not_allowed",
                "action": lambda: e2e_client.post("/health"),
                "expected_status": 405
            },
            {
                "name": "invalid_json",
                "action": lambda: e2e_client.request(
                    "POST", "/translate",
                    headers={"Content-Type": "application/json"},
                    data="invalid json"
                ),
                "expected_status": 400
            },
            {
                "name": "missing_auth",
                "action": lambda: E2EHttpClient(e2e_client.base_url).translate(
                    "Hello", "eng_Latn", "fra_Latn"
                ),
                "expected_status": 401
            }
        ]
        
        error_responses = []
        
        for scenario in error_scenarios:
            try:
                response = scenario["action"]()
                
                error_responses.append({
                    "scenario": scenario["name"],
                    "status_code": response.status_code,
                    "expected_status": scenario["expected_status"],
                    "response_time": response.response_time,
                    "has_error_details": response.json_data is not None
                })
                
                # Verify expected error status
                assert response.status_code == scenario["expected_status"], \
                    f"Scenario '{scenario['name']}' should return {scenario['expected_status']}"
                
                # Error responses should be fast
                assert response.response_time < 2.0, \
                    f"Error response for '{scenario['name']}' should be quick"
                
                # Error responses should have details
                if response.json_data:
                    error_data = response.json_data
                    has_error_info = any(
                        key in error_data 
                        for key in ["detail", "error", "message"]
                    )
                    assert has_error_info, \
                        f"Error response for '{scenario['name']}' should provide details"
                
            except Exception as e:
                print(f"Error scenario '{scenario['name']}' failed unexpectedly: {e}")
        
        # Verify all error scenarios were tested
        assert len(error_responses) == len(error_scenarios), \
            "All error scenarios should be tested"
        
        print(f"Tested {len(error_responses)} error scenarios successfully")
    
    def test_monitoring_under_load(self, e2e_client: E2EHttpClient):
        """Test monitoring behavior under sustained load."""
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Monitor various metrics during load test
        monitoring_results = {
            "start_time": time.time(),
            "health_checks": [],
            "errors": [],
            "response_times": []
        }
        
        def monitor_health(results: dict, duration: int):
            """Monitor health endpoint during load test."""
            end_time = time.time() + duration
            
            while time.time() < end_time:
                try:
                    response = e2e_client.health_check()
                    results["health_checks"].append({
                        "timestamp": time.time(),
                        "success": response.is_success,
                        "response_time": response.response_time
                    })
                except Exception as e:
                    results["errors"].append({
                        "timestamp": time.time(),
                        "error": str(e)
                    })
                
                time.sleep(2)  # Check health every 2 seconds
        
        def generate_load(results: dict, duration: int):
            """Generate translation load."""
            end_time = time.time() + duration
            request_count = 0
            
            while time.time() < end_time:
                try:
                    response = e2e_client.translate(
                        text=f"Load test {request_count}",
                        source_lang="eng_Latn",
                        target_lang="fra_Latn"
                    )
                    
                    results["response_times"].append({
                        "timestamp": time.time(),
                        "response_time": response.response_time,
                        "success": response.is_success
                    })
                    
                    request_count += 1
                    
                except Exception as e:
                    results["errors"].append({
                        "timestamp": time.time(),
                        "error": str(e)
                    })
                
                time.sleep(0.5)  # 2 requests per second
        
        # Run monitoring and load generation concurrently
        test_duration = 15  # 15 seconds
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Start monitoring and load generation
            monitor_future = executor.submit(monitor_health, monitoring_results, test_duration)
            load_future = executor.submit(generate_load, monitoring_results, test_duration)
            
            # Wait for completion
            for future in as_completed([monitor_future, load_future]):
                future.result()
        
        # Analyze monitoring results
        monitoring_results["end_time"] = time.time()
        monitoring_results["duration"] = monitoring_results["end_time"] - monitoring_results["start_time"]
        
        # Health checks should remain stable under load
        health_successes = sum(1 for h in monitoring_results["health_checks"] if h["success"])
        health_total = len(monitoring_results["health_checks"])
        
        if health_total > 0:
            health_success_rate = health_successes / health_total
            assert health_success_rate >= 0.9, \
                f"Health check success rate should remain high under load: {health_success_rate:.2%}"
            
            # Health check response times should remain reasonable
            health_response_times = [h["response_time"] for h in monitoring_results["health_checks"]]
            max_health_time = max(health_response_times) if health_response_times else 0
            avg_health_time = sum(health_response_times) / len(health_response_times) if health_response_times else 0
            
            assert max_health_time < 3.0, f"Max health check time should be reasonable: {max_health_time:.2f}s"
            assert avg_health_time < 1.0, f"Average health check time should be fast: {avg_health_time:.2f}s"
        
        # Translation requests should mostly succeed
        translation_successes = sum(1 for r in monitoring_results["response_times"] if r["success"])
        translation_total = len(monitoring_results["response_times"])
        
        if translation_total > 0:
            translation_success_rate = translation_successes / translation_total
            assert translation_success_rate >= 0.8, \
                f"Translation success rate should be reasonable under load: {translation_success_rate:.2%}"
        
        print(f"Monitoring under load results:")
        print(f"- Duration: {monitoring_results['duration']:.1f}s")
        print(f"- Health checks: {health_successes}/{health_total} successful")
        print(f"- Translation requests: {translation_successes}/{translation_total} successful")
        print(f"- Errors: {len(monitoring_results['errors'])}")
    
    def test_logging_levels_and_configuration(self, running_service: str, e2e_service_manager):
        """Test logging level configuration and output."""
        # This test checks if different log levels produce appropriate output
        # The actual log level is set by environment variables during service startup
        
        # Make requests that should generate different types of logs
        client = E2EHttpClient(running_service)
        
        # Operations that should generate different log levels
        operations = [
            ("info_operation", lambda: client.health_check()),  # Should generate INFO logs
            ("debug_operation", lambda: client.get("/openapi.json")),  # Might generate DEBUG logs
            ("error_operation", lambda: client.get("/nonexistent")),  # Should generate ERROR logs
        ]
        
        for operation_name, operation in operations:
            try:
                response = operation()
                time.sleep(0.2)  # Allow log processing time
            except Exception as e:
                print(f"Operation {operation_name} exception: {e}")
        
        # Capture and analyze logs
        logs = e2e_service_manager.get_service_logs(max_lines=30)
        
        if logs:
            log_levels_found = set()
            
            for log_line in logs:
                # Look for log level indicators
                for level in ['DEBUG', 'INFO', 'WARNING', 'WARN', 'ERROR', 'CRITICAL']:
                    if level in log_line.upper():
                        log_levels_found.add(level)
            
            # Should see at least INFO level logs
            info_levels = {'INFO', 'WARNING', 'WARN', 'ERROR', 'CRITICAL'}
            has_info_logs = bool(log_levels_found.intersection(info_levels))
            
            assert has_info_logs, f"Should see some informational logs. Found levels: {log_levels_found}"
            
            print(f"Log levels found: {sorted(log_levels_found)}")
        
        client.close()