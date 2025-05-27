# Multi-Model Test Strategy

## Overview

This document outlines the testing strategy for the multi-model translation system following the refactoring to comply with proper testing pyramid principles.

## Test Organization

### 1. End-to-End Tests (E2E)
**Location**: `tests/e2e/test_multimodel_e2e_refactored.py`

- **NO MOCKS ALLOWED** - Tests use real models and complete system
- Tests real API interactions with actual ML models
- Marked with `@pytest.mark.slow` for CI/CD configuration
- Uses session-scoped fixtures for model caching
- Validates system behavior without asserting exact translations

**Key Tests**:
- Service startup with real models
- Translation workflows with flexible validation
- Language detection
- Batch processing
- Error handling
- Concurrent request handling

### 2. Integration Tests
**Location**: `tests/e2e/test_multimodel_integration.py`

- May use selective mocking for performance
- Tests component interactions
- Marked with `@pytest.mark.integration`
- Focus on API contracts and system integration

**Key Tests**:
- Model switching with mocked models
- Performance benchmarks with controlled timing
- Complex workflows with predictable outcomes

### 3. Unit Tests
**Location**: `server/tests/unit/`

- Fully mocked dependencies
- Test individual components in isolation
- Fast execution
- High code coverage

## Test Data Management

**File**: `tests/e2e/test_data.py`

Provides flexible test data that:
- Doesn't require exact translation matches
- Validates based on keywords, length, or patterns
- Supports multiple test scenarios
- Enables consistent test behavior

## Performance Optimization

### Model Caching
- Session-scoped fixtures cache models across tests
- Environment variable `MODEL_CACHE_DIR` for persistent caching
- `E2E_USE_TEST_MODELS=true` signals to use smaller models

### Test Execution
- Parallel test execution where possible
- Separate CI/CD workflows for fast vs. comprehensive tests
- Timeout configuration for long-running tests

## CI/CD Configuration

### Test Profiles

1. **Fast Tests** (Unit + Integration)
   ```bash
   pytest -m "not slow"
   ```
   - Runs on every push/PR
   - < 5 minutes execution time
   - No real model loading

2. **Full E2E Tests**
   ```bash
   pytest -m "slow"
   ```
   - Runs on main branch commits
   - Uses real models
   - < 30 minutes execution time

3. **Nightly Full Suite**
   - Comprehensive test coverage
   - All test levels
   - Performance benchmarks

## Guidelines for New Tests

### E2E Tests
1. Never import server code directly
2. Use HTTP client for all interactions
3. Don't assert exact translations
4. Focus on system behavior and contracts
5. Mark with `@pytest.mark.slow`

### Integration Tests
1. Mock only external dependencies
2. Test component interactions
3. Use controlled test data
4. Mark with `@pytest.mark.integration`

### Unit Tests
1. Mock all dependencies
2. Test edge cases thoroughly
3. Aim for high code coverage
4. Keep tests fast and isolated

## Running Tests

```bash
# Run all E2E tests (with real models)
pytest tests/e2e/test_multimodel_e2e_refactored.py -v -m slow

# Run integration tests
pytest tests/e2e/test_multimodel_integration.py -v

# Run fast tests only
pytest -m "not slow"

# Run specific test
pytest tests/e2e/test_multimodel_e2e_refactored.py::TestMultiModelE2E::test_nllb_translation_workflow -v
```

## Environment Variables

- `E2E_USE_TEST_MODELS`: Use lightweight models for E2E tests
- `MODEL_CACHE_DIR`: Directory for caching downloaded models
- `PYTEST_RUNNING`: Signal to service that tests are running
- `TEST_TIMEOUT`: Maximum time for test execution

## Success Metrics

1. **No mocks in E2E tests** ✅
2. **All tests pass** (target: 100%)
3. **E2E suite < 5 minutes** (with test models)
4. **Clear test organization** ✅
5. **CI/CD friendly** ✅

## Future Improvements

1. Add visual regression tests for UI components
2. Implement contract testing between services
3. Add chaos engineering tests for resilience
4. Expand performance benchmarking suite
5. Add multilingual test coverage