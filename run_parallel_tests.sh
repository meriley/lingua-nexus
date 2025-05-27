#!/bin/bash

# Parallel Test Execution Script for E2E Tests
# Demonstrates different parallel execution modes

echo "=== E2E Test Parallel Execution Demo ==="
echo

# Check if pytest-xdist is available
if ! python -c "import xdist" 2>/dev/null; then
    echo "Installing pytest-xdist for parallel execution..."
    pip install pytest-xdist
fi

cd /mnt/dionysus/coding/tg-text-translate

echo "1. Testing parallel execution framework..."
python -m pytest tests/e2e/test_parallel_execution.py -v --tb=short

echo
echo "2. Running retry mechanism tests in parallel (2 workers)..."
python -m pytest tests/e2e/test_retry_mechanisms.py -n 2 -v --tb=short

echo
echo "3. Running memory monitoring tests in parallel (auto workers)..."
python -m pytest tests/e2e/performance/test_memory_monitoring.py -n auto -v --tb=short

echo
echo "=== Parallel Execution Complete ==="
echo
echo "Available parallel options:"
echo "  -n auto          # Auto-detect number of CPU cores"
echo "  -n 4             # Use 4 parallel workers"
echo "  --dist=loadscope # Distribute tests by scope (class/module)"
echo "  --dist=loadfile  # Distribute tests by file"
echo "  --dist=worksteal # Work-stealing distribution"
echo
echo "Example usage:"
echo "  pytest tests/e2e/ -n auto --dist=loadscope"
echo "  pytest tests/e2e/performance/ -n 4"