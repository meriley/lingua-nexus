# Multi-Model Translation E2E Tests

This directory contains comprehensive end-to-end tests for the multi-model translation system, verifying the complete functionality from API endpoints to model integration.

## 🏗️ Test Architecture

### Test Structure
```
tests/e2e/
├── test_multimodel_e2e.py           # Main E2E test suite
├── test_multimodel_workflows.py     # Workflow integration tests
├── utils/
│   ├── service_manager.py           # Service lifecycle management
│   ├── multimodel_http_client.py    # Enhanced HTTP client
│   ├── test_reporter.py             # Test result reporting
│   ├── performance_monitor.py       # Performance monitoring
│   └── debug_helpers.py             # Debugging utilities
├── pytest.ini                       # Test configuration
└── README_multimodel.md             # This file
```

### Test Coverage

#### ✅ Core Functionality
- **Service Startup & Health**: Service initialization and health monitoring
- **Model Management**: Loading, unloading, and switching between models
- **Translation Workflows**: Single and batch translation requests
- **Language Support**: Language detection and support queries
- **Error Handling**: Comprehensive error scenario testing

#### ✅ Multi-Model Features
- **NLLB Integration**: Facebook NLLB model functionality
- **Aya Expanse Integration**: Cohere Aya Expanse 8B model functionality
- **Model Switching**: Dynamic switching between translation models
- **Auto Language Detection**: Automatic source language detection
- **Batch Processing**: Multi-request batch translation

#### ✅ API Compatibility
- **REST API Endpoints**: All multi-model API endpoints
- **Legacy Compatibility**: Backward compatibility with original API
- **Authentication**: API key authentication and security
- **Rate Limiting**: Request rate limiting and throttling

#### ✅ Performance & Reliability
- **Performance Benchmarks**: Response time and throughput testing
- **Concurrent Requests**: Multi-threaded request handling
- **Service Recovery**: Failure recovery and resilience testing
- **Memory Management**: Resource usage and cleanup verification

## 🚀 Running E2E Tests

### Prerequisites
```bash
# Install dependencies
pip install -r server/requirements-dev.txt

# Ensure server components are available
cd server
python -c "import app.main_multimodel"
```

### Quick Test Run
```bash
# Run from project root
./run_multimodel_e2e_tests.sh quick
```

### Full Test Suite
```bash
# Run complete E2E test suite
./run_multimodel_e2e_tests.sh full

# Or run directly with pytest
cd tests/e2e
pytest test_multimodel_e2e.py -v
```

### Specific Test Categories
```bash
# Run only multi-model tests
pytest -m "multimodel" -v

# Run performance tests
pytest -m "performance" -v

# Run NLLB specific tests
pytest -m "nllb" -v

# Run Aya specific tests  
pytest -m "aya" -v
```

## 🔧 Test Configuration

### Environment Variables
```bash
export API_KEY="test-api-key-e2e"
export LOG_LEVEL="INFO"
export MODEL_CACHE_DIR="/tmp/e2e_model_cache"
export TIMEOUT="300"
```

### Service Configuration
Tests automatically start services with test-specific configurations:
- **Multi-model service**: `app.main_multimodel:app`
- **Legacy service**: `app.main:app` (for compatibility tests)
- **Test ports**: Auto-allocated to avoid conflicts
- **Mock models**: Used to avoid long loading times

## 📊 Test Reports

### HTML Report Generation
```bash
# Generate comprehensive HTML report
./run_multimodel_e2e_tests.sh full

# Report location
open test_reports/multimodel_e2e/multimodel_e2e_summary.html
```

### JUnit XML Reports
```bash
# XML reports for CI/CD integration
pytest --junit-xml=test_reports/e2e_results.xml
```

### Performance Reports
```bash
# Detailed performance analysis
pytest -m "performance" --benchmark-json=test_reports/benchmarks.json
```

## 🧪 Test Scenarios

### Service Lifecycle Tests
- Service startup and initialization
- Health check endpoints
- Graceful shutdown and cleanup
- Service recovery after failures

### Model Management Tests
- Loading NLLB and Aya models
- Model availability verification
- Dynamic model switching
- Model unloading and cleanup

### Translation Workflow Tests
- Single text translation
- Batch translation processing
- Auto language detection
- Custom model options

### API Contract Tests
- Request/response format validation
- Error response consistency
- Authentication and authorization
- Rate limiting behavior

### Performance Tests
- Response time benchmarks
- Concurrent request handling
- Memory usage monitoring
- Throughput measurements

### Integration Tests
- Multi-model workflow orchestration
- Language code conversion
- Cross-model compatibility
- End-to-end user scenarios

## 🐛 Debugging Tests

### Verbose Output
```bash
pytest -v -s --log-cli-level=DEBUG
```

### Service Logs
```bash
# View service logs during tests
tail -f test_reports/multimodel_e2e/*.log
```

### Debug Mode
```bash
# Run with debugging enabled
export DEBUG=true
pytest --pdb-trace
```

### Test Isolation
```bash
# Run single test for debugging
pytest test_multimodel_e2e.py::TestMultiModelE2E::test_nllb_translation_workflow -v -s
```

## 📈 Performance Monitoring

### Metrics Collected
- **Response Times**: API endpoint response latencies
- **Throughput**: Requests per second capacity
- **Resource Usage**: CPU and memory consumption
- **Error Rates**: Success/failure ratios
- **Model Performance**: Translation quality metrics

### Benchmark Targets
- **Single Translation**: < 500ms response time
- **Batch Translation**: < 100ms per item
- **Model Loading**: < 30s initialization
- **Concurrent Requests**: 10+ simultaneous requests
- **Memory Usage**: < 2GB per model

## 🔄 CI/CD Integration

### GitHub Actions Example
```yaml
name: Multi-Model E2E Tests
on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v3
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: pip install -r server/requirements-dev.txt
      - name: Run E2E tests
        run: ./run_multimodel_e2e_tests.sh full
      - name: Upload test reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: e2e-test-reports
          path: test_reports/
```

## 🛡️ Test Data & Security

### Test Data Management
- **Mock Models**: Lightweight mocks for fast testing
- **Sample Texts**: Multilingual test corpus
- **API Keys**: Test-specific authentication tokens
- **Cleanup**: Automatic test data cleanup

### Security Considerations
- **Isolated Environment**: Tests run in isolated containers/processes
- **No Real Models**: Production models not used in tests
- **Credential Management**: Test credentials separate from production
- **Data Privacy**: No real user data in tests

## 📝 Adding New Tests

### Test Template
```python
def test_new_functionality(self, client, test_reporter):
    """Test description."""
    with test_reporter.test_case("new_functionality"):
        # Test implementation
        result = client.some_api_call()
        assert result.status_code == 200
        
        test_reporter.record_success("Test completed", {
            "metric": "value"
        })
```

### Test Categories
Use pytest markers to categorize tests:
```python
@pytest.mark.multimodel
@pytest.mark.performance
def test_example():
    pass
```

## 🤝 Contributing

### Test Guidelines
1. **Descriptive Names**: Use clear, descriptive test names
2. **Test Documentation**: Include docstrings explaining test purpose
3. **Error Scenarios**: Test both success and failure cases
4. **Performance Awareness**: Monitor test execution time
5. **Clean Isolation**: Ensure tests don't interfere with each other

### Code Review Checklist
- [ ] Tests cover new functionality
- [ ] Error cases are tested
- [ ] Performance impact is considered
- [ ] Test data is properly managed
- [ ] Documentation is updated

## 📞 Support

For issues with E2E tests:
1. Check test logs in `test_reports/`
2. Run tests with debug output: `pytest -v -s`
3. Verify service startup manually
4. Check model loading capabilities
5. Review test environment configuration

## 🔮 Future Enhancements

### Planned Improvements
- [ ] **Visual Testing**: Screenshot comparison for UI components
- [ ] **Load Testing**: High-volume stress testing
- [ ] **Multi-Environment**: Testing across different deployment environments
- [ ] **Real Model Testing**: Optional tests with actual models
- [ ] **API Versioning**: Tests for API version compatibility
- [ ] **Security Testing**: Penetration testing scenarios