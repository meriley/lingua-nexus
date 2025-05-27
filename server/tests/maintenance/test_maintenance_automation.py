"""
Test Maintenance Automation
Automated test maintenance, cleanup routines, and test health monitoring
"""

import pytest
import os
import sys
import time
import json
import shutil
import tempfile
import subprocess
import glob
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
import re
import ast
from collections import defaultdict

from fastapi.testclient import TestClient
from app.main import app


class TestSuiteAnalyzer:
    """Analyzes test suite health and maintenance needs"""
    
    def __init__(self, test_root: str = "tests"):
        self.test_root = test_root
        self.maintenance_report = {
            'test_files': [],
            'duplicate_tests': [],
            'slow_tests': [],
            'failing_tests': [],
            'outdated_tests': [],
            'coverage_gaps': [],
            'recommendations': []
        }
    
    def scan_test_files(self) -> List[Dict[str, Any]]:
        """Scan all test files and analyze their structure"""
        test_files = []
        
        # Find all test files
        for root, dirs, files in os.walk(self.test_root):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    test_info = self._analyze_test_file(file_path)
                    test_files.append(test_info)
        
        self.maintenance_report['test_files'] = test_files
        return test_files
    
    def _analyze_test_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze individual test file"""
        file_info = {
            'path': file_path,
            'name': os.path.basename(file_path),
            'size': 0,
            'lines': 0,
            'test_count': 0,
            'class_count': 0,
            'fixture_count': 0,
            'last_modified': None,
            'imports': [],
            'test_methods': [],
            'issues': []
        }
        
        try:
            stat = os.stat(file_path)
            file_info['size'] = stat.st_size
            file_info['last_modified'] = datetime.fromtimestamp(stat.st_mtime)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                file_info['lines'] = len(content.splitlines())
            
            # Parse AST to analyze structure
            try:
                tree = ast.parse(content)
                file_info.update(self._analyze_ast(tree))
            except SyntaxError as e:
                file_info['issues'].append(f"Syntax error: {e}")
                
        except Exception as e:
            file_info['issues'].append(f"File analysis error: {e}")
        
        return file_info
    
    def _analyze_ast(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze AST for test structure"""
        analysis = {
            'imports': [],
            'test_methods': [],
            'test_count': 0,
            'class_count': 0,
            'fixture_count': 0
        }
        
        for node in ast.walk(tree):
            # Imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis['imports'].append(alias.name)
                else:
                    module = node.module or ''
                    analysis['imports'].append(module)
            
            # Classes
            elif isinstance(node, ast.ClassDef):
                if node.name.startswith('Test'):
                    analysis['class_count'] += 1
            
            # Functions
            elif isinstance(node, ast.FunctionDef):
                if node.name.startswith('test_'):
                    analysis['test_count'] += 1
                    analysis['test_methods'].append({
                        'name': node.name,
                        'line': node.lineno,
                        'args': len(node.args.args),
                        'decorators': [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list]
                    })
                
                # Check for fixtures
                for decorator in node.decorator_list:
                    if (isinstance(decorator, ast.Name) and decorator.id == 'fixture') or \
                       (isinstance(decorator, ast.Attribute) and decorator.attr == 'fixture'):
                        analysis['fixture_count'] += 1
        
        return analysis
    
    def detect_duplicate_tests(self) -> List[Dict[str, Any]]:
        """Detect potentially duplicate test methods"""
        duplicates = []
        test_signatures = defaultdict(list)
        
        for file_info in self.maintenance_report['test_files']:
            for test_method in file_info['test_methods']:
                # Create signature based on name pattern
                signature = self._normalize_test_name(test_method['name'])
                test_signatures[signature].append({
                    'file': file_info['path'],
                    'method': test_method['name'],
                    'line': test_method['line']
                })
        
        # Find duplicates
        for signature, tests in test_signatures.items():
            if len(tests) > 1:
                duplicates.append({
                    'signature': signature,
                    'count': len(tests),
                    'tests': tests
                })
        
        self.maintenance_report['duplicate_tests'] = duplicates
        return duplicates
    
    def _normalize_test_name(self, name: str) -> str:
        """Normalize test name for duplicate detection"""
        # Remove common variations
        name = re.sub(r'test_', '', name)
        name = re.sub(r'_\d+$', '', name)  # Remove trailing numbers
        name = re.sub(r'_with_.*', '', name)  # Remove specific variations
        name = re.sub(r'_valid|_invalid|_success|_failure|_error', '', name)
        return name.lower()
    
    def detect_slow_tests(self, threshold_seconds: float = 5.0) -> List[Dict[str, Any]]:
        """Detect potentially slow tests (heuristic analysis)"""
        slow_tests = []
        
        slow_indicators = [
            'sleep', 'time.sleep', 'asyncio.sleep',
            'ThreadPoolExecutor', 'concurrent.futures',
            'subprocess', 'requests.get', 'requests.post',
            'for.*in.*range.*100', 'while.*True'
        ]
        
        for file_info in self.maintenance_report['test_files']:
            try:
                with open(file_info['path'], 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for test_method in file_info['test_methods']:
                    # Extract test method content (simplified)
                    method_pattern = rf"def {test_method['name']}\(.*?\):(.*?)(?=def|\Z)"
                    method_match = re.search(method_pattern, content, re.DOTALL)
                    
                    if method_match:
                        method_content = method_match.group(1)
                        slow_score = 0
                        found_indicators = []
                        
                        for indicator in slow_indicators:
                            if re.search(indicator, method_content, re.IGNORECASE):
                                slow_score += 1
                                found_indicators.append(indicator)
                        
                        if slow_score >= 2:  # Multiple indicators
                            slow_tests.append({
                                'file': file_info['path'],
                                'method': test_method['name'],
                                'line': test_method['line'],
                                'slow_score': slow_score,
                                'indicators': found_indicators
                            })
                            
            except Exception:
                continue  # Skip files we can't analyze
        
        self.maintenance_report['slow_tests'] = slow_tests
        return slow_tests
    
    def detect_outdated_tests(self, days_threshold: int = 90) -> List[Dict[str, Any]]:
        """Detect tests that haven't been updated recently"""
        outdated = []
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        
        for file_info in self.maintenance_report['test_files']:
            if file_info['last_modified'] and file_info['last_modified'] < cutoff_date:
                # Check if file has any recent activity patterns
                try:
                    with open(file_info['path'], 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Look for outdated patterns
                    outdated_patterns = [
                        r'unittest\.TestCase',  # Old unittest style
                        r'self\.assert',  # Old assertion style
                        r'mock\.Mock\(\)',  # Old mock usage
                        r'from mock import',  # Old mock import
                    ]
                    
                    outdated_score = 0
                    for pattern in outdated_patterns:
                        if re.search(pattern, content):
                            outdated_score += 1
                    
                    if outdated_score > 0:
                        outdated.append({
                            'file': file_info['path'],
                            'last_modified': file_info['last_modified'],
                            'days_old': (datetime.now() - file_info['last_modified']).days,
                            'outdated_score': outdated_score
                        })
                        
                except Exception:
                    continue
        
        self.maintenance_report['outdated_tests'] = outdated
        return outdated
    
    def generate_maintenance_recommendations(self) -> List[str]:
        """Generate maintenance recommendations based on analysis"""
        recommendations = []
        
        # Duplicate tests
        if self.maintenance_report['duplicate_tests']:
            count = len(self.maintenance_report['duplicate_tests'])
            recommendations.append(f"Review {count} potential duplicate test groups for consolidation")
        
        # Slow tests
        if self.maintenance_report['slow_tests']:
            count = len(self.maintenance_report['slow_tests'])
            recommendations.append(f"Optimize {count} potentially slow tests")
            recommendations.append("Consider using mocks instead of real network/file operations")
        
        # Outdated tests
        if self.maintenance_report['outdated_tests']:
            count = len(self.maintenance_report['outdated_tests'])
            recommendations.append(f"Update {count} outdated test files")
            recommendations.append("Migrate from unittest to pytest style")
            recommendations.append("Update mock imports to use unittest.mock")
        
        # Large test files
        large_files = [f for f in self.maintenance_report['test_files'] if f['lines'] > 500]
        if large_files:
            recommendations.append(f"Consider splitting {len(large_files)} large test files")
        
        # Missing fixtures
        files_without_fixtures = [f for f in self.maintenance_report['test_files'] if f['fixture_count'] == 0 and f['test_count'] > 5]
        if files_without_fixtures:
            recommendations.append(f"Add fixtures to {len(files_without_fixtures)} test files for better organization")
        
        self.maintenance_report['recommendations'] = recommendations
        return recommendations


class TestCleanupManager:
    """Manages test cleanup operations"""
    
    def __init__(self):
        self.cleanup_report = {
            'files_cleaned': [],
            'space_recovered': 0,
            'errors': []
        }
    
    def cleanup_test_artifacts(self, test_root: str = "tests") -> Dict[str, Any]:
        """Clean up test artifacts and temporary files"""
        cleanup_patterns = [
            "**/__pycache__/**",
            "**/*.pyc",
            "**/*.pyo",
            "**/.*cache/**",
            "**/test_temp_*",
            "**/temp_test_*",
            "**/.coverage*",
            "**/htmlcov/**",
            "**/test-results/**",
            "**/test_output_*"
        ]
        
        files_cleaned = []
        space_recovered = 0
        
        for pattern in cleanup_patterns:
            try:
                matches = glob.glob(os.path.join(test_root, pattern), recursive=True)
                
                for match in matches:
                    try:
                        if os.path.isfile(match):
                            size = os.path.getsize(match)
                            os.remove(match)
                            files_cleaned.append(match)
                            space_recovered += size
                        elif os.path.isdir(match):
                            dir_size = self._get_directory_size(match)
                            shutil.rmtree(match)
                            files_cleaned.append(match)
                            space_recovered += dir_size
                            
                    except Exception as e:
                        self.cleanup_report['errors'].append(f"Failed to clean {match}: {e}")
                        
            except Exception as e:
                self.cleanup_report['errors'].append(f"Pattern {pattern} failed: {e}")
        
        self.cleanup_report['files_cleaned'] = files_cleaned
        self.cleanup_report['space_recovered'] = space_recovered
        
        return self.cleanup_report
    
    def _get_directory_size(self, path: str) -> int:
        """Calculate directory size recursively"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        continue
        except Exception:
            pass
        return total_size
    
    def organize_test_reports(self, reports_dir: str = "test_reports") -> Dict[str, Any]:
        """Organize test reports and remove old ones"""
        organization_report = {
            'organized_files': 0,
            'removed_files': 0,
            'errors': []
        }
        
        if not os.path.exists(reports_dir):
            return organization_report
        
        try:
            # Group reports by date
            reports_by_date = defaultdict(list)
            cutoff_date = datetime.now() - timedelta(days=30)  # Keep reports for 30 days
            
            for filename in os.listdir(reports_dir):
                filepath = os.path.join(reports_dir, filename)
                
                if os.path.isfile(filepath):
                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                        date_key = mtime.strftime('%Y-%m-%d')
                        
                        if mtime < cutoff_date:
                            # Remove old reports
                            os.remove(filepath)
                            organization_report['removed_files'] += 1
                        else:
                            reports_by_date[date_key].append(filename)
                            
                    except Exception as e:
                        organization_report['errors'].append(f"Failed to process {filename}: {e}")
            
            # Organize remaining reports by date
            for date, files in reports_by_date.items():
                date_dir = os.path.join(reports_dir, date)
                
                if not os.path.exists(date_dir):
                    os.makedirs(date_dir)
                
                for filename in files:
                    old_path = os.path.join(reports_dir, filename)
                    new_path = os.path.join(date_dir, filename)
                    
                    if old_path != new_path:  # Don't move if already in correct location
                        try:
                            shutil.move(old_path, new_path)
                            organization_report['organized_files'] += 1
                        except Exception as e:
                            organization_report['errors'].append(f"Failed to move {filename}: {e}")
                            
        except Exception as e:
            organization_report['errors'].append(f"Report organization failed: {e}")
        
        return organization_report


class TestHealthMonitor:
    """Monitors test suite health and performance"""
    
    def __init__(self):
        self.health_metrics = {
            'execution_time': {},
            'memory_usage': {},
            'failure_rates': {},
            'coverage_trends': {}
        }
    
    def measure_test_performance(self, test_command: str = "pytest tests/") -> Dict[str, Any]:
        """Measure test suite performance"""
        performance_metrics = {
            'total_time': 0,
            'test_count': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': [],
            'slow_tests': []
        }
        
        try:
            start_time = time.time()
            
            # Run tests with verbose output
            result = subprocess.run(
                test_command.split(),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            performance_metrics['total_time'] = time.time() - start_time
            
            # Parse output for metrics
            if result.stdout:
                output = result.stdout
                
                # Extract test counts
                passed_match = re.search(r'(\d+) passed', output)
                failed_match = re.search(r'(\d+) failed', output)
                skipped_match = re.search(r'(\d+) skipped', output)
                
                if passed_match:
                    performance_metrics['passed'] = int(passed_match.group(1))
                if failed_match:
                    performance_metrics['failed'] = int(failed_match.group(1))
                if skipped_match:
                    performance_metrics['skipped'] = int(skipped_match.group(1))
                
                performance_metrics['test_count'] = (
                    performance_metrics['passed'] + 
                    performance_metrics['failed'] + 
                    performance_metrics['skipped']
                )
                
                # Extract slow tests (if using pytest-benchmark or similar)
                slow_pattern = r'SLOW.*?(\w+::\w+).*?(\d+\.\d+)s'
                slow_matches = re.findall(slow_pattern, output)
                performance_metrics['slow_tests'] = [
                    {'test': match[0], 'duration': float(match[1])}
                    for match in slow_matches
                ]
            
            if result.stderr:
                performance_metrics['errors'].append(result.stderr)
                
        except subprocess.TimeoutExpired:
            performance_metrics['errors'].append("Test execution timed out")
        except Exception as e:
            performance_metrics['errors'].append(f"Performance measurement failed: {e}")
        
        return performance_metrics
    
    def check_test_dependencies(self) -> Dict[str, Any]:
        """Check for test dependency issues"""
        dependency_report = {
            'missing_imports': [],
            'version_conflicts': [],
            'unused_imports': [],
            'recommendations': []
        }
        
        # Check requirements files
        req_files = ['requirements.txt', 'requirements-dev.txt', 'test-requirements.txt']
        installed_packages = {}
        
        try:
            # Get installed packages
            result = subprocess.run(
                ['pip', 'list', '--format=json'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                packages = json.loads(result.stdout)
                installed_packages = {pkg['name'].lower(): pkg['version'] for pkg in packages}
                
        except Exception as e:
            dependency_report['recommendations'].append(f"Could not check installed packages: {e}")
        
        # Analyze test files for import issues
        test_analyzer = TestSuiteAnalyzer()
        test_files = test_analyzer.scan_test_files()
        
        all_imports = set()
        for file_info in test_files:
            all_imports.update(file_info['imports'])
        
        # Check for common missing test dependencies
        common_test_deps = [
            'pytest', 'pytest-cov', 'pytest-asyncio', 
            'pytest-mock', 'requests', 'httpx'
        ]
        
        for dep in common_test_deps:
            if dep not in installed_packages:
                dependency_report['missing_imports'].append(dep)
        
        if dependency_report['missing_imports']:
            dependency_report['recommendations'].append(
                f"Install missing test dependencies: {', '.join(dependency_report['missing_imports'])}"
            )
        
        return dependency_report


class TestMaintenanceAutomation:
    """Main test maintenance automation controller"""
    
    def __init__(self):
        self.analyzer = TestSuiteAnalyzer()
        self.cleanup_manager = TestCleanupManager()
        self.health_monitor = TestHealthMonitor()
    
    def run_full_maintenance(self) -> Dict[str, Any]:
        """Run complete test maintenance cycle"""
        maintenance_results = {
            'timestamp': datetime.now().isoformat(),
            'analysis': {},
            'cleanup': {},
            'health_check': {},
            'summary': {}
        }
        
        # Analysis phase
        print("Running test suite analysis...")
        self.analyzer.scan_test_files()
        self.analyzer.detect_duplicate_tests()
        self.analyzer.detect_slow_tests()
        self.analyzer.detect_outdated_tests()
        recommendations = self.analyzer.generate_maintenance_recommendations()
        
        maintenance_results['analysis'] = {
            'test_files': len(self.analyzer.maintenance_report['test_files']),
            'duplicates': len(self.analyzer.maintenance_report['duplicate_tests']),
            'slow_tests': len(self.analyzer.maintenance_report['slow_tests']),
            'outdated_tests': len(self.analyzer.maintenance_report['outdated_tests']),
            'recommendations': recommendations
        }
        
        # Cleanup phase
        print("Running cleanup operations...")
        cleanup_result = self.cleanup_manager.cleanup_test_artifacts()
        reports_result = self.cleanup_manager.organize_test_reports()
        
        maintenance_results['cleanup'] = {
            'files_cleaned': len(cleanup_result['files_cleaned']),
            'space_recovered_mb': cleanup_result['space_recovered'] / (1024 * 1024),
            'reports_organized': reports_result['organized_files'],
            'reports_removed': reports_result['removed_files']
        }
        
        # Health check phase
        print("Running health checks...")
        performance = self.health_monitor.measure_test_performance()
        dependencies = self.health_monitor.check_test_dependencies()
        
        maintenance_results['health_check'] = {
            'performance': performance,
            'dependencies': dependencies
        }
        
        # Summary
        maintenance_results['summary'] = {
            'total_recommendations': len(recommendations),
            'cleanup_successful': len(cleanup_result['errors']) == 0,
            'health_score': self._calculate_health_score(maintenance_results)
        }
        
        return maintenance_results
    
    def _calculate_health_score(self, results: Dict[str, Any]) -> float:
        """Calculate overall test suite health score"""
        score = 100.0
        
        # Deduct for issues
        analysis = results.get('analysis', {})
        score -= analysis.get('duplicates', 0) * 2  # -2 per duplicate group
        score -= analysis.get('slow_tests', 0) * 1   # -1 per slow test
        score -= analysis.get('outdated_tests', 0) * 1  # -1 per outdated test
        
        # Deduct for cleanup issues
        cleanup = results.get('cleanup', {})
        if not cleanup.get('cleanup_successful', True):
            score -= 10
        
        # Deduct for health issues
        health = results.get('health_check', {})
        if health.get('dependencies', {}).get('missing_imports'):
            score -= len(health['dependencies']['missing_imports']) * 5
        
        return max(0.0, min(100.0, score))


class TestTestMaintenanceAutomation:
    """Test Maintenance Automation Test Suite"""
    
    @pytest.fixture(autouse=True)
    def setup(self, enhanced_mock_objects):
        """Setup for maintenance tests"""
        self.maintenance_system = TestMaintenanceAutomation()
        self.enhanced_mock_objects = enhanced_mock_objects
    
    def test_test_suite_analysis(self):
        """Test test suite analysis functionality"""
        analyzer = TestSuiteAnalyzer(test_root="tests")
        
        # Scan test files
        test_files = analyzer.scan_test_files()
        
        # Should find test files
        assert len(test_files) > 0, "No test files found"
        
        # Check file analysis
        for file_info in test_files:
            assert 'path' in file_info
            assert 'name' in file_info
            assert 'test_count' in file_info
            assert file_info['test_count'] >= 0
        
        # At least some files should have tests
        total_tests = sum(f['test_count'] for f in test_files)
        assert total_tests > 0, "No tests found in test files"
    
    def test_duplicate_detection(self):
        """Test duplicate test detection"""
        analyzer = TestSuiteAnalyzer(test_root="tests")
        analyzer.scan_test_files()
        
        # Detect duplicates
        duplicates = analyzer.detect_duplicate_tests()
        
        # Should return a list (may be empty)
        assert isinstance(duplicates, list)
        
        # If duplicates found, they should have proper structure
        for duplicate in duplicates:
            assert 'signature' in duplicate
            assert 'count' in duplicate
            assert 'tests' in duplicate
            assert duplicate['count'] >= 2
    
    def test_slow_test_detection(self):
        """Test slow test detection"""
        analyzer = TestSuiteAnalyzer(test_root="tests")
        analyzer.scan_test_files()
        
        # Detect slow tests
        slow_tests = analyzer.detect_slow_tests()
        
        # Should return a list
        assert isinstance(slow_tests, list)
        
        # Check structure of slow test entries
        for slow_test in slow_tests:
            assert 'file' in slow_test
            assert 'method' in slow_test
            assert 'slow_score' in slow_test
            assert slow_test['slow_score'] > 0
    
    def test_outdated_test_detection(self):
        """Test outdated test detection"""
        analyzer = TestSuiteAnalyzer(test_root="tests")
        analyzer.scan_test_files()
        
        # Detect outdated tests
        outdated_tests = analyzer.detect_outdated_tests(days_threshold=30)
        
        # Should return a list
        assert isinstance(outdated_tests, list)
        
        # Check structure of outdated test entries
        for outdated_test in outdated_tests:
            assert 'file' in outdated_test
            assert 'last_modified' in outdated_test
            assert 'days_old' in outdated_test
    
    def test_maintenance_recommendations(self):
        """Test maintenance recommendation generation"""
        analyzer = TestSuiteAnalyzer(test_root="tests")
        analyzer.scan_test_files()
        analyzer.detect_duplicate_tests()
        analyzer.detect_slow_tests()
        analyzer.detect_outdated_tests()
        
        # Generate recommendations
        recommendations = analyzer.generate_maintenance_recommendations()
        
        # Should return a list of strings
        assert isinstance(recommendations, list)
        for rec in recommendations:
            assert isinstance(rec, str)
            assert len(rec) > 10  # Should be meaningful recommendations
    
    def test_cleanup_operations(self):
        """Test cleanup operations"""
        cleanup_manager = TestCleanupManager()
        
        # Create temporary test artifacts
        temp_dir = tempfile.mkdtemp(prefix="test_cleanup_")
        
        try:
            # Create some test artifacts
            test_artifacts = [
                os.path.join(temp_dir, '__pycache__', 'test.pyc'),
                os.path.join(temp_dir, 'test_temp_file.txt'),
                os.path.join(temp_dir, '.coverage'),
            ]
            
            for artifact in test_artifacts:
                os.makedirs(os.path.dirname(artifact), exist_ok=True)
                with open(artifact, 'w') as f:
                    f.write("test content")
            
            # Run cleanup
            cleanup_result = cleanup_manager.cleanup_test_artifacts(temp_dir)
            
            # Check cleanup results
            assert 'files_cleaned' in cleanup_result
            assert 'space_recovered' in cleanup_result
            assert isinstance(cleanup_result['files_cleaned'], list)
            assert cleanup_result['space_recovered'] >= 0
            
        finally:
            # Clean up test directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    def test_health_monitoring(self):
        """Test health monitoring functionality"""
        health_monitor = TestHealthMonitor()
        
        # Test dependency checking
        dependency_report = health_monitor.check_test_dependencies()
        
        # Should return proper structure
        assert 'missing_imports' in dependency_report
        assert 'version_conflicts' in dependency_report
        assert 'recommendations' in dependency_report
        
        assert isinstance(dependency_report['missing_imports'], list)
        assert isinstance(dependency_report['recommendations'], list)
    
    def test_full_maintenance_cycle(self):
        """Test complete maintenance automation cycle"""
        # Run full maintenance (with mocked subprocess calls to avoid actual execution)
        with patch('subprocess.run') as mock_run:
            # Mock successful pytest run
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "5 passed, 1 failed, 0 skipped"
            mock_run.return_value.stderr = ""
            
            maintenance_results = self.maintenance_system.run_full_maintenance()
        
        # Check structure of results
        required_sections = ['timestamp', 'analysis', 'cleanup', 'health_check', 'summary']
        for section in required_sections:
            assert section in maintenance_results, f"Missing section: {section}"
        
        # Check analysis section
        analysis = maintenance_results['analysis']
        assert 'test_files' in analysis
        assert 'recommendations' in analysis
        assert isinstance(analysis['recommendations'], list)
        
        # Check cleanup section
        cleanup = maintenance_results['cleanup']
        assert 'files_cleaned' in cleanup
        assert 'space_recovered_mb' in cleanup
        
        # Check summary
        summary = maintenance_results['summary']
        assert 'health_score' in summary
        assert 0 <= summary['health_score'] <= 100
    
    def test_maintenance_error_handling(self):
        """Test error handling in maintenance operations"""
        # Test with non-existent directory
        analyzer = TestSuiteAnalyzer(test_root="non_existent_dir")
        test_files = analyzer.scan_test_files()
        
        # Should handle gracefully
        assert isinstance(test_files, list)
        assert len(test_files) == 0
        
        # Test cleanup with invalid path
        cleanup_manager = TestCleanupManager()
        cleanup_result = cleanup_manager.cleanup_test_artifacts("invalid_path")
        
        # Should handle gracefully
        assert 'files_cleaned' in cleanup_result
        assert 'errors' in cleanup_result
    
    def test_performance_measurement(self):
        """Test performance measurement functionality"""
        health_monitor = TestHealthMonitor()
        
        # Mock subprocess for performance measurement
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "10 passed, 2 failed, 1 skipped in 5.32s"
            mock_run.return_value.stderr = ""
            
            performance = health_monitor.measure_test_performance("pytest tests/")
        
        # Check performance metrics
        assert 'total_time' in performance
        assert 'test_count' in performance
        assert 'passed' in performance
        assert 'failed' in performance
        assert 'skipped' in performance
        
        # Values should be reasonable
        assert performance['passed'] >= 0
        assert performance['failed'] >= 0
        assert performance['skipped'] >= 0