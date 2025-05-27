"""
Edge Case Discovery System
Automated edge case discovery and testing for comprehensive coverage
"""

import pytest
import random
import string
import json
import time
import itertools
from typing import Dict, List, Any, Optional, Tuple, Set, Generator
from dataclasses import dataclass
from enum import Enum
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from app.main import app


class EdgeCaseCategory(Enum):
    """Categories of edge cases to discover"""
    BOUNDARY_VALUES = "boundary_values"
    UNICODE_VARIANTS = "unicode_variants"
    LENGTH_EXTREMES = "length_extremes"
    FORMAT_VARIATIONS = "format_variations"
    ENCODING_ISSUES = "encoding_issues"
    CONCURRENT_ACCESS = "concurrent_access"
    RESOURCE_LIMITS = "resource_limits"
    STATE_TRANSITIONS = "state_transitions"


@dataclass
class EdgeCase:
    """Represents a discovered edge case"""
    category: EdgeCaseCategory
    description: str
    test_input: Dict[str, Any]
    expected_behavior: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    discovered_by: str
    test_result: Optional[Dict[str, Any]] = None


class EdgeCaseGenerator:
    """Generates edge cases for testing"""
    
    def __init__(self):
        self.discovered_cases = []
        self.generation_strategies = {
            EdgeCaseCategory.BOUNDARY_VALUES: self._generate_boundary_cases,
            EdgeCaseCategory.UNICODE_VARIANTS: self._generate_unicode_cases,
            EdgeCaseCategory.LENGTH_EXTREMES: self._generate_length_cases,
            EdgeCaseCategory.FORMAT_VARIATIONS: self._generate_format_cases,
            EdgeCaseCategory.ENCODING_ISSUES: self._generate_encoding_cases,
            EdgeCaseCategory.CONCURRENT_ACCESS: self._generate_concurrency_cases,
            EdgeCaseCategory.RESOURCE_LIMITS: self._generate_resource_cases,
            EdgeCaseCategory.STATE_TRANSITIONS: self._generate_state_cases
        }
    
    def generate_all_edge_cases(self) -> List[EdgeCase]:
        """Generate all categories of edge cases"""
        all_cases = []
        
        for category, generator in self.generation_strategies.items():
            try:
                cases = generator()
                all_cases.extend(cases)
            except Exception as e:
                # Log error but continue with other categories
                print(f"Error generating {category}: {e}")
        
        self.discovered_cases = all_cases
        return all_cases
    
    def _generate_boundary_cases(self) -> List[EdgeCase]:
        """Generate boundary value edge cases"""
        cases = []
        
        # String length boundaries
        boundary_texts = [
            "",  # Empty string
            "a",  # Single character
            "ab",  # Two characters
            "a" * 255,  # Typical string limit
            "a" * 256,  # Just over limit
            "a" * 1023,  # Near KB boundary
            "a" * 1024,  # Exactly 1KB
            "a" * 1025,  # Just over 1KB
            "a" * 65535,  # 16-bit limit
            "a" * 65536,  # Just over 16-bit
        ]
        
        for text in boundary_texts:
            cases.append(EdgeCase(
                category=EdgeCaseCategory.BOUNDARY_VALUES,
                description=f"Text with {len(text)} characters",
                test_input={
                    "text": text,
                    "source_lang": "eng_Latn",
                    "target_lang": "fra_Latn"
                },
                expected_behavior="Handle gracefully or return appropriate error",
                severity="medium" if len(text) < 1000 else "high",
                discovered_by="_generate_boundary_cases"
            ))
        
        # Language code boundaries
        lang_boundary_cases = [
            {"source_lang": "", "target_lang": "fra_Latn"},  # Empty source
            {"source_lang": "eng_Latn", "target_lang": ""},  # Empty target
            {"source_lang": "a", "target_lang": "fra_Latn"},  # Too short
            {"source_lang": "eng_Latn", "target_lang": "b"},  # Too short target
            {"source_lang": "x" * 100, "target_lang": "fra_Latn"},  # Too long source
            {"source_lang": "eng_Latn", "target_lang": "y" * 100},  # Too long target
        ]
        
        for lang_case in lang_boundary_cases:
            cases.append(EdgeCase(
                category=EdgeCaseCategory.BOUNDARY_VALUES,
                description=f"Language boundary: {lang_case}",
                test_input={
                    "text": "Boundary test",
                    **lang_case
                },
                expected_behavior="Return validation error for invalid language codes",
                severity="high",
                discovered_by="_generate_boundary_cases"
            ))
        
        return cases
    
    def _generate_unicode_cases(self) -> List[EdgeCase]:
        """Generate Unicode-related edge cases"""
        cases = []
        
        # Unicode categories
        unicode_test_cases = [
            # Combining characters
            ("cafe\u0301", "Text with combining acute accent"),
            ("A\u0300\u0301\u0302", "Multiple combining characters"),
            
            # Bidirectional text
            ("Hello \u202Eworld\u202D", "Right-to-left override"),
            ("English العربية English", "Mixed LTR/RTL text"),
            
            # Surrogate pairs
            ("𝕳𝖊𝖑𝖑𝖔", "Mathematical bold text"),
            ("🌍🌎🌏", "Multiple emoji"),
            
            # Zero-width characters
            ("Test\u200Bword", "Zero-width space"),
            ("Invisible\u200C\u200Dtext", "Zero-width non-joiner/joiner"),
            
            # Different Unicode blocks
            ("αβγδε", "Greek letters"),
            ("中文测试", "Chinese characters"),
            ("тест на русском", "Cyrillic text"),
            ("اختبار عربي", "Arabic text"),
            ("हिंदी परीक्षण", "Devanagari script"),
            
            # Unicode normalization edge cases
            ("fi", "Normal text"),
            ("\uFB01", "Ligature fi"),
            ("1⁄2", "Fraction one half"),
            ("½", "Vulgar fraction one half"),
            
            # Control characters
            ("Text\x00with\x01null", "Text with control characters"),
            ("Line\r\nbreak\n\rtest", "Various line breaks"),
            
            # Unicode escape sequences
            ("\\u0048\\u0065\\u006C\\u006C\\u006F", "Unicode escape sequences"),
        ]
        
        for text, description in unicode_test_cases:
            cases.append(EdgeCase(
                category=EdgeCaseCategory.UNICODE_VARIANTS,
                description=description,
                test_input={
                    "text": text,
                    "source_lang": "eng_Latn",
                    "target_lang": "fra_Latn"
                },
                expected_behavior="Handle Unicode properly without corruption",
                severity="medium",
                discovered_by="_generate_unicode_cases"
            ))
        
        return cases
    
    def _generate_length_cases(self) -> List[EdgeCase]:
        """Generate length extreme edge cases"""
        cases = []
        
        # Generate texts of various extreme lengths
        length_scenarios = [
            (0, "empty", "critical"),
            (1, "single_char", "high"),
            (10000, "very_long", "medium"),
            (50000, "extremely_long", "high"),
            (100000, "massive_text", "critical"),
        ]
        
        for length, scenario_name, severity in length_scenarios:
            if length == 0:
                text = ""
            else:
                # Create varied content to avoid simple repetition
                base_text = "This is a test sentence for translation. It contains various words and punctuation! "
                text = (base_text * (length // len(base_text) + 1))[:length]
            
            cases.append(EdgeCase(
                category=EdgeCaseCategory.LENGTH_EXTREMES,
                description=f"Text length {length} characters ({scenario_name})",
                test_input={
                    "text": text,
                    "source_lang": "eng_Latn",
                    "target_lang": "fra_Latn"
                },
                expected_behavior="Handle length appropriately or return size limit error",
                severity=severity,
                discovered_by="_generate_length_cases"
            ))
        
        return cases
    
    def _generate_format_cases(self) -> List[EdgeCase]:
        """Generate format variation edge cases"""
        cases = []
        
        # Different text formats
        format_cases = [
            # Structured text
            ("JSON: {\"key\": \"value\", \"nested\": {\"data\": 123}}", "JSON format"),
            ("XML: <root><item id='1'>value</item></root>", "XML format"),
            ("CSV: name,age,city\\nJohn,25,NYC\\nJane,30,LA", "CSV format"),
            
            # Code snippets
            ("def hello():\\n    print('Hello, World!')\\n    return True", "Python code"),
            ("SELECT * FROM users WHERE id = 1; -- SQL comment", "SQL query"),
            ("console.log('Hello'); /* JS comment */", "JavaScript code"),
            
            # Mathematical expressions
            ("E = mc²", "Mathematical formula"),
            ("∫₀^∞ e^(-x²) dx = √π/2", "Mathematical integral"),
            ("lim(x→0) sin(x)/x = 1", "Mathematical limit"),
            
            # URLs and paths
            ("https://example.com/path?param=value&other=123", "URL with parameters"),
            ("/usr/local/bin/python3.9", "Unix file path"),
            ("C:\\\\Program Files\\\\App\\\\file.exe", "Windows file path"),
            
            # Formatted numbers
            ("Price: $1,234.56", "Currency format"),
            ("Date: 2023-12-31T23:59:59Z", "ISO datetime"),
            ("Phone: +1 (555) 123-4567", "Phone number"),
            
            # Special punctuation
            ("Hello… world!?", "Ellipsis and multiple punctuation"),
            ("Text with \"smart quotes\" and 'apostrophes'", "Smart quotes"),
            ("En–dash and Em—dash usage", "Different dash types"),
        ]
        
        for text, description in format_cases:
            cases.append(EdgeCase(
                category=EdgeCaseCategory.FORMAT_VARIATIONS,
                description=description,
                test_input={
                    "text": text,
                    "source_lang": "eng_Latn",
                    "target_lang": "fra_Latn"
                },
                expected_behavior="Preserve formatting or handle structured content appropriately",
                severity="medium",
                discovered_by="_generate_format_cases"
            ))
        
        return cases
    
    def _generate_encoding_cases(self) -> List[EdgeCase]:
        """Generate encoding-related edge cases"""
        cases = []
        
        encoding_scenarios = [
            # Different encodings represented as text
            ("Caf\u00e9", "UTF-8 encoded café"),
            ("Caf\u00c3\u00a9", "Double-encoded UTF-8"),
            ("\ufeffHello World", "BOM prefix"),
            ("Hello\ufffdWorld", "Replacement character"),
            
            # Percent encoding
            ("Hello%20World%21", "URL percent encoding"),
            ("Caf%C3%A9", "UTF-8 percent encoded"),
            
            # Base64-like patterns
            ("SGVsbG8gV29ybGQ=", "Base64-like string"),
            ("VGVzdCBzdHJpbmc=", "Another Base64-like string"),
            
            # HTML entities
            ("Caf&eacute;", "HTML entity"),
            ("&lt;tag&gt;content&lt;/tag&gt;", "HTML entities for tags"),
            ("&amp;&lt;&gt;&quot;&apos;", "HTML special characters"),
            
            # Escape sequences
            ("Hello\\nWorld\\t!", "Escape sequences"),
            ("Path\\\\to\\\\file", "Escaped backslashes"),
            ("Quote: \\\"Hello\\\"", "Escaped quotes"),
        ]
        
        for text, description in encoding_scenarios:
            cases.append(EdgeCase(
                category=EdgeCaseCategory.ENCODING_ISSUES,
                description=description,
                test_input={
                    "text": text,
                    "source_lang": "eng_Latn",
                    "target_lang": "fra_Latn"
                },
                expected_behavior="Handle encoding properly without corruption",
                severity="high",
                discovered_by="_generate_encoding_cases"
            ))
        
        return cases
    
    def _generate_concurrency_cases(self) -> List[EdgeCase]:
        """Generate concurrency-related edge cases"""
        cases = []
        
        # Different concurrency scenarios
        concurrency_scenarios = [
            (2, "dual_request", "medium"),
            (5, "burst_request", "high"),
            (10, "high_concurrency", "high"),
            (20, "stress_concurrency", "critical"),
        ]
        
        for thread_count, scenario_name, severity in concurrency_scenarios:
            cases.append(EdgeCase(
                category=EdgeCaseCategory.CONCURRENT_ACCESS,
                description=f"Concurrent access with {thread_count} threads ({scenario_name})",
                test_input={
                    "concurrent_threads": thread_count,
                    "text": f"Concurrent test {scenario_name}",
                    "source_lang": "eng_Latn",
                    "target_lang": "fra_Latn"
                },
                expected_behavior="Handle concurrent requests without race conditions",
                severity=severity,
                discovered_by="_generate_concurrency_cases"
            ))
        
        return cases
    
    def _generate_resource_cases(self) -> List[EdgeCase]:
        """Generate resource limit edge cases"""
        cases = []
        
        resource_scenarios = [
            # Memory pressure scenarios
            {
                "description": "High memory usage text",
                "multiplier": 1000,
                "severity": "high"
            },
            {
                "description": "Extreme memory usage text", 
                "multiplier": 5000,
                "severity": "critical"
            },
            
            # CPU intensive scenarios (complex text patterns)
            {
                "description": "Complex nested patterns",
                "pattern": "((nested(patterns(with)many)brackets))" * 100,
                "severity": "medium"
            },
            {
                "description": "Repetitive complex pattern",
                "pattern": "abcdefghijklmnopqrstuvwxyz" * 1000,
                "severity": "medium"
            }
        ]
        
        for scenario in resource_scenarios:
            if 'multiplier' in scenario:
                text = "Resource intensive test text. " * scenario['multiplier']
            else:
                text = scenario['pattern']
            
            cases.append(EdgeCase(
                category=EdgeCaseCategory.RESOURCE_LIMITS,
                description=scenario['description'],
                test_input={
                    "text": text,
                    "source_lang": "eng_Latn",
                    "target_lang": "fra_Latn"
                },
                expected_behavior="Handle resource constraints gracefully",
                severity=scenario['severity'],
                discovered_by="_generate_resource_cases"
            ))
        
        return cases
    
    def _generate_state_cases(self) -> List[EdgeCase]:
        """Generate state transition edge cases"""
        cases = []
        
        # Different API state scenarios
        state_scenarios = [
            # Authentication state changes
            {
                "description": "Valid to invalid API key transition",
                "test_sequence": [
                    {"headers": {"X-API-Key": "test_api_key"}, "should_succeed": True},
                    {"headers": {"X-API-Key": "invalid_key"}, "should_succeed": False}
                ],
                "severity": "high"
            },
            
            # Rate limiting state changes
            {
                "description": "Rate limit boundary transition",
                "test_sequence": [
                    {"rapid_requests": 5, "should_succeed": True},
                    {"rapid_requests": 15, "should_succeed": False}  # Should hit rate limit
                ],
                "severity": "medium"
            },
            
            # Content state changes
            {
                "description": "Valid to invalid content transition",
                "test_sequence": [
                    {"text": "Valid text", "should_succeed": True},
                    {"text": "", "should_succeed": False}
                ],
                "severity": "medium"
            }
        ]
        
        for scenario in state_scenarios:
            cases.append(EdgeCase(
                category=EdgeCaseCategory.STATE_TRANSITIONS,
                description=scenario['description'],
                test_input={
                    "test_sequence": scenario['test_sequence'],
                    "base_request": {
                        "text": "State transition test",
                        "source_lang": "eng_Latn",
                        "target_lang": "fra_Latn"
                    }
                },
                expected_behavior="Handle state transitions correctly",
                severity=scenario['severity'],
                discovered_by="_generate_state_cases"
            ))
        
        return cases


class EdgeCaseTester:
    """Tests discovered edge cases"""
    
    def __init__(self, client: TestClient):
        self.client = client
        self.test_results = []
    
    def test_edge_case(self, edge_case: EdgeCase) -> Dict[str, Any]:
        """Test a single edge case"""
        test_result = {
            'edge_case': edge_case,
            'test_passed': False,
            'response_code': None,
            'response_data': None,
            'execution_time': 0,
            'error': None,
            'notes': []
        }
        
        start_time = time.time()
        
        try:
            if edge_case.category == EdgeCaseCategory.CONCURRENT_ACCESS:
                test_result = self._test_concurrent_case(edge_case, test_result)
            elif edge_case.category == EdgeCaseCategory.STATE_TRANSITIONS:
                test_result = self._test_state_transition_case(edge_case, test_result)
            else:
                test_result = self._test_standard_case(edge_case, test_result)
                
        except Exception as e:
            test_result['error'] = str(e)
            test_result['notes'].append(f"Exception during test: {e}")
        
        test_result['execution_time'] = time.time() - start_time
        
        # Update edge case with test results
        edge_case.test_result = test_result
        self.test_results.append(test_result)
        
        return test_result
    
    def _test_standard_case(self, edge_case: EdgeCase, test_result: Dict[str, Any]) -> Dict[str, Any]:
        """Test standard edge cases"""
        test_input = edge_case.test_input
        
        response = self.client.post(
            "/translate",
            json=test_input,
            headers={"X-API-Key": "test_api_key"}
        )
        
        test_result['response_code'] = response.status_code
        test_result['response_data'] = response.json() if response.content else None
        
        # Determine if test passed based on expected behavior
        if edge_case.severity == "critical":
            # Critical cases should either work or fail gracefully (not crash)
            test_result['test_passed'] = response.status_code in [200, 400, 422, 413]
        elif edge_case.severity == "high":
            # High severity should handle gracefully
            test_result['test_passed'] = response.status_code in [200, 400, 422]
        else:
            # Medium/low severity - more lenient
            test_result['test_passed'] = response.status_code < 500
        
        # Additional validation based on category
        if edge_case.category == EdgeCaseCategory.UNICODE_VARIANTS:
            if response.status_code == 200 and test_result['response_data']:
                # Check that Unicode wasn't corrupted
                translated_text = test_result['response_data'].get('translated_text', '')
                if '\ufffd' in translated_text:  # Replacement character indicates corruption
                    test_result['notes'].append("Unicode corruption detected")
                    test_result['test_passed'] = False
        
        return test_result
    
    def _test_concurrent_case(self, edge_case: EdgeCase, test_result: Dict[str, Any]) -> Dict[str, Any]:
        """Test concurrent access edge cases"""
        thread_count = edge_case.test_input.get('concurrent_threads', 2)
        
        def make_request():
            return self.client.post(
                "/translate",
                json={
                    "text": edge_case.test_input['text'],
                    "source_lang": edge_case.test_input['source_lang'],
                    "target_lang": edge_case.test_input['target_lang']
                },
                headers={"X-API-Key": "test_api_key"}
            )
        
        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [executor.submit(make_request) for _ in range(thread_count)]
            responses = [future.result() for future in futures]
        
        # Analyze results
        status_codes = [r.status_code for r in responses]
        success_count = sum(1 for code in status_codes if code == 200)
        error_count = sum(1 for code in status_codes if code >= 500)
        
        test_result['response_code'] = status_codes[0] if status_codes else None
        test_result['response_data'] = {
            'concurrent_responses': len(responses),
            'success_count': success_count,
            'error_count': error_count,
            'status_codes': status_codes
        }
        
        # Test passes if no server errors and reasonable success rate
        test_result['test_passed'] = (error_count == 0 and success_count >= thread_count * 0.5)
        
        return test_result
    
    def _test_state_transition_case(self, edge_case: EdgeCase, test_result: Dict[str, Any]) -> Dict[str, Any]:
        """Test state transition edge cases"""
        test_sequence = edge_case.test_input['test_sequence']
        base_request = edge_case.test_input['base_request']
        
        sequence_results = []
        
        for step in test_sequence:
            step_result = {}
            
            if 'headers' in step:
                # Authentication state test
                response = self.client.post(
                    "/translate",
                    json=base_request,
                    headers=step['headers']
                )
                step_result['response_code'] = response.status_code
                step_result['expected_success'] = step['should_succeed']
                step_result['actual_success'] = response.status_code == 200
                
            elif 'rapid_requests' in step:
                # Rate limiting state test
                request_count = step['rapid_requests']
                responses = []
                
                for _ in range(request_count):
                    response = self.client.post(
                        "/translate",
                        json=base_request,
                        headers={"X-API-Key": "test_api_key"}
                    )
                    responses.append(response.status_code)
                
                rate_limited = any(code == 429 for code in responses)
                step_result['response_codes'] = responses
                step_result['rate_limited'] = rate_limited
                step_result['expected_success'] = step['should_succeed']
                step_result['actual_success'] = not rate_limited if step['should_succeed'] else rate_limited
            
            elif 'text' in step:
                # Content state test
                test_request = base_request.copy()
                test_request['text'] = step['text']
                
                response = self.client.post(
                    "/translate",
                    json=test_request,
                    headers={"X-API-Key": "test_api_key"}
                )
                step_result['response_code'] = response.status_code
                step_result['expected_success'] = step['should_succeed']
                step_result['actual_success'] = response.status_code == 200
            
            sequence_results.append(step_result)
        
        # Test passes if all state transitions behaved as expected
        all_correct = all(
            result.get('actual_success') == result.get('expected_success')
            for result in sequence_results
        )
        
        test_result['test_passed'] = all_correct
        test_result['response_data'] = {'sequence_results': sequence_results}
        
        return test_result
    
    def analyze_test_results(self) -> Dict[str, Any]:
        """Analyze all test results and provide summary"""
        if not self.test_results:
            return {"error": "No test results to analyze"}
        
        analysis = {
            'total_tests': len(self.test_results),
            'passed_tests': 0,
            'failed_tests': 0,
            'by_category': {},
            'by_severity': {},
            'critical_failures': [],
            'performance_issues': [],
            'recommendations': []
        }
        
        for result in self.test_results:
            edge_case = result['edge_case']
            category = edge_case.category.value
            severity = edge_case.severity
            
            # Count by pass/fail
            if result['test_passed']:
                analysis['passed_tests'] += 1
            else:
                analysis['failed_tests'] += 1
                
                if severity == 'critical':
                    analysis['critical_failures'].append({
                        'description': edge_case.description,
                        'category': category,
                        'error': result.get('error'),
                        'response_code': result.get('response_code')
                    })
            
            # Count by category
            if category not in analysis['by_category']:
                analysis['by_category'][category] = {'total': 0, 'passed': 0, 'failed': 0}
            
            analysis['by_category'][category]['total'] += 1
            if result['test_passed']:
                analysis['by_category'][category]['passed'] += 1
            else:
                analysis['by_category'][category]['failed'] += 1
            
            # Count by severity
            if severity not in analysis['by_severity']:
                analysis['by_severity'][severity] = {'total': 0, 'passed': 0, 'failed': 0}
            
            analysis['by_severity'][severity]['total'] += 1
            if result['test_passed']:
                analysis['by_severity'][severity]['passed'] += 1
            else:
                analysis['by_severity'][severity]['failed'] += 1
            
            # Check for performance issues
            if result['execution_time'] > 5.0:  # 5 second threshold
                analysis['performance_issues'].append({
                    'description': edge_case.description,
                    'execution_time': result['execution_time'],
                    'category': category
                })
        
        # Generate recommendations
        if analysis['critical_failures']:
            analysis['recommendations'].append(f"Address {len(analysis['critical_failures'])} critical failures immediately")
        
        if analysis['performance_issues']:
            analysis['recommendations'].append(f"Optimize {len(analysis['performance_issues'])} slow edge cases")
        
        # Category-specific recommendations
        for category, stats in analysis['by_category'].items():
            if stats['failed'] > stats['passed']:
                analysis['recommendations'].append(f"Focus on improving {category} handling")
        
        return analysis


class TestEdgeCaseDiscovery:
    """Edge Case Discovery Test Suite"""
    
    @pytest.fixture(autouse=True)
    def setup(self, enhanced_mock_objects):
        """Setup for edge case discovery tests"""
        self.generator = EdgeCaseGenerator()
        self.enhanced_mock_objects = enhanced_mock_objects
    
    def test_edge_case_generation(self):
        """Test edge case generation across all categories"""
        edge_cases = self.generator.generate_all_edge_cases()
        
        # Should generate cases
        assert len(edge_cases) > 0, "No edge cases generated"
        
        # Check category coverage
        categories_found = set(case.category for case in edge_cases)
        expected_categories = set(EdgeCaseCategory)
        
        # Should cover most categories
        coverage_rate = len(categories_found) / len(expected_categories)
        assert coverage_rate >= 0.7, f"Poor category coverage: {coverage_rate:.2%}"
        
        # Check severity distribution
        severities = [case.severity for case in edge_cases]
        unique_severities = set(severities)
        assert len(unique_severities) >= 3, f"Need more severity variety: {unique_severities}"
    
    def test_boundary_value_cases(self):
        """Test boundary value edge case generation"""
        boundary_cases = self.generator._generate_boundary_cases()
        
        assert len(boundary_cases) > 0, "No boundary cases generated"
        
        # Should include empty string case
        empty_cases = [case for case in boundary_cases if case.test_input.get('text') == '']
        assert len(empty_cases) > 0, "Missing empty string boundary case"
        
        # Should include large text cases
        large_cases = [case for case in boundary_cases if len(case.test_input.get('text', '')) > 1000]
        assert len(large_cases) > 0, "Missing large text boundary cases"
    
    def test_unicode_edge_cases(self):
        """Test Unicode edge case generation"""
        unicode_cases = self.generator._generate_unicode_cases()
        
        assert len(unicode_cases) > 0, "No Unicode cases generated"
        
        # Check for various Unicode categories
        unicode_texts = [case.test_input.get('text', '') for case in unicode_cases]
        
        # Should include emoji
        emoji_cases = [text for text in unicode_texts if any(ord(c) > 0x1F600 for c in text)]
        assert len(emoji_cases) > 0, "Missing emoji Unicode cases"
        
        # Should include combining characters
        combining_cases = [text for text in unicode_texts if any(unicodedata.combining(c) for c in text)]
        assert len(combining_cases) > 0, "Missing combining character cases"
    
    def test_edge_case_testing(self, test_client, enhanced_mock_objects):
        """Test edge case testing functionality"""
        # Generate some test cases
        edge_cases = self.generator._generate_boundary_cases()[:5]  # Limit for speed
        
        # Test them
        tester = EdgeCaseTester(test_client)
        
        for edge_case in edge_cases:
            result = tester.test_edge_case(edge_case)
            
            # Should have test result structure
            assert 'test_passed' in result
            assert 'response_code' in result
            assert 'execution_time' in result
            assert result['execution_time'] >= 0
    
    def test_concurrent_edge_cases(self, test_client, enhanced_mock_objects):
        """Test concurrent edge case handling"""
        concurrent_cases = self.generator._generate_concurrency_cases()
        
        assert len(concurrent_cases) > 0, "No concurrent cases generated"
        
        # Test a simple concurrent case
        simple_case = min(concurrent_cases, key=lambda x: x.test_input.get('concurrent_threads', 1))
        
        tester = EdgeCaseTester(test_client)
        result = tester.test_edge_case(simple_case)
        
        # Should handle concurrent access
        assert 'response_data' in result
        assert result['response_data'] is not None
    
    def test_format_variation_cases(self):
        """Test format variation edge case generation"""
        format_cases = self.generator._generate_format_cases()
        
        assert len(format_cases) > 0, "No format cases generated"
        
        # Check for various format types
        format_texts = [case.test_input.get('text', '') for case in format_cases]
        
        # Should include JSON-like content
        json_cases = [text for text in format_texts if '{' in text and '}' in text]
        assert len(json_cases) > 0, "Missing JSON format cases"
        
        # Should include URL-like content
        url_cases = [text for text in format_texts if 'http' in text or '://' in text]
        assert len(url_cases) > 0, "Missing URL format cases"
    
    def test_resource_limit_cases(self):
        """Test resource limit edge case generation"""
        resource_cases = self.generator._generate_resource_cases()
        
        assert len(resource_cases) > 0, "No resource cases generated"
        
        # Should include high-resource cases
        large_cases = [case for case in resource_cases if len(case.test_input.get('text', '')) > 10000]
        assert len(large_cases) > 0, "Missing large resource test cases"
        
        # Should have critical severity cases
        critical_cases = [case for case in resource_cases if case.severity == 'critical']
        assert len(critical_cases) > 0, "Missing critical resource cases"
    
    def test_comprehensive_edge_case_analysis(self, test_client, enhanced_mock_objects):
        """Test comprehensive edge case analysis"""
        # Generate a subset of edge cases for full testing
        all_cases = self.generator.generate_all_edge_cases()
        test_cases = random.sample(all_cases, min(20, len(all_cases)))  # Limit for test speed
        
        # Test all selected cases
        tester = EdgeCaseTester(test_client)
        
        for edge_case in test_cases:
            tester.test_edge_case(edge_case)
        
        # Analyze results
        analysis = tester.analyze_test_results()
        
        # Should have comprehensive analysis
        assert 'total_tests' in analysis
        assert 'by_category' in analysis
        assert 'by_severity' in analysis
        assert 'recommendations' in analysis
        
        assert analysis['total_tests'] == len(test_cases)
        assert analysis['total_tests'] == analysis['passed_tests'] + analysis['failed_tests']
        
        # Should have reasonable pass rate
        pass_rate = analysis['passed_tests'] / analysis['total_tests']
        assert pass_rate >= 0.5, f"Edge case pass rate too low: {pass_rate:.2%}"