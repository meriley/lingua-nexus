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
