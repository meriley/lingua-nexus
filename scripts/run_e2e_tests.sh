#!/bin/bash

# Comprehensive E2E Test Runner
# Supports various test configurations and parallel execution

set -e

# Default values
TEST_SUITE="smoke"
MODEL_TYPE="nllb"
PARALLEL_WORKERS="1"
TIMEOUT="300"
OUTPUT_DIR="test_reports"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --suite)
            TEST_SUITE="$2"
            shift 2
            ;;
        --model)
            MODEL_TYPE="$2"
            shift 2
            ;;
        --parallel)
            PARALLEL_WORKERS="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --suite SUITE       Test suite: smoke, integration, performance, all"
            echo "  --model MODEL       Model type: nllb, aya, both"
            echo "  --parallel N        Number of parallel workers"
            echo "  --timeout SECONDS   Test timeout"
            echo "  --output-dir DIR    Output directory for reports"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=== E2E Test Execution ==="
echo "Suite: $TEST_SUITE"
echo "Model: $MODEL_TYPE"
echo "Parallel Workers: $PARALLEL_WORKERS"
echo "Timeout: $TIMEOUT seconds"
echo "Output Directory: $OUTPUT_DIR"
echo

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Export environment variables
export E2E_TIMEOUT="$TIMEOUT"
export E2E_OUTPUT_DIR="$OUTPUT_DIR"

# Change to server directory
cd server

# Run tests based on suite
case $TEST_SUITE in
    smoke)
        echo "Running smoke tests..."
        python -m pytest ../tests/e2e/ -m smoke -v --tb=short --timeout="$TIMEOUT"
        ;;
    integration)
        echo "Running integration tests..."
        if [ "$PARALLEL_WORKERS" -gt 1 ]; then
            python -m pytest ../tests/e2e/ -m "not slow and not performance" -n "$PARALLEL_WORKERS" -v --tb=short --timeout="$TIMEOUT"
        else
            python -m pytest ../tests/e2e/ -m "not slow and not performance" -v --tb=short --timeout="$TIMEOUT"
        fi
        ;;
    performance)
        echo "Running performance tests..."
        python -m pytest ../tests/e2e/performance/ -v --tb=short --timeout="$TIMEOUT"
        ;;
    all)
        echo "Running all test suites..."
        # Run in sequence to avoid resource conflicts
        $0 --suite smoke --model "$MODEL_TYPE" --timeout "$TIMEOUT" --output-dir "$OUTPUT_DIR"
        $0 --suite integration --model "$MODEL_TYPE" --parallel "$PARALLEL_WORKERS" --timeout "$TIMEOUT" --output-dir "$OUTPUT_DIR"
        $0 --suite performance --model "$MODEL_TYPE" --timeout "$TIMEOUT" --output-dir "$OUTPUT_DIR"
        ;;
    *)
        echo "Unknown test suite: $TEST_SUITE"
        exit 1
        ;;
esac

echo "=== Test Execution Complete ==="
