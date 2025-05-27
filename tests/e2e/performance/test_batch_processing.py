"""
E2E Test: Batch Processing Stress Tests
Tests batch translation performance and stress scenarios.
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


class BatchProcessingCollector:
    """Collects and analyzes batch processing performance metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, List[Dict]] = {}
        self.test_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def record_batch(self, model_name: str, test_type: str, 
                    batch_size: int, total_duration: float,
                    successful_translations: int, failed_translations: int,
                    total_chars: int, metadata: Optional[Dict] = None):
        """Record batch processing metrics."""
        key = f"{model_name}_{test_type}"
        
        if key not in self.metrics:
            self.metrics[key] = []
            
        record = {
            "timestamp": datetime.now().isoformat(),
            "batch_size": batch_size,
            "total_duration": total_duration,
            "successful_translations": successful_translations,
            "failed_translations": failed_translations,
            "success_rate": successful_translations / batch_size if batch_size > 0 else 0,
            "total_chars": total_chars,
            "throughput_chars_per_sec": total_chars / total_duration if total_duration > 0 else 0,
            "throughput_translations_per_sec": successful_translations / total_duration if total_duration > 0 else 0,
            "metadata": metadata or {}
        }
        
        self.metrics[key].append(record)
        
    def analyze_batch_performance(self, model_name: str, test_type: str) -> Dict:
        """Analyze batch performance metrics."""
        key = f"{model_name}_{test_type}"
        
        if key not in self.metrics or not self.metrics[key]:
            return {"error": "No metrics found"}
            
        metrics = self.metrics[key]
        
        # Extract key performance indicators
        success_rates = [m["success_rate"] for m in metrics]
        throughput_chars = [m["throughput_chars_per_sec"] for m in metrics]
        throughput_translations = [m["throughput_translations_per_sec"] for m in metrics]
        durations = [m["total_duration"] for m in metrics]
        batch_sizes = [m["batch_size"] for m in metrics]
        
        analysis = {
            "test_info": {
                "model_name": model_name,
                "test_type": test_type,
                "total_batches": len(metrics),
                "total_translations": sum(m["successful_translations"] + m["failed_translations"] for m in metrics),
                "total_successful": sum(m["successful_translations"] for m in metrics),
                "overall_success_rate": sum(m["successful_translations"] for m in metrics) / 
                                      sum(m["successful_translations"] + m["failed_translations"] for m in metrics)
                                      if sum(m["successful_translations"] + m["failed_translations"] for m in metrics) > 0 else 0
            },
            "success_rate_stats": {
                "mean": statistics.mean(success_rates),
                "min": min(success_rates),
                "max": max(success_rates),
                "std_dev": statistics.stdev(success_rates) if len(success_rates) > 1 else 0
            },
            "throughput_chars_stats": {
                "mean_chars_per_sec": statistics.mean(throughput_chars),
                "median_chars_per_sec": statistics.median(throughput_chars),
                "min_chars_per_sec": min(throughput_chars),
                "max_chars_per_sec": max(throughput_chars),
                "std_dev_chars_per_sec": statistics.stdev(throughput_chars) if len(throughput_chars) > 1 else 0
            },
            "throughput_translation_stats": {
                "mean_translations_per_sec": statistics.mean(throughput_translations),
                "median_translations_per_sec": statistics.median(throughput_translations),
                "min_translations_per_sec": min(throughput_translations),
                "max_translations_per_sec": max(throughput_translations),
                "std_dev_translations_per_sec": statistics.stdev(throughput_translations) if len(throughput_translations) > 1 else 0
            },
            "duration_stats": {
                "mean_duration": statistics.mean(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "total_duration": sum(durations)
            },
            "batch_size_stats": {
                "mean_batch_size": statistics.mean(batch_sizes),
                "min_batch_size": min(batch_sizes), 
                "max_batch_size": max(batch_sizes)
            }
        }
        
        return analysis
        
    def save_report(self, output_dir: str = "test_reports"):
        """Save batch processing report to JSON file."""
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
            report["analysis"][key] = self.analyze_batch_performance(model_name, test_type)
            
        filename = f"{output_dir}/batch_processing_{self.test_session_id}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
            
        return filename


class TestBatchProcessing:
    """Test suite for batch processing performance and stress tests."""
    
    @pytest.fixture(scope="class")
    def batch_collector(self):
        """Create batch processing collector for the test session."""
        return BatchProcessingCollector()
        
    @pytest.fixture(scope="class") 
    def test_texts_batch(self):
        """Test texts for batch processing."""
        return [
            "Hello world",
            "How are you today?",
            "The weather is nice.",
            "I love learning languages.",
            "Translation is important for communication.",
            "Technology makes the world smaller.",
            "Artificial intelligence is fascinating.",
            "Machine learning helps solve problems.",
            "Natural language processing is evolving.",
            "Global communication breaks down barriers."
        ]
        
    def test_nllb_small_batch_processing(self, batch_collector, test_texts_batch):
        """Test NLLB small batch processing performance."""
        config = ServiceConfig(
            model_name="facebook/nllb-200-distilled-600M",
            cache_dir="/mnt/dionysus/coding/tg-text-translate/test-data/cache"
        )
        
        service_manager = RobustServiceManager()
        service_url = service_manager.start_with_model_wait(
            config=config, model_name="nllb", timeout=1800)
        
        try:
            client = ComprehensiveTestClient(service_url)
            
            # Test small batches
            batch_sizes = [2, 5]
            
            for batch_size in batch_sizes:
                print(f"\nTesting NLLB batch size: {batch_size}")
                
                # Create batch from test texts
                batch_texts = test_texts_batch[:batch_size]
                total_chars = sum(len(text) for text in batch_texts)
                
                start_time = time.time()
                successful = 0
                failed = 0
                
                # Process batch sequentially for now (to avoid overwhelming service)
                for i, text in enumerate(batch_texts):
                    try:
                        response = client.translate(
                            text=text,
                            source_lang="en",
                            target_lang="es"
                        )
                        
                        if response.get("status") == "success":
                            successful += 1
                            print(f"  Translation {i+1}/{batch_size}: SUCCESS")
                        else:
                            failed += 1
                            print(f"  Translation {i+1}/{batch_size}: FAILED - {response.get('error', 'Unknown')}")
                            
                    except Exception as e:
                        failed += 1
                        print(f"  Translation {i+1}/{batch_size}: ERROR - {str(e)}")
                
                total_duration = time.time() - start_time
                
                # Record batch metrics
                batch_collector.record_batch(
                    model_name="nllb",
                    test_type="small_batch",
                    batch_size=batch_size,
                    total_duration=total_duration,
                    successful_translations=successful,
                    failed_translations=failed,
                    total_chars=total_chars,
                    metadata={
                        "processing_mode": "sequential",
                        "source_lang": "en",
                        "target_lang": "es"
                    }
                )
                
                print(f"Batch {batch_size} results:")
                print(f"  Duration: {total_duration:.2f}s")
                print(f"  Success rate: {successful}/{batch_size} ({100*successful/batch_size:.1f}%)")
                print(f"  Throughput: {total_chars/total_duration:.1f} chars/sec")
                print(f"  Translations per sec: {successful/total_duration:.2f}")
                
        finally:
            service_manager.cleanup()
            
        # Verify we collected metrics
        analysis = batch_collector.analyze_batch_performance("nllb", "small_batch")
        assert "error" not in analysis, "No metrics collected for small batch test"
        print(f"\nSmall batch performance summary:")
        print(f"  Overall success rate: {analysis['test_info']['overall_success_rate']:.1%}")
        print(f"  Mean throughput: {analysis['throughput_chars_stats']['mean_chars_per_sec']:.1f} chars/sec")
        
    def test_nllb_stress_batch_processing(self, batch_collector, test_texts_batch):
        """Test NLLB stress batch processing with larger batches.""" 
        config = ServiceConfig(
            model_name="facebook/nllb-200-distilled-600M",
            cache_dir="/mnt/dionysus/coding/tg-text-translate/test-data/cache"
        )
        
        service_manager = RobustServiceManager()
        service_url = service_manager.start_with_model_wait(
            config=config, model_name="nllb", timeout=1800)
        
        try:
            client = ComprehensiveTestClient(service_url)
            
            # Test stress batch (use all texts, repeat to make larger batch)
            stress_batch = test_texts_batch * 2  # 20 translations
            batch_size = len(stress_batch)
            total_chars = sum(len(text) for text in stress_batch)
            
            print(f"\nTesting NLLB stress batch: {batch_size} translations")
            print(f"Total characters: {total_chars}")
            
            start_time = time.time()
            successful = 0
            failed = 0
            
            # Process stress batch
            for i, text in enumerate(stress_batch):
                try:
                    response = client.translate(
                        text=text,
                        source_lang="en",
                        target_lang="es"
                    )
                    
                    if response.get("status") == "success":
                        successful += 1
                        if (i + 1) % 5 == 0:  # Progress update every 5 translations
                            print(f"  Progress: {i+1}/{batch_size} translations completed")
                    else:
                        failed += 1
                        print(f"  Translation {i+1}: FAILED - {response.get('error', 'Unknown')}")
                        
                except Exception as e:
                    failed += 1
                    print(f"  Translation {i+1}: ERROR - {str(e)}")
            
            total_duration = time.time() - start_time
            
            # Record stress batch metrics
            batch_collector.record_batch(
                model_name="nllb",
                test_type="stress_batch",
                batch_size=batch_size,
                total_duration=total_duration,
                successful_translations=successful,
                failed_translations=failed,
                total_chars=total_chars,
                metadata={
                    "processing_mode": "sequential",
                    "source_lang": "en",
                    "target_lang": "es",
                    "stress_test": True
                }
            )
            
            print(f"\nStress batch results:")
            print(f"  Duration: {total_duration:.2f}s")
            print(f"  Success rate: {successful}/{batch_size} ({100*successful/batch_size:.1f}%)")
            print(f"  Throughput: {total_chars/total_duration:.1f} chars/sec")
            print(f"  Translations per sec: {successful/total_duration:.2f}")
            
        finally:
            service_manager.cleanup()
            
        # Verify we collected metrics
        analysis = batch_collector.analyze_batch_performance("nllb", "stress_batch")
        assert "error" not in analysis, "No metrics collected for stress batch test"
        print(f"\nStress batch performance summary:")
        print(f"  Overall success rate: {analysis['test_info']['overall_success_rate']:.1%}")
        print(f"  Mean throughput: {analysis['throughput_chars_stats']['mean_chars_per_sec']:.1f} chars/sec")
        
    def test_concurrent_batch_processing(self, batch_collector, test_texts_batch):
        """Test concurrent batch processing with multiple parallel requests."""
        config = ServiceConfig(
            model_name="facebook/nllb-200-distilled-600M",
            cache_dir="/mnt/dionysus/coding/tg-text-translate/test-data/cache"
        )
        
        service_manager = RobustServiceManager()
        service_url = service_manager.start_with_model_wait(
            config=config, model_name="nllb", timeout=1800)
        
        try:
            def process_translation(text: str, index: int) -> Tuple[int, bool, str]:
                """Process single translation in thread."""
                client = ComprehensiveTestClient(service_url)
                try:
                    response = client.translate(
                        text=text,
                        source_lang="en",
                        target_lang="es"
                    )
                    success = response.get("status") == "success"
                    error = None if success else response.get("error", "Unknown")
                    return index, success, error
                except Exception as e:
                    return index, False, str(e)
            
            # Test concurrent processing with moderate batch
            concurrent_batch = test_texts_batch[:6]  # 6 concurrent translations
            batch_size = len(concurrent_batch)
            total_chars = sum(len(text) for text in concurrent_batch)
            
            print(f"\nTesting concurrent batch processing: {batch_size} parallel translations")
            
            start_time = time.time()
            
            # Use ThreadPoolExecutor for concurrent processing
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                # Submit all tasks
                futures = [
                    executor.submit(process_translation, text, i)
                    for i, text in enumerate(concurrent_batch)
                ]
                
                # Collect results
                results = []
                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())
                    
            total_duration = time.time() - start_time
            
            # Analyze results
            successful = sum(1 for _, success, _ in results if success)
            failed = batch_size - successful
            
            # Record concurrent batch metrics
            batch_collector.record_batch(
                model_name="nllb",
                test_type="concurrent_batch",
                batch_size=batch_size,
                total_duration=total_duration,
                successful_translations=successful,
                failed_translations=failed,
                total_chars=total_chars,
                metadata={
                    "processing_mode": "concurrent",
                    "max_workers": 3,
                    "source_lang": "en",
                    "target_lang": "es"
                }
            )
            
            print(f"Concurrent batch results:")
            print(f"  Duration: {total_duration:.2f}s")
            print(f"  Success rate: {successful}/{batch_size} ({100*successful/batch_size:.1f}%)")
            print(f"  Throughput: {total_chars/total_duration:.1f} chars/sec")
            print(f"  Translations per sec: {successful/total_duration:.2f}")
            
            # Print individual results
            for index, success, error in sorted(results):
                status = "SUCCESS" if success else f"FAILED: {error}"
                print(f"  Translation {index+1}: {status}")
                
        finally:
            service_manager.cleanup()
            
        # Verify we collected metrics
        analysis = batch_collector.analyze_batch_performance("nllb", "concurrent_batch")
        assert "error" not in analysis, "No metrics collected for concurrent batch test"
        print(f"\nConcurrent batch performance summary:")
        print(f"  Overall success rate: {analysis['test_info']['overall_success_rate']:.1%}")
        print(f"  Mean throughput: {analysis['throughput_chars_stats']['mean_chars_per_sec']:.1f} chars/sec")
        
    @pytest.fixture(scope="class", autouse=True)
    def save_batch_report(self, request, batch_collector):
        """Save batch processing report after all tests complete."""
        yield
        
        # This runs after all tests in the class
        report_file = batch_collector.save_report()
        print(f"\nBatch processing report saved to: {report_file}")
        
        # Print summary
        print("\n=== BATCH PROCESSING SUMMARY ===")
        for key, metrics in batch_collector.metrics.items():
            if metrics:
                model_name, test_type = key.split("_", 1)
                analysis = batch_collector.analyze_batch_performance(model_name, test_type)
                if "error" not in analysis:
                    print(f"\n{model_name.upper()} - {test_type}:")
                    print(f"  Total Batches: {analysis['test_info']['total_batches']}")
                    print(f"  Overall Success Rate: {analysis['test_info']['overall_success_rate']:.1%}")
                    print(f"  Mean Throughput: {analysis['throughput_chars_stats']['mean_chars_per_sec']:.1f} chars/sec")
                    print(f"  Mean Translations/sec: {analysis['throughput_translation_stats']['mean_translations_per_sec']:.2f}")