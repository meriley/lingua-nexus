"""
Load testing framework for the NLLB Translation API.

This module provides comprehensive load testing capabilities including:
- Concurrent request handling
- Stress testing under high load
- Resource utilization monitoring
- Performance degradation detection
"""

import time
import asyncio
import pytest
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple, Optional
import statistics
import psutil
from dataclasses import dataclass, field
from pathlib import Path
import json

@dataclass
class LoadTestResult:
    """Container for load test results and metrics."""
    
    test_name: str
    concurrent_users: int
    total_requests: int
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration: float = 0.0
    response_times: List[float] = field(default_factory=list)
    error_details: List[str] = field(default_factory=list)
    memory_usage: List[float] = field(default_factory=list)
    cpu_usage: List[float] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def throughput(self) -> float:
        """Calculate requests per second."""
        if self.total_duration == 0:
            return 0.0
        return self.successful_requests / self.total_duration
    
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time in milliseconds."""
        if not self.response_times:
            return 0.0
        return statistics.mean(self.response_times) * 1000
    
    @property
    def p95_response_time(self) -> float:
        """Calculate 95th percentile response time in milliseconds."""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        idx = int(0.95 * len(sorted_times))
        return sorted_times[idx] * 1000
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary for reporting."""
        return {
            'test_name': self.test_name,
            'concurrent_users': self.concurrent_users,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': self.success_rate,
            'total_duration': self.total_duration,
            'throughput': self.throughput,
            'avg_response_time': self.avg_response_time,
            'p95_response_time': self.p95_response_time,
            'max_response_time': max(self.response_times) * 1000 if self.response_times else 0,
            'min_response_time': min(self.response_times) * 1000 if self.response_times else 0,
            'avg_memory_usage': statistics.mean(self.memory_usage) if self.memory_usage else 0,
            'max_memory_usage': max(self.memory_usage) if self.memory_usage else 0,
            'avg_cpu_usage': statistics.mean(self.cpu_usage) if self.cpu_usage else 0,
            'max_cpu_usage': max(self.cpu_usage) if self.cpu_usage else 0,
            'error_details': self.error_details[:10]  # Limit error details for readability
        }

class LoadTestRunner:
    """Core load testing engine with resource monitoring."""
    
    def __init__(self, test_client, api_key_header: Dict[str, str]):
        self.test_client = test_client
        self.api_key_header = api_key_header
        self.process = psutil.Process()
        self._monitoring_active = False
        self._monitoring_thread: Optional[threading.Thread] = None
        self._resource_data: List[Tuple[float, float]] = []  # (memory_mb, cpu_percent)
    
    def _monitor_resources(self):
        """Background thread to monitor system resources during load test."""
        while self._monitoring_active:
            try:
                memory_mb = self.process.memory_info().rss / 1024 / 1024
                cpu_percent = self.process.cpu_percent()
                self._resource_data.append((memory_mb, cpu_percent))
                time.sleep(0.1)  # Monitor every 100ms
            except Exception as e:
                print(f"Resource monitoring error: {e}")
                break
    
    def _start_monitoring(self):
        """Start resource monitoring in background thread."""
        self._monitoring_active = True
        self._resource_data.clear()
        self._monitoring_thread = threading.Thread(target=self._monitor_resources)
        self._monitoring_thread.daemon = True
        self._monitoring_thread.start()
    
    def _stop_monitoring(self) -> Tuple[List[float], List[float]]:
        """Stop resource monitoring and return collected data."""
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=1.0)
        
        if self._resource_data:
            memory_usage = [data[0] for data in self._resource_data]
            cpu_usage = [data[1] for data in self._resource_data]
            return memory_usage, cpu_usage
        return [], []
    
    def _single_request(self, request_data: Dict) -> Tuple[bool, float, str]:
        """Execute a single translation request and measure performance."""
        try:
            start_time = time.time()
            response = self.test_client.post("/translate", json=request_data, headers=self.api_key_header)
            end_time = time.time()
            
            duration = end_time - start_time
            success = response.status_code == 200
            error_msg = "" if success else f"HTTP {response.status_code}: {response.text[:100]}"
            
            return success, duration, error_msg
        except Exception as e:
            return False, 0.0, f"Request exception: {str(e)}"
    
    def run_concurrent_load_test(self, concurrent_users: int, requests_per_user: int, 
                               request_data: Dict, test_name: str = "Load Test") -> LoadTestResult:
        """Run concurrent load test with specified parameters."""
        
        result = LoadTestResult(
            test_name=test_name,
            concurrent_users=concurrent_users,
            total_requests=concurrent_users * requests_per_user
        )
        
        self._start_monitoring()
        
        def user_session(user_id: int) -> List[Tuple[bool, float, str]]:
            """Simulate a user session with multiple requests."""
            session_results = []
            for req_num in range(requests_per_user):
                success, duration, error = self._single_request(request_data)
                session_results.append((success, duration, error))
                
                # Small delay between requests to simulate realistic usage
                time.sleep(0.01)
            
            return session_results
        
        start_time = time.time()
        
        # Execute concurrent user sessions
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            future_to_user = {
                executor.submit(user_session, user_id): user_id 
                for user_id in range(concurrent_users)
            }
            
            for future in as_completed(future_to_user):
                user_id = future_to_user[future]
                try:
                    session_results = future.result()
                    for success, duration, error in session_results:
                        if success:
                            result.successful_requests += 1
                            result.response_times.append(duration)
                        else:
                            result.failed_requests += 1
                            if error:
                                result.error_details.append(f"User {user_id}: {error}")
                except Exception as e:
                    result.failed_requests += requests_per_user
                    result.error_details.append(f"User {user_id} session failed: {str(e)}")
        
        end_time = time.time()
        result.total_duration = end_time - start_time
        
        # Stop monitoring and collect resource data
        memory_usage, cpu_usage = self._stop_monitoring()
        result.memory_usage = memory_usage
        result.cpu_usage = cpu_usage
        
        return result
    
    def run_stress_test(self, max_concurrent_users: int, request_data: Dict, 
                       duration_seconds: int = 30) -> List[LoadTestResult]:
        """Run stress test with gradually increasing load."""
        
        stress_results = []
        user_increments = [1, 5, 10, 20, 50] if max_concurrent_users >= 50 else [1, 2, 5, 10]
        
        for concurrent_users in user_increments:
            if concurrent_users > max_concurrent_users:
                break
            
            # Calculate requests per user based on duration
            requests_per_user = max(1, duration_seconds // 5)  # Roughly 5 seconds per request
            
            test_name = f"Stress Test - {concurrent_users} users"
            result = self.run_concurrent_load_test(
                concurrent_users=concurrent_users,
                requests_per_user=requests_per_user,
                request_data=request_data,
                test_name=test_name
            )
            
            stress_results.append(result)
            
            # Stop if success rate drops below 90%
            if result.success_rate < 90:
                print(f"Stopping stress test at {concurrent_users} users due to low success rate: {result.success_rate:.1f}%")
                break
            
            # Brief cooldown between stress levels
            time.sleep(2)
        
        return stress_results

@pytest.fixture
def load_test_runner(test_client, api_key_header):
    """Fixture providing load test runner instance."""
    return LoadTestRunner(test_client, api_key_header)

@pytest.fixture
def standard_load_request():
    """Standard request data for load testing."""
    return {
        "text": "Load testing translation request with moderate text length for realistic performance evaluation.",
        "source_lang": "eng_Latn",
        "target_lang": "fra_Latn"
    }

class TestLoadTesting:
    """Load testing test cases for the translation API."""
    
    def test_light_concurrent_load(self, load_test_runner, enhanced_mock_objects, standard_load_request):
        """Test light concurrent load - 5 concurrent users."""
        
        result = load_test_runner.run_concurrent_load_test(
            concurrent_users=5,
            requests_per_user=3,
            request_data=standard_load_request,
            test_name="Light Concurrent Load"
        )
        
        # Assertions for light load
        assert result.success_rate >= 95, f"Success rate {result.success_rate:.1f}% below 95% for light load"
        assert result.throughput >= 2, f"Throughput {result.throughput:.2f} req/s too low for light load"
        assert result.avg_response_time <= 3000, f"Avg response time {result.avg_response_time:.0f}ms too high"
        assert result.p95_response_time <= 5000, f"P95 response time {result.p95_response_time:.0f}ms too high"
        
        print(f"Light Load Results: {result.success_rate:.1f}% success, {result.throughput:.2f} req/s, {result.avg_response_time:.0f}ms avg")
    
    def test_moderate_concurrent_load(self, load_test_runner, enhanced_mock_objects, standard_load_request):
        """Test moderate concurrent load - 10 concurrent users."""
        
        result = load_test_runner.run_concurrent_load_test(
            concurrent_users=10,
            requests_per_user=5,
            request_data=standard_load_request,
            test_name="Moderate Concurrent Load"
        )
        
        # Assertions for moderate load
        assert result.success_rate >= 90, f"Success rate {result.success_rate:.1f}% below 90% for moderate load"
        assert result.throughput >= 1.5, f"Throughput {result.throughput:.2f} req/s too low for moderate load"
        assert result.avg_response_time <= 5000, f"Avg response time {result.avg_response_time:.0f}ms too high"
        assert result.p95_response_time <= 8000, f"P95 response time {result.p95_response_time:.0f}ms too high"
        
        print(f"Moderate Load Results: {result.success_rate:.1f}% success, {result.throughput:.2f} req/s, {result.avg_response_time:.0f}ms avg")
    
    def test_heavy_concurrent_load(self, load_test_runner, enhanced_mock_objects, standard_load_request):
        """Test heavy concurrent load - 20 concurrent users."""
        
        result = load_test_runner.run_concurrent_load_test(
            concurrent_users=20,
            requests_per_user=3,
            request_data=standard_load_request,
            test_name="Heavy Concurrent Load"
        )
        
        # More lenient assertions for heavy load
        assert result.success_rate >= 80, f"Success rate {result.success_rate:.1f}% below 80% for heavy load"
        assert result.throughput >= 1.0, f"Throughput {result.throughput:.2f} req/s too low for heavy load"
        assert result.avg_response_time <= 10000, f"Avg response time {result.avg_response_time:.0f}ms too high"
        
        print(f"Heavy Load Results: {result.success_rate:.1f}% success, {result.throughput:.2f} req/s, {result.avg_response_time:.0f}ms avg")
    
    @pytest.mark.slow
    def test_stress_test_progressive_load(self, load_test_runner, enhanced_mock_objects, standard_load_request):
        """Test progressive stress testing with increasing concurrent users."""
        
        stress_results = load_test_runner.run_stress_test(
            max_concurrent_users=30,
            request_data=standard_load_request,
            duration_seconds=20
        )
        
        assert len(stress_results) > 0, "No stress test results generated"
        
        # Analyze stress test progression
        for i, result in enumerate(stress_results):
            print(f"Stress Level {i+1}: {result.concurrent_users} users, "
                  f"{result.success_rate:.1f}% success, {result.throughput:.2f} req/s")
            
            # Each stress level should have some successful requests
            assert result.successful_requests > 0, f"No successful requests at {result.concurrent_users} users"
        
        # Find breaking point (where success rate drops significantly)
        breaking_point = None
        for i in range(1, len(stress_results)):
            prev_success = stress_results[i-1].success_rate
            curr_success = stress_results[i].success_rate
            
            if prev_success - curr_success > 20:  # 20% drop in success rate
                breaking_point = stress_results[i].concurrent_users
                break
        
        if breaking_point:
            print(f"System breaking point detected at {breaking_point} concurrent users")
        else:
            print("System handled all stress levels without significant degradation")
    
    def test_burst_load_handling(self, load_test_runner, enhanced_mock_objects, standard_load_request):
        """Test handling of sudden burst load scenarios."""
        
        # Simulate burst by sending many requests quickly
        result = load_test_runner.run_concurrent_load_test(
            concurrent_users=15,
            requests_per_user=2,
            request_data=standard_load_request,
            test_name="Burst Load Test"
        )
        
        # Burst handling expectations
        assert result.success_rate >= 70, f"Burst handling success rate {result.success_rate:.1f}% too low"
        assert len(result.error_details) <= result.total_requests * 0.3, "Too many errors during burst"
        
        # Response time distribution analysis
        if result.response_times:
            response_variance = statistics.stdev(result.response_times)
            avg_response = statistics.mean(result.response_times)
            coefficient_of_variation = response_variance / avg_response if avg_response > 0 else 0
            
            # Response times shouldn't be too erratic during burst
            assert coefficient_of_variation < 2.0, f"Response time variance too high during burst: {coefficient_of_variation:.2f}"
        
        print(f"Burst Load: {result.success_rate:.1f}% success rate, {result.avg_response_time:.0f}ms avg response")
    
    def test_mixed_request_types_load(self, load_test_runner, enhanced_mock_objects):
        """Test load handling with mixed request types and sizes."""
        
        # Different request types
        request_variants = [
            {
                "text": "Short text",
                "source_lang": "eng_Latn",
                "target_lang": "fra_Latn"
            },
            {
                "text": "Medium length text for translation testing with multiple sentences. This simulates more realistic usage patterns.",
                "source_lang": "eng_Latn",
                "target_lang": "deu_Latn"
            },
            {
                "text": "Long text content for stress testing translation capabilities. " * 5,
                "source_lang": "fra_Latn",
                "target_lang": "eng_Latn"
            }
        ]
        
        mixed_results = []
        
        for i, request_data in enumerate(request_variants):
            result = load_test_runner.run_concurrent_load_test(
                concurrent_users=8,
                requests_per_user=2,
                request_data=request_data,
                test_name=f"Mixed Load Test - Variant {i+1}"
            )
            mixed_results.append(result)
        
        # All variants should perform reasonably well
        for i, result in enumerate(mixed_results):
            assert result.success_rate >= 85, f"Mixed load variant {i+1} success rate {result.success_rate:.1f}% too low"
            print(f"Mixed Load Variant {i+1}: {result.success_rate:.1f}% success, {result.avg_response_time:.0f}ms avg")
        
        # Performance should be consistent across variants
        avg_times = [result.avg_response_time for result in mixed_results]
        max_time = max(avg_times)
        min_time = min(avg_times)
        time_variance_ratio = max_time / min_time if min_time > 0 else 1
        
        assert time_variance_ratio < 5, f"Response time variance across request types too high: {time_variance_ratio:.2f}"
    
    def test_load_test_reporting(self, load_test_runner, enhanced_mock_objects, standard_load_request):
        """Test load test result reporting and metrics collection."""
        
        result = load_test_runner.run_concurrent_load_test(
            concurrent_users=5,
            requests_per_user=4,
            request_data=standard_load_request,
            test_name="Reporting Test"
        )
        
        # Verify all metrics are collected
        assert result.total_requests == 20, f"Expected 20 total requests, got {result.total_requests}"
        assert result.successful_requests + result.failed_requests == result.total_requests
        assert result.total_duration > 0, "Test duration should be recorded"
        assert len(result.response_times) == result.successful_requests, "Response times count mismatch"
        
        # Test metrics calculation
        assert 0 <= result.success_rate <= 100, f"Success rate {result.success_rate}% out of valid range"
        assert result.throughput >= 0, f"Throughput {result.throughput} should be non-negative"
        
        if result.response_times:
            assert result.avg_response_time > 0, "Average response time should be positive"
            assert result.p95_response_time >= result.avg_response_time, "P95 should be >= average"
        
        # Test result serialization
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict), "Result should serialize to dictionary"
        assert 'test_name' in result_dict, "Serialized result missing test_name"
        assert 'success_rate' in result_dict, "Serialized result missing success_rate"
        assert 'throughput' in result_dict, "Serialized result missing throughput"
        
        print(f"Load test reporting verified: {result.success_rate:.1f}% success rate")
    
    def test_save_load_test_report(self, load_test_runner, enhanced_mock_objects, standard_load_request):
        """Test saving comprehensive load test report."""
        
        # Run multiple load tests
        test_results = []
        
        for concurrent_users in [3, 6, 9]:
            result = load_test_runner.run_concurrent_load_test(
                concurrent_users=concurrent_users,
                requests_per_user=2,
                request_data=standard_load_request,
                test_name=f"Report Test - {concurrent_users} users"
            )
            test_results.append(result)
        
        # Create comprehensive report
        report = {
            'timestamp': time.time(),
            'test_summary': {
                'total_tests': len(test_results),
                'overall_success_rate': statistics.mean([r.success_rate for r in test_results]),
                'avg_throughput': statistics.mean([r.throughput for r in test_results]),
                'avg_response_time': statistics.mean([r.avg_response_time for r in test_results])
            },
            'individual_tests': [result.to_dict() for result in test_results]
        }
        
        # Save report
        report_path = "/mnt/dionysus/coding/tg-text-translate/test_reports/load_test_report.json"
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Verify report was saved
        assert Path(report_path).exists(), "Load test report not saved"
        
        with open(report_path, 'r') as f:
            saved_report = json.load(f)
        
        assert 'test_summary' in saved_report, "Report missing test summary"
        assert 'individual_tests' in saved_report, "Report missing individual test results"
        assert len(saved_report['individual_tests']) == len(test_results), "Report missing test results"
        
        print(f"Load test report saved: {report['test_summary']['overall_success_rate']:.1f}% overall success rate")