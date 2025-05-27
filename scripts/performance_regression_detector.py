#!/usr/bin/env python3
"""
Performance Regression Detection Script
Analyzes performance reports and detects regressions compared to baselines.
"""

import json
import argparse
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import sys


@dataclass
class PerformanceMetric:
    """Performance metric with threshold configuration."""
    name: str
    current_value: float
    baseline_value: Optional[float]
    threshold_percent: float  # Percentage increase that triggers regression alert
    unit: str
    
    @property
    def regression_threshold(self) -> Optional[float]:
        """Calculate absolute regression threshold."""
        if self.baseline_value is None:
            return None
        return self.baseline_value * (1 + self.threshold_percent / 100)
    
    @property
    def is_regression(self) -> bool:
        """Check if current value represents a regression."""
        if self.baseline_value is None or self.regression_threshold is None:
            return False
        return self.current_value > self.regression_threshold
    
    @property
    def change_percent(self) -> Optional[float]:
        """Calculate percentage change from baseline."""
        if self.baseline_value is None or self.baseline_value == 0:
            return None
        return ((self.current_value - self.baseline_value) / self.baseline_value) * 100


@dataclass
class RegressionReport:
    """Report of performance regression analysis."""
    timestamp: str
    total_metrics: int
    regressions: List[PerformanceMetric]
    warnings: List[PerformanceMetric]
    improvements: List[PerformanceMetric]
    
    @property
    def has_regressions(self) -> bool:
        """Check if any regressions were detected."""
        return len(self.regressions) > 0
    
    @property
    def severity(self) -> str:
        """Get severity level of the report."""
        if len(self.regressions) >= 3:
            return "HIGH"
        elif len(self.regressions) > 0:
            return "MEDIUM"
        elif len(self.warnings) > 0:
            return "LOW"
        else:
            return "NONE"


class PerformanceRegressionDetector:
    """Detects performance regressions by comparing current metrics to baselines."""
    
    def __init__(self, baseline_dir: str = "performance_baselines", 
                 regression_thresholds: Optional[Dict[str, float]] = None):
        """
        Initialize regression detector.
        
        Args:
            baseline_dir: Directory containing baseline performance data
            regression_thresholds: Custom thresholds for different metrics (percentage increase)
        """
        self.baseline_dir = Path(baseline_dir)
        self.regression_thresholds = regression_thresholds or {
            "model_loading_time": 25.0,  # 25% slower loading time
            "inference_latency": 20.0,   # 20% slower inference
            "memory_usage": 30.0,        # 30% more memory usage
            "throughput": -15.0,         # 15% lower throughput (negative because lower is worse)
            "batch_processing_time": 25.0,  # 25% slower batch processing
            "success_rate": -5.0,        # 5% lower success rate
        }
        
    def load_baseline_metrics(self, metric_type: str, model_name: str) -> Optional[Dict]:
        """Load baseline metrics for a specific type and model."""
        baseline_file = self.baseline_dir / f"{metric_type}_{model_name}_baseline.json"
        
        if not baseline_file.exists():
            return None
            
        try:
            with open(baseline_file) as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load baseline {baseline_file}: {e}")
            return None
    
    def extract_model_loading_metrics(self, report_data: Dict) -> List[PerformanceMetric]:
        """Extract model loading performance metrics."""
        metrics = []
        
        if "analysis" not in report_data:
            return metrics
            
        for model_key, analysis in report_data["analysis"].items():
            if "loading_time_stats" not in analysis:
                continue
                
            model_name = model_key.split("_")[0]  # Extract model name from key
            stats = analysis["loading_time_stats"]
            
            # Load baseline
            baseline = self.load_baseline_metrics("model_loading", model_name)
            baseline_time = None
            if baseline and "analysis" in baseline:
                for baseline_key, baseline_analysis in baseline["analysis"].items():
                    if model_name in baseline_key and "loading_time_stats" in baseline_analysis:
                        baseline_time = baseline_analysis["loading_time_stats"]["mean_duration_seconds"]
                        break
            
            metric = PerformanceMetric(
                name=f"{model_name}_loading_time",
                current_value=stats["mean_duration_seconds"],
                baseline_value=baseline_time,
                threshold_percent=self.regression_thresholds["model_loading_time"],
                unit="seconds"
            )
            metrics.append(metric)
            
        return metrics
    
    def extract_inference_metrics(self, report_data: Dict) -> List[PerformanceMetric]:
        """Extract inference performance metrics."""
        metrics = []
        
        if "analysis" not in report_data:
            return metrics
            
        for model_key, analysis in report_data["analysis"].items():
            if "latency_stats" not in analysis:
                continue
                
            model_name = model_key.split("_")[0]
            latency_stats = analysis["latency_stats"]
            throughput_stats = analysis.get("throughput_stats", {})
            
            # Load baseline
            baseline = self.load_baseline_metrics("inference", model_name)
            baseline_latency = None
            baseline_throughput = None
            
            if baseline and "analysis" in baseline:
                for baseline_key, baseline_analysis in baseline["analysis"].items():
                    if model_name in baseline_key:
                        if "latency_stats" in baseline_analysis:
                            baseline_latency = baseline_analysis["latency_stats"]["mean_seconds"]
                        if "throughput_stats" in baseline_analysis:
                            baseline_throughput = baseline_analysis["throughput_stats"]["mean_chars_per_sec"]
                        break
            
            # Latency metric
            if "mean_seconds" in latency_stats:
                metric = PerformanceMetric(
                    name=f"{model_name}_inference_latency",
                    current_value=latency_stats["mean_seconds"],
                    baseline_value=baseline_latency,
                    threshold_percent=self.regression_thresholds["inference_latency"],
                    unit="seconds"
                )
                metrics.append(metric)
            
            # Throughput metric
            if "mean_chars_per_sec" in throughput_stats:
                metric = PerformanceMetric(
                    name=f"{model_name}_throughput",
                    current_value=throughput_stats["mean_chars_per_sec"],
                    baseline_value=baseline_throughput,
                    threshold_percent=self.regression_thresholds["throughput"],
                    unit="chars/sec"
                )
                metrics.append(metric)
                
        return metrics
    
    def extract_memory_metrics(self, report_data: Dict) -> List[PerformanceMetric]:
        """Extract memory usage metrics."""
        metrics = []
        
        if "memory_statistics" not in report_data:
            return metrics
            
        stats = report_data["memory_statistics"]
        
        # Load baseline
        baseline = self.load_baseline_metrics("memory", "process")
        baseline_rss = None
        baseline_growth = None
        
        if baseline and "memory_statistics" in baseline:
            baseline_stats = baseline["memory_statistics"]
            if "process_memory" in baseline_stats:
                baseline_rss = baseline_stats["process_memory"]["rss_mb"]["max"]
                baseline_growth = baseline_stats["process_memory"]["rss_mb"]["growth"]
        
        # Process RSS metric
        if "process_memory" in stats and "rss_mb" in stats["process_memory"]:
            rss_stats = stats["process_memory"]["rss_mb"]
            
            metric = PerformanceMetric(
                name="memory_peak_rss",
                current_value=rss_stats["max"],
                baseline_value=baseline_rss,
                threshold_percent=self.regression_thresholds["memory_usage"],
                unit="MB"
            )
            metrics.append(metric)
            
            # Memory growth metric
            metric = PerformanceMetric(
                name="memory_growth",
                current_value=rss_stats["growth"],
                baseline_value=baseline_growth,
                threshold_percent=self.regression_thresholds["memory_usage"],
                unit="MB"
            )
            metrics.append(metric)
            
        return metrics
    
    def extract_batch_metrics(self, report_data: Dict) -> List[PerformanceMetric]:
        """Extract batch processing metrics."""
        metrics = []
        
        if "analysis" not in report_data:
            return metrics
            
        for model_key, analysis in report_data["analysis"].items():
            if "duration_stats" not in analysis:
                continue
                
            model_name = model_key.split("_")[0]
            duration_stats = analysis["duration_stats"]
            success_rate = analysis.get("test_info", {}).get("overall_success_rate", 0)
            
            # Load baseline
            baseline = self.load_baseline_metrics("batch", model_name)
            baseline_duration = None
            baseline_success_rate = None
            
            if baseline and "analysis" in baseline:
                for baseline_key, baseline_analysis in baseline["analysis"].items():
                    if model_name in baseline_key:
                        if "duration_stats" in baseline_analysis:
                            baseline_duration = baseline_analysis["duration_stats"]["mean_duration"]
                        if "test_info" in baseline_analysis:
                            baseline_success_rate = baseline_analysis["test_info"]["overall_success_rate"]
                        break
            
            # Duration metric
            if "mean_duration" in duration_stats:
                metric = PerformanceMetric(
                    name=f"{model_name}_batch_duration",
                    current_value=duration_stats["mean_duration"],
                    baseline_value=baseline_duration,
                    threshold_percent=self.regression_thresholds["batch_processing_time"],
                    unit="seconds"
                )
                metrics.append(metric)
            
            # Success rate metric
            metric = PerformanceMetric(
                name=f"{model_name}_batch_success_rate",
                current_value=success_rate * 100,  # Convert to percentage
                baseline_value=baseline_success_rate * 100 if baseline_success_rate else None,
                threshold_percent=self.regression_thresholds["success_rate"],
                unit="%"
            )
            metrics.append(metric)
            
        return metrics
    
    def analyze_report(self, report_file: str) -> List[PerformanceMetric]:
        """Analyze a performance report file and extract metrics."""
        report_path = Path(report_file)
        
        if not report_path.exists():
            raise FileNotFoundError(f"Report file not found: {report_file}")
            
        try:
            with open(report_path) as f:
                report_data = json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse report file: {e}")
        
        metrics = []
        
        # Determine report type and extract appropriate metrics
        filename = report_path.name.lower()
        
        if "baseline" in filename or "loading" in filename:
            metrics.extend(self.extract_model_loading_metrics(report_data))
        elif "inference" in filename:
            metrics.extend(self.extract_inference_metrics(report_data))
        elif "memory" in filename:
            metrics.extend(self.extract_memory_metrics(report_data))
        elif "batch" in filename:
            metrics.extend(self.extract_batch_metrics(report_data))
        else:
            # Try to extract from all types
            metrics.extend(self.extract_model_loading_metrics(report_data))
            metrics.extend(self.extract_inference_metrics(report_data))
            metrics.extend(self.extract_memory_metrics(report_data))
            metrics.extend(self.extract_batch_metrics(report_data))
        
        return metrics
    
    def detect_regressions(self, metrics: List[PerformanceMetric]) -> RegressionReport:
        """Detect performance regressions from a list of metrics."""
        regressions = []
        warnings = []
        improvements = []
        
        for metric in metrics:
            if metric.baseline_value is None:
                continue  # Skip metrics without baselines
                
            if metric.is_regression:
                regressions.append(metric)
            elif metric.change_percent is not None:
                if abs(metric.change_percent) > abs(metric.threshold_percent) / 2:
                    warnings.append(metric)  # Warning at 50% of threshold
                elif metric.change_percent < -5:  # Improvement of more than 5%
                    improvements.append(metric)
        
        return RegressionReport(
            timestamp=datetime.now().isoformat(),
            total_metrics=len(metrics),
            regressions=regressions,
            warnings=warnings,
            improvements=improvements
        )
    
    def generate_report_text(self, report: RegressionReport) -> str:
        """Generate human-readable regression report."""
        lines = []
        lines.append("=== Performance Regression Analysis ===")
        lines.append(f"Timestamp: {report.timestamp}")
        lines.append(f"Total Metrics Analyzed: {report.total_metrics}")
        lines.append(f"Severity: {report.severity}")
        lines.append("")
        
        if report.regressions:
            lines.append("🚨 PERFORMANCE REGRESSIONS DETECTED:")
            for metric in report.regressions:
                change = f"{metric.change_percent:+.1f}%" if metric.change_percent else "N/A"
                lines.append(f"  - {metric.name}: {metric.current_value:.2f} {metric.unit} "
                           f"(baseline: {metric.baseline_value:.2f} {metric.unit}, change: {change})")
            lines.append("")
        
        if report.warnings:
            lines.append("⚠️  PERFORMANCE WARNINGS:")
            for metric in report.warnings:
                change = f"{metric.change_percent:+.1f}%" if metric.change_percent else "N/A"
                lines.append(f"  - {metric.name}: {metric.current_value:.2f} {metric.unit} "
                           f"(baseline: {metric.baseline_value:.2f} {metric.unit}, change: {change})")
            lines.append("")
        
        if report.improvements:
            lines.append("✅ PERFORMANCE IMPROVEMENTS:")
            for metric in report.improvements:
                change = f"{metric.change_percent:+.1f}%" if metric.change_percent else "N/A"
                lines.append(f"  - {metric.name}: {metric.current_value:.2f} {metric.unit} "
                           f"(baseline: {metric.baseline_value:.2f} {metric.unit}, change: {change})")
            lines.append("")
        
        if not report.regressions and not report.warnings:
            lines.append("✅ No performance regressions detected!")
            lines.append("")
        
        return "\n".join(lines)


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description="Detect performance regressions in E2E test reports")
    parser.add_argument("reports", nargs="+", help="Performance report files to analyze")
    parser.add_argument("--baseline-dir", default="performance_baselines", 
                       help="Directory containing baseline performance data")
    parser.add_argument("--output", help="Output file for regression report")
    parser.add_argument("--fail-on-regression", action="store_true",
                       help="Exit with error code if regressions are detected")
    parser.add_argument("--threshold-config", help="JSON file with custom regression thresholds")
    
    args = parser.parse_args()
    
    # Load custom thresholds if provided
    thresholds = None
    if args.threshold_config:
        try:
            with open(args.threshold_config) as f:
                thresholds = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load threshold config: {e}")
    
    # Initialize detector
    detector = PerformanceRegressionDetector(
        baseline_dir=args.baseline_dir,
        regression_thresholds=thresholds
    )
    
    # Analyze all reports
    all_metrics = []
    for report_file in args.reports:
        try:
            metrics = detector.analyze_report(report_file)
            all_metrics.extend(metrics)
            print(f"Analyzed {len(metrics)} metrics from {report_file}")
        except Exception as e:
            print(f"Error analyzing {report_file}: {e}")
    
    # Detect regressions
    report = detector.detect_regressions(all_metrics)
    
    # Generate report
    report_text = detector.generate_report_text(report)
    print(report_text)
    
    # Save report if requested
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report_text)
        print(f"Report saved to {args.output}")
    
    # Exit with error if regressions detected and flag is set
    if args.fail_on_regression and report.has_regressions:
        sys.exit(1)


if __name__ == "__main__":
    main()