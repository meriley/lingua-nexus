"""
Performance baseline tests for the NLLB Translation API.

This module establishes performance baselines and benchmarks for:
- Translation endpoint response times
- Memory usage during translation
- Throughput measurements
- Resource utilization tracking
"""

import time
import psutil
import pytest
import asyncio
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics
import json
from pathlib import Path

class PerformanceMetrics:
    """Utility class for tracking and analyzing performance metrics."""
    
    def __init__(self):
        self.metrics = {
            'response_times': [],
            'memory_usage': [],
            'cpu_usage': [],
            'throughput': [],
            'error_rates': []
        }
    
    def record_response_time(self, duration: float):
        """Record API response time in milliseconds."""
        self.metrics['response_times'].append(duration * 1000)  # Convert to ms
    
    def record_memory_usage(self, memory_mb: float):
        """Record memory usage in MB."""
        self.metrics['memory_usage'].append(memory_mb)
    
    def record_cpu_usage(self, cpu_percent: float):
        """Record CPU usage percentage."""
        self.metrics['cpu_usage'].append(cpu_percent)
    
    def calculate_statistics(self, metric_name: str) -> Dict[str, float]:
        """Calculate statistical measures for a given metric."""
        data = self.metrics.get(metric_name, [])
        if not data:
            return {}
        
        return {
            'mean': statistics.mean(data),
            'median': statistics.median(data),
            'std_dev': statistics.stdev(data) if len(data) > 1 else 0,
            'min': min(data),
            'max': max(data),
            'p95': sorted(data)[int(0.95 * len(data))] if data else 0,
            'p99': sorted(data)[int(0.99 * len(data))] if data else 0
        }
    
    def save_report(self, filepath: str):
        """Save performance metrics to a JSON report."""
        report = {
            'timestamp': time.time(),
            'statistics': {
                metric: self.calculate_statistics(metric) 
                for metric in self.metrics.keys()
            },
            'raw_data': self.metrics
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)

@pytest.fixture
def performance_metrics():
    """Fixture providing performance metrics tracking."""
    return PerformanceMetrics()

@pytest.fixture
def baseline_request_data():
    """Standard request data for performance testing."""
    return {
        "text": "Hello, this is a test translation request for performance benchmarking.",
        "source_lang": "eng_Latn",
        "target_lang": "fra_Latn"
    }

class TestBaselinePerformance:
    """Performance baseline tests for translation API."""
    
    def test_single_translation_response_time(self, test_client, enhanced_mock_objects, 
                                            api_key_header, baseline_request_data, performance_metrics):
        """Test single translation request response time baseline."""
        
        # Warm-up request
        test_client.post("/translate", json=baseline_request_data, headers=api_key_header)
        
        # Measure baseline response time
        start_time = time.time()
        response = test_client.post("/translate", json=baseline_request_data, headers=api_key_header)
        end_time = time.time()
        
        duration = end_time - start_time
        performance_metrics.record_response_time(duration)
        
        assert response.status_code == 200
        assert duration < 2.0, f"Single translation took {duration:.3f}s, exceeds 2s baseline"
        
        print(f"Single translation baseline: {duration*1000:.2f}ms")
    
    def test_translation_memory_usage(self, test_client, enhanced_mock_objects, 
                                    api_key_header, baseline_request_data, performance_metrics):
        """Test memory usage during translation operations."""
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform multiple translations to measure memory impact
        for i in range(10):
            response = test_client.post("/translate", json=baseline_request_data, headers=api_key_header)
            assert response.status_code == 200
            
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            performance_metrics.record_memory_usage(current_memory)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable for 10 translations
        assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB for 10 translations"
        
        print(f"Memory usage - Initial: {initial_memory:.2f}MB, Final: {final_memory:.2f}MB, Increase: {memory_increase:.2f}MB")
    
    def test_sequential_request_throughput(self, test_client, enhanced_mock_objects, 
                                         api_key_header, baseline_request_data, performance_metrics):
        """Test sequential request processing throughput."""
        
        num_requests = 20
        start_time = time.time()
        
        successful_requests = 0
        for i in range(num_requests):
            response = test_client.post("/translate", json=baseline_request_data, headers=api_key_header)
            if response.status_code == 200:
                successful_requests += 1
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = successful_requests / duration  # requests per second
        
        performance_metrics.metrics['throughput'].append(throughput)
        
        assert throughput > 5, f"Sequential throughput {throughput:.2f} req/s below 5 req/s baseline"
        
        print(f"Sequential throughput: {throughput:.2f} requests/second")
    
    def test_translation_text_length_scaling(self, test_client, enhanced_mock_objects, 
                                           api_key_header, performance_metrics):
        """Test how response time scales with input text length."""
        
        text_lengths = [10, 50, 100, 200, 500]  # Number of words
        base_text = "This is a test sentence for scaling performance measurements. "
        
        scaling_results = []
        
        for length in text_lengths:
            # Create text of specified word count
            text = (base_text * (length // 10 + 1))[:length * 6]  # Approximate word length
            
            request_data = {
                "text": text,
                "source_lang": "eng_Latn",
                "target_lang": "fra_Latn"
            }
            
            start_time = time.time()
            response = test_client.post("/translate", json=request_data, headers=api_key_header)
            end_time = time.time()
            
            duration = end_time - start_time
            performance_metrics.record_response_time(duration)
            
            assert response.status_code == 200
            scaling_results.append((length, duration))
            
            print(f"Text length {length} words: {duration*1000:.2f}ms")
        
        # Verify scaling is reasonable (not exponential)
        max_duration = max(result[1] for result in scaling_results)
        min_duration = min(result[1] for result in scaling_results)
        scaling_factor = max_duration / min_duration
        
        assert scaling_factor < 5, f"Response time scaling factor {scaling_factor:.2f} too high"
    
    def test_different_language_pairs_performance(self, test_client, enhanced_mock_objects, 
                                                api_key_header, performance_metrics):
        """Test performance consistency across different language pairs."""
        
        language_pairs = [
            ("eng_Latn", "fra_Latn"),
            ("eng_Latn", "deu_Latn"),
            ("eng_Latn", "spa_Latn"),
            ("fra_Latn", "eng_Latn"),
            ("deu_Latn", "eng_Latn")
        ]
        
        base_text = "This is a performance test for different language pairs."
        language_performance = []
        
        for source_lang, target_lang in language_pairs:
            request_data = {
                "text": base_text,
                "source_lang": source_lang,
                "target_lang": target_lang
            }
            
            start_time = time.time()
            response = test_client.post("/translate", json=request_data, headers=api_key_header)
            end_time = time.time()
            
            duration = end_time - start_time
            performance_metrics.record_response_time(duration)
            
            assert response.status_code == 200
            language_performance.append((f"{source_lang}->{target_lang}", duration))
            
            print(f"Language pair {source_lang}->{target_lang}: {duration*1000:.2f}ms")
        
        # Verify performance consistency across language pairs
        durations = [perf[1] for perf in language_performance]
        max_duration = max(durations)
        min_duration = min(durations)
        variance_ratio = max_duration / min_duration
        
        assert variance_ratio < 3, f"Language pair performance variance {variance_ratio:.2f} too high"
    
    def test_save_performance_baseline_report(self, performance_metrics):
        """Save performance baseline report for future comparisons."""
        
        report_path = "/mnt/dionysus/coding/tg-text-translate/test_reports/performance_baseline.json"
        performance_metrics.save_report(report_path)
        
        # Verify report was created
        assert Path(report_path).exists(), "Performance baseline report not created"
        
        print(f"Performance baseline report saved to {report_path}")