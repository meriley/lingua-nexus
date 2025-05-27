"""
E2E Test: Inference Performance Tests
Tests translation performance, latency patterns, and throughput benchmarks.
"""

import pytest
import time
import statistics
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import asyncio
import concurrent.futures
from pathlib import Path

from tests.e2e.utils.robust_service_manager import RobustServiceManager
from tests.e2e.utils.comprehensive_client import ComprehensiveTestClient
from tests.e2e.utils.service_manager import ServiceConfig


class InferencePerformanceCollector:
    """Collects and analyzes inference performance metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, List[Dict]] = {}
        self.test_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def record_inference(self, model_name: str, test_type: str, 
                        text_length: int, duration_seconds: float,
                        success: bool, metadata: Optional[Dict] = None):
        """Record inference performance metrics."""
        key = f"{model_name}_{test_type}"
        
        if key not in self.metrics:
            self.metrics[key] = []
            
        record = {
            "timestamp": datetime.now().isoformat(),
            "text_length": text_length,
            "duration_seconds": duration_seconds,
            "success": success,
            "throughput_chars_per_sec": text_length / duration_seconds if duration_seconds > 0 else 0,
            "metadata": metadata or {}
        }
        
        self.metrics[key].append(record)
        
    def analyze_performance(self, model_name: str, test_type: str) -> Dict:
        """Analyze performance metrics for a specific test."""
        key = f"{model_name}_{test_type}"
        
        if key not in self.metrics or not self.metrics[key]:
            return {"error": "No metrics found"}
            
        successful_metrics = [m for m in self.metrics[key] if m["success"]]
        
        if not successful_metrics:
            return {"error": "No successful inferences"}
            
        durations = [m["duration_seconds"] for m in successful_metrics]
        throughputs = [m["throughput_chars_per_sec"] for m in successful_metrics]
        text_lengths = [m["text_length"] for m in successful_metrics]
        
        analysis = {
            "test_info": {
                "model_name": model_name,
                "test_type": test_type,
                "total_inferences": len(self.metrics[key]),
                "successful_inferences": len(successful_metrics),
                "success_rate": len(successful_metrics) / len(self.metrics[key])
            },
            "latency_stats": {
                "mean_seconds": statistics.mean(durations),
                "median_seconds": statistics.median(durations),
                "min_seconds": min(durations),
                "max_seconds": max(durations),
                "std_dev_seconds": statistics.stdev(durations) if len(durations) > 1 else 0
            },
            "throughput_stats": {
                "mean_chars_per_sec": statistics.mean(throughputs),
                "median_chars_per_sec": statistics.median(throughputs),
                "min_chars_per_sec": min(throughputs),
                "max_chars_per_sec": max(throughputs),
                "std_dev_chars_per_sec": statistics.stdev(throughputs) if len(throughputs) > 1 else 0
            },
            "text_length_stats": {
                "mean_length": statistics.mean(text_lengths),
                "min_length": min(text_lengths),
                "max_length": max(text_lengths)
            }
        }
        
        return analysis
        
    def save_report(self, output_dir: str = "test_reports"):
        """Save performance report to JSON file."""
        os.makedirs(output_dir, exist_ok=True)
        
        report = {
            "session_id": self.test_session_id,
            "timestamp": datetime.now().isoformat(),
            "raw_metrics": self.metrics,
            "analysis": {}
        }
        
        # Generate analysis for each test type
        for key in self.metrics:
            model_name, test_type = key.split("_", 1)
            report["analysis"][key] = self.analyze_performance(model_name, test_type)
            
        filename = f"{output_dir}/inference_performance_{self.test_session_id}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
            
        return filename


class TestInferencePerformance:
    """Test suite for inference performance benchmarks."""
    
    @pytest.fixture(scope="class")
    def performance_collector(self):
        """Create performance collector for the test session."""
        return InferencePerformanceCollector()
        
    @pytest.fixture(scope="class") 
    def test_texts(self):
        """Test texts of varying lengths for performance testing."""
        return {
            "short": "Hello world",
            "medium": "The quick brown fox jumps over the lazy dog. " * 10,
            "long": "This is a longer text for testing translation performance with more complex sentences and vocabulary. " * 20,
            "very_long": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 50
        }
        
    def test_nllb_single_inference_performance(self, performance_collector, test_texts):
        """Test NLLB single inference performance across text lengths."""
        config = ServiceConfig(
            model_name="facebook/nllb-200-distilled-600M",
            cache_dir="/mnt/dionysus/coding/tg-text-translate/test-data/cache"
        )
        
        service_manager = RobustServiceManager()
        service_url = service_manager.start_with_model_wait(
            config=config, model_name="nllb", timeout=1800)
        
        try:
            client = ComprehensiveTestClient(service_url)
            
            # Test each text length category
            for length_category, text in test_texts.items():
                print(f"\nTesting NLLB single inference - {length_category} text ({len(text)} chars)")
                
                # Perform multiple inferences for statistical significance
                for i in range(5):
                    start_time = time.time()
                    
                    try:
                        response = client.translate(
                            text=text,
                            source_lang="en", 
                            target_lang="es"
                        )
                        duration = time.time() - start_time
                        success = response.get("status") == "success"
                        
                        performance_collector.record_inference(
                            model_name="nllb",
                            test_type=f"single_{length_category}",
                            text_length=len(text),
                            duration_seconds=duration,
                            success=success,
                            metadata={
                                "iteration": i + 1,
                                "source_lang": "en",
                                "target_lang": "es"
                            }
                        )
                        
                        if success:
                            print(f"  Iteration {i+1}: {duration:.3f}s ({len(text)/duration:.1f} chars/sec)")
                        else:
                            print(f"  Iteration {i+1}: FAILED - {response.get('error', 'Unknown error')}")
                            
                    except Exception as e:
                        duration = time.time() - start_time
                        performance_collector.record_inference(
                            model_name="nllb",
                            test_type=f"single_{length_category}",
                            text_length=len(text),
                            duration_seconds=duration,
                            success=False,
                            metadata={
                                "iteration": i + 1,
                                "error": str(e)
                            }
                        )
                        print(f"  Iteration {i+1}: ERROR - {str(e)}")
                        
        finally:
            service_manager.cleanup()
            
        # Verify we collected metrics
        for length_category in test_texts.keys():
            analysis = performance_collector.analyze_performance("nllb", f"single_{length_category}")
            assert "error" not in analysis, f"No metrics collected for {length_category} text"
            print(f"\n{length_category.upper()} text performance:")
            print(f"  Mean latency: {analysis['latency_stats']['mean_seconds']:.3f}s")
            print(f"  Mean throughput: {analysis['throughput_stats']['mean_chars_per_sec']:.1f} chars/sec")
            
    def test_concurrent_inference_performance(self, performance_collector, test_texts):
        """Test concurrent inference performance with multiple requests."""
        config = ServiceConfig(
            model_name="facebook/nllb-200-distilled-600M",
            cache_dir="/mnt/dionysus/coding/tg-text-translate/test-data/cache"
        )
        
        service_manager = RobustServiceManager()
        service_url = service_manager.start_with_model_wait(
            config=config, model_name="nllb", timeout=1800)
        
        try:
            def single_translation(iteration: int, text: str) -> Tuple[int, bool, float, Optional[str]]:
                """Perform a single translation and return metrics."""
                client = ComprehensiveTestClient(service_url)
                start_time = time.time()
                
                try:
                    response = client.translate(
                        text=text,
                        source_lang="en",
                        target_lang="es"
                    )
                    duration = time.time() - start_time
                    success = response.get("status") == "success"
                    error = None if success else response.get("error", "Unknown error")
                    
                    return iteration, success, duration, error
                    
                except Exception as e:
                    duration = time.time() - start_time
                    return iteration, False, duration, str(e)
            
            # Test concurrent load with medium text
            test_text = test_texts["medium"]
            concurrent_requests = 3
            
            print(f"\nTesting concurrent inference - {concurrent_requests} requests")
            print(f"Text length: {len(test_text)} chars")
            
            # Use ThreadPoolExecutor for concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
                # Submit all tasks
                futures = [
                    executor.submit(single_translation, i, test_text)
                    for i in range(concurrent_requests)
                ]
                
                # Collect results
                start_time = time.time()
                results = []
                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())
                total_time = time.time() - start_time
                
            # Record metrics for each request
            for iteration, success, duration, error in results:
                performance_collector.record_inference(
                    model_name="nllb",
                    test_type="concurrent",
                    text_length=len(test_text),
                    duration_seconds=duration,
                    success=success,
                    metadata={
                        "iteration": iteration,
                        "concurrent_requests": concurrent_requests,
                        "total_batch_time": total_time,
                        "error": error
                    }
                )
                
                if success:
                    print(f"  Request {iteration}: {duration:.3f}s ({len(test_text)/duration:.1f} chars/sec)")
                else:
                    print(f"  Request {iteration}: FAILED - {error}")
                    
            # Analyze concurrent performance
            analysis = performance_collector.analyze_performance("nllb", "concurrent")
            assert "error" not in analysis, "No metrics collected for concurrent test"
            
            print(f"\nConcurrent performance summary:")
            print(f"  Total batch time: {total_time:.3f}s")
            print(f"  Success rate: {analysis['test_info']['success_rate']:.1%}")
            print(f"  Mean individual latency: {analysis['latency_stats']['mean_seconds']:.3f}s")
            print(f"  Total throughput: {(len(test_text) * concurrent_requests) / total_time:.1f} chars/sec")
            
        finally:
            service_manager.cleanup()
            
    def test_aya_inference_performance(self, performance_collector, test_texts):
        """Test Aya model inference performance."""
        config = ServiceConfig(
            model_name="CohereForAI/aya-expanse-8b",
            cache_dir="/mnt/dionysus/coding/tg-text-translate/test-data/cache"
        )
        
        service_manager = RobustServiceManager()
        service_url = service_manager.start_with_model_wait(
            config=config, model_name="aya", timeout=1800)
        
        try:
            client = ComprehensiveTestClient(service_url)
            
            # Test with medium text for comparison with NLLB
            text = test_texts["medium"]
            print(f"\nTesting Aya inference performance")
            print(f"Text length: {len(text)} chars")
            
            # Perform multiple inferences for statistical significance
            for i in range(3):
                start_time = time.time()
                
                try:
                    response = client.translate(
                        text=text,
                        source_lang="en",
                        target_lang="es"
                    )
                    duration = time.time() - start_time
                    success = response.get("status") == "success"
                    
                    performance_collector.record_inference(
                        model_name="aya",
                        test_type="single_medium",
                        text_length=len(text),
                        duration_seconds=duration,
                        success=success,
                        metadata={
                            "iteration": i + 1,
                            "source_lang": "en", 
                            "target_lang": "es"
                        }
                    )
                    
                    if success:
                        print(f"  Iteration {i+1}: {duration:.3f}s ({len(text)/duration:.1f} chars/sec)")
                    else:
                        print(f"  Iteration {i+1}: FAILED - {response.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    duration = time.time() - start_time
                    performance_collector.record_inference(
                        model_name="aya",
                        test_type="single_medium", 
                        text_length=len(text),
                        duration_seconds=duration,
                        success=False,
                        metadata={
                            "iteration": i + 1,
                            "error": str(e)
                        }
                    )
                    print(f"  Iteration {i+1}: ERROR - {str(e)}")
                    
        finally:
            service_manager.cleanup()
            
        # Verify we collected metrics
        analysis = performance_collector.analyze_performance("aya", "single_medium")
        assert "error" not in analysis, "No metrics collected for Aya"
        print(f"\nAya performance summary:")
        print(f"  Mean latency: {analysis['latency_stats']['mean_seconds']:.3f}s")
        print(f"  Mean throughput: {analysis['throughput_stats']['mean_chars_per_sec']:.1f} chars/sec")
        
    @pytest.fixture(scope="class", autouse=True)
    def save_performance_report(self, request, performance_collector):
        """Save performance report after all tests complete."""
        yield
        
        # This runs after all tests in the class
        report_file = performance_collector.save_report()
        print(f"\nPerformance report saved to: {report_file}")
        
        # Print summary
        print("\n=== INFERENCE PERFORMANCE SUMMARY ===")
        for key, metrics in performance_collector.metrics.items():
            if metrics:
                model_name, test_type = key.split("_", 1)
                analysis = performance_collector.analyze_performance(model_name, test_type)
                if "error" not in analysis:
                    print(f"\n{model_name.upper()} - {test_type}:")
                    print(f"  Success Rate: {analysis['test_info']['success_rate']:.1%}")
                    print(f"  Mean Latency: {analysis['latency_stats']['mean_seconds']:.3f}s")
                    print(f"  Mean Throughput: {analysis['throughput_stats']['mean_chars_per_sec']:.1f} chars/sec")