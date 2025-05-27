# Test Fix Task List - Prioritized Implementation

## Task Priority Matrix

| Priority | Impact | Effort | Dependencies | Risk |
|----------|---------|---------|--------------|------|
| P0 | Blocks all | < 2h | None | Critical |
| P1 | Blocks many | 2-4h | P0 | High |
| P2 | Blocks some | 4-8h | P1 | Medium |
| P3 | Quality improvement | 8h+ | P2 | Low |

## Phase 1: Critical Blockers (P0) - Day 1

### TASK-001: Fix Enhanced Mock Configuration [2h]
**Priority**: P0 | **Blocks**: 15+ tests  
**Location**: `/server/tests/conftest.py`
```python
# Add to EnhancedMockConfig.__init__():
self.prefix = ""
self.task = "translation"
self.is_encoder_decoder = True
self.framework = "pt"

# Update model_type to supported value:
self.model_type = "m2m_100"  # Changed from unsupported type
```

### TASK-002: Fix E2E ServiceManager Import [1h]
**Priority**: P0 | **Blocks**: All E2E tests  
**Location**: `/tests/e2e/utils/service_manager.py`
- Create missing `E2EServiceManager` class
- Export `ServiceConfig` dataclass
- Fix import statements in `conftest.py`

### TASK-003: Add UserScript Mock Environment [1.5h]
**Priority**: P0 | **Blocks**: All UserScript tests  
**Location**: `/userscript/tests/setup.js`
```javascript
// Add before all tests:
global.GM_addStyle = jest.fn();
global.GM_getValue = jest.fn();
global.GM_setValue = jest.fn();
global.GM_registerMenuCommand = jest.fn();
global.GM_xmlhttpRequest = jest.fn();
```

## Phase 2: Core Functionality (P1) - Day 2

### TASK-004: Fix Language Detection for Cyrillic [3h]
**Priority**: P1 | **Failed Tests**: 2  
**Location**: `/server/app/utils/language_detection.py`
- Implement proper Unicode range detection
- Add contextual analysis for mixed scripts
- Return appropriate language codes based on content

### TASK-005: Fix Character-Based Detection [2h]
**Priority**: P1 | **Failed Tests**: 1  
**Location**: `/server/app/models/aya_model.py`
```python
def _detect_language_from_characters(self, text: str) -> Optional[str]:
    # Implement Unicode block analysis
    # Use regex patterns for script detection
    # Return None if uncertain (fallback to other methods)
```

### TASK-006: Fix Model Registry Error Handling [2h]
**Priority**: P1 | **Failed Tests**: 1  
**Location**: `/server/app/models/registry.py`
- Add proper error messages for unknown models
- Implement graceful fallback mechanism
- Update error response format

## Phase 3: Validation & Error Handling (P2) - Day 3

### TASK-007: Fix Request Validation Error Codes [4h]
**Priority**: P2 | **Failed Tests**: 9  
**Location**: `/server/app/main.py` and `/server/app/main_multimodel.py`
- Add validation middleware
- Transform validation errors to 422 responses
- Ensure consistent error format

### TASK-008: Update Integration Test Imports [2h]
**Priority**: P2 | **Blocks**: Integration tests  
**Locations**: Multiple files in `/server/tests/integration/`
- Change `from server.app.main import app` to `from app.main import app`
- Update all affected test files
- Verify import paths

### TASK-009: Implement Mock Pipeline Support [4h]
**Priority**: P2 | **Enhancement**  
**Location**: `/server/tests/conftest.py`
- Create MockPipeline class
- Support both legacy and new interfaces
- Add configuration validation

## Phase 4: Test Quality (P3) - Days 4-5

### TASK-010: Add Integration Test Fixtures [6h]
**Priority**: P3 | **Enhancement**  
**Location**: `/server/tests/integration/conftest.py`
- Create database fixtures
- Add API client fixtures
- Implement test data factories

### TASK-011: Create E2E Test Scenarios [8h]
**Priority**: P3 | **New Tests**  
**Location**: `/tests/e2e/test_translation_workflows.py`
- Multi-language translation flow
- Error recovery scenarios
- Performance benchmarks

### TASK-012: Improve Mock Realism [4h]
**Priority**: P3 | **Quality**  
**Location**: `/server/tests/conftest.py`
- Add response time simulation
- Implement realistic error rates
- Create data variation

## Phase 5: Documentation & Tooling (P3) - Day 6

### TASK-013: Create Test Troubleshooting Guide [3h]
**Priority**: P3 | **Documentation**  
**Location**: `/docs/testing/troubleshooting.md`
- Common failure patterns
- Debug techniques
- Mock configuration guide

### TASK-014: Add Test Performance Metrics [4h]
**Priority**: P3 | **Tooling**  
- Install pytest-benchmark
- Add performance tests
- Create baseline metrics

### TASK-015: Implement Test Report Generation [3h]
**Priority**: P3 | **Tooling**  
- Add pytest-html
- Configure Allure reporting
- Create CI/CD integration

## Implementation Checklist

### Day 1 Checklist
- [ ] TASK-001: Enhanced Mock Configuration
- [ ] TASK-002: E2E ServiceManager
- [ ] TASK-003: UserScript Mocks
- [ ] Run: `cd server && python -m pytest tests/unit/ -v`
- [ ] Verify: P0 blockers resolved

### Day 2 Checklist
- [ ] TASK-004: Cyrillic Detection
- [ ] TASK-005: Character Detection
- [ ] TASK-006: Registry Errors
- [ ] Run: `cd server && python -m pytest tests/unit/test_*_model.py -v`
- [ ] Verify: Language detection passing

### Day 3 Checklist
- [ ] TASK-007: Validation Errors
- [ ] TASK-008: Import Fixes
- [ ] TASK-009: Mock Pipeline
- [ ] Run: `./run_and_report_tests.sh`
- [ ] Verify: < 5 failing tests

### Days 4-5 Checklist
- [ ] TASK-010: Integration Fixtures
- [ ] TASK-011: E2E Scenarios
- [ ] TASK-012: Mock Improvements
- [ ] Run: Full test suite
- [ ] Verify: > 90% pass rate

### Day 6 Checklist
- [ ] TASK-013: Documentation
- [ ] TASK-014: Performance
- [ ] TASK-015: Reporting
- [ ] Final validation
- [ ] Deploy fixes

## Success Criteria

### Immediate (End of Day 1)
- All test suites can execute without import errors
- Mock configuration errors resolved
- Basic test infrastructure operational

### Short-term (End of Day 3)
- Unit tests: 55/57 passing (>96%)
- Integration tests: Executable
- E2E tests: Basic scenarios passing

### Complete (End of Day 6)
- All tests passing
- Performance baselines established
- Documentation complete
- CI/CD integration working

## Risk Mitigation

1. **Blocked Progress**: If P0 tasks take longer, delay P3 tasks
2. **New Failures**: Document and defer non-critical issues
3. **Time Constraints**: Focus on P0-P2, document P3 for later

## Command Reference

```bash
# After each task, verify with:
cd /mnt/dionysus/coding/tg-text-translate

# Unit tests only
cd server && python -m pytest tests/unit/ -v

# Specific test file
cd server && python -m pytest tests/unit/test_request_models.py -v

# With coverage
cd server && python -m pytest tests/ --cov=app --cov-report=html

# Full suite
./run_and_report_tests.sh
```