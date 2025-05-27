# Single-Model Integration Tests

This document describes the comprehensive integration test suite for the single-model architecture implementation.

## Overview

The integration tests validate the complete single-model-per-instance architecture, ensuring:

- **100% API Compatibility**: All endpoints work correctly with single-model instances
- **Model-Specific Functionality**: Each model type (Aya Expanse 8B, NLLB) works as expected
- **Architectural Constraints**: Single-model constraints are properly enforced
- **Memory Efficiency**: Single-model instances use resources efficiently
- **Operational Simplicity**: Simplified deployment and management patterns

## Test Structure

### Core Integration Tests

#### `test_single_model_api.py`
**Primary test suite for single-model API validation.**

**Test Classes:**
- `TestSingleModelAPI`: Core API endpoint testing
- `TestSingleModelServerIntegration`: Server lifecycle and integration
- `TestModelSpecificIntegration`: Model-specific integration scenarios
- `TestAPICompatibility`: API compatibility and architectural constraints

**Key Test Categories:**
1. **Health Check Endpoints**
   - Healthy model state validation
   - Unhealthy/not ready state handling
   - Model info inclusion in health checks

2. **Model Info Endpoints**
   - Model metadata retrieval
   - Authentication requirements
   - Error handling for non-ready models

3. **Translation Endpoints**
   - Basic translation functionality
   - Request validation
   - Error handling and edge cases
   - Processing time reporting

4. **Language Detection**
   - Language detection endpoint testing
   - Model-specific detection capabilities
   - Error handling

5. **Server Lifecycle**
   - Model loading and initialization
   - Cleanup and shutdown procedures
   - Error handling during startup

6. **Architectural Constraints**
   - Single-model-per-instance enforcement
   - Memory efficiency patterns
   - Operational simplicity validation

### Model-Specific Tests

#### `test_aya_expanse_8b_integration.py`
**Comprehensive testing for Aya Expanse 8B model integration.**

**Test Classes:**
- `TestAyaExpanse8BIntegration`: Core Aya functionality
- `TestAyaExpanse8BLoadingAndConfiguration`: Loading and configuration

**Aya-Specific Features:**
1. **GGUF Model Characteristics**
   - Quantization support (Q4_K_M)
   - Extended context length (32,768 tokens)
   - Memory usage (8.0 GB)
   - Model size (4.5 GB)

2. **Multilingual Capabilities**
   - 16+ language support
   - High-quality translations
   - Complex text handling
   - Technical term translation

3. **Generation Capabilities**
   - Text generation alongside translation
   - Extended context processing
   - Creative and technical text handling

4. **Performance Characteristics**
   - Longer loading times (GGUF initialization)
   - Higher memory requirements
   - CPU-optimized inference

#### `test_nllb_integration.py`
**Comprehensive testing for NLLB model integration.**

**Test Classes:**
- `TestNLLBIntegration`: Core NLLB functionality
- `TestNLLBLoadingAndConfiguration`: Loading and configuration
- `TestNLLBAPICompatibilityAndPerformance`: Performance and compatibility

**NLLB-Specific Features:**
1. **Transformers Model Characteristics**
   - Distilled model (600M parameters)
   - Efficient memory usage (2.5 GB)
   - Smaller model size (1.2 GB)
   - Facebook/Meta model pipeline

2. **Extensive Language Support**
   - 200+ language support
   - Comprehensive language family coverage
   - African language specialization
   - Cross-language translation (non-English pairs)

3. **Translation Quality**
   - Bidirectional translation
   - Long text handling
   - Character-based language detection
   - Consistent translation formats

4. **Performance Characteristics**
   - Faster loading than GGUF models
   - Lower memory requirements
   - Optimized for multilingual tasks

## Test Implementation Patterns

### Mocking Strategy

**Model Mocking:**
```python
@pytest.fixture
def mock_model(self):
    mock = AsyncMock(spec=TranslationModel)
    mock.model_name = "test-model"
    mock.initialize = AsyncMock()
    mock.cleanup = AsyncMock()
    mock.health_check = AsyncMock(return_value=True)
    # ... detailed mock setup
    return mock
```

**Server Mocking:**
```python
@pytest.fixture
def mock_server(self, mock_model):
    server = Mock(spec=SingleModelServer)
    server.model_name = "test-model"
    server.model = mock_model
    server.is_ready.return_value = True
    # ... server behavior simulation
    return server
```

**Client Testing:**
```python
@pytest.fixture
def client(self, mock_server):
    with patch.dict(os.environ, {"LINGUA_NEXUS_MODEL": "test-model"}):
        app = create_app()
        with patch('app.single_model_main.server', mock_server):
            return TestClient(app)
```

### Translation Test Patterns

**Multilingual Test Cases:**
```python
test_cases = [
    ("Hello, world!", "en", "ru", "Привет, мир!"),
    ("Hello, world!", "en", "es", "¡Hola, mundo!"),
    # ... additional language pairs
]

for text, source, target, expected in test_cases:
    # Test each translation pair
```

**Error Handling Patterns:**
```python
def test_model_not_ready(self, client, mock_server):
    mock_server.is_ready.return_value = False
    response = client.post("/translate", json=data, headers=headers)
    assert response.status_code == 503
    assert "not ready" in response.json()["detail"]
```

### Async Testing Patterns

**Server Lifecycle Testing:**
```python
@pytest.mark.asyncio
async def test_server_lifecycle(self):
    server = SingleModelServer("test-model")
    await server.startup()
    assert server.is_ready()
    await server.shutdown()
    assert not server.is_ready()
```

**Model Loading Testing:**
```python
@pytest.mark.asyncio
async def test_model_loading(self):
    with patch('models.aya_expanse_8b.model.AyaExpanse8BModel') as mock:
        server = SingleModelServer("aya-expanse-8b")
        model = await server._load_model("aya-expanse-8b")
        assert model == mock.return_value
```

## Test Coverage Requirements

### Functional Coverage
- ✅ **API Endpoints**: All endpoints tested with success and error cases
- ✅ **Model Loading**: Both supported models (Aya, NLLB) loading tested
- ✅ **Translation Quality**: Multiple language pairs and text types
- ✅ **Error Handling**: Comprehensive error scenario coverage
- ✅ **Authentication**: API key validation and security

### Architectural Coverage
- ✅ **Single-Model Constraint**: Enforcement of one-model-per-instance
- ✅ **Memory Efficiency**: Resource usage validation
- ✅ **Operational Simplicity**: Simplified management patterns
- ✅ **API Compatibility**: 100% backward compatibility
- ✅ **Environment Configuration**: Model selection via environment

### Model-Specific Coverage
- ✅ **Aya Expanse 8B**: GGUF, quantization, generation capabilities
- ✅ **NLLB**: Transformers, distilled model, extensive languages
- ✅ **Performance Characteristics**: Model-specific behavior validation
- ✅ **Error Patterns**: Model-specific error handling

## Running Integration Tests

### Individual Test Files
```bash
# Run core single-model API tests
pytest server/tests/integration/test_single_model_api.py -v

# Run Aya-specific integration tests
pytest server/tests/integration/test_aya_expanse_8b_integration.py -v

# Run NLLB-specific integration tests
pytest server/tests/integration/test_nllb_integration.py -v
```

### Full Integration Suite
```bash
# Run all integration tests
pytest server/tests/integration/ -v

# Run with coverage reporting
pytest server/tests/integration/ --cov=app --cov-report=html
```

### Makefile Integration
```bash
# Test specific model integration
make test-integration:aya-expanse-8b
make test-integration:nllb

# Test all integration
make test-integration
```

## Success Criteria

### Test Pass Requirements
1. **100% Test Pass Rate**: All integration tests must pass
2. **No Mock Leakage**: Tests must not depend on implementation details
3. **Realistic Scenarios**: Tests must simulate real-world usage
4. **Performance Validation**: Processing times and resource usage verified
5. **Error Resilience**: Comprehensive error handling validation

### Architecture Validation
1. **Single-Model Enforcement**: No multi-model patterns allowed
2. **Memory Efficiency**: Resource usage within expected bounds
3. **API Compatibility**: All existing endpoints work correctly
4. **Model Isolation**: Each model instance operates independently
5. **Operational Simplicity**: Deployment and management simplified

## Integration with CI/CD

### Test Pipeline Integration
```yaml
integration_tests:
  stage: test
  script:
    - pytest server/tests/integration/ --junitxml=integration-results.xml
  artifacts:
    reports:
      junit: integration-results.xml
  coverage: '/TOTAL.*\s+(\d+%)$/'
```

### Model-Specific Testing
```yaml
test_aya_integration:
  extends: .integration_tests
  variables:
    LINGUA_NEXUS_MODEL: "aya-expanse-8b"
  script:
    - pytest server/tests/integration/test_aya_expanse_8b_integration.py

test_nllb_integration:
  extends: .integration_tests
  variables:
    LINGUA_NEXUS_MODEL: "nllb"
  script:
    - pytest server/tests/integration/test_nllb_integration.py
```

## Maintenance and Updates

### Adding New Models
1. Create model-specific integration test file: `test_{model_name}_integration.py`
2. Implement model-specific test classes following established patterns
3. Add model loading tests to core integration suite
4. Update documentation with new model characteristics

### Test Data Management
1. **Translation Pairs**: Maintain comprehensive language pair datasets
2. **Error Scenarios**: Document and test all error conditions
3. **Performance Baselines**: Establish and validate performance expectations
4. **Mock Behaviors**: Keep mocks synchronized with real model behaviors

### Quality Assurance
1. **Regular Review**: Review test coverage and effectiveness monthly
2. **Performance Monitoring**: Track test execution times and reliability
3. **Mock Validation**: Periodically validate mocks against real models
4. **Documentation Updates**: Keep test documentation current with changes

## Conclusion

The single-model integration test suite provides comprehensive validation of:

- ✅ **Complete API Functionality**: All endpoints tested with realistic scenarios
- ✅ **Model-Specific Features**: Aya and NLLB capabilities thoroughly validated
- ✅ **Architectural Compliance**: Single-model constraints properly enforced
- ✅ **Error Resilience**: Comprehensive error handling and edge cases
- ✅ **Performance Validation**: Resource usage and processing times verified

This testing framework ensures the single-model architecture delivers on its promises of:
- 50%+ memory reduction per instance
- 100% API compatibility
- Operational simplicity
- Reliable model-specific functionality

The test suite supports confident deployment and maintenance of the single-model architecture while maintaining high quality standards and comprehensive coverage.
