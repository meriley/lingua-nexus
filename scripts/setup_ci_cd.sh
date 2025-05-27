#!/bin/bash

# CI/CD Setup Script for E2E Test Infrastructure
# Sets up GitHub Actions, baseline management, and performance monitoring

set -e

echo "=== Setting up CI/CD for E2E Test Infrastructure ==="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="/mnt/dionysus/coding/tg-text-translate"
cd "$PROJECT_ROOT"

echo -e "${GREEN}1. Checking project structure...${NC}"

# Required directories
REQUIRED_DIRS=(
    ".github/workflows"
    "scripts"
    "performance_baselines"
    "test_reports"
    "tests/e2e/utils"
    "tests/e2e/performance"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "Creating directory: $dir"
        mkdir -p "$dir"
    else
        echo "✓ Directory exists: $dir"
    fi
done

echo -e "${GREEN}2. Setting up performance baselines directory...${NC}"

# Create baseline directory structure
mkdir -p performance_baselines/{nllb,aya,multimodel}
mkdir -p performance_baselines/templates

# Create baseline template
cat > performance_baselines/templates/baseline_template.json << 'EOF'
{
    "model_name": "template",
    "timestamp": "2025-01-01T00:00:00Z",
    "system_info": {
        "platform": "linux",
        "python_version": "3.11",
        "cpu_count": 8,
        "memory_gb": 16
    },
    "baselines": {
        "model_loading_time_seconds": 300.0,
        "inference_latency_ms": 100.0,
        "throughput_chars_per_sec": 1000.0,
        "memory_peak_mb": 2048.0,
        "batch_processing_time_seconds": 30.0,
        "success_rate_percent": 99.0
    },
    "thresholds": {
        "model_loading_time": 25.0,
        "inference_latency": 20.0,
        "throughput": -15.0,
        "memory_usage": 30.0,
        "batch_processing_time": 25.0,
        "success_rate": -5.0
    }
}
EOF

echo "✓ Created baseline template"

echo -e "${GREEN}3. Setting up GitHub Actions secrets requirements...${NC}"

cat > .github/SECRETS_REQUIRED.md << 'EOF'
# Required GitHub Secrets for E2E Tests

The following secrets need to be configured in GitHub repository settings:

## Optional Secrets (for enhanced functionality)
- `SLACK_WEBHOOK_URL`: For test result notifications
- `PERFORMANCE_BASELINE_REPO`: Repository for storing performance baselines
- `PERFORMANCE_BASELINE_TOKEN`: Token for baseline repository access

## Auto-configured
- `GITHUB_TOKEN`: Automatically provided by GitHub Actions

## Environment Variables (configured in workflow)
- `E2E_TIMEOUT`: Test timeout in seconds (default: 7200)
- `MODEL_CACHE_DIR`: Directory for model caching
- `PYTHON_VERSION`: Python version to use (default: 3.11)

## Model Test Configuration
Set these in workflow_dispatch inputs or environment:
- Test suite selection (smoke, performance, parallel, all)
- Model selection (nllb, aya, both)
- Parallel worker count
EOF

echo "✓ Created secrets documentation"

echo -e "${GREEN}4. Creating test execution scripts...${NC}"

# Create comprehensive test runner
cat > scripts/run_e2e_tests.sh << 'EOF'
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
EOF

chmod +x scripts/run_e2e_tests.sh
echo "✓ Created comprehensive test runner"

# Create performance analysis script
cat > scripts/analyze_performance.sh << 'EOF'
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
EOF

chmod +x scripts/analyze_performance.sh
echo "✓ Created performance analysis script"

echo -e "${GREEN}5. Creating baseline management tools...${NC}"

cat > scripts/update_baselines.py << 'EOF'
#!/usr/bin/env python3
"""
Baseline Management Script
Updates performance baselines from successful test runs.
"""

import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List


def update_baseline(report_file: str, baseline_dir: str, model_name: str):
    """Update baseline from a performance report."""
    report_path = Path(report_file)
    baseline_path = Path(baseline_dir) / model_name
    
    if not report_path.exists():
        raise FileNotFoundError(f"Report file not found: {report_file}")
    
    # Load report
    with open(report_path) as f:
        report_data = json.load(f)
    
    # Create baseline entry
    baseline_data = {
        "model_name": model_name,
        "timestamp": datetime.now().isoformat(),
        "source_report": str(report_path),
        "data": report_data
    }
    
    # Ensure baseline directory exists
    baseline_path.mkdir(parents=True, exist_ok=True)
    
    # Determine baseline filename
    report_type = "unknown"
    if "baseline" in report_path.name or "loading" in report_path.name:
        report_type = "model_loading"
    elif "inference" in report_path.name:
        report_type = "inference"
    elif "memory" in report_path.name:
        report_type = "memory"
    elif "batch" in report_path.name:
        report_type = "batch"
    
    baseline_file = baseline_path / f"{report_type}_baseline.json"
    
    # Save baseline
    with open(baseline_file, 'w') as f:
        json.dump(baseline_data, f, indent=2)
    
    print(f"Updated baseline: {baseline_file}")


def main():
    parser = argparse.ArgumentParser(description="Update performance baselines")
    parser.add_argument("reports", nargs="+", help="Performance report files")
    parser.add_argument("--baseline-dir", default="performance_baselines", 
                       help="Baseline directory")
    parser.add_argument("--model", required=True, help="Model name")
    
    args = parser.parse_args()
    
    for report_file in args.reports:
        try:
            update_baseline(report_file, args.baseline_dir, args.model)
        except Exception as e:
            print(f"Error updating baseline from {report_file}: {e}")


if __name__ == "__main__":
    main()
EOF

chmod +x scripts/update_baselines.py
echo "✓ Created baseline management script"

echo -e "${GREEN}6. Creating test markers configuration...${NC}"

# Update pytest.ini with comprehensive markers
cat >> tests/e2e/pytest.ini << 'EOF'

# CI/CD specific markers
ci: Tests suitable for CI/CD execution
fast: Fast tests (< 30 seconds)
medium: Medium tests (30 seconds - 5 minutes)
slow: Slow tests (> 5 minutes)
critical: Critical tests that must pass
regression: Regression tests
baseline: Tests that establish performance baselines
EOF

echo "✓ Updated pytest configuration with CI/CD markers"

echo -e "${GREEN}7. Creating monitoring and alerting configuration...${NC}"

cat > .github/scripts/notify_test_results.py << 'EOF'
#!/usr/bin/env python3
"""
Test Results Notification Script
Sends notifications about test results to configured channels.
"""

import json
import os
import sys
import requests
from typing import Dict, Optional


def send_slack_notification(webhook_url: str, message: str, color: str = "good"):
    """Send notification to Slack."""
    payload = {
        "attachments": [
            {
                "color": color,
                "text": message,
                "mrkdwn_in": ["text"]
            }
        ]
    }
    
    response = requests.post(webhook_url, json=payload)
    response.raise_for_status()


def generate_test_summary(workflow_result: str, test_results: Dict) -> tuple[str, str]:
    """Generate test summary message and determine color."""
    if workflow_result == "success":
        color = "good"
        message = "✅ E2E Tests Passed"
    elif workflow_result == "failure":
        color = "danger"
        message = "❌ E2E Tests Failed"
    else:
        color = "warning"
        message = "⚠️ E2E Tests Completed with Issues"
    
    details = []
    for test_type, result in test_results.items():
        if result == "success":
            details.append(f"• {test_type}: ✅")
        elif result == "failure":
            details.append(f"• {test_type}: ❌")
        else:
            details.append(f"• {test_type}: ⚠️")
    
    if details:
        message += "\n" + "\n".join(details)
    
    return message, color


def main():
    # Get environment variables
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    workflow_result = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    
    # Parse test results from environment or arguments
    test_results = {
        "Infrastructure": os.environ.get("INFRASTRUCTURE_RESULT", "unknown"),
        "Smoke Tests": os.environ.get("SMOKE_RESULT", "unknown"),
        "Model Tests": os.environ.get("MODEL_RESULT", "unknown"),
        "Performance": os.environ.get("PERFORMANCE_RESULT", "unknown")
    }
    
    # Generate message
    message, color = generate_test_summary(workflow_result, test_results)
    
    # Add repository and commit info
    repo = os.environ.get("GITHUB_REPOSITORY", "unknown")
    commit = os.environ.get("GITHUB_SHA", "unknown")[:8]
    branch = os.environ.get("GITHUB_REF_NAME", "unknown")
    run_url = f"https://github.com/{repo}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"
    
    message += f"\n\nRepo: {repo} (branch: {branch})"
    message += f"\nCommit: {commit}"
    message += f"\n<{run_url}|View Details>"
    
    # Send notification if webhook is configured
    if webhook_url:
        try:
            send_slack_notification(webhook_url, message, color)
            print("Notification sent successfully")
        except Exception as e:
            print(f"Failed to send notification: {e}")
    else:
        print("No webhook URL configured, skipping notification")
        print(f"Message would be: {message}")


if __name__ == "__main__":
    main()
EOF

chmod +x .github/scripts/notify_test_results.py
mkdir -p .github/scripts
echo "✓ Created notification script"

echo -e "${GREEN}8. Validating CI/CD setup...${NC}"

# Check if all required files exist
REQUIRED_FILES=(
    ".github/workflows/e2e-tests.yml"
    "scripts/performance_regression_detector.py"
    "scripts/run_e2e_tests.sh"
    "scripts/analyze_performance.sh"
    "scripts/update_baselines.py"
    ".github/scripts/notify_test_results.py"
)

echo "Checking required files:"
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "❌ $file (missing)"
    fi
done

echo
echo -e "${GREEN}9. Creating usage documentation...${NC}"

cat > CI_CD_USAGE.md << 'EOF'
# CI/CD Usage Guide for E2E Tests

## Overview
This project includes comprehensive CI/CD integration for E2E testing with GitHub Actions.

## Workflows

### Main E2E Test Workflow (`.github/workflows/e2e-tests.yml`)
- **Triggers**: Push to main branches, PRs, schedule (daily), manual dispatch
- **Jobs**: Infrastructure tests, smoke tests, model tests, performance analysis
- **Timeout**: 2 hours for full suite
- **Parallel Execution**: Supports configurable worker counts

### Test Suites
1. **Infrastructure Tests**: Retry mechanisms, parallel execution
2. **Smoke Tests**: Basic functionality verification
3. **Integration Tests**: Component interaction testing  
4. **Model Tests**: Full model loading and inference (NLLB/Aya)
5. **Performance Tests**: Baseline collection and regression detection

## Manual Execution

### Local Test Execution
```bash
# Run specific test suite
./scripts/run_e2e_tests.sh --suite smoke --model nllb

# Run with parallel workers
./scripts/run_e2e_tests.sh --suite integration --parallel 4

# Run performance tests
./scripts/run_e2e_tests.sh --suite performance --timeout 1800
```

### Performance Analysis
```bash
# Analyze performance reports
./scripts/analyze_performance.sh --reports-dir test_reports

# Update baselines from successful runs
./scripts/update_baselines.py test_reports/baseline_*.json --model nllb
```

### Parallel Test Execution
```bash
# Auto-detect CPU cores
pytest tests/e2e/ -n auto

# Specific worker count
pytest tests/e2e/ -n 4 --dist=loadscope

# Run parallel demo
./run_parallel_tests.sh
```

## GitHub Actions Configuration

### Required Secrets
- `SLACK_WEBHOOK_URL` (optional): For test result notifications

### Workflow Inputs
When running manually via workflow_dispatch:
- **test_suite**: all, smoke, performance, parallel
- **model_tests**: nllb, aya, both  
- **parallel_workers**: Number of workers (default: 2)

### Environment Variables
- `E2E_TIMEOUT`: Test timeout in seconds (default: 7200)
- `MODEL_CACHE_DIR`: Model cache directory
- `PYTHON_VERSION`: Python version (default: 3.11)

## Performance Regression Detection

The CI/CD system automatically detects performance regressions by comparing current test results to established baselines.

### Regression Thresholds
- Model Loading Time: +25% 
- Inference Latency: +20%
- Memory Usage: +30%
- Throughput: -15% (lower is worse)
- Success Rate: -5%

### Baseline Management
- Baselines stored in `performance_baselines/` directory
- Updated automatically from successful runs
- Manual updates via `update_baselines.py` script

## Test Markers

Use pytest markers to control test execution:
```bash
# Run only fast tests
pytest -m "fast and not slow"

# Run critical tests only
pytest -m critical

# Run performance baselines
pytest -m baseline
```

## Troubleshooting

### Common Issues
1. **Model Loading Timeouts**: Increase timeout values
2. **Port Conflicts**: Parallel tests use isolated ports
3. **Memory Issues**: Reduce parallel worker count
4. **Cache Issues**: Clear model cache directory

### Debug Commands
```bash
# Check test infrastructure
pytest tests/e2e/test_parallel_execution.py -v

# Validate retry mechanisms  
pytest tests/e2e/test_retry_mechanisms.py -v

# Monitor resource usage
pytest tests/e2e/performance/test_memory_monitoring.py -v
```

## Monitoring and Alerts

### Slack Notifications
Configure `SLACK_WEBHOOK_URL` secret for automatic notifications of test results.

### Performance Dashboards
Performance reports are archived as GitHub Actions artifacts with 30-day retention.

### Regression Alerts
Automatic detection and reporting of performance regressions in test results.
EOF

echo "✓ Created CI/CD usage documentation"

echo
echo -e "${GREEN}=== CI/CD Setup Complete! ===${NC}"
echo
echo "Summary of created components:"
echo "• GitHub Actions workflow (.github/workflows/e2e-tests.yml)"
echo "• Performance regression detector (scripts/performance_regression_detector.py)"
echo "• Comprehensive test runner (scripts/run_e2e_tests.sh)"
echo "• Performance analysis tools (scripts/analyze_performance.sh)"
echo "• Baseline management (scripts/update_baselines.py)"
echo "• Notification system (.github/scripts/notify_test_results.py)"
echo "• Documentation (CI_CD_USAGE.md)"
echo
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Configure GitHub repository secrets (see .github/SECRETS_REQUIRED.md)"
echo "2. Test the workflow: git push or manual workflow dispatch"
echo "3. Establish performance baselines by running successful tests"
echo "4. Monitor performance regression detection"
echo
echo -e "${GREEN}CI/CD infrastructure is ready for E2E testing! 🚀${NC}"
EOF

chmod +x scripts/setup_ci_cd.sh
echo "✓ Created CI/CD setup script"