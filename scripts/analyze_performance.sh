#!/bin/bash

# Performance Analysis Script
# Analyzes test reports and detects regressions

set -e

REPORTS_DIR="test_reports"
BASELINES_DIR="performance_baselines"
OUTPUT_FILE="performance_analysis.txt"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --reports-dir)
            REPORTS_DIR="$2"
            shift 2
            ;;
        --baselines-dir)
            BASELINES_DIR="$2"
            shift 2
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=== Performance Analysis ==="
echo "Reports Directory: $REPORTS_DIR"
echo "Baselines Directory: $BASELINES_DIR"
echo "Output File: $OUTPUT_FILE"
echo

# Find performance report files
REPORT_FILES=$(find "$REPORTS_DIR" -name "*.json" -type f 2>/dev/null || true)

if [ -z "$REPORT_FILES" ]; then
    echo "No performance reports found in $REPORTS_DIR"
    exit 0
fi

echo "Found performance reports:"
echo "$REPORT_FILES"
echo

# Run regression detection
python3 scripts/performance_regression_detector.py \
    --baseline-dir "$BASELINES_DIR" \
    --output "$OUTPUT_FILE" \
    $REPORT_FILES

echo "Analysis complete. Results saved to $OUTPUT_FILE"
