#!/usr/bin/env python3
"""
Test runner script that fixes Python path issues for comprehensive testing.
"""
import os
import sys
import subprocess

def main():
    """Run all tests with proper Python path configuration."""
    
    # Set the project root for imports
    project_root = os.path.abspath(os.path.dirname(__file__))
    
    # Set environment variables
    env = os.environ.copy()
    env['PYTHONPATH'] = project_root
    
    # Change to server directory for pytest
    server_dir = os.path.join(project_root, 'server')
    os.chdir(server_dir)
    
    # Run pytest with proper configuration
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/',
        '--tb=short',
        '-v',
        '--maxfail=10'  # Stop after 10 failures to avoid overwhelming output
    ]
    
    print(f"Running tests from: {server_dir}")
    print(f"PYTHONPATH: {project_root}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    # Execute pytest
    result = subprocess.run(cmd, env=env)
    return result.returncode

if __name__ == '__main__':
    sys.exit(main())