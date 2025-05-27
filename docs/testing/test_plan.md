# NLLB Translation System Test Plan

## Overview

This document outlines the testing strategy for the NLLB Translation System, aiming to achieve 90% code coverage across all three components:

1. Server Component (FastAPI)
2. Browser UserScript Component
3. AutoHotkey Component

## Testing Philosophy

The testing approach follows these principles:

- **Shift-left testing**: Test early and often throughout the development lifecycle
- **Pyramid approach**: More unit tests than integration tests, more integration tests than end-to-end tests
- **Component isolation**: Test each component individually before testing integration
- **Realistic scenarios**: Test with real-world translation scenarios and input patterns
- **Error handling**: Ensure all error paths are tested thoroughly
- **Performance validation**: Verify system works within expected performance parameters

## Test Types and Frameworks

### Server Component

| Test Type | Framework/Tools | Purpose |
|-----------|----------------|---------|
| Unit Tests | pytest, pytest-cov | Test individual functions and classes |
| Integration Tests | pytest, TestClient | Test API endpoints and model integration |
| Load Tests | locust | Verify performance under load |
| Security Tests | bandit, OWASP ZAP | Identify security vulnerabilities |
| Coverage | pytest-cov | Track test coverage |

### Browser UserScript Component

| Test Type | Framework/Tools | Purpose |
|-----------|----------------|---------|
| Unit Tests | Jest, Istanbul | Test utility functions and UI components |
| Integration Tests | Puppeteer | Test DOM integration with Telegram web |
| End-to-End Tests | Playwright | Test full userscript functionality |
| Coverage | Istanbul | Track test coverage |

### AutoHotkey Component

| Test Type | Framework/Tools | Purpose |
|-----------|----------------|---------|
| Unit Tests | Ahk-unit | Test individual functions |
| Integration Tests | Custom framework | Test clipboard integration and API communication |
| End-to-End Tests | AutoHotkey test wrapper | Test full functionality with simulated input |
| Coverage | Custom instrumentation | Track test coverage |

## Coverage Targets

| Component | Target Coverage | Focus Areas |
|-----------|----------------|-------------|
| Server Component | 95% | Model loading, translation logic, API endpoints, error handling |
| Browser UserScript | 90% | DOM manipulation, translation logic, API communication |
| AutoHotkey Component | 85% | Hotkey detection, clipboard handling, API communication |

## Detailed Test Plans by Component

### 1. Server Component Tests

#### 1.1 Unit Tests

| Module | Test Target | Test Cases |
|--------|------------|------------|
| `app/utils/model_loader.py` | `load_nllb_model()` | - Successful model loading<br>- Model loading with different configurations<br>- Error handling for missing model files |
| `app/utils/language_detection.py` | `detect_language()` | - Pure English text<br>- Pure Russian text<br>- Mixed language text<br>- Empty text<br>- Special characters/numbers only |
| `app/utils/cache.py` | Cache implementation | - Cache hit<br>- Cache miss<br>- Cache expiration<br>- Cache size limits |
| `app/security/auth.py` | Authentication logic | - Valid API key<br>- Invalid API key<br>- Missing API key<br>- Expired API key |

#### 1.2 Integration Tests

| API Endpoint | Test Cases |
|--------------|------------|
| `POST /translate` | - Valid translation request (EN->RU)<br>- Valid translation request (RU->EN)<br>- Empty text<br>- Oversized text<br>- Rate limiting behavior<br>- Authentication failures |
| `GET /health` | - Server up with model loaded<br>- Server up but model loading<br>- Resource usage stats |
| `GET /metrics` | - Check metrics collection<br>- Verify performance counters |

#### 1.3 Load Tests

- Concurrent translation requests (10, 50, 100 simultaneous users)
- Sustained load (50 requests per minute for 1 hour)
- Memory usage monitoring during sustained load
- Recovery after peak load

#### 1.4 Mocking Strategy

- Mock NLLB model for faster test execution
- Create small test model for integration tests
- Mock external dependencies (if any)

### 2. Browser UserScript Component Tests

#### 2.1 Unit Tests

| Module | Test Target | Test Cases |
|--------|------------|------------|
| `translateText()` | Translation function | - Successful translation<br>- API error handling<br>- Timeout handling |
| `addTranslationButton()` | UI element creation | - Button added to message<br>- Button styling<br>- Button click handler |
| `detectMessageLanguage()` | Language detection | - English messages<br>- Russian messages<br>- Mixed content |
| `settingsManager` | User settings | - Save settings<br>- Load settings<br>- Default settings |

#### 2.2 Integration Tests

| Feature | Test Cases |
|---------|------------|
| Telegram Web Integration | - Message detection on different Telegram Web versions<br>- DOM monitoring stability<br>- UI element positioning |
| Translation Flow | - Button click -> API call -> UI update<br>- Error handling and user feedback<br>- Translation result formatting |
| Settings UI | - Open settings panel<br>- Change settings<br>- Verify settings persistence |

#### 2.3 End-to-End Tests

- Complete translation workflow on Telegram Web
- Performance impact measurements
- Cross-browser compatibility (Chrome, Firefox, Edge)

#### 2.4 Mocking Strategy

- Mock the translation API for unit tests
- Mock Telegram Web DOM for integration tests
- Use fixtures for consistent test environments

### 3. AutoHotkey Component Tests

#### 3.1 Unit Tests

| Module | Test Target | Test Cases |
|--------|------------|------------|
| API communication | `SendTranslationRequest()` | - Successful request<br>- Error handling<br>- Timeout handling |
| Clipboard handling | `GetTextFromClipboard()` | - Text extraction<br>- Empty clipboard<br>- Non-text content |
| Configuration | `LoadSettings()` | - Default settings<br>- Custom settings<br>- Missing config file |
| Notifications | `ShowNotification()` | - Success notification<br>- Error notification<br>- Notification timeout |

#### 3.2 Integration Tests

| Feature | Test Cases |
|---------|------------|
| Hotkey Detection | - Various key combinations<br>- Key conflict handling |
| Translation Workflow | - Selection -> Copy -> Translate -> Display<br>- Error handling paths |
| Settings UI | - Open settings dialog<br>- Change and save settings<br>- Apply settings without restart |

#### 3.3 End-to-End Tests

- Full workflow with simulated user input
- System interactions (clipboard, keyboard)
- Performance impact measurement

#### 3.4 Special Testing Considerations

- Windows version compatibility testing (Win 10, Win 11)
- Test with different keyboard layouts
- Test with different clipboard content types

## Testing Infrastructure

### Continuous Integration

- GitHub Actions workflow for automated testing
- Pre-commit hooks for code quality and test execution
- Daily scheduled test runs for regression testing

### Test Data Management

- Create translation test corpus covering various text types
- Synthetic test data generation for edge cases
- Real-world samples (anonymized) for realistic testing

### Test Environment Setup

```bash
# Server test environment setup
cd server
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
pytest --cov=app tests/

# UserScript test environment setup
cd userscript
npm install
npm test

# AutoHotkey test environment setup
cd ahk
ahk test/runner.ahk
```

## Test Reporting and Quality Gates

### Coverage Reports

- Generate HTML coverage reports for visual inspection
- Fail builds if coverage drops below thresholds:
  - Server: 95%
  - UserScript: 90%
  - AutoHotkey: 85%

### Test Result Publishing

- Export JUnit format for CI integration
- Generate test trend reports
- Track test performance over time

### Code Quality Gates

- All tests must pass before merging to main branch
- No known security vulnerabilities
- Code quality metrics (maintainability, complexity) within acceptable ranges

## Test Automation Schedule

| Test Type | Frequency | Trigger |
|-----------|-----------|---------|
| Unit Tests | Each commit | Pre-commit hook, CI |
| Integration Tests | Each PR | CI workflow |
| End-to-End Tests | Daily | Scheduled workflow |
| Load Tests | Weekly | Scheduled workflow |
| Security Tests | Weekly | Scheduled workflow |

## Defect Management

- Bugs found during testing should be documented with:
  - Test case that found the issue
  - Expected vs. actual behavior
  - Environment information
  - Reproduction steps
  - Severity and priority assignment

- Regression tests should be added for each fixed defect

## Special Test Cases

### Security Testing

- API key injection attempts
- Rate limiting bypassing attempts
- Input sanitization tests
- Sensitive data exposure checks

### Internationalization Testing

- Non-Latin characters handling
- Right-to-left language support
- Special characters and emoji handling
- Unicode edge cases

### Accessibility Testing

- Keyboard navigation in UI components
- Screen reader compatibility
- Color contrast in UI elements
- Focus handling

## Test Plan Maintenance

This test plan should be reviewed and updated:

- When new features are added
- When significant architectural changes occur
- Quarterly for general updates and improvements

## Appendix A: Sample Test Cases

### Server Component Sample Test

```python
def test_translate_endpoint_en_to_ru():
    """Test the translation endpoint with English to Russian translation."""
    client = TestClient(app)
    request_data = {
        "text": "Hello world",
        "source_lang": "en",
        "target_lang": "ru"
    }
    
    response = client.post(
        "/translate",
        json=request_data,
        headers={"X-API-Key": "test_api_key"}
    )
    
    assert response.status_code == 200
    assert "translated_text" in response.json()
    assert response.json()["detected_lang"] == "en"
    assert len(response.json()["translated_text"]) > 0
```

### Browser UserScript Sample Test

```javascript
describe('Translation Button', () => {
  test('should add translation button to message element', () => {
    // Setup
    document.body.innerHTML = `
      <div class="message-content">
        <div class="message-text">Hello world</div>
      </div>
    `;
    const messageEl = document.querySelector('.message-content');
    
    // Execute
    addTranslationButton(messageEl);
    
    // Assert
    const button = messageEl.querySelector('.translate-button');
    expect(button).not.toBeNull();
    expect(button.textContent).toBe('Translate');
  });
});
```

### AutoHotkey Sample Test

```autohotkey
#Include %A_ScriptDir%\..\src\translator.ahk
#Include %A_ScriptDir%\ahk-unit.ahk

TestSuite("TranslatorTests")

Test_DetectLanguage()
{
    ; English text detection
    result := DetectLanguage("Hello world")
    Assert.Equal(result, "en", "Should detect English language")
    
    ; Russian text detection
    result := DetectLanguage("Привет мир")
    Assert.Equal(result, "ru", "Should detect Russian language")
    
    ; Mixed text with predominant Russian
    result := DetectLanguage("Привет world")
    Assert.Equal(result, "ru", "Should detect predominant language as Russian")
}

RunTests()
```