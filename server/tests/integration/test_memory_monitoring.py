"""
Memory usage monitoring tests for the NLLB Translation API.

This module provides comprehensive memory usage testing including:
- Memory leak detection during translation operations
- Memory usage patterns under different loads
- Memory efficiency analysis
- Memory growth monitoring over time
"""

import time
import psutil
import pytest
import gc
import threading
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
import statistics
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class MemorySnapshot:
    """Container for memory usage snapshot data."""
    
    timestamp: float
    rss_mb: float  # Resident Set Size in MB
    vms_mb: float  # Virtual Memory Size in MB
    percent: float  # Memory percentage
    available_mb: float  # Available system memory in MB
    num_fds: int  # Number of file descriptors
    num_threads: int  # Number of threads
    
    @classmethod
    def capture(cls, process: psutil.Process) -> 'MemorySnapshot':
        """Capture current memory snapshot."""
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()
        system_memory = psutil.virtual_memory()
        
        try:
            num_fds = process.num_fds()
        except (AttributeError, OSError):
            num_fds = 0  # Not available on all platforms
        
        return cls(
            timestamp=time.time(),
            rss_mb=memory_info.rss / 1024 / 1024,
            vms_mb=memory_info.vms / 1024 / 1024,
            percent=memory_percent,
            available_mb=system_memory.available / 1024 / 1024,
            num_fds=num_fds,
            num_threads=process.num_threads()
        )

class MemoryMonitor:
    """Memory monitoring utility for translation operations."""
    
    def __init__(self, process: Optional[psutil.Process] = None):
        self.process = process or psutil.Process()
        self.snapshots: List[MemorySnapshot] = []
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_interval = 0.5  # Monitor every 500ms
    
    def start_monitoring(self, interval: float = 0.5):
        """Start continuous memory monitoring in background thread."""
        if self.monitoring_active:
            return
        
        self.monitor_interval = interval
        self.monitoring_active = True
        self.snapshots.clear()
        
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self) -> List[MemorySnapshot]:
        """Stop monitoring and return collected snapshots."""
        if not self.monitoring_active:
            return self.snapshots
        
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        
        return self.snapshots.copy()
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.monitoring_active:
            try:
                snapshot = MemorySnapshot.capture(self.process)
                self.snapshots.append(snapshot)
                time.sleep(self.monitor_interval)
            except Exception as e:
                print(f"Memory monitoring error: {e}")
                break
    
    def capture_snapshot(self) -> MemorySnapshot:
        """Capture a single memory snapshot."""
        return MemorySnapshot.capture(self.process)
    
    def analyze_memory_growth(self) -> Dict[str, float]:
        """Analyze memory growth patterns from collected snapshots."""
        if len(self.snapshots) < 2:
            return {}
        
        first_snapshot = self.snapshots[0]
        last_snapshot = self.snapshots[-1]
        duration = last_snapshot.timestamp - first_snapshot.timestamp
        
        # Calculate growth rates
        rss_growth = last_snapshot.rss_mb - first_snapshot.rss_mb
        vms_growth = last_snapshot.vms_mb - first_snapshot.vms_mb
        
        # Calculate memory usage statistics
        rss_values = [s.rss_mb for s in self.snapshots]
        vms_values = [s.vms_mb for s in self.snapshots]
        
        return {
            'duration_seconds': duration,
            'rss_growth_mb': rss_growth,
            'vms_growth_mb': vms_growth,
            'rss_growth_rate_mb_per_min': (rss_growth / duration * 60) if duration > 0 else 0,
            'vms_growth_rate_mb_per_min': (vms_growth / duration * 60) if duration > 0 else 0,
            'peak_rss_mb': max(rss_values),
            'peak_vms_mb': max(vms_values),
            'avg_rss_mb': statistics.mean(rss_values),
            'avg_vms_mb': statistics.mean(vms_values),
            'rss_variance': statistics.variance(rss_values) if len(rss_values) > 1 else 0,
            'vms_variance': statistics.variance(vms_values) if len(vms_values) > 1 else 0,
            'num_snapshots': len(self.snapshots)
        }
    
    def detect_memory_leaks(self, threshold_mb: float = 50.0) -> Dict[str, any]:
        """Detect potential memory leaks based on growth patterns."""
        analysis = self.analyze_memory_growth()
        
        if not analysis:
            return {'leak_detected': False, 'reason': 'Insufficient data'}
        
        # Leak detection criteria
        leak_indicators = []
        
        # Check growth rate
        if analysis['rss_growth_rate_mb_per_min'] > threshold_mb:
            leak_indicators.append(f"High RSS growth rate: {analysis['rss_growth_rate_mb_per_min']:.2f} MB/min")
        
        if analysis['vms_growth_rate_mb_per_min'] > threshold_mb:
            leak_indicators.append(f"High VMS growth rate: {analysis['vms_growth_rate_mb_per_min']:.2f} MB/min")
        
        # Check absolute growth
        if analysis['rss_growth_mb'] > threshold_mb * 2:
            leak_indicators.append(f"Large RSS growth: {analysis['rss_growth_mb']:.2f} MB")
        
        # Check memory variance (unstable memory usage)
        if analysis['rss_variance'] > (analysis['avg_rss_mb'] * 0.1) ** 2:
            leak_indicators.append(f"High memory variance: {analysis['rss_variance']:.2f}")
        
        return {
            'leak_detected': len(leak_indicators) > 0,
            'indicators': leak_indicators,
            'analysis': analysis
        }

@pytest.fixture
def memory_monitor():
    """Fixture providing memory monitor instance."""
    monitor = MemoryMonitor()
    yield monitor
    if monitor.monitoring_active:
        monitor.stop_monitoring()

class TestMemoryMonitoring:
    """Memory monitoring and leak detection tests."""
    
    def test_baseline_memory_usage(self, test_client, enhanced_mock_objects, api_key_header, memory_monitor):
        """Establish baseline memory usage for single translation requests."""
        
        # Capture initial memory state
        initial_snapshot = memory_monitor.capture_snapshot()
        
        # Force garbage collection to establish clean baseline
        gc.collect()
        time.sleep(0.1)
        baseline_snapshot = memory_monitor.capture_snapshot()
        
        # Perform single translation
        request_data = {
            "text": "Baseline memory usage test for single translation request",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        response = test_client.post("/translate", json=request_data, headers=api_key_header)
        assert response.status_code == 200
        
        # Capture post-translation memory
        post_translation_snapshot = memory_monitor.capture_snapshot()
        
        # Analyze memory impact
        memory_increase = post_translation_snapshot.rss_mb - baseline_snapshot.rss_mb
        
        # Single translation should have minimal memory impact
        assert memory_increase < 10.0, f"Single translation used {memory_increase:.2f} MB, exceeds 10 MB baseline"
        
        # Verify memory is reasonable
        assert post_translation_snapshot.rss_mb < 500.0, f"Total memory usage {post_translation_snapshot.rss_mb:.2f} MB seems excessive"
        
        print(f"Baseline memory: {baseline_snapshot.rss_mb:.2f} MB, "
              f"Post-translation: {post_translation_snapshot.rss_mb:.2f} MB, "
              f"Increase: {memory_increase:.2f} MB")
    
    def test_memory_usage_scaling(self, test_client, enhanced_mock_objects, api_key_header, memory_monitor):
        """Test how memory usage scales with number of translation requests."""
        
        request_counts = [1, 5, 10, 20]
        memory_usage_data = []
        
        request_data = {
            "text": "Memory scaling test with increasing request counts",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        for count in request_counts:
            # Force garbage collection before each test
            gc.collect()
            time.sleep(0.1)
            
            pre_test_snapshot = memory_monitor.capture_snapshot()
            
            # Execute multiple requests
            for i in range(count):
                response = test_client.post("/translate", json=request_data, headers=api_key_header)
                assert response.status_code == 200
            
            post_test_snapshot = memory_monitor.capture_snapshot()
            memory_increase = post_test_snapshot.rss_mb - pre_test_snapshot.rss_mb
            
            memory_usage_data.append((count, memory_increase, post_test_snapshot.rss_mb))
            
            print(f"{count} requests: {memory_increase:.2f} MB increase, total: {post_test_snapshot.rss_mb:.2f} MB")
        
        # Analyze scaling pattern
        memory_increases = [data[1] for data in memory_usage_data]
        
        # Memory increase should not grow exponentially
        max_increase = max(memory_increases)
        assert max_increase < 50.0, f"Maximum memory increase {max_increase:.2f} MB too high for scaling test"
        
        # Memory usage should be relatively stable across different request counts
        if len(memory_increases) > 1:
            memory_variance = statistics.variance(memory_increases)
            avg_increase = statistics.mean(memory_increases)
            coefficient_of_variation = (memory_variance ** 0.5) / avg_increase if avg_increase > 0 else 0
            
            assert coefficient_of_variation < 1.0, f"Memory usage scaling too variable: CV = {coefficient_of_variation:.2f}"
    
    def test_memory_leak_detection_sequential(self, test_client, enhanced_mock_objects, api_key_header, memory_monitor):
        """Test for memory leaks during sequential translation requests."""
        
        request_data = {
            "text": "Sequential memory leak detection test with repeated translations",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        # Start continuous monitoring
        memory_monitor.start_monitoring(interval=0.2)
        
        # Execute many sequential requests
        num_requests = 50
        start_time = time.time()
        
        for i in range(num_requests):
            response = test_client.post("/translate", json=request_data, headers=api_key_header)
            assert response.status_code == 200
            
            # Small delay to allow monitoring
            time.sleep(0.05)
        
        end_time = time.time()
        
        # Stop monitoring and analyze
        snapshots = memory_monitor.stop_monitoring()
        leak_analysis = memory_monitor.detect_memory_leaks(threshold_mb=20.0)
        
        # Verify no significant memory leaks
        assert not leak_analysis['leak_detected'], f"Memory leak detected: {leak_analysis['indicators']}"
        
        analysis = leak_analysis['analysis']
        
        # Memory growth should be minimal for sequential requests
        assert analysis['rss_growth_mb'] < 30.0, f"Excessive memory growth: {analysis['rss_growth_mb']:.2f} MB"
        assert analysis['rss_growth_rate_mb_per_min'] < 15.0, f"High memory growth rate: {analysis['rss_growth_rate_mb_per_min']:.2f} MB/min"
        
        print(f"Sequential leak test: {num_requests} requests, "
              f"{analysis['rss_growth_mb']:.2f} MB growth, "
              f"{analysis['rss_growth_rate_mb_per_min']:.2f} MB/min rate")
    
    def test_memory_usage_concurrent_requests(self, test_client, enhanced_mock_objects, api_key_header, memory_monitor):
        """Test memory usage patterns during concurrent translation requests."""
        
        request_data = {
            "text": "Concurrent memory usage test with simultaneous translation requests",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        # Start monitoring before concurrent test
        memory_monitor.start_monitoring(interval=0.1)
        
        concurrent_users = 15
        requests_per_user = 3
        successful_requests = 0
        
        def concurrent_worker(worker_id: int):
            nonlocal successful_requests
            for req_num in range(requests_per_user):
                try:
                    response = test_client.post("/translate", json=request_data, headers=api_key_header)
                    if response.status_code == 200:
                        successful_requests += 1
                    time.sleep(0.02)  # Small delay between requests
                except Exception as e:
                    print(f"Worker {worker_id} request {req_num} failed: {e}")
        
        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [
                executor.submit(concurrent_worker, worker_id)
                for worker_id in range(concurrent_users)
            ]
            
            # Wait for completion
            for future in futures:
                future.result()
        
        # Stop monitoring and analyze
        snapshots = memory_monitor.stop_monitoring()
        leak_analysis = memory_monitor.detect_memory_leaks(threshold_mb=30.0)
        
        # Verify concurrent memory handling
        analysis = leak_analysis['analysis']
        
        # Memory should not grow excessively during concurrent operations
        assert analysis['rss_growth_mb'] < 50.0, f"Excessive concurrent memory growth: {analysis['rss_growth_mb']:.2f} MB"
        assert analysis['peak_rss_mb'] < 600.0, f"Peak memory usage too high: {analysis['peak_rss_mb']:.2f} MB"
        
        # No memory leaks should be detected
        assert not leak_analysis['leak_detected'], f"Memory leak during concurrent test: {leak_analysis['indicators']}"
        
        print(f"Concurrent memory test: {successful_requests} successful requests, "
              f"Peak: {analysis['peak_rss_mb']:.2f} MB, "
              f"Growth: {analysis['rss_growth_mb']:.2f} MB")
    
    def test_memory_recovery_after_load(self, test_client, enhanced_mock_objects, api_key_header, memory_monitor):
        """Test memory recovery after high load scenarios."""
        
        # Capture baseline memory
        gc.collect()
        time.sleep(0.5)
        baseline_snapshot = memory_monitor.capture_snapshot()
        
        request_data = {
            "text": "Memory recovery test after high load translation processing",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        # Apply high load
        high_load_requests = 30
        for i in range(high_load_requests):
            response = test_client.post("/translate", json=request_data, headers=api_key_header)
            assert response.status_code == 200
        
        # Capture memory after load
        post_load_snapshot = memory_monitor.capture_snapshot()
        load_memory_increase = post_load_snapshot.rss_mb - baseline_snapshot.rss_mb
        
        # Allow time for garbage collection and memory recovery
        gc.collect()
        time.sleep(2.0)
        gc.collect()
        
        # Capture memory after recovery period
        recovery_snapshot = memory_monitor.capture_snapshot()
        recovery_memory_decrease = post_load_snapshot.rss_mb - recovery_snapshot.rss_mb
        
        # Memory should recover significantly after load
        recovery_percentage = (recovery_memory_decrease / load_memory_increase * 100) if load_memory_increase > 0 else 0
        
        assert recovery_percentage > 30, f"Poor memory recovery: {recovery_percentage:.1f}% recovered"
        
        # Final memory should not be excessively higher than baseline
        final_memory_increase = recovery_snapshot.rss_mb - baseline_snapshot.rss_mb
        assert final_memory_increase < 25.0, f"Memory not properly recovered: {final_memory_increase:.2f} MB above baseline"
        
        print(f"Memory recovery: Baseline: {baseline_snapshot.rss_mb:.2f} MB, "
              f"Post-load: {post_load_snapshot.rss_mb:.2f} MB, "
              f"Recovery: {recovery_snapshot.rss_mb:.2f} MB, "
              f"Recovery rate: {recovery_percentage:.1f}%")
    
    def test_memory_usage_different_text_lengths(self, test_client, enhanced_mock_objects, api_key_header, memory_monitor):
        """Test memory usage patterns with different text lengths."""
        
        # Different text lengths for testing
        text_variants = [
            "Short text",
            "Medium length text for translation testing with several words and phrases",
            "Long text content for comprehensive memory usage analysis. " * 10,
            "Very long text content for extensive memory usage testing. " * 25
        ]
        
        memory_usage_by_length = []
        
        for i, text in enumerate(text_variants):
            request_data = {
                "text": text,
                "source_lang": "eng_Latn",
                "target_lang": "fra_Latn"
            }
            
            # Capture memory before translation
            gc.collect()
            time.sleep(0.1)
            pre_snapshot = memory_monitor.capture_snapshot()
            
            # Execute translation
            response = test_client.post("/translate", json=request_data, headers=api_key_header)
            assert response.status_code == 200
            
            # Capture memory after translation
            post_snapshot = memory_monitor.capture_snapshot()
            
            memory_increase = post_snapshot.rss_mb - pre_snapshot.rss_mb
            text_length = len(text)
            
            memory_usage_by_length.append((text_length, memory_increase))
            
            print(f"Text length {text_length} chars: {memory_increase:.2f} MB memory increase")
        
        # Analyze memory scaling with text length
        text_lengths = [data[0] for data in memory_usage_by_length]
        memory_increases = [data[1] for data in memory_usage_by_length]
        
        # Memory usage should not grow exponentially with text length
        max_memory_increase = max(memory_increases)
        assert max_memory_increase < 30.0, f"Excessive memory usage for long text: {max_memory_increase:.2f} MB"
        
        # Check if memory usage correlates reasonably with text length
        if len(memory_increases) > 2:
            # Memory increase shouldn't be dramatically different for different lengths
            memory_range = max(memory_increases) - min(memory_increases)
            assert memory_range < 25.0, f"Memory usage varies too much with text length: {memory_range:.2f} MB range"
    
    def test_memory_monitoring_system_health(self, memory_monitor):
        """Test the memory monitoring system itself for accuracy and reliability."""
        
        # Test snapshot capture
        snapshot1 = memory_monitor.capture_snapshot()
        assert snapshot1.rss_mb > 0, "RSS memory should be positive"
        assert snapshot1.vms_mb > 0, "VMS memory should be positive"
        assert 0 <= snapshot1.percent <= 100, f"Memory percentage {snapshot1.percent} out of range"
        assert snapshot1.available_mb > 0, "Available memory should be positive"
        assert snapshot1.num_threads > 0, "Thread count should be positive"
        
        # Test monitoring start/stop
        memory_monitor.start_monitoring(interval=0.1)
        assert memory_monitor.monitoring_active, "Monitoring should be active after start"
        
        time.sleep(0.5)  # Allow some snapshots to be collected
        
        snapshots = memory_monitor.stop_monitoring()
        assert not memory_monitor.monitoring_active, "Monitoring should be inactive after stop"
        assert len(snapshots) > 0, "Should have collected some snapshots"
        
        # Test analysis functions
        if len(snapshots) >= 2:
            analysis = memory_monitor.analyze_memory_growth()
            assert 'duration_seconds' in analysis, "Analysis missing duration"
            assert 'rss_growth_mb' in analysis, "Analysis missing RSS growth"
            assert analysis['num_snapshots'] == len(snapshots), "Snapshot count mismatch"
            
            # Test leak detection
            leak_analysis = memory_monitor.detect_memory_leaks(threshold_mb=1000.0)  # High threshold for health check
            assert 'leak_detected' in leak_analysis, "Leak analysis missing detection result"
            assert 'analysis' in leak_analysis, "Leak analysis missing detailed analysis"
        
        print(f"Memory monitoring health check passed: {len(snapshots)} snapshots collected")
    
    def test_save_memory_usage_report(self, test_client, enhanced_mock_objects, api_key_header, memory_monitor):
        """Test saving comprehensive memory usage report."""
        
        # Start monitoring for comprehensive test
        memory_monitor.start_monitoring(interval=0.2)
        
        request_data = {
            "text": "Memory usage reporting test with comprehensive data collection",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        }
        
        # Execute various operations for report data
        test_operations = [
            ("Single request", 1),
            ("Multiple requests", 5),
            ("Batch requests", 10)
        ]
        
        operation_results = []
        
        for operation_name, request_count in test_operations:
            start_snapshot = memory_monitor.capture_snapshot()
            
            for i in range(request_count):
                response = test_client.post("/translate", json=request_data, headers=api_key_header)
                assert response.status_code == 200
                time.sleep(0.1)
            
            end_snapshot = memory_monitor.capture_snapshot()
            
            operation_results.append({
                'operation': operation_name,
                'request_count': request_count,
                'start_memory_mb': start_snapshot.rss_mb,
                'end_memory_mb': end_snapshot.rss_mb,
                'memory_increase_mb': end_snapshot.rss_mb - start_snapshot.rss_mb,
                'duration_seconds': end_snapshot.timestamp - start_snapshot.timestamp
            })
        
        # Stop monitoring and create comprehensive report
        all_snapshots = memory_monitor.stop_monitoring()
        analysis = memory_monitor.analyze_memory_growth()
        leak_analysis = memory_monitor.detect_memory_leaks()
        
        # Create comprehensive report
        report = {
            'timestamp': time.time(),
            'test_summary': {
                'total_operations': len(operation_results),
                'monitoring_duration': analysis.get('duration_seconds', 0),
                'total_snapshots': len(all_snapshots),
                'memory_leak_detected': leak_analysis['leak_detected']
            },
            'memory_analysis': analysis,
            'leak_detection': leak_analysis,
            'operation_results': operation_results,
            'memory_snapshots': [
                {
                    'timestamp': s.timestamp,
                    'rss_mb': s.rss_mb,
                    'vms_mb': s.vms_mb,
                    'percent': s.percent,
                    'available_mb': s.available_mb,
                    'num_threads': s.num_threads
                }
                for s in all_snapshots[::5]  # Every 5th snapshot to reduce report size
            ]
        }
        
        # Save comprehensive report
        report_path = "/mnt/dionysus/coding/tg-text-translate/test_reports/memory_usage_report.json"
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Verify report was saved and contains expected data
        assert Path(report_path).exists(), "Memory usage report not saved"
        
        with open(report_path, 'r') as f:
            saved_report = json.load(f)
        
        assert 'test_summary' in saved_report, "Report missing test summary"
        assert 'memory_analysis' in saved_report, "Report missing memory analysis"
        assert 'operation_results' in saved_report, "Report missing operation results"
        assert len(saved_report['operation_results']) == len(operation_results), "Report missing operation data"
        
        print(f"Memory usage report saved: {len(all_snapshots)} snapshots, "
              f"{analysis.get('rss_growth_mb', 0):.2f} MB growth, "
              f"Leak detected: {leak_analysis['leak_detected']}")