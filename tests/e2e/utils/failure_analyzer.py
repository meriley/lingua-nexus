"""Failure analysis utilities for E2E tests."""

import re
import time
from typing import Dict, List, Any, Optional, Pattern
from dataclasses import dataclass
from collections import defaultdict
import logging


@dataclass
class FailurePattern:
    """Represents a failure pattern with matching criteria."""
    name: str
    pattern: Pattern[str]
    category: str
    severity: str  # critical, high, medium, low
    description: str
    suggested_actions: List[str]


class FailureAnalyzer:
    """Analyzes test failures and provides insights."""
    
    def __init__(self):
        self.failure_patterns = self._initialize_failure_patterns()
        self.failure_history: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)
    
    def _initialize_failure_patterns(self) -> List[FailurePattern]:
        """Initialize known failure patterns."""
        return [
            FailurePattern(
                name="connection_timeout",
                pattern=re.compile(r"(connection.*timeout|timeout.*connection|read timeout)", re.IGNORECASE),
                category="network",
                severity="high",
                description="Connection or read timeout errors",
                suggested_actions=[
                    "Increase timeout values",
                    "Check network connectivity",
                    "Verify service responsiveness",
                    "Monitor network latency"
                ]
            ),
            FailurePattern(
                name="connection_refused",
                pattern=re.compile(r"connection refused|connection reset", re.IGNORECASE),
                category="network",
                severity="critical",
                description="Service connection failures",
                suggested_actions=[
                    "Verify service is running",
                    "Check port availability",
                    "Validate service configuration",
                    "Check firewall settings"
                ]
            ),
            FailurePattern(
                name="authentication_error",
                pattern=re.compile(r"401|403|unauthorized|forbidden|authentication.*failed|invalid.*key", re.IGNORECASE),
                category="authentication",
                severity="high",
                description="Authentication or authorization failures",
                suggested_actions=[
                    "Verify API key configuration",
                    "Check authentication headers",
                    "Validate credential expiration",
                    "Review access permissions"
                ]
            ),
            FailurePattern(
                name="server_error",
                pattern=re.compile(r"500|internal server error|server error", re.IGNORECASE),
                category="server",
                severity="critical",
                description="Internal server errors",
                suggested_actions=[
                    "Check server logs",
                    "Monitor server resources",
                    "Verify service configuration",
                    "Check for application bugs"
                ]
            ),
            FailurePattern(
                name="rate_limit_exceeded",
                pattern=re.compile(r"429|rate limit|too many requests", re.IGNORECASE),
                category="rate_limiting",
                severity="medium",
                description="Rate limiting errors",
                suggested_actions=[
                    "Reduce request frequency",
                    "Implement request throttling",
                    "Check rate limit configuration",
                    "Use exponential backoff"
                ]
            ),
            FailurePattern(
                name="service_unavailable",
                pattern=re.compile(r"503|service unavailable|temporarily unavailable", re.IGNORECASE),
                category="availability",
                severity="high",
                description="Service availability issues",
                suggested_actions=[
                    "Check service health",
                    "Monitor service load",
                    "Verify deployment status",
                    "Check dependencies"
                ]
            ),
            FailurePattern(
                name="validation_error",
                pattern=re.compile(r"400|bad request|validation.*failed|invalid.*format", re.IGNORECASE),
                category="validation",
                severity="medium",
                description="Request validation failures",
                suggested_actions=[
                    "Check request format",
                    "Validate required fields",
                    "Review API documentation",
                    "Fix request parameters"
                ]
            ),
            FailurePattern(
                name="resource_not_found",
                pattern=re.compile(r"404|not found|resource.*not.*found", re.IGNORECASE),
                category="resource",
                severity="medium",
                description="Resource not found errors",
                suggested_actions=[
                    "Verify endpoint URLs",
                    "Check resource existence",
                    "Review API routes",
                    "Validate request paths"
                ]
            ),
            FailurePattern(
                name="memory_error",
                pattern=re.compile(r"out of memory|memory.*error|oom", re.IGNORECASE),
                category="resource",
                severity="critical",
                description="Memory-related errors",
                suggested_actions=[
                    "Increase memory allocation",
                    "Check for memory leaks",
                    "Optimize memory usage",
                    "Monitor resource consumption"
                ]
            ),
            FailurePattern(
                name="docker_error",
                pattern=re.compile(r"docker.*error|container.*failed|image.*not.*found", re.IGNORECASE),
                category="infrastructure",
                severity="high",
                description="Docker or container-related errors",
                suggested_actions=[
                    "Check Docker daemon status",
                    "Verify image availability",
                    "Review container configuration",
                    "Check resource limits"
                ]
            ),
            FailurePattern(
                name="startup_failure",
                pattern=re.compile(r"failed to start|startup.*failed|initialization.*error", re.IGNORECASE),
                category="startup",
                severity="critical",
                description="Service startup failures",
                suggested_actions=[
                    "Check configuration files",
                    "Verify dependencies",
                    "Review startup logs",
                    "Check port availability"
                ]
            )
        ]
    
    def analyze_failure(
        self, 
        test_name: str,
        error_message: str,
        test_category: str = "unknown",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze a single test failure."""
        failure_data = {
            "test_name": test_name,
            "test_category": test_category,
            "error_message": error_message,
            "timestamp": time.time(),
            "additional_context": additional_context or {},
            "analysis": self._classify_failure(error_message),
            "severity": "unknown",
            "suggested_actions": []
        }
        
        # Classify the failure
        classification = self._classify_failure(error_message)
        failure_data.update(classification)
        
        # Store in history
        self.failure_history.append(failure_data)
        
        self.logger.info(
            f"Failure analyzed: {test_name} - "
            f"Category: {failure_data.get('failure_category', 'unknown')}, "
            f"Severity: {failure_data.get('severity', 'unknown')}"
        )
        
        return failure_data
    
    def _classify_failure(self, error_message: str) -> Dict[str, Any]:
        """Classify a failure based on error message."""
        matched_patterns = []
        
        for pattern in self.failure_patterns:
            if pattern.pattern.search(error_message):
                matched_patterns.append({
                    "name": pattern.name,
                    "category": pattern.category,
                    "severity": pattern.severity,
                    "description": pattern.description,
                    "suggested_actions": pattern.suggested_actions
                })
        
        if matched_patterns:
            # Use the most severe pattern
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            primary_pattern = min(matched_patterns, key=lambda p: severity_order.get(p["severity"], 4))
            
            return {
                "failure_category": primary_pattern["category"],
                "failure_type": primary_pattern["name"],
                "severity": primary_pattern["severity"],
                "description": primary_pattern["description"],
                "suggested_actions": primary_pattern["suggested_actions"],
                "matched_patterns": matched_patterns
            }
        else:
            return {
                "failure_category": "unknown",
                "failure_type": "unclassified",
                "severity": "unknown",
                "description": "Unclassified failure",
                "suggested_actions": [
                    "Review error message details",
                    "Check logs for more context",
                    "Investigate test environment",
                    "Consider adding failure pattern"
                ],
                "matched_patterns": []
            }
    
    def analyze_failure_trends(self) -> Dict[str, Any]:
        """Analyze trends in failure patterns."""
        if not self.failure_history:
            return {"message": "No failure data available for trend analysis"}
        
        # Group failures by category and type
        category_counts = defaultdict(int)
        type_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        
        # Time-based analysis
        recent_failures = []
        hour_ago = time.time() - 3600
        
        for failure in self.failure_history:
            category = failure.get("failure_category", "unknown")
            failure_type = failure.get("failure_type", "unknown")
            severity = failure.get("severity", "unknown")
            
            category_counts[category] += 1
            type_counts[failure_type] += 1
            severity_counts[severity] += 1
            
            if failure["timestamp"] > hour_ago:
                recent_failures.append(failure)
        
        # Find most common issues
        most_common_category = max(category_counts.items(), key=lambda x: x[1]) if category_counts else ("none", 0)
        most_common_type = max(type_counts.items(), key=lambda x: x[1]) if type_counts else ("none", 0)
        
        # Calculate failure rate by test category
        test_category_failures = defaultdict(int)
        for failure in self.failure_history:
            test_cat = failure.get("test_category", "unknown")
            test_category_failures[test_cat] += 1
        
        return {
            "total_failures": len(self.failure_history),
            "recent_failures_1h": len(recent_failures),
            "failure_categories": dict(category_counts),
            "failure_types": dict(type_counts),
            "severity_distribution": dict(severity_counts),
            "most_common_category": most_common_category,
            "most_common_type": most_common_type,
            "test_category_failures": dict(test_category_failures),
            "analysis_timestamp": time.time()
        }
    
    def get_failure_recommendations(self) -> Dict[str, Any]:
        """Get recommendations based on failure analysis."""
        if not self.failure_history:
            return {"message": "No failures to analyze"}
        
        trends = self.analyze_failure_trends()
        recommendations = []
        
        # Category-based recommendations
        category_counts = trends["failure_categories"]
        
        if category_counts.get("network", 0) > 2:
            recommendations.append({
                "priority": "high",
                "category": "network",
                "issue": "Multiple network-related failures detected",
                "actions": [
                    "Check network connectivity and stability",
                    "Increase timeout values for network operations",
                    "Implement retry mechanisms with exponential backoff",
                    "Monitor network latency and packet loss"
                ]
            })
        
        if category_counts.get("authentication", 0) > 1:
            recommendations.append({
                "priority": "high",
                "category": "authentication",
                "issue": "Authentication failures detected",
                "actions": [
                    "Verify API key configuration across all tests",
                    "Check for expired credentials",
                    "Validate authentication header format",
                    "Review access control policies"
                ]
            })
        
        if category_counts.get("server", 0) > 0:
            recommendations.append({
                "priority": "critical",
                "category": "server",
                "issue": "Server errors indicating application issues",
                "actions": [
                    "Investigate server logs immediately",
                    "Check application health and dependencies",
                    "Monitor server resources (CPU, memory, disk)",
                    "Verify deployment integrity"
                ]
            })
        
        # Severity-based recommendations
        severity_counts = trends["severity_distribution"]
        
        if severity_counts.get("critical", 0) > 0:
            recommendations.append({
                "priority": "critical",
                "category": "severity",
                "issue": f"Critical failures detected: {severity_counts['critical']}",
                "actions": [
                    "Address critical failures immediately",
                    "Review test environment setup",
                    "Check service health and configuration",
                    "Consider temporarily disabling affected tests"
                ]
            })
        
        # Frequency-based recommendations
        if trends["total_failures"] > 5:
            recommendations.append({
                "priority": "medium",
                "category": "stability",
                "issue": "High number of test failures indicating stability issues",
                "actions": [
                    "Review test environment stability",
                    "Implement more robust error handling",
                    "Add retry mechanisms for flaky tests",
                    "Consider test isolation improvements"
                ]
            })
        
        # Recent failure spike detection
        if trends["recent_failures_1h"] > trends["total_failures"] * 0.5:
            recommendations.append({
                "priority": "high",
                "category": "recent",
                "issue": "High failure rate in recent tests",
                "actions": [
                    "Investigate recent changes to test environment",
                    "Check for service degradation",
                    "Review recent code deployments",
                    "Monitor system resources"
                ]
            })
        
        return {
            "recommendations": recommendations,
            "failure_summary": trends,
            "generated_at": time.time()
        }
    
    def generate_failure_report(self) -> Dict[str, Any]:
        """Generate a comprehensive failure analysis report."""
        trends = self.analyze_failure_trends()
        recommendations = self.get_failure_recommendations()
        
        # Group failures by pattern for detailed analysis
        pattern_analysis = {}
        for failure in self.failure_history:
            failure_type = failure.get("failure_type", "unknown")
            if failure_type not in pattern_analysis:
                pattern_analysis[failure_type] = {
                    "count": 0,
                    "examples": [],
                    "suggested_actions": failure.get("suggested_actions", [])
                }
            
            pattern_analysis[failure_type]["count"] += 1
            if len(pattern_analysis[failure_type]["examples"]) < 3:
                pattern_analysis[failure_type]["examples"].append({
                    "test_name": failure["test_name"],
                    "error_message": failure["error_message"][:200] + "..." if len(failure["error_message"]) > 200 else failure["error_message"],
                    "timestamp": failure["timestamp"]
                })
        
        return {
            "summary": {
                "total_failures_analyzed": len(self.failure_history),
                "unique_failure_types": len(pattern_analysis),
                "most_common_category": trends.get("most_common_category", ("none", 0))[0],
                "most_common_type": trends.get("most_common_type", ("none", 0))[0]
            },
            "trends": trends,
            "pattern_analysis": pattern_analysis,
            "recommendations": recommendations,
            "failure_timeline": [
                {
                    "test_name": f["test_name"],
                    "category": f.get("failure_category", "unknown"),
                    "type": f.get("failure_type", "unknown"),
                    "severity": f.get("severity", "unknown"),
                    "timestamp": f["timestamp"]
                }
                for f in sorted(self.failure_history, key=lambda x: x["timestamp"])
            ],
            "generated_at": time.time()
        }
    
    def add_custom_pattern(
        self,
        name: str,
        pattern: str,
        category: str,
        severity: str,
        description: str,
        suggested_actions: List[str]
    ):
        """Add a custom failure pattern for analysis."""
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            custom_pattern = FailurePattern(
                name=name,
                pattern=compiled_pattern,
                category=category,
                severity=severity,
                description=description,
                suggested_actions=suggested_actions
            )
            self.failure_patterns.append(custom_pattern)
            self.logger.info(f"Added custom failure pattern: {name}")
        except re.error as e:
            self.logger.error(f"Invalid regex pattern for {name}: {e}")
            raise ValueError(f"Invalid regex pattern: {e}")