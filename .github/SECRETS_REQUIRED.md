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
