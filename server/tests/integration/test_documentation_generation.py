"""
Documentation Generation Tests
Tests automated documentation generation and accuracy validation
"""

import pytest
import json
import os
import tempfile
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from app.main import app


class DocumentationGenerator:
    """Generates and validates API documentation"""
    
    def __init__(self):
        self.doc_formats = ['openapi', 'markdown', 'html']
        self.validation_rules = {
            'endpoints': ['health', 'translate'],
            'methods': ['GET', 'POST'],
            'response_codes': [200, 400, 401, 422, 429, 500],
            'required_fields': ['text', 'source_lang', 'target_lang']
        }
    
    def generate_openapi_spec(self, client: TestClient) -> Dict[str, Any]:
        """Generate OpenAPI specification from FastAPI app"""
        # Get OpenAPI JSON from the app
        response = client.get("/openapi.json")
        
        if response.status_code != 200:
            return {}
        
        return response.json()
    
    def validate_openapi_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Validate OpenAPI specification completeness"""
        validation = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'coverage': {
                'endpoints': 0,
                'methods': 0,
                'responses': 0,
                'schemas': 0
            }
        }
        
        # Check basic structure
        required_keys = ['openapi', 'info', 'paths']
        for key in required_keys:
            if key not in spec:
                validation['valid'] = False
                validation['errors'].append(f"Missing required key: {key}")
        
        if 'paths' in spec:
            paths = spec['paths']
            
            # Check for expected endpoints
            for endpoint in self.validation_rules['endpoints']:
                endpoint_found = False
                for path in paths.keys():
                    if endpoint in path:
                        endpoint_found = True
                        validation['coverage']['endpoints'] += 1
                        break
                
                if not endpoint_found:
                    validation['warnings'].append(f"Endpoint not documented: {endpoint}")
            
            # Check methods and responses
            for path, path_info in paths.items():
                for method, method_info in path_info.items():
                    if method.upper() in self.validation_rules['methods']:
                        validation['coverage']['methods'] += 1
                    
                    if 'responses' in method_info:
                        for response_code in method_info['responses'].keys():
                            try:
                                code = int(response_code)
                                if code in self.validation_rules['response_codes']:
                                    validation['coverage']['responses'] += 1
                            except ValueError:
                                validation['warnings'].append(f"Non-numeric response code: {response_code}")
        
        # Check schemas
        if 'components' in spec and 'schemas' in spec['components']:
            validation['coverage']['schemas'] = len(spec['components']['schemas'])
        
        return validation
    
    def generate_markdown_docs(self, spec: Dict[str, Any]) -> str:
        """Generate Markdown documentation from OpenAPI spec"""
        markdown = []
        
        # Title and description
        if 'info' in spec:
            info = spec['info']
            markdown.append(f"# {info.get('title', 'API Documentation')}")
            markdown.append("")
            if 'description' in info:
                markdown.append(info['description'])
                markdown.append("")
            if 'version' in info:
                markdown.append(f"**Version:** {info['version']}")
                markdown.append("")
        
        # Endpoints
        if 'paths' in spec:
            markdown.append("## Endpoints")
            markdown.append("")
            
            for path, path_info in spec['paths'].items():
                markdown.append(f"### {path}")
                markdown.append("")
                
                for method, method_info in path_info.items():
                    markdown.append(f"#### {method.upper()}")
                    
                    if 'summary' in method_info:
                        markdown.append(method_info['summary'])
                        markdown.append("")
                    
                    if 'description' in method_info:
                        markdown.append(method_info['description'])
                        markdown.append("")
                    
                    # Parameters
                    if 'parameters' in method_info:
                        markdown.append("**Parameters:**")
                        for param in method_info['parameters']:
                            param_desc = f"- `{param.get('name', 'unknown')}` ({param.get('in', 'unknown')})"
                            if param.get('required', False):
                                param_desc += " *required*"
                            if 'description' in param:
                                param_desc += f": {param['description']}"
                            markdown.append(param_desc)
                        markdown.append("")
                    
                    # Request body
                    if 'requestBody' in method_info:
                        markdown.append("**Request Body:**")
                        request_body = method_info['requestBody']
                        if 'description' in request_body:
                            markdown.append(request_body['description'])
                        markdown.append("")
                    
                    # Responses
                    if 'responses' in method_info:
                        markdown.append("**Responses:**")
                        for code, response in method_info['responses'].items():
                            response_desc = f"- `{code}`: {response.get('description', 'No description')}"
                            markdown.append(response_desc)
                        markdown.append("")
                    
                    markdown.append("---")
                    markdown.append("")
        
        return "\n".join(markdown)
    
    def validate_documentation_accuracy(self, client: TestClient, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that documentation matches actual API behavior"""
        validation = {
            'accurate': True,
            'discrepancies': [],
            'endpoint_tests': []
        }
        
        if 'paths' not in spec:
            validation['accurate'] = False
            validation['discrepancies'].append("No paths found in specification")
            return validation
        
        # Test each documented endpoint
        for path, path_info in spec['paths'].items():
            for method, method_info in path_info.items():
                endpoint_test = {
                    'path': path,
                    'method': method.upper(),
                    'documented_responses': list(method_info.get('responses', {}).keys()),
                    'actual_responses': [],
                    'matches': True
                }
                
                # Test the endpoint
                try:
                    if method.upper() == 'GET':
                        if path == '/health':
                            response = client.get(path)
                            endpoint_test['actual_responses'].append(str(response.status_code))
                        
                    elif method.upper() == 'POST':
                        if 'translate' in path:
                            # Test valid request
                            response = client.post(
                                path,
                                json={
                                    "text": "Documentation test",
                                    "source_lang": "eng_Latn",
                                    "target_lang": "fra_Latn"
                                },
                                headers={"X-API-Key": "test_api_key"}
                            )
                            endpoint_test['actual_responses'].append(str(response.status_code))
                            
                            # Test invalid request
                            response = client.post(path, json={})
                            endpoint_test['actual_responses'].append(str(response.status_code))
                
                except Exception as e:
                    endpoint_test['error'] = str(e)
                    endpoint_test['matches'] = False
                
                # Check if documented responses match actual responses
                documented_codes = set(endpoint_test['documented_responses'])
                actual_codes = set(endpoint_test['actual_responses'])
                
                if not documented_codes.intersection(actual_codes):
                    endpoint_test['matches'] = False
                    validation['discrepancies'].append(
                        f"{method.upper()} {path}: documented {documented_codes} vs actual {actual_codes}"
                    )
                
                validation['endpoint_tests'].append(endpoint_test)
                
                if not endpoint_test['matches']:
                    validation['accurate'] = False
        
        return validation


class DocumentationTestHelper:
    """Helper for documentation testing operations"""
    
    def __init__(self):
        self.temp_dir = None
        self.generated_files = []
    
    def create_temp_workspace(self) -> str:
        """Create temporary workspace for documentation generation"""
        self.temp_dir = tempfile.mkdtemp(prefix="doc_test_")
        return self.temp_dir
    
    def cleanup_workspace(self):
        """Clean up temporary workspace"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
        self.generated_files = []
    
    def save_documentation(self, content: str, filename: str, doc_format: str) -> str:
        """Save documentation to file"""
        if not self.temp_dir:
            self.create_temp_workspace()
        
        file_path = os.path.join(self.temp_dir, filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if doc_format == 'json':
                    if isinstance(content, str):
                        f.write(content)
                    else:
                        json.dump(content, f, indent=2)
                else:
                    f.write(content)
            
            self.generated_files.append(file_path)
            return file_path
            
        except Exception as e:
            raise RuntimeError(f"Failed to save documentation: {e}")
    
    def validate_file_structure(self, file_path: str, expected_format: str) -> Dict[str, Any]:
        """Validate generated documentation file structure"""
        validation = {
            'valid': True,
            'errors': [],
            'file_size': 0,
            'format_correct': False
        }
        
        try:
            if not os.path.exists(file_path):
                validation['valid'] = False
                validation['errors'].append("File does not exist")
                return validation
            
            validation['file_size'] = os.path.getsize(file_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Format-specific validation
            if expected_format == 'json':
                try:
                    json.loads(content)
                    validation['format_correct'] = True
                except json.JSONDecodeError as e:
                    validation['errors'].append(f"Invalid JSON: {e}")
                    
            elif expected_format == 'markdown':
                # Check for markdown elements
                if re.search(r'^#+ ', content, re.MULTILINE):
                    validation['format_correct'] = True
                else:
                    validation['errors'].append("No markdown headers found")
                    
            elif expected_format == 'html':
                # Check for HTML elements
                if '<html>' in content or '<body>' in content or '<h1>' in content:
                    validation['format_correct'] = True
                else:
                    validation['errors'].append("No HTML elements found")
            
            if validation['file_size'] == 0:
                validation['valid'] = False
                validation['errors'].append("Empty file")
                
        except Exception as e:
            validation['valid'] = False
            validation['errors'].append(f"File validation error: {e}")
        
        return validation


class TestDocumentationGeneration:
    """Documentation Generation Test Suite"""
    
    @pytest.fixture(autouse=True)
    def setup(self, enhanced_mock_objects):
        """Setup for documentation tests"""
        self.doc_generator = DocumentationGenerator()
        self.doc_helper = DocumentationTestHelper()
        self.enhanced_mock_objects = enhanced_mock_objects
    
    def teardown_method(self):
        """Cleanup after each test"""
        self.doc_helper.cleanup_workspace()
    
    def test_openapi_spec_generation(self, test_client, enhanced_mock_objects):
        """Test OpenAPI specification generation"""
        # Generate OpenAPI spec
        openapi_spec = self.doc_generator.generate_openapi_spec(test_client)
        
        # Basic structure validation
        assert isinstance(openapi_spec, dict), "OpenAPI spec should be a dictionary"
        assert len(openapi_spec) > 0, "OpenAPI spec should not be empty"
        
        # Check required fields
        required_fields = ['openapi', 'info', 'paths']
        for field in required_fields:
            assert field in openapi_spec, f"OpenAPI spec missing required field: {field}"
        
        # Validate info section
        assert 'title' in openapi_spec['info'], "OpenAPI info missing title"
        assert 'version' in openapi_spec['info'], "OpenAPI info missing version"
        
        # Validate paths section
        paths = openapi_spec['paths']
        assert len(paths) > 0, "No paths found in OpenAPI spec"
        
        # Check for expected endpoints
        endpoint_paths = list(paths.keys())
        assert any('/health' in path for path in endpoint_paths), "Health endpoint not documented"
        assert any('translate' in path for path in endpoint_paths), "Translate endpoint not documented"
    
    def test_openapi_spec_validation(self, test_client, enhanced_mock_objects):
        """Test OpenAPI specification validation"""
        # Generate and validate spec
        openapi_spec = self.doc_generator.generate_openapi_spec(test_client)
        validation = self.doc_generator.validate_openapi_spec(openapi_spec)
        
        # Should be valid
        assert validation['valid'], f"OpenAPI spec validation failed: {validation['errors']}"
        
        # Coverage checks
        assert validation['coverage']['endpoints'] >= 2, f"Insufficient endpoint coverage: {validation['coverage']['endpoints']}"
        assert validation['coverage']['methods'] >= 2, f"Insufficient method coverage: {validation['coverage']['methods']}"
        assert validation['coverage']['responses'] >= 5, f"Insufficient response coverage: {validation['coverage']['responses']}"
        
        # Should have minimal warnings
        assert len(validation['warnings']) <= 3, f"Too many validation warnings: {validation['warnings']}"
    
    def test_markdown_documentation_generation(self, test_client, enhanced_mock_objects):
        """Test Markdown documentation generation"""
        # Generate OpenAPI spec first
        openapi_spec = self.doc_generator.generate_openapi_spec(test_client)
        
        # Generate Markdown documentation
        markdown_docs = self.doc_generator.generate_markdown_docs(openapi_spec)
        
        # Basic validation
        assert isinstance(markdown_docs, str), "Markdown docs should be a string"
        assert len(markdown_docs) > 100, "Markdown docs should have substantial content"
        
        # Check for markdown structure
        assert re.search(r'^# ', markdown_docs, re.MULTILINE), "Markdown should have main heading"
        assert re.search(r'^## ', markdown_docs, re.MULTILINE), "Markdown should have section headings"
        assert re.search(r'^### ', markdown_docs, re.MULTILINE), "Markdown should have subsection headings"
        
        # Check for expected content
        assert 'health' in markdown_docs.lower(), "Health endpoint should be documented"
        assert 'translate' in markdown_docs.lower(), "Translate endpoint should be documented"
        assert 'POST' in markdown_docs, "POST method should be documented"
        assert 'GET' in markdown_docs, "GET method should be documented"
    
    def test_documentation_accuracy_validation(self, test_client, enhanced_mock_objects):
        """Test that documentation accurately reflects API behavior"""
        # Generate OpenAPI spec
        openapi_spec = self.doc_generator.generate_openapi_spec(test_client)
        
        # Validate documentation accuracy
        accuracy_validation = self.doc_generator.validate_documentation_accuracy(test_client, openapi_spec)
        
        # Documentation should be accurate
        assert accuracy_validation['accurate'], f"Documentation inaccurate: {accuracy_validation['discrepancies']}"
        
        # Should have tested endpoints
        assert len(accuracy_validation['endpoint_tests']) >= 2, "Insufficient endpoint testing"
        
        # Most endpoint tests should match
        matching_tests = sum(1 for test in accuracy_validation['endpoint_tests'] if test['matches'])
        match_rate = matching_tests / len(accuracy_validation['endpoint_tests'])
        assert match_rate >= 0.8, f"Poor documentation accuracy: {match_rate:.2%} matching"
    
    def test_documentation_file_generation(self, test_client, enhanced_mock_objects):
        """Test documentation file generation and saving"""
        workspace = self.doc_helper.create_temp_workspace()
        
        # Generate OpenAPI spec
        openapi_spec = self.doc_generator.generate_openapi_spec(test_client)
        
        # Save as JSON
        json_file = self.doc_helper.save_documentation(
            json.dumps(openapi_spec, indent=2),
            "api_spec.json",
            "json"
        )
        
        # Validate JSON file
        json_validation = self.doc_helper.validate_file_structure(json_file, "json")
        assert json_validation['valid'], f"JSON file validation failed: {json_validation['errors']}"
        assert json_validation['format_correct'], "JSON format validation failed"
        assert json_validation['file_size'] > 100, "JSON file too small"
        
        # Generate and save Markdown
        markdown_content = self.doc_generator.generate_markdown_docs(openapi_spec)
        markdown_file = self.doc_helper.save_documentation(
            markdown_content,
            "api_docs.md",
            "markdown"
        )
        
        # Validate Markdown file
        md_validation = self.doc_helper.validate_file_structure(markdown_file, "markdown")
        assert md_validation['valid'], f"Markdown file validation failed: {md_validation['errors']}"
        assert md_validation['format_correct'], "Markdown format validation failed"
        assert md_validation['file_size'] > 200, "Markdown file too small"
        
        # Verify files exist
        assert os.path.exists(json_file), "JSON file not created"
        assert os.path.exists(markdown_file), "Markdown file not created"
    
    def test_documentation_completeness_check(self, test_client, enhanced_mock_objects):
        """Test documentation completeness across all endpoints"""
        openapi_spec = self.doc_generator.generate_openapi_spec(test_client)
        
        completeness_report = {
            'total_endpoints': 0,
            'documented_endpoints': 0,
            'missing_documentation': [],
            'incomplete_documentation': []
        }
        
        # Define expected API endpoints
        expected_endpoints = [
            {'path': '/health', 'method': 'GET'},
            {'path': '/translate', 'method': 'POST'},
        ]
        
        completeness_report['total_endpoints'] = len(expected_endpoints)
        
        # Check each expected endpoint
        for expected in expected_endpoints:
            found = False
            complete = False
            
            if 'paths' in openapi_spec:
                for path, path_info in openapi_spec['paths'].items():
                    if expected['path'] in path:
                        if expected['method'].lower() in path_info:
                            found = True
                            method_info = path_info[expected['method'].lower()]
                            
                            # Check completeness
                            has_description = 'description' in method_info or 'summary' in method_info
                            has_responses = 'responses' in method_info and len(method_info['responses']) > 0
                            
                            if has_description and has_responses:
                                complete = True
                            else:
                                completeness_report['incomplete_documentation'].append({
                                    'endpoint': f"{expected['method']} {expected['path']}",
                                    'missing': {
                                        'description': not has_description,
                                        'responses': not has_responses
                                    }
                                })
                            break
            
            if found and complete:
                completeness_report['documented_endpoints'] += 1
            elif not found:
                completeness_report['missing_documentation'].append(f"{expected['method']} {expected['path']}")
        
        # Calculate completeness rate
        completeness_rate = completeness_report['documented_endpoints'] / completeness_report['total_endpoints']
        
        # Validate completeness
        assert completeness_rate >= 0.8, f"Documentation completeness insufficient: {completeness_rate:.2%}"
        assert len(completeness_report['missing_documentation']) == 0, f"Missing documentation: {completeness_report['missing_documentation']}"
        
        # Allow some incomplete documentation but not too much
        assert len(completeness_report['incomplete_documentation']) <= 1, f"Too much incomplete documentation: {completeness_report['incomplete_documentation']}"
    
    def test_documentation_consistency_check(self, test_client, enhanced_mock_objects):
        """Test consistency between different documentation formats"""
        # Generate OpenAPI spec
        openapi_spec = self.doc_generator.generate_openapi_spec(test_client)
        
        # Generate Markdown documentation
        markdown_docs = self.doc_generator.generate_markdown_docs(openapi_spec)
        
        # Extract information from both formats
        openapi_endpoints = set()
        markdown_endpoints = set()
        
        # Extract from OpenAPI
        if 'paths' in openapi_spec:
            for path, path_info in openapi_spec['paths'].items():
                for method in path_info.keys():
                    openapi_endpoints.add(f"{method.upper()} {path}")
        
        # Extract from Markdown (simple pattern matching)
        method_pattern = r'#### (GET|POST|PUT|DELETE|PATCH)'
        path_pattern = r'### (/[^\n]*)'
        
        methods = re.findall(method_pattern, markdown_docs)
        paths = re.findall(path_pattern, markdown_docs)
        
        # Create combinations (this is simplified - real implementation would be more sophisticated)
        for method in methods:
            for path in paths:
                markdown_endpoints.add(f"{method} {path}")
        
        # Check consistency
        consistency_report = {
            'openapi_endpoints': openapi_endpoints,
            'markdown_endpoints': markdown_endpoints,
            'common_endpoints': openapi_endpoints.intersection(markdown_endpoints),
            'openapi_only': openapi_endpoints - markdown_endpoints,
            'markdown_only': markdown_endpoints - openapi_endpoints
        }
        
        # Most endpoints should be in both formats
        if len(openapi_endpoints) > 0:
            consistency_rate = len(consistency_report['common_endpoints']) / len(openapi_endpoints)
            assert consistency_rate >= 0.7, f"Poor documentation consistency: {consistency_rate:.2%}"
        
        # Should not have too many format-specific endpoints
        assert len(consistency_report['openapi_only']) <= 2, f"Too many OpenAPI-only endpoints: {consistency_report['openapi_only']}"
        assert len(consistency_report['markdown_only']) <= 2, f"Too many Markdown-only endpoints: {consistency_report['markdown_only']}"
    
    def test_documentation_update_detection(self, test_client, enhanced_mock_objects):
        """Test detection of documentation updates needed"""
        # Generate current documentation
        current_spec = self.doc_generator.generate_openapi_spec(test_client)
        
        # Create a mock "previous" version with differences
        previous_spec = current_spec.copy()
        
        # Simulate changes
        if 'info' in previous_spec:
            previous_spec['info']['version'] = '0.1.0'  # Different version
        
        if 'paths' in previous_spec and '/translate' in str(previous_spec['paths']):
            # Remove a response code to simulate a change
            for path, path_info in previous_spec['paths'].items():
                if 'translate' in path:
                    for method, method_info in path_info.items():
                        if 'responses' in method_info and '422' in method_info['responses']:
                            del method_info['responses']['422']
                            break
                    break
        
        # Compare versions
        update_analysis = {
            'version_changed': False,
            'endpoints_changed': False,
            'responses_changed': False,
            'update_needed': False
        }
        
        # Check version
        if (current_spec.get('info', {}).get('version') != 
            previous_spec.get('info', {}).get('version')):
            update_analysis['version_changed'] = True
            update_analysis['update_needed'] = True
        
        # Check endpoints (simplified comparison)
        current_paths = set(current_spec.get('paths', {}).keys())
        previous_paths = set(previous_spec.get('paths', {}).keys())
        
        if current_paths != previous_paths:
            update_analysis['endpoints_changed'] = True
            update_analysis['update_needed'] = True
        
        # Check responses (simplified)
        current_responses = 0
        previous_responses = 0
        
        for path_info in current_spec.get('paths', {}).values():
            for method_info in path_info.values():
                current_responses += len(method_info.get('responses', {}))
        
        for path_info in previous_spec.get('paths', {}).values():
            for method_info in path_info.values():
                previous_responses += len(method_info.get('responses', {}))
        
        if current_responses != previous_responses:
            update_analysis['responses_changed'] = True
            update_analysis['update_needed'] = True
        
        # Should detect that updates are needed
        assert update_analysis['update_needed'], "Failed to detect documentation updates needed"
        assert update_analysis['version_changed'] or update_analysis['responses_changed'], "Should detect specific changes"