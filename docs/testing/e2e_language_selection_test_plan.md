# E2E Language Selection Test Plan

## Executive Summary

This test plan addresses critical testing gaps in the recently implemented ad hoc language selection system with bidirectional translation support. The plan identifies 27 missing test scenarios across API, UserScript, and AutoHotkey components that require comprehensive E2E testing.

## Testing Gaps Analysis

### Current Test Coverage
- ✅ Basic API translation workflow (eng_Latn → fra_Latn, spa_Latn)
- ✅ Unicode text handling over HTTP
- ✅ Large text payload processing
- ✅ Basic error handling for unsupported languages
- ✅ Concurrent request handling
- ✅ Malformed request validation
- ✅ AutoHotkey clipboard operations (mocked)
- ✅ UserScript DOM manipulation (placeholder tests)

### Critical Missing Test Areas

#### 1. Language Selection API Tests
- ❌ **NEW** `/languages` endpoint validation
- ❌ **NEW** Language metadata structure validation
- ❌ **NEW** Popular vs non-popular language filtering
- ❌ **NEW** Language family and script validation
- ❌ **NEW** RTL language support validation
- ❌ **NEW** API caching headers validation
- ❌ **NEW** Language code format validation (BCP-47 + ISO 639-3/15924)

#### 2. Bidirectional Translation Workflow Tests
- ❌ **NEW** Language pair selection and validation
- ❌ **NEW** Language swap functionality end-to-end
- ❌ **NEW** Source language auto-detection with target override
- ❌ **NEW** Cross-platform language persistence
- ❌ **NEW** Recent language tracking and retrieval
- ❌ **NEW** Language pair history management

#### 3. UserScript E2E Integration Tests
- ❌ **NEW** Language dropdown component rendering
- ❌ **NEW** Language selector modal functionality
- ❌ **NEW** Settings migration from v2.x to v3.x
- ❌ **NEW** Language swap button interaction
- ❌ **NEW** Recent languages display and selection
- ❌ **NEW** Error handling for failed language API calls
- ❌ **NEW** Accessibility compliance (WCAG 2.1 AA)
- ❌ **NEW** Progressive enhancement fallbacks

#### 4. AutoHotkey v2.0 Integration Tests
- ❌ **NEW** Language selection GUI functionality
- ❌ **NEW** Language Manager API integration
- ❌ **NEW** INI configuration persistence
- ❌ **NEW** Hotkey-triggered language selection
- ❌ **NEW** Error handling for offline scenarios
- ❌ **NEW** Language fallback mechanisms

#### 5. Cross-Platform Integration Tests
- ❌ **NEW** Language synchronization between platforms
- ❌ **NEW** API key validation across all clients
- ❌ **NEW** Consistent error messaging
- ❌ **NEW** Performance consistency across platforms

## Priority Classification

### P0 - Critical (Blocking)
Must be implemented to ensure system reliability and user safety.

1. **Language Selection API Validation** - Ensures new `/languages` endpoint works correctly
2. **Bidirectional Translation Workflow** - Core functionality of the new system
3. **Settings Migration Testing** - Prevents data loss during upgrades
4. **Cross-Platform Language Consistency** - Ensures unified user experience

### P1 - High (Release Blocking)
Should be implemented before next release.

5. **Language Swap E2E Testing** - Key user feature validation
6. **Recent Languages Functionality** - User experience enhancement validation
7. **Error Handling Validation** - Graceful degradation testing
8. **AutoHotkey v2.0 GUI Testing** - Platform-specific functionality

### P2 - Medium (Quality)
Important for long-term maintainability and user experience.

9. **Accessibility Compliance Testing** - WCAG 2.1 AA validation
10. **Performance Testing** - Language loading and caching validation
11. **UserScript DOM Integration** - Real browser environment testing

### P3 - Low (Enhancement)
Nice-to-have for comprehensive coverage.

12. **Edge Case Scenario Testing** - Unusual language combinations
13. **Long-term Persistence Testing** - Data retention validation

## Testing Strategy

### Test Environment Requirements
- **API Server**: FastAPI with NLLB model loaded
- **Browser Environment**: Chrome/Firefox with Tampermonkey
- **AutoHotkey Environment**: Windows with AHK v2.0
- **Network Conditions**: Online/offline scenarios
- **Data Persistence**: localStorage, sessionStorage, INI files

### Test Data Requirements
- **Languages**: All 32+ supported NLLB languages
- **Text Samples**: Unicode, RTL, large payloads, special characters
- **User Scenarios**: First-time users, existing users, migration scenarios
- **Error Conditions**: Network failures, invalid responses, missing data

### Automated Testing Approach
- **API Tests**: Pytest with comprehensive fixtures
- **UserScript Tests**: Playwright for real browser automation
- **AutoHotkey Tests**: AHK v2.0 test framework with mocking
- **Integration Tests**: Docker-compose orchestration

## Success Criteria

### Functional Requirements
1. All 27 identified test scenarios pass consistently
2. Cross-platform language synchronization works correctly
3. Bidirectional translation maintains data integrity
4. Error handling provides clear user feedback
5. Performance meets established benchmarks

### Quality Requirements
1. Test coverage >90% for new language selection features
2. All tests run in <5 minutes total execution time
3. Tests are deterministic and reliable
4. Clear failure reporting with actionable error messages
5. Comprehensive test documentation

### Acceptance Criteria
1. ✅ All P0 and P1 tests implemented and passing
2. ✅ CI/CD integration completed with automated execution
3. ✅ Test reports generated with coverage metrics
4. ✅ Documentation updated with test procedures
5. ✅ Team training completed on new test procedures

## Risk Assessment

### High Risk Areas
- **Cross-Platform Synchronization**: Complex state management
- **Settings Migration**: Data corruption potential
- **API Integration**: Network dependency and failure modes
- **Browser Compatibility**: UserScript across different environments

### Mitigation Strategies
- Comprehensive mocking for network dependencies
- Incremental migration testing with rollback capabilities
- Multi-browser testing matrix
- Fallback mechanism validation

## Resource Requirements

### Development Time Estimate
- **Implementation**: 8-12 developer days
- **Review and Debugging**: 3-5 developer days
- **Documentation**: 2-3 developer days
- **Total**: 13-20 developer days

### Infrastructure Requirements
- CI/CD pipeline with browser automation
- Test data management system
- Performance monitoring and alerting
- Cross-platform test execution environment

## Next Steps

1. **Review and Approval**: Stakeholder sign-off on test plan
2. **Task Prioritization**: Detailed task breakdown and estimation
3. **Resource Allocation**: Assign testing engineer and timeline
4. **Implementation**: Execute according to priority order
5. **Monitoring**: Track progress and adjust as needed

---

*This test plan covers the comprehensive testing strategy for the ad hoc language selection system. It should be reviewed and updated as the system evolves.*