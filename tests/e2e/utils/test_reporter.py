"""Test result reporting utilities for E2E tests."""

import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging
from contextlib import contextmanager


class E2ETestReporter:
    """Reports and analyzes E2E test results."""
    
    def __init__(self, output_dir: str = "/tmp/e2e_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        self.test_results: List[Dict[str, Any]] = []
        self.start_time = time.time()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_test_case = None
        self.test_case_start_time = None
    
    def record_test_result(
        self,
        test_name: str,
        test_category: str,
        status: str,
        duration: float,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a test result."""
        result = {
            "test_name": test_name,
            "test_category": test_category,
            "status": status,  # passed, failed, skipped, error
            "duration": duration,
            "timestamp": time.time(),
            "error_message": error_message,
            "metadata": metadata or {}
        }
        
        self.test_results.append(result)
        self.logger.info(f"Test recorded: {test_name} - {status} ({duration:.2f}s)")
    
    @contextmanager
    def test_case(self, test_name: str):
        """Context manager for tracking test case execution."""
        self.current_test_case = test_name
        self.test_case_start_time = time.time()
        
        try:
            yield self
        except Exception as e:
            # Record failure
            duration = time.time() - self.test_case_start_time
            self.record_test_result(
                test_name=test_name,
                test_category="e2e",
                status="failed",
                duration=duration,
                error_message=str(e)
            )
            raise
        else:
            # Record success
            duration = time.time() - self.test_case_start_time
            self.record_test_result(
                test_name=test_name,
                test_category="e2e",
                status="passed",
                duration=duration
            )
        finally:
            self.current_test_case = None
            self.test_case_start_time = None
    
    def record_performance_metrics(
        self,
        test_name: str,
        metrics: Dict[str, float]
    ):
        """Record performance metrics for a test."""
        # Find the test result and add performance metrics
        for result in reversed(self.test_results):
            if result["test_name"] == test_name:
                if "performance" not in result["metadata"]:
                    result["metadata"]["performance"] = {}
                result["metadata"]["performance"].update(metrics)
                break
    
    def record_error_details(
        self,
        test_name: str,
        error_type: str,
        error_details: Dict[str, Any]
    ):
        """Record detailed error information."""
        for result in reversed(self.test_results):
            if result["test_name"] == test_name:
                if "errors" not in result["metadata"]:
                    result["metadata"]["errors"] = []
                result["metadata"]["errors"].append({
                    "type": error_type,
                    "details": error_details,
                    "timestamp": time.time()
                })
                break
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate a summary report of all test results."""
        total_tests = len(self.test_results)
        
        if total_tests == 0:
            return {"error": "No test results recorded"}
        
        # Count results by status
        status_counts = {}
        for result in self.test_results:
            status = result["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count results by category
        category_counts = {}
        for result in self.test_results:
            category = result["test_category"]
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Calculate timing statistics
        durations = [r["duration"] for r in self.test_results]
        total_duration = sum(durations)
        avg_duration = total_duration / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        
        # Calculate success rate
        passed_tests = status_counts.get("passed", 0)
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Find slowest and fastest tests
        sorted_by_duration = sorted(self.test_results, key=lambda x: x["duration"])
        slowest_test = sorted_by_duration[-1] if sorted_by_duration else None
        fastest_test = sorted_by_duration[0] if sorted_by_duration else None
        
        # Session timing
        session_duration = time.time() - self.start_time
        
        return {
            "session_id": self.session_id,
            "session_duration": session_duration,
            "total_tests": total_tests,
            "status_counts": status_counts,
            "category_counts": category_counts,
            "success_rate": success_rate,
            "timing": {
                "total_duration": total_duration,
                "average_duration": avg_duration,
                "max_duration": max_duration,
                "min_duration": min_duration,
                "slowest_test": {
                    "name": slowest_test["test_name"],
                    "duration": slowest_test["duration"]
                } if slowest_test else None,
                "fastest_test": {
                    "name": fastest_test["test_name"],
                    "duration": fastest_test["duration"]
                } if fastest_test else None
            },
            "generated_at": datetime.now().isoformat()
        }
    
    def generate_detailed_report(self) -> Dict[str, Any]:
        """Generate a detailed report including all test results."""
        summary = self.generate_summary_report()
        
        return {
            "summary": summary,
            "test_results": self.test_results,
            "performance_analysis": self._analyze_performance(),
            "error_analysis": self._analyze_errors(),
            "recommendations": self._generate_recommendations()
        }
    
    def _analyze_performance(self) -> Dict[str, Any]:
        """Analyze performance metrics across tests."""
        performance_data = []
        
        for result in self.test_results:
            if "performance" in result.get("metadata", {}):
                perf_metrics = result["metadata"]["performance"]
                perf_data = {
                    "test_name": result["test_name"],
                    "test_category": result["test_category"],
                    "duration": result["duration"],
                    **perf_metrics
                }
                performance_data.append(perf_data)
        
        if not performance_data:
            return {"message": "No performance data available"}
        
        # Analyze response times if available
        response_times = [p.get("response_time", 0) for p in performance_data]
        throughput_values = [p.get("throughput", 0) for p in performance_data]
        
        analysis = {
            "total_performance_tests": len(performance_data),
            "response_time_analysis": {
                "average": sum(response_times) / len(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0,
                "min": min(response_times) if response_times else 0
            } if response_times else None,
            "throughput_analysis": {
                "average": sum(throughput_values) / len(throughput_values) if throughput_values else 0,
                "max": max(throughput_values) if throughput_values else 0,
                "min": min(throughput_values) if throughput_values else 0
            } if throughput_values else None,
            "performance_data": performance_data
        }
        
        return analysis
    
    def _analyze_errors(self) -> Dict[str, Any]:
        """Analyze error patterns across tests."""
        failed_tests = [r for r in self.test_results if r["status"] in ["failed", "error"]]
        
        if not failed_tests:
            return {"message": "No failures to analyze"}
        
        # Group errors by type
        error_types = {}
        error_messages = {}
        
        for test in failed_tests:
            error_msg = test.get("error_message", "Unknown error")
            
            # Categorize error type
            if "timeout" in error_msg.lower():
                error_type = "timeout"
            elif "connection" in error_msg.lower():
                error_type = "connection"
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                error_type = "authentication"
            elif "404" in error_msg or "not found" in error_msg.lower():
                error_type = "not_found"
            elif "500" in error_msg or "server error" in error_msg.lower():
                error_type = "server_error"
            else:
                error_type = "other"
            
            error_types[error_type] = error_types.get(error_type, 0) + 1
            
            if error_type not in error_messages:
                error_messages[error_type] = []
            error_messages[error_type].append({
                "test_name": test["test_name"],
                "message": error_msg
            })
        
        return {
            "total_failures": len(failed_tests),
            "error_types": error_types,
            "error_examples": error_messages,
            "failure_rate_by_category": self._calculate_failure_rates_by_category()
        }
    
    def _calculate_failure_rates_by_category(self) -> Dict[str, float]:
        """Calculate failure rates by test category."""
        category_totals = {}
        category_failures = {}
        
        for result in self.test_results:
            category = result["test_category"]
            category_totals[category] = category_totals.get(category, 0) + 1
            
            if result["status"] in ["failed", "error"]:
                category_failures[category] = category_failures.get(category, 0) + 1
        
        failure_rates = {}
        for category, total in category_totals.items():
            failures = category_failures.get(category, 0)
            failure_rates[category] = (failures / total) * 100 if total > 0 else 0
        
        return failure_rates
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        summary = self.generate_summary_report()
        
        # Success rate recommendations
        if summary["success_rate"] < 90:
            recommendations.append(
                f"Success rate is {summary['success_rate']:.1f}%. "
                "Consider investigating failing tests and improving test stability."
            )
        
        # Performance recommendations
        if summary["timing"]["max_duration"] > 60:
            recommendations.append(
                f"Slowest test takes {summary['timing']['max_duration']:.1f}s. "
                "Consider optimizing long-running tests or increasing timeouts."
            )
        
        # Category-specific recommendations
        failure_rates = self._calculate_failure_rates_by_category()
        for category, rate in failure_rates.items():
            if rate > 20:
                recommendations.append(
                    f"Category '{category}' has {rate:.1f}% failure rate. "
                    "Focus on improving reliability in this area."
                )
        
        # Error pattern recommendations
        error_analysis = self._analyze_errors()
        if "error_types" in error_analysis:
            error_types = error_analysis["error_types"]
            
            if error_types.get("timeout", 0) > 2:
                recommendations.append(
                    "Multiple timeout errors detected. "
                    "Consider increasing timeouts or improving service performance."
                )
            
            if error_types.get("connection", 0) > 2:
                recommendations.append(
                    "Multiple connection errors detected. "
                    "Check network configuration and service stability."
                )
        
        if not recommendations:
            recommendations.append("Test results look good! No major issues detected.")
        
        return recommendations
    
    def save_report(self, report_type: str = "detailed") -> str:
        """Save report to file and return file path."""
        if report_type == "summary":
            report_data = self.generate_summary_report()
        else:
            report_data = self.generate_detailed_report()
        
        filename = f"e2e_report_{self.session_id}_{report_type}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        self.logger.info(f"Report saved to: {filepath}")
        return str(filepath)
    
    def print_summary(self):
        """Print a summary report to console."""
        summary = self.generate_summary_report()
        
        print(f"\n{'='*60}")
        print(f"E2E TEST SUMMARY - Session {summary['session_id']}")
        print(f"{'='*60}")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Session Duration: {summary['session_duration']:.1f}s")
        print()
        
        print("Status Breakdown:")
        for status, count in summary['status_counts'].items():
            print(f"  {status.capitalize()}: {count}")
        print()
        
        print("Category Breakdown:")
        for category, count in summary['category_counts'].items():
            print(f"  {category}: {count}")
        print()
        
        timing = summary['timing']
        print(f"Timing Statistics:")
        print(f"  Average Test Duration: {timing['average_duration']:.2f}s")
        print(f"  Fastest Test: {timing['fastest_test']['name']} ({timing['fastest_test']['duration']:.2f}s)")
        print(f"  Slowest Test: {timing['slowest_test']['name']} ({timing['slowest_test']['duration']:.2f}s)")
        print()
        
        # Print recommendations
        recommendations = self._generate_recommendations()
        print("Recommendations:")
        for i, recommendation in enumerate(recommendations, 1):
            print(f"  {i}. {recommendation}")
        
        print(f"{'='*60}")


# Global reporter instance for easy access
_global_reporter: Optional[E2ETestReporter] = None


def get_global_reporter() -> E2ETestReporter:
    """Get or create the global test reporter instance."""
    global _global_reporter
    if _global_reporter is None:
        _global_reporter = E2ETestReporter()
    return _global_reporter


def record_test_result(test_name: str, test_category: str, status: str, duration: float, 
                      error_message: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
    """Convenience function to record test results."""
    reporter = get_global_reporter()
    reporter.record_test_result(test_name, test_category, status, duration, error_message, metadata)