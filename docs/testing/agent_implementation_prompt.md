# AI Agent Implementation Prompt: NLLB API Test Suite Development

## Mission Statement

You are an AI Agent tasked with implementing a comprehensive API test suite for the NLLB Translation System. Your goal is to execute the detailed implementation plan to achieve 95% server code coverage while fixing critical test gaps and establishing robust test infrastructure.

## Context and Background

The NLLB Translation System is a FastAPI server that provides translation services using HuggingFace's No Language Left Behind (NLLB) model. The current test suite has ~75% coverage with significant gaps in async rate limiting, error handling, and edge case scenarios.

### Current System Architecture
```
server/
├── app/
│   ├── main.py                    # FastAPI app with /health and /translate endpoints
│   └── utils/
│       ├── model_loader.py        # NLLB model loading and translation logic
│       └── language_detection.py  # Russian/English language detection
├── tests/
│   ├── conftest.py               # Basic fixtures and mocks
│   ├── integration/
│   │   └── test_api_endpoints.py # Existing API endpoint tests
│   └── unit/
│       ├── test_language_detection.py
│       └── test_model_loader.py
```

### Key Technologies
- **FastAPI** for async API endpoints
- **SlowAPI** for rate limiting (10 requests/minute)
- **HuggingFace Transformers** for NLLB model integration
- **Pytest** for testing framework
- **Pydantic** for request/response validation

## Your Implementation Strategy

Execute the implementation plan systematically, following the prioritized task sequence. **Start with Phase 1 (Priority 1 tasks)** and work through each phase sequentially.

### Phase 1: Foundation and Critical Fixes (START HERE)
**Immediate Priority**: Fix existing test failures and establish solid foundation

**Tasks to Execute (in order):**
1. **T001**: Enhance Mock Infrastructure (`/server/tests/conftest.py`)
2. **T002**: Fix Rate Limiting Tests (create `/server/tests/integration/test_rate_limiting.py`)
3. **T003**: Add Translation Format Validation (modify existing tests)
4. **T004**: Complete API Key Validation Coverage (create `/server/tests/integration/test_authentication.py`)
5. **T005**: Enhance Startup Event Testing
6. **T006**: Add Comprehensive Error Handling Tests (create `/server/tests/integration/test_error_handling.py`)
7. **T007**: Fix async Test Support (update `/server/pytest.ini`)
8. **T008**: Add Request Models Validation Testing (create `/server/tests/unit/test_request_models.py`)

## Implementation Instructions

### Step 1: Environment Setup
Before starting implementation:
1. Read the complete implementation plan at `/mnt/dionysus/coding/tg-text-translate/docs/testing/implementation_execution_plan.md`
2. Examine existing test files to understand current patterns
3. Run existing tests to identify current failures
4. Set up your development environment with proper dependencies

### Step 2: Task Execution Protocol
For each task:
1. **Read task details** from the implementation plan
2. **Check dependencies** - ensure prerequisite tasks are completed
3. **Review acceptance criteria** to understand success conditions
4. **Implement the solution** following existing code patterns
5. **Test your implementation** to ensure it works
6. **Validate coverage improvement** after each major change

### Step 3: Quality Standards
Maintain these standards throughout implementation:
- **Follow existing code style** and patterns from the codebase
- **Use proper async/await patterns** for FastAPI testing
- **Implement comprehensive assertions** not just basic checks
- **Add descriptive docstrings** for all test functions
- **Ensure test isolation** - tests should not depend on each other
- **Mock external dependencies** properly to avoid flaky tests

## Detailed Implementation Guidance

### Enhanced Mock Infrastructure (T001) - Start Here

Upgrade `/server/tests/conftest.py` with enhanced mock classes:

```python
# Key improvements needed:
class EnhancedMockModel:
    """Enhanced NLLB model mock with better interface support."""
    def __init__(self):
        self.config = MockConfig()
        self.test_id = f"mock_model_{time.time()}"
        self.device = "cpu"
        self.call_count = 0
    
    def to(self, device):
        self.device = device
        return self
    
    def generate(self, input_ids, max_length=128, **kwargs):
        # Proper tensor generation matching real model behavior
        pass

class EnhancedMockTokenizer:
    """Enhanced tokenizer mock with proper language handling."""
    # Implement proper language switching and tokenization
    pass
```

### Rate Limiting Tests (T002) - High Priority

Create `/server/tests/integration/test_rate_limiting.py`:

```python
class TestRateLimiting:
    def test_rate_limit_enforcement(self, test_client, enhanced_mock_objects, api_key_header):
        """Test basic rate limit enforcement - 10 requests/minute limit."""
        # Send 10 requests (should succeed)
        # Send 11th request (should return 429)
        # Validate rate limit error message
        
    def test_concurrent_rate_limiting(self, test_client, enhanced_mock_objects, api_key_header):
        """Test rate limiting with concurrent requests."""
        # Use ThreadPoolExecutor to simulate concurrent requests
        # Verify only 10 requests succeed, rest get 429
```

### Critical Implementation Notes

**Async Testing Patterns:**
- Use `TestClient` for API endpoint testing (handles async automatically)
- For testing startup events: `asyncio.run(startup_event())`
- Mock async dependencies properly with `async def` when needed

**Rate Limiting Testing Strategy:**
- Mock the SlowAPI rate limiter for deterministic behavior
- Use request counters to simulate rate limit enforcement
- Test both sequential and concurrent request scenarios

**Error Handling Coverage:**
- Test all exception paths in the translation pipeline
- Verify proper HTTP status codes (400, 403, 429, 500, 503)
- Ensure error messages are descriptive and helpful

**Translation Format Validation:**
- Verify "Translated: " prefix is always present
- Test with different language pairs
- Validate consistency across all translation scenarios

## Success Criteria for Phase 1

Before moving to Phase 2, ensure:
- [ ] All 8 Priority 1 tasks completed
- [ ] Coverage increases by at least 5%
- [ ] All existing test failures resolved
- [ ] New tests run reliably in CI/CD environment
- [ ] Mock infrastructure supports all required interfaces
- [ ] Rate limiting tests pass consistently
- [ ] Error handling comprehensive and tested

## Running and Validating Your Implementation

### Test Execution Commands
```bash
# Run all tests
pytest server/tests/

# Run with coverage
pytest server/tests/ --cov=app --cov-report=html

# Run specific test categories
pytest server/tests/unit/           # Unit tests only
pytest server/tests/integration/   # Integration tests only

# Run with verbose output
pytest server/tests/ -v --tb=short
```

### Coverage Validation
- Target: 80%+ coverage after Phase 1 completion
- Monitor coverage improvements after each task
- Identify and address any significant coverage gaps

### Performance Validation
- Unit tests should complete in < 30 seconds
- Integration tests should complete in < 2 minutes
- Full test suite should complete in < 5 minutes

## Common Pitfalls to Avoid

1. **Don't mock too broadly** - Mock only what's necessary for test isolation
2. **Avoid flaky tests** - Ensure deterministic behavior, especially for timing-dependent tests
3. **Don't skip error scenarios** - Comprehensive error testing is critical
4. **Maintain test isolation** - Tests should not depend on execution order
5. **Follow async patterns** - Properly handle async code in FastAPI application

## Resources and References

**Essential Files to Study:**
- `/mnt/dionysus/coding/tg-text-translate/docs/testing/implementation_execution_plan.md` - Complete task details
- `/mnt/dionysus/coding/tg-text-translate/server/tests/conftest.py` - Current mock implementation
- `/mnt/dionysus/coding/tg-text-translate/server/tests/integration/test_api_endpoints.py` - Existing test patterns
- `/mnt/dionysus/coding/tg-text-translate/server/app/main.py` - API implementation details

**Testing Documentation:**
- FastAPI testing: https://fastapi.tiangolo.com/tutorial/testing/
- Pytest async: https://pytest-asyncio.readthedocs.io/
- Coverage.py: https://coverage.readthedocs.io/

## Communication Protocol

**Progress Reporting:**
Report completion of each Priority 1 task with:
- Task ID and name completed
- Coverage improvement achieved
- Any issues encountered and resolved
- Next task to be started

**Issue Escalation:**
If you encounter blockers:
- Document the specific issue
- Describe attempted solutions
- Provide error messages/logs
- Suggest alternative approaches

## Next Steps After Phase 1

Once Phase 1 is complete and validated:
1. **Run full test suite** and confirm 80%+ coverage
2. **Generate coverage report** to identify remaining gaps
3. **Proceed to Phase 2** tasks (T009-T020)
4. **Target 90% coverage** by end of Phase 2

Remember: **Quality over speed**. It's better to implement fewer tasks thoroughly than many tasks incompletely. Each task should fully meet its acceptance criteria before moving to the next.

**Begin with T001 (Enhanced Mock Infrastructure)** and work systematically through the Priority 1 tasks. Good luck!