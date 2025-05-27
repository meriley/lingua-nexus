"""Performance monitoring utilities for E2E tests."""

import time
import statistics
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from contextlib import contextmanager
import psutil
import requests


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    response_time: float
    throughput: float
    cpu_usage: float
    memory_usage: float
    concurrent_connections: int
    error_rate: float
    timestamp: float


class PerformanceMonitor:
    """Monitors and tracks performance metrics during E2E tests."""
    
    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
        self.baseline_metrics: Optional[PerformanceMetrics] = None
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        
    def start_monitoring(self, interval: float = 1.0):
        """Start continuous performance monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop continuous performance monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
    
    def _monitor_loop(self, interval: float):
        """Background monitoring loop."""
        while self._monitoring:
            try:
                # Basic system metrics
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory_info = psutil.virtual_memory()
                
                # Create basic metrics entry
                metrics = PerformanceMetrics(
                    response_time=0.0,  # Will be updated by request measurements
                    throughput=0.0,     # Will be calculated separately
                    cpu_usage=cpu_percent,
                    memory_usage=memory_info.percent,
                    concurrent_connections=0,  # Will be updated by connection tracking
                    error_rate=0.0,    # Will be calculated from request results
                    timestamp=time.time()
                )
                
                self.metrics_history.append(metrics)
                
            except Exception:
                pass  # Continue monitoring even if metrics collection fails
            
            time.sleep(interval)
    
    def measure_request_performance(
        self, 
        request_func: Callable[[], Any],
        expected_response_time: float = 2.0
    ) -> Dict[str, Any]:
        """Measure performance of a single request."""
        start_time = time.time()
        start_cpu = psutil.cpu_percent()
        start_memory = psutil.virtual_memory().percent
        
        try:
            result = request_func()
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        end_time = time.time()
        end_cpu = psutil.cpu_percent()
        end_memory = psutil.virtual_memory().percent
        
        response_time = end_time - start_time
        
        performance_data = {
            "response_time": response_time,
            "success": success,
            "error": error,
            "cpu_change": end_cpu - start_cpu,
            "memory_change": end_memory - start_memory,
            "meets_sla": response_time <= expected_response_time,
            "timestamp": start_time
        }
        
        return performance_data
    
    def measure_concurrent_performance(
        self,
        request_func: Callable[[], Any],
        num_concurrent: int = 5,
        duration: float = 10.0
    ) -> Dict[str, Any]:
        """Measure performance under concurrent load."""
        results = []
        errors = []
        
        def worker():
            """Worker thread for concurrent requests."""
            end_time = time.time() + duration
            while time.time() < end_time:
                try:
                    start_time = time.time()
                    result = request_func()
                    response_time = time.time() - start_time
                    
                    results.append({
                        "response_time": response_time,
                        "timestamp": start_time,
                        "success": True
                    })
                    
                except Exception as e:
                    errors.append({
                        "error": str(e),
                        "timestamp": time.time()
                    })
                
                time.sleep(0.1)  # Small delay between requests
        
        # Start monitoring
        start_monitoring_time = time.time()
        
        # Launch concurrent workers
        threads = []
        for _ in range(num_concurrent):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        end_monitoring_time = time.time()
        
        # Analyze results
        total_requests = len(results) + len(errors)
        successful_requests = len(results)
        error_rate = len(errors) / total_requests if total_requests > 0 else 0
        
        response_times = [r["response_time"] for r in results]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max_response_time
        else:
            avg_response_time = max_response_time = min_response_time = p95_response_time = 0
        
        throughput = successful_requests / (end_monitoring_time - start_monitoring_time)
        
        return {
            "concurrent_connections": num_concurrent,
            "duration": end_monitoring_time - start_monitoring_time,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "error_rate": error_rate,
            "throughput": throughput,
            "response_time_stats": {
                "average": avg_response_time,
                "min": min_response_time,
                "max": max_response_time,
                "p95": p95_response_time
            },
            "errors": errors[:10]  # Keep first 10 errors for analysis
        }
    
    def measure_service_startup_performance(
        self,
        service_manager,
        config,
        expected_startup_time: float = 30.0
    ) -> Dict[str, Any]:
        """Measure service startup performance."""
        start_time = time.time()
        start_cpu = psutil.cpu_percent()
        start_memory = psutil.virtual_memory().percent
        
        try:
            service_url = service_manager.start_service(config, timeout=expected_startup_time)
            startup_success = True
            error_message = None
        except Exception as e:
            service_url = None
            startup_success = False
            error_message = str(e)
        
        end_time = time.time()
        end_cpu = psutil.cpu_percent()
        end_memory = psutil.virtual_memory().percent
        
        startup_time = end_time - start_time
        
        # Test readiness after startup
        readiness_time = None
        if startup_success and service_url:
            readiness_start = time.time()
            try:
                response = requests.get(f"{service_url}/health", timeout=5)
                readiness_success = response.status_code == 200
                readiness_time = time.time() - readiness_start
            except Exception:
                readiness_success = False
                readiness_time = None
        else:
            readiness_success = False
        
        return {
            "startup_time": startup_time,
            "startup_success": startup_success,
            "readiness_time": readiness_time,
            "readiness_success": readiness_success,
            "meets_startup_sla": startup_time <= expected_startup_time,
            "cpu_usage_during_startup": end_cpu - start_cpu,
            "memory_usage_during_startup": end_memory - start_memory,
            "error_message": error_message
        }
    
    def analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends from collected metrics."""
        if len(self.metrics_history) < 2:
            return {"error": "Insufficient data for trend analysis"}
        
        # Extract time series data
        timestamps = [m.timestamp for m in self.metrics_history]
        cpu_usage = [m.cpu_usage for m in self.metrics_history]
        memory_usage = [m.memory_usage for m in self.metrics_history]
        
        # Calculate trends
        def calculate_trend(values):
            if len(values) < 2:
                return 0
            return (values[-1] - values[0]) / len(values)
        
        cpu_trend = calculate_trend(cpu_usage)
        memory_trend = calculate_trend(memory_usage)
        
        # Calculate statistics
        analysis = {
            "data_points": len(self.metrics_history),
            "time_span": timestamps[-1] - timestamps[0] if len(timestamps) >= 2 else 0,
            "cpu_analysis": {
                "average": statistics.mean(cpu_usage),
                "max": max(cpu_usage),
                "min": min(cpu_usage),
                "trend": cpu_trend,
                "stable": abs(cpu_trend) < 1.0  # Less than 1% change per measurement
            },
            "memory_analysis": {
                "average": statistics.mean(memory_usage),
                "max": max(memory_usage),
                "min": min(memory_usage),
                "trend": memory_trend,
                "stable": abs(memory_trend) < 0.5  # Less than 0.5% change per measurement
            },
            "stability_assessment": {
                "cpu_stable": abs(cpu_trend) < 1.0,
                "memory_stable": abs(memory_trend) < 0.5,
                "overall_stable": abs(cpu_trend) < 1.0 and abs(memory_trend) < 0.5
            }
        }
        
        return analysis
    
    def set_baseline(self):
        """Set current performance as baseline for comparison."""
        if self.metrics_history:
            latest_metrics = self.metrics_history[-1]
            self.baseline_metrics = latest_metrics
    
    def compare_to_baseline(self) -> Optional[Dict[str, Any]]:
        """Compare current performance to baseline."""
        if not self.baseline_metrics or not self.metrics_history:
            return None
        
        current_metrics = self.metrics_history[-1]
        
        return {
            "cpu_change": current_metrics.cpu_usage - self.baseline_metrics.cpu_usage,
            "memory_change": current_metrics.memory_usage - self.baseline_metrics.memory_usage,
            "response_time_change": current_metrics.response_time - self.baseline_metrics.response_time,
            "throughput_change": current_metrics.throughput - self.baseline_metrics.throughput,
            "performance_degraded": (
                current_metrics.cpu_usage > self.baseline_metrics.cpu_usage + 10 or
                current_metrics.memory_usage > self.baseline_metrics.memory_usage + 10 or
                current_metrics.response_time > self.baseline_metrics.response_time * 1.5
            )
        }
    
    @contextmanager
    def performance_context(self, test_name: str):
        """Context manager for measuring performance of a test block."""
        start_time = time.time()
        start_metrics_count = len(self.metrics_history)
        
        # Start monitoring if not already active
        was_monitoring = self._monitoring
        if not was_monitoring:
            self.start_monitoring()
        
        try:
            yield self
        finally:
            end_time = time.time()
            
            # Stop monitoring if we started it
            if not was_monitoring:
                self.stop_monitoring()
            
            # Analyze performance during this context
            test_duration = end_time - start_time
            test_metrics = self.metrics_history[start_metrics_count:]
            
            if test_metrics:
                avg_cpu = statistics.mean([m.cpu_usage for m in test_metrics])
                avg_memory = statistics.mean([m.memory_usage for m in test_metrics])
                
                print(f"Performance summary for {test_name}:")
                print(f"  Duration: {test_duration:.2f}s")
                print(f"  Average CPU: {avg_cpu:.1f}%")
                print(f"  Average Memory: {avg_memory:.1f}%")
                print(f"  Metrics collected: {len(test_metrics)}")
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate a comprehensive performance report."""
        if not self.metrics_history:
            return {"error": "No performance data available"}
        
        trends = self.analyze_performance_trends()
        baseline_comparison = self.compare_to_baseline()
        
        return {
            "summary": {
                "total_measurements": len(self.metrics_history),
                "monitoring_duration": trends.get("time_span", 0),
                "has_baseline": self.baseline_metrics is not None
            },
            "trends": trends,
            "baseline_comparison": baseline_comparison,
            "recommendations": self._generate_performance_recommendations(trends),
            "generated_at": time.time()
        }
    
    def _generate_performance_recommendations(self, trends: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations based on trends."""
        recommendations = []
        
        cpu_analysis = trends.get("cpu_analysis", {})
        memory_analysis = trends.get("memory_analysis", {})
        
        if cpu_analysis.get("average", 0) > 80:
            recommendations.append("High average CPU usage detected. Consider optimizing CPU-intensive operations.")
        
        if memory_analysis.get("average", 0) > 80:
            recommendations.append("High average memory usage detected. Monitor for memory leaks.")
        
        if not cpu_analysis.get("stable", True):
            recommendations.append("CPU usage is unstable. Investigate irregular CPU spikes.")
        
        if not memory_analysis.get("stable", True):
            recommendations.append("Memory usage is unstable. Check for memory leaks or inefficient memory management.")
        
        if cpu_analysis.get("trend", 0) > 2:
            recommendations.append("CPU usage is trending upward. Monitor for performance degradation.")
        
        if memory_analysis.get("trend", 0) > 1:
            recommendations.append("Memory usage is trending upward. Potential memory leak detected.")
        
        if not recommendations:
            recommendations.append("Performance metrics look stable and healthy.")
        
        return recommendations