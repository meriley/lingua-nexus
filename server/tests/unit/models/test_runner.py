#!/usr/bin/env python3
"""
Simple test runner for model unit tests.

This script runs the model unit tests without requiring the full server environment.
"""

import sys
import os
import subprocess
import tempfile
from pathlib import Path

def run_model_tests():
    """Run model unit tests with minimal dependencies."""
    
    # Get the project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    server_path = project_root / "server"
    
    # Set up minimal environment
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root)
    
    # Create a temporary conftest that doesn't import server dependencies
    temp_conftest = """
import pytest
import sys
import os
from unittest.mock import Mock, patch

# Add models to path
models_path = os.path.join(os.path.dirname(__file__), '../../../../..')
if models_path not in sys.path:
    sys.path.insert(0, models_path)

@pytest.fixture(autouse=True)
def mock_dependencies():
    '''Mock heavy dependencies that aren't needed for unit tests.'''
    with patch('torch.cuda.is_available', return_value=False):
        with patch('transformers.AutoModelForSeq2SeqLM'):
            with patch('transformers.AutoTokenizer'):
                with patch('transformers.pipeline'):
                    yield
"""
    
    tests_dir = server_path / "tests" / "unit" / "models"
    
    # Write temporary conftest
    temp_conftest_path = tests_dir / "conftest_temp.py"
    with open(temp_conftest_path, 'w') as f:
        f.write(temp_conftest)
    
    try:
        # Run each test file individually
        test_files = [
            "test_base_interface.py",
            "test_aya_expanse_8b.py", 
            "test_nllb.py"
        ]
        
        results = {}
        for test_file in test_files:
            test_path = tests_dir / test_file
            if test_path.exists():
                print(f"\n{'='*60}")
                print(f"Running {test_file}")
                print(f"{'='*60}")
                
                # Run pytest with minimal configuration
                cmd = [
                    sys.executable, "-m", "pytest", 
                    str(test_path),
                    "--tb=short",
                    "-v",
                    f"--confcutdir={tests_dir}",
                    "--no-header"
                ]
                
                result = subprocess.run(
                    cmd, 
                    cwd=str(tests_dir),
                    env=env,
                    capture_output=True,
                    text=True
                )
                
                results[test_file] = {
                    'returncode': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
                
                print(result.stdout)
                if result.stderr:
                    print("STDERR:", result.stderr)
                
                if result.returncode == 0:
                    print(f"✅ {test_file} PASSED")
                else:
                    print(f"❌ {test_file} FAILED")
            else:
                print(f"⚠️  {test_file} not found")
                results[test_file] = {'returncode': -1, 'stdout': '', 'stderr': 'File not found'}
        
        # Summary
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        
        passed = sum(1 for r in results.values() if r['returncode'] == 0)
        total = len([r for r in results.values() if r['returncode'] != -1])
        
        for test_file, result in results.items():
            if result['returncode'] == -1:
                status = "NOT FOUND"
            elif result['returncode'] == 0:
                status = "PASSED"
            else:
                status = "FAILED"
            print(f"{test_file:<30} {status}")
        
        print(f"\nResults: {passed}/{total} tests passed")
        
        return passed == total
        
    finally:
        # Cleanup temporary conftest
        if temp_conftest_path.exists():
            temp_conftest_path.unlink()


if __name__ == "__main__":
    success = run_model_tests()
    sys.exit(0 if success else 1)