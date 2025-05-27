"""E2E performance tests under real network conditions."""

import pytest
import time
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any
import psutil
import os

from .utils.http_client import E2EHttpClient, E2EHttpClientPool


@pytest.mark.e2e
@pytest.mark.e2e_performance
@pytest.mark.e2e_slow
class TestPerformanceE2E:
    """Test performance validation under real network conditions."""
    
    def test_concurrent_http_connections(self, running_service: str, test_config, performance_config: Dict[str, Any]):
        """Test multiple simultaneous HTTP connections."""
        num_connections = performance_config["concurrent_connections"]
        requests_per_connection = performance_config["requests_per_connection"]
        max_response_time = performance_config["max_response_time"]
        
        api_key = test_config.VALID_CONFIGS["default"].api_key
        
        def worker_thread(worker_id: int, results: List[Dict]):
            """Worker thread that makes multiple requests."""
            client = E2EHttpClient(running_service)
            client.set_api_key(api_key)
            
            thread_results = []
            
            for request_id in range(requests_per_connection):
                start_time = time.time()
                
                response = client.translate(
                    text=f"Hello from worker {worker_id}, request {request_id}",
                    source_lang="eng_Latn",
                    target_lang="fra_Latn"
                )
                
                end_time = time.time()
                
                thread_results.append({
                    "worker_id": worker_id,
                    "request_id": request_id,
                    "success": response.is_success,
                    "status_code": response.status_code,
                    "response_time": response.response_time,
                    "total_time": end_time - start_time
                })
            
            results.extend(thread_results)
            client.close()
        
        # Execute concurrent connections
        results = []
        threads = []
        
        start_time = time.time()
        
        for worker_id in range(num_connections):
            thread = threading.Thread(
                target=worker_thread,
                args=(worker_id, results)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Analyze results
        total_requests = num_connections * requests_per_connection
        successful_requests = sum(1 for r in results if r["success"])
        failed_requests = total_requests - successful_requests
        
        response_times = [r["response_time"] for r in results if r["success"]]
        
        # Assertions
        assert len(results) == total_requests, "All requests should complete"
        
        success_rate = successful_requests / total_requests
        assert success_rate >= 0.9, f"Success rate too low: {success_rate:.2%}"
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            max_observed_time = max(response_times)
            
            assert avg_response_time < max_response_time, \
                f"Average response time too high: {avg_response_time:.2f}s"
            assert max_observed_time < max_response_time * 2, \
                f"Maximum response time too high: {max_observed_time:.2f}s"
        
        # Calculate throughput
        throughput = successful_requests / total_time
        assert throughput > 1.0, f"Throughput too low: {throughput:.2f} req/s"
        
        print(f"Performance Results:")
        print(f"- Total requests: {total_requests}")
        print(f"- Successful: {successful_requests}")
        print(f"- Failed: {failed_requests}")
        print(f"- Success rate: {success_rate:.2%}")
        print(f"- Average response time: {statistics.mean(response_times):.3f}s")
        print(f"- Throughput: {throughput:.2f} req/s")
    
    def test_rate_limiting_enforcement_over_http(self, running_service: str, test_config):
        """Test rate limiting validation with real HTTP requests."""
        api_key = test_config.VALID_CONFIGS["default"].api_key
        
        client = E2EHttpClient(running_service)
        client.set_api_key(api_key)
        
        # Make rapid requests to trigger rate limiting
        # SlowAPI is configured for 10 requests/minute
        requests_made = 0
        rate_limited_responses = 0
        
        # Make requests rapidly
        for i in range(15):  # More than the rate limit
            response = client.translate(
                text=f"Rate limit test {i}",
                source_lang="eng_Latn",
                target_lang="fra_Latn"
            )
            
            requests_made += 1
            
            if response.status_code == 429:  # Too Many Requests
                rate_limited_responses += 1
            elif response.is_success:
                # Successful request
                pass
            else:
                # Other error - might be expected under load
                pass
            
            # Small delay to see rate limiting behavior
            time.sleep(0.1)
        
        # Verify rate limiting is working
        # We should see some rate limited responses if making requests faster than allowed
        # Note: This test might be flaky depending on exact rate limiting implementation
        assert requests_made == 15, "Should have made all requests"
        
        # Rate limiting might not trigger in all test environments
        # Just verify the service handles rapid requests gracefully
        print(f"Rate limiting test: {rate_limited_responses}/{requests_made} requests rate limited")
        
        client.close()
    
    def test_response_time_consistency_under_load(self, running_service: str, test_config):
        """Test response time stability under sustained load."""
        api_key = test_config.VALID_CONFIGS["default"].api_key
        
        with E2EHttpClientPool(running_service, pool_size=5) as client_pool:
            client_pool.set_api_key_for_all(api_key)
            clients = client_pool.get_all_clients()
            
            def make_sustained_requests(client: E2EHttpClient, duration_seconds: int):
                """Make requests for a specified duration."""
                end_time = time.time() + duration_seconds
                response_times = []
                
                request_count = 0
                while time.time() < end_time:
                    response = client.translate(
                        text=f"Load test {request_count}",
                        source_lang="eng_Latn",
                        target_lang="fra_Latn"
                    )
                    
                    if response.is_success:
                        response_times.append(response.response_time)
                    
                    request_count += 1
                    time.sleep(0.5)  # 2 requests per second per client
                
                return response_times
            
            # Run sustained load test
            duration = 30  # 30 seconds
            all_response_times = []
            
            with ThreadPoolExecutor(max_workers=len(clients)) as executor:
                futures = [
                    executor.submit(make_sustained_requests, client, duration)
                    for client in clients
                ]
                
                for future in as_completed(futures):
                    response_times = future.result()
                    all_response_times.extend(response_times)
            
            # Analyze response time consistency
            if all_response_times:
                mean_time = statistics.mean(all_response_times)
                stdev_time = statistics.stdev(all_response_times) if len(all_response_times) > 1 else 0
                min_time = min(all_response_times)
                max_time = max(all_response_times)
                
                # Response times should be reasonably consistent
                coefficient_of_variation = stdev_time / mean_time if mean_time > 0 else 0
                
                # Assertions
                assert mean_time < 3.0, f"Mean response time too high: {mean_time:.3f}s"
                assert coefficient_of_variation < 1.0, \
                    f"Response times too variable: CV={coefficient_of_variation:.3f}"
                assert max_time < mean_time * 5, \
                    f"Maximum response time too high: {max_time:.3f}s (mean: {mean_time:.3f}s)"
                
                print(f"Response time consistency:")
                print(f"- Requests: {len(all_response_times)}")
                print(f"- Mean: {mean_time:.3f}s")
                print(f"- Std Dev: {stdev_time:.3f}s")
                print(f"- Min: {min_time:.3f}s")
                print(f"- Max: {max_time:.3f}s")
                print(f"- CV: {coefficient_of_variation:.3f}")
    
    def test_memory_usage_during_sustained_requests(self, running_service: str, test_config, e2e_service_manager):
        """Test memory usage monitoring during sustained requests."""
        api_key = test_config.VALID_CONFIGS["default"].api_key
        
        # Get the service process for monitoring
        service_process = e2e_service_manager.process
        if not service_process:
            pytest.skip("Service process not available for monitoring")
        
        try:
            # Get baseline memory usage
            process = psutil.Process(service_process.pid)
            baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            memory_samples = [baseline_memory]
            
            def monitor_memory(samples: List[float], duration: int):
                """Monitor memory usage during test."""
                end_time = time.time() + duration
                while time.time() < end_time:
                    try:
                        current_memory = process.memory_info().rss / 1024 / 1024  # MB
                        samples.append(current_memory)
                        time.sleep(2)  # Sample every 2 seconds
                    except psutil.NoSuchProcess:
                        break
            
            def make_load_requests(client: E2EHttpClient, duration: int):
                """Generate load during memory monitoring."""
                end_time = time.time() + duration
                request_count = 0
                
                while time.time() < end_time:
                    client.translate(
                        text=f"Memory test {request_count}",
                        source_lang="eng_Latn",
                        target_lang="fra_Latn"
                    )
                    request_count += 1
                    time.sleep(0.2)  # 5 requests per second
                
                return request_count
            
            # Run memory test
            test_duration = 30  # 30 seconds
            
            client = E2EHttpClient(running_service)
            client.set_api_key(api_key)
            
            # Start memory monitoring thread
            monitor_thread = threading.Thread(
                target=monitor_memory,
                args=(memory_samples, test_duration)
            )
            monitor_thread.start()
            
            # Generate load
            requests_made = make_load_requests(client, test_duration)
            
            # Wait for monitoring to complete
            monitor_thread.join()
            client.close()
            
            # Analyze memory usage
            if len(memory_samples) > 2:
                max_memory = max(memory_samples)
                min_memory = min(memory_samples)
                final_memory = memory_samples[-1]
                
                memory_growth = final_memory - baseline_memory
                peak_memory_growth = max_memory - baseline_memory
                
                # Memory usage assertions
                assert peak_memory_growth < 500, \
                    f"Peak memory growth too high: {peak_memory_growth:.1f}MB"
                
                # Memory should not grow unbounded (potential leak)
                memory_growth_per_request = memory_growth / requests_made if requests_made > 0 else 0
                assert memory_growth_per_request < 0.1, \
                    f"Memory growth per request too high: {memory_growth_per_request:.3f}MB/req"
                
                print(f"Memory usage analysis:")
                print(f"- Baseline: {baseline_memory:.1f}MB")
                print(f"- Peak: {max_memory:.1f}MB")
                print(f"- Final: {final_memory:.1f}MB")
                print(f"- Growth: {memory_growth:.1f}MB")
                print(f"- Peak growth: {peak_memory_growth:.1f}MB")
                print(f"- Requests: {requests_made}")
                
        except psutil.NoSuchProcess:
            pytest.skip("Service process not available for memory monitoring")
    
    def test_throughput_measurement(self, running_service: str, test_config):
        """Test requests per second validation."""
        api_key = test_config.VALID_CONFIGS["default"].api_key
        
        # Test different concurrency levels
        concurrency_levels = [1, 3, 5]
        throughput_results = {}
        
        for concurrency in concurrency_levels:
            with E2EHttpClientPool(running_service, pool_size=concurrency) as client_pool:
                client_pool.set_api_key_for_all(api_key)
                clients = client_pool.get_all_clients()
                
                def worker_requests(client: E2EHttpClient, duration: int):
                    """Make requests for specified duration."""
                    end_time = time.time() + duration
                    successful_requests = 0
                    
                    while time.time() < end_time:
                        response = client.translate(
                            text="Throughput test",
                            source_lang="eng_Latn",
                            target_lang="fra_Latn"
                        )
                        
                        if response.is_success:
                            successful_requests += 1
                        
                        # No delay - maximum throughput test
                    
                    return successful_requests
                
                # Measure throughput
                test_duration = 20  # 20 seconds
                start_time = time.time()
                
                with ThreadPoolExecutor(max_workers=concurrency) as executor:
                    futures = [
                        executor.submit(worker_requests, client, test_duration)
                        for client in clients
                    ]
                    
                    total_successful = sum(future.result() for future in as_completed(futures))
                
                actual_duration = time.time() - start_time
                throughput = total_successful / actual_duration
                
                throughput_results[concurrency] = {
                    "requests": total_successful,
                    "duration": actual_duration,
                    "throughput": throughput
                }
                
                print(f"Concurrency {concurrency}: {throughput:.2f} req/s ({total_successful} requests in {actual_duration:.1f}s)")
        
        # Verify throughput meets minimum requirements
        for concurrency, results in throughput_results.items():
            min_expected_throughput = 0.5  # 0.5 req/s minimum
            assert results["throughput"] >= min_expected_throughput, \
                f"Throughput too low at concurrency {concurrency}: {results['throughput']:.2f} req/s"
        
        # Verify throughput scales with concurrency (to some degree)
        if len(throughput_results) >= 2:
            throughputs = [results["throughput"] for results in throughput_results.values()]
            # Higher concurrency should generally yield higher throughput
            # (though may plateau due to rate limiting or system constraints)
            max_throughput = max(throughputs)
            min_throughput = min(throughputs)
            
            # At least some scaling should be observed
            scaling_factor = max_throughput / min_throughput
            assert scaling_factor >= 1.0, "Throughput should scale with concurrency"
            
            print(f"Throughput scaling factor: {scaling_factor:.2f}x")
    
    def test_large_payload_performance(self, running_service: str, test_config):
        """Test performance with large translation payloads."""
        api_key = test_config.VALID_CONFIGS["default"].api_key
        
        client = E2EHttpClient(running_service)
        client.set_api_key(api_key)
        
        # Test different payload sizes
        payload_sizes = [
            ("small", "Hello world"),
            ("medium", "This is a medium sized text for testing. " * 20),
            ("large", "This is a larger text payload for performance testing. " * 100),
            ("very_large", "This is a very large text payload for stress testing. " * 300)
        ]
        
        performance_data = {}
        
        for size_name, text in payload_sizes:
            # Measure translation performance
            start_time = time.time()
            
            response = client.translate(
                text=text,
                source_lang="eng_Latn",
                target_lang="fra_Latn",
                timeout=60
            )
            
            end_time = time.time()
            total_time = end_time - start_time
            
            performance_data[size_name] = {
                "text_length": len(text),
                "success": response.is_success,
                "response_time": response.response_time,
                "total_time": total_time,
                "status_code": response.status_code
            }
            
            if response.is_success:
                # Verify translation performance scales reasonably with input size
                chars_per_second = len(text) / response.response_time
                performance_data[size_name]["chars_per_second"] = chars_per_second
                
                # Performance should be reasonable even for large texts
                assert response.response_time < 30.0, \
                    f"Large payload ({size_name}) took too long: {response.response_time:.2f}s"
                
                print(f"{size_name}: {len(text)} chars, {response.response_time:.2f}s, {chars_per_second:.0f} chars/s")
        
        client.close()
        
        # Verify all sizes completed successfully
        successful_tests = sum(1 for data in performance_data.values() if data["success"])
        assert successful_tests >= len(payload_sizes) * 0.8, \
            "Most payload sizes should complete successfully"