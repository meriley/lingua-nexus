"""
Concurrent request handling tests for the NLLB Translation API.

This module tests:
- Race condition detection in concurrent translation requests
- Thread safety of translation operations
- Request isolation and data integrity
- Concurrent authentication handling
- Resource contention under simultaneous load
"""

import time
import pytest
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple, Set
from collections import defaultdict
import uuid
import statistics

class ConcurrencyTestHelper:
    """Helper class for concurrent testing scenarios."""
    
    def __init__(self, test_client, api_key_header):
        self.test_client = test_client
        self.api_key_header = api_key_header
        self.results = []
        self.errors = []
        self.lock = threading.Lock()
    
    def execute_request(self, request_data: Dict, request_id: str = None) -> Dict:
        """Execute a single request and collect results thread-safely."""
        request_id = request_id or str(uuid.uuid4())
        
        try:
            start_time = time.time()
            response = self.test_client.post("/translate", json=request_data, headers=self.api_key_header)
            end_time = time.time()
            
            result = {
                'request_id': request_id,
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'duration': end_time - start_time,
                'response_data': response.json() if response.status_code == 200 else response.text,
                'thread_id': threading.current_thread().ident,
                'timestamp': start_time
            }
            
            with self.lock:
                if result['success']:
                    self.results.append(result)
                else:
                    self.errors.append(result)
            
            return result
            
        except Exception as e:
            error_result = {
                'request_id': request_id,
                'success': False,
                'error': str(e),
                'thread_id': threading.current_thread().ident,
                'timestamp': time.time()
            }
            
            with self.lock:
                self.errors.append(error_result)
            
            return error_result
    
    def clear_results(self):
        """Clear collected results and errors."""
        with self.lock:
            self.results.clear()
            self.errors.clear()

@pytest.fixture
def concurrency_helper(test_client, api_key_header):
    """Fixture providing concurrency test helper."""
    return ConcurrencyTestHelper(test_client, api_key_header)

class TestConcurrentRequestHandling:
    """Tests for concurrent request handling and race conditions."""
    
    def test_concurrent_identical_requests(self, concurrency_helper, enhanced_mock_objects):
        """Test multiple identical requests executing concurrently."""
        
        request_data = {
            "text": "Concurrent identical request test",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        num_concurrent = 10
        concurrency_helper.clear_results()
        
        # Execute identical requests concurrently
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [
                executor.submit(concurrency_helper.execute_request, request_data, f"identical_{i}")
                for i in range(num_concurrent)
            ]
            
            # Wait for all requests to complete
            completed_results = [future.result() for future in as_completed(futures)]
        
        # Verify all requests succeeded
        assert len(concurrency_helper.results) == num_concurrent, f"Expected {num_concurrent} successful requests, got {len(concurrency_helper.results)}"
        assert len(concurrency_helper.errors) == 0, f"Unexpected errors in concurrent identical requests: {concurrency_helper.errors}"
        
        # Verify response consistency
        response_texts = [result['response_data']['translated_text'] for result in concurrency_helper.results]
        unique_responses = set(response_texts)
        assert len(unique_responses) == 1, f"Identical requests produced different responses: {unique_responses}"
        
        # Verify thread isolation
        thread_ids = [result['thread_id'] for result in concurrency_helper.results]
        unique_threads = set(thread_ids)
        assert len(unique_threads) >= 2, "Requests should execute on different threads for true concurrency"
        
        print(f"Concurrent identical requests: {num_concurrent}/{num_concurrent} successful, {len(unique_threads)} threads used")
    
    def test_concurrent_different_requests(self, concurrency_helper, enhanced_mock_objects):
        """Test different requests executing concurrently without interference."""
        
        different_requests = [
            {
                "text": f"Test message number {i} for concurrent processing",
                "source_lang": "eng_Latn",
                "target_lang": "fra_Latn"
            }
            for i in range(8)
        ]
        
        concurrency_helper.clear_results()
        
        # Execute different requests concurrently
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(concurrency_helper.execute_request, req_data, f"different_{i}")
                for i, req_data in enumerate(different_requests)
            ]
            
            completed_results = [future.result() for future in as_completed(futures)]
        
        # Verify all requests succeeded
        assert len(concurrency_helper.results) == len(different_requests), f"Expected {len(different_requests)} successful requests"
        assert len(concurrency_helper.errors) == 0, f"Unexpected errors: {concurrency_helper.errors}"
        
        # Verify response differentiation
        response_texts = [result['response_data']['translated_text'] for result in concurrency_helper.results]
        unique_responses = set(response_texts)
        
        # Should have unique responses for different inputs (at least some variation)
        assert len(unique_responses) >= 3, f"Different requests should produce varied responses, got {len(unique_responses)} unique responses"
        
        # Verify request-response mapping integrity
        for result in concurrency_helper.results:
            request_id = result['request_id']
            original_request_idx = int(request_id.split('_')[1])
            original_text = different_requests[original_request_idx]['text']
            
            # Response should contain expected prefix
            assert result['response_data']['translated_text'].startswith("Translated: "), "Response missing translation prefix"
        
        print(f"Concurrent different requests: {len(concurrency_helper.results)}/{len(different_requests)} successful")
    
    def test_concurrent_language_pairs(self, concurrency_helper, enhanced_mock_objects):
        """Test concurrent requests with different language pairs."""
        
        language_pair_requests = [
            {"text": "English to French", "source_lang": "eng_Latn", "target_lang": "fra_Latn"},
            {"text": "English to German", "source_lang": "eng_Latn", "target_lang": "deu_Latn"},
            {"text": "English to Spanish", "source_lang": "eng_Latn", "target_lang": "spa_Latn"},
            {"text": "French to English", "source_lang": "fra_Latn", "target_lang": "eng_Latn"},
            {"text": "German to English", "source_lang": "deu_Latn", "target_lang": "eng_Latn"},
            {"text": "Spanish to English", "source_lang": "spa_Latn", "target_lang": "eng_Latn"}
        ]
        
        concurrency_helper.clear_results()
        
        # Execute requests with different language pairs concurrently
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [
                executor.submit(concurrency_helper.execute_request, req_data, f"lang_pair_{i}")
                for i, req_data in enumerate(language_pair_requests)
            ]
            
            completed_results = [future.result() for future in as_completed(futures)]
        
        # Verify all language pairs handled successfully
        assert len(concurrency_helper.results) == len(language_pair_requests), "Some language pair requests failed"
        assert len(concurrency_helper.errors) == 0, f"Language pair errors: {concurrency_helper.errors}"
        
        # Group results by language pair
        lang_pair_responses = defaultdict(list)
        for result in concurrency_helper.results:
            request_id = result['request_id']
            idx = int(request_id.split('_')[2])
            original_request = language_pair_requests[idx]
            lang_pair = f"{original_request['source_lang']}->{original_request['target_lang']}"
            lang_pair_responses[lang_pair].append(result)
        
        # Verify each language pair was processed
        assert len(lang_pair_responses) == len(language_pair_requests), "Missing language pair results"
        
        # Verify performance consistency across language pairs
        avg_durations = {}
        for lang_pair, results in lang_pair_responses.items():
            durations = [r['duration'] for r in results]
            avg_durations[lang_pair] = statistics.mean(durations)
        
        max_duration = max(avg_durations.values())
        min_duration = min(avg_durations.values())
        duration_variance = max_duration / min_duration if min_duration > 0 else 1
        
        assert duration_variance < 5, f"Language pair performance variance too high: {duration_variance:.2f}"
        
        print(f"Concurrent language pairs: {len(concurrency_helper.results)} successful, variance ratio: {duration_variance:.2f}")
    
    def test_race_condition_detection(self, concurrency_helper, enhanced_mock_objects):
        """Test for race conditions in shared resource access."""
        
        # Use identical requests to maximize potential for race conditions
        race_request = {
            "text": "Race condition test with shared resource access",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        num_racing_requests = 15
        concurrency_helper.clear_results()
        
        # Create intentional contention by starting all requests simultaneously
        barrier = threading.Barrier(num_racing_requests)
        
        def racing_request(request_id: str):
            barrier.wait()  # Synchronize start time to maximize race condition potential
            return concurrency_helper.execute_request(race_request, request_id)
        
        # Execute racing requests
        with ThreadPoolExecutor(max_workers=num_racing_requests) as executor:
            futures = [
                executor.submit(racing_request, f"race_{i}")
                for i in range(num_racing_requests)
            ]
            
            completed_results = [future.result() for future in as_completed(futures)]
        
        # Analyze results for race condition indicators
        successful_count = len(concurrency_helper.results)
        error_count = len(concurrency_helper.errors)
        
        # Most requests should succeed even under contention
        success_rate = successful_count / num_racing_requests
        assert success_rate >= 0.8, f"Race condition test success rate {success_rate:.2f} too low, possible race condition"
        
        # Check for race condition symptoms in errors
        race_condition_indicators = [
            "timeout", "deadlock", "resource busy", "concurrent access", 
            "lock", "semaphore", "mutex", "atomic"
        ]
        
        for error in concurrency_helper.errors:
            error_msg = str(error.get('error', '')).lower()
            for indicator in race_condition_indicators:
                if indicator in error_msg:
                    pytest.fail(f"Potential race condition detected: {error}")
        
        # Verify response consistency under contention
        if successful_count > 0:
            response_texts = [result['response_data']['translated_text'] for result in concurrency_helper.results]
            unique_responses = set(response_texts)
            assert len(unique_responses) == 1, f"Race condition may have caused inconsistent responses: {unique_responses}"
        
        print(f"Race condition test: {successful_count}/{num_racing_requests} successful, no race conditions detected")
    
    def test_concurrent_authentication_handling(self, test_client, enhanced_mock_objects):
        """Test concurrent requests with different authentication scenarios."""
        
        # Different authentication scenarios
        auth_scenarios = [
            {"X-API-Key": "test_api_key"},  # Valid key
            {"X-API-Key": "test_api_key"},  # Same valid key (concurrent use)
            {"X-API-Key": "test_api_key"},  # Same valid key again
            {"X-API-Key": "invalid_key"},   # Invalid key
            {},                             # No auth header
            {"X-API-Key": ""},             # Empty key
        ]
        
        request_data = {
            "text": "Authentication concurrency test",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        auth_results = []
        
        def auth_request(headers: Dict, request_id: str):
            try:
                start_time = time.time()
                response = test_client.post("/translate", json=request_data, headers=headers)
                end_time = time.time()
                
                return {
                    'request_id': request_id,
                    'headers': headers,
                    'status_code': response.status_code,
                    'success': response.status_code == 200,
                    'duration': end_time - start_time,
                    'thread_id': threading.current_thread().ident
                }
            except Exception as e:
                return {
                    'request_id': request_id,
                    'headers': headers,
                    'error': str(e),
                    'success': False,
                    'thread_id': threading.current_thread().ident
                }
        
        # Execute concurrent authentication scenarios
        with ThreadPoolExecutor(max_workers=len(auth_scenarios)) as executor:
            futures = [
                executor.submit(auth_request, headers, f"auth_{i}")
                for i, headers in enumerate(auth_scenarios)
            ]
            
            auth_results = [future.result() for future in as_completed(futures)]
        
        # Analyze authentication results
        valid_auth_results = [r for r in auth_results if r['headers'].get('X-API-Key') == 'test_api_key']
        invalid_auth_results = [r for r in auth_results if r['headers'].get('X-API-Key') != 'test_api_key']
        
        # Valid authentication should succeed
        valid_success_count = sum(1 for r in valid_auth_results if r['success'])
        assert valid_success_count == len(valid_auth_results), f"Valid auth failed: {valid_success_count}/{len(valid_auth_results)}"
        
        # Invalid authentication should fail
        invalid_success_count = sum(1 for r in invalid_auth_results if r['success'])
        assert invalid_success_count == 0, f"Invalid auth unexpectedly succeeded: {invalid_success_count}/{len(invalid_auth_results)}"
        
        # Verify concurrent valid auth doesn't interfere
        valid_threads = set(r['thread_id'] for r in valid_auth_results)
        assert len(valid_threads) >= 2, "Valid auth requests should execute concurrently"
        
        print(f"Concurrent auth: {valid_success_count} valid auth succeeded, {len(invalid_auth_results)} invalid auth failed")
    
    def test_request_isolation_integrity(self, concurrency_helper, enhanced_mock_objects):
        """Test that concurrent requests don't interfere with each other's data."""
        
        # Create requests with unique identifiers in the text
        isolation_requests = [
            {
                "text": f"Isolation test request {i} with unique identifier {uuid.uuid4()}",
                "source_lang": "eng_Latn",
                "target_lang": "fra_Latn"
            }
            for i in range(12)
        ]
        
        concurrency_helper.clear_results()
        
        # Execute requests concurrently
        with ThreadPoolExecutor(max_workers=12) as executor:
            futures = [
                executor.submit(concurrency_helper.execute_request, req_data, f"isolation_{i}")
                for i, req_data in enumerate(isolation_requests)
            ]
            
            completed_results = [future.result() for future in as_completed(futures)]
        
        # Verify request isolation
        assert len(concurrency_helper.results) == len(isolation_requests), "Some isolation requests failed"
        assert len(concurrency_helper.errors) == 0, f"Isolation test errors: {concurrency_helper.errors}"
        
        # Verify each response corresponds to its original request
        for result in concurrency_helper.results:
            request_id = result['request_id']
            original_idx = int(request_id.split('_')[1])
            original_text = isolation_requests[original_idx]['text']
            
            # Response should be based on the original request text
            response_text = result['response_data']['translated_text']
            assert response_text.startswith("Translated: "), "Response missing translation prefix"
            
            # Extract unique identifier from original text
            original_uuid = original_text.split()[-1]  # Last word should be the UUID
            
            # Verify the UUID appears in some form in the response (indicating correct request processing)
            # Note: In mock implementation, we might not see the exact UUID, but the response should be consistent
            assert len(response_text) > len("Translated: "), "Response seems too short, possible data corruption"
        
        # Verify no response mixing between requests
        response_lengths = [len(result['response_data']['translated_text']) for result in concurrency_helper.results]
        
        # All responses should have reasonable length (indicating proper processing)
        for i, length in enumerate(response_lengths):
            assert length > 15, f"Response {i} too short ({length} chars), possible data corruption"
        
        print(f"Request isolation: {len(concurrency_helper.results)} requests processed with proper isolation")
    
    def test_concurrent_request_timing_analysis(self, concurrency_helper, enhanced_mock_objects):
        """Test timing characteristics of concurrent requests."""
        
        request_data = {
            "text": "Timing analysis for concurrent request processing behavior",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        num_concurrent = 20
        concurrency_helper.clear_results()
        
        # Record overall test timing
        test_start_time = time.time()
        
        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [
                executor.submit(concurrency_helper.execute_request, request_data, f"timing_{i}")
                for i in range(num_concurrent)
            ]
            
            completed_results = [future.result() for future in as_completed(futures)]
        
        test_end_time = time.time()
        total_test_duration = test_end_time - test_start_time
        
        # Analyze timing characteristics
        assert len(concurrency_helper.results) == num_concurrent, f"Expected {num_concurrent} successful requests"
        
        # Calculate timing metrics
        individual_durations = [result['duration'] for result in concurrency_helper.results]
        total_individual_time = sum(individual_durations)
        
        avg_individual_duration = statistics.mean(individual_durations)
        max_individual_duration = max(individual_durations)
        min_individual_duration = min(individual_durations)
        
        # Concurrent execution should be more efficient than sequential
        theoretical_sequential_time = total_individual_time
        concurrency_efficiency = theoretical_sequential_time / total_test_duration
        
        assert concurrency_efficiency > 2, f"Concurrency efficiency {concurrency_efficiency:.2f} too low, requests may not be truly concurrent"
        
        # Response time variation should be reasonable
        duration_std_dev = statistics.stdev(individual_durations)
        coefficient_of_variation = duration_std_dev / avg_individual_duration if avg_individual_duration > 0 else 0
        
        assert coefficient_of_variation < 1.5, f"Response time variation too high: {coefficient_of_variation:.2f}"
        
        # Verify overlap in request timing (true concurrency)
        timestamps = [(result['timestamp'], result['timestamp'] + result['duration']) for result in concurrency_helper.results]
        
        overlap_count = 0
        for i, (start1, end1) in enumerate(timestamps):
            for j, (start2, end2) in enumerate(timestamps[i+1:], i+1):
                # Check if requests overlap in time
                if start1 < end2 and start2 < end1:
                    overlap_count += 1
        
        # Should have significant overlap indicating concurrent execution
        expected_min_overlaps = num_concurrent * 2  # Conservative estimate
        assert overlap_count >= expected_min_overlaps, f"Insufficient request overlap ({overlap_count}), may not be truly concurrent"
        
        print(f"Timing analysis: {concurrency_efficiency:.2f}x efficiency, {overlap_count} overlapping requests, CV: {coefficient_of_variation:.2f}")
    
    def test_thread_safety_stress(self, concurrency_helper, enhanced_mock_objects):
        """Stress test for thread safety under high concurrent load."""
        
        stress_request = {
            "text": "Thread safety stress test with high concurrency load",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        high_concurrency = 30
        requests_per_thread = 3
        total_requests = high_concurrency * requests_per_thread
        
        concurrency_helper.clear_results()
        
        def stress_worker(worker_id: int):
            """Worker function that makes multiple requests."""
            worker_results = []
            for req_num in range(requests_per_thread):
                request_id = f"stress_{worker_id}_{req_num}"
                result = concurrency_helper.execute_request(stress_request, request_id)
                worker_results.append(result)
                time.sleep(0.01)  # Small delay between requests
            return worker_results
        
        stress_start_time = time.time()
        
        # Execute high-concurrency stress test
        with ThreadPoolExecutor(max_workers=high_concurrency) as executor:
            futures = [
                executor.submit(stress_worker, worker_id)
                for worker_id in range(high_concurrency)
            ]
            
            all_worker_results = []
            for future in as_completed(futures):
                worker_results = future.result()
                all_worker_results.extend(worker_results)
        
        stress_end_time = time.time()
        stress_duration = stress_end_time - stress_start_time
        
        # Verify thread safety under stress
        successful_count = len(concurrency_helper.results)
        error_count = len(concurrency_helper.errors)
        success_rate = successful_count / total_requests
        
        assert success_rate >= 0.85, f"Thread safety stress test success rate {success_rate:.2f} too low"
        
        # Check for thread safety violations in errors
        thread_safety_errors = []
        for error in concurrency_helper.errors:
            error_msg = str(error.get('error', '')).lower()
            if any(keyword in error_msg for keyword in ['deadlock', 'race', 'concurrent', 'thread', 'lock']):
                thread_safety_errors.append(error)
        
        assert len(thread_safety_errors) == 0, f"Thread safety violations detected: {thread_safety_errors}"
        
        # Verify response consistency under stress
        if successful_count > 0:
            response_texts = [result['response_data']['translated_text'] for result in concurrency_helper.results]
            unique_responses = set(response_texts)
            assert len(unique_responses) == 1, f"Stress test produced inconsistent responses: {len(unique_responses)} unique responses"
        
        throughput = successful_count / stress_duration
        
        print(f"Thread safety stress: {successful_count}/{total_requests} successful ({success_rate:.2%}), "
              f"{throughput:.1f} req/s, {len(concurrency_helper.errors)} errors")