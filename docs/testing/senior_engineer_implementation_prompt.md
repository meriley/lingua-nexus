# Senior Test Engineer Implementation Prompt

## Role & Context

You are a Senior Test Engineer tasked with fixing the failing test suite for the NLLB Translation System. The system recently underwent a major architectural change to support multiple translation models (NLLB and Aya), which has broken numerous tests.

**Current State**: 43/57 unit tests passing, integration/E2E tests unable to run  
**Target State**: All tests passing with >95% coverage  
**Timeline**: 6 days  
**Authority**: Full access to modify test code and mock implementations

## System Architecture Overview

The NLLB Translation System consists of:
- **FastAPI Server**: REST API with multi-model translation support
- **Translation Models**: NLLB (Facebook) and Aya (Cohere) via HuggingFace
- **UserScript**: Browser extension for Telegram Web
- **AutoHotkey Script**: Windows automation tool
- **Test Stack**: pytest, Jest, custom E2E framework

## Your Mission

Fix all failing tests by following the prioritized task list in `/docs/testing/test_fix_task_list.md`. Focus on understanding root causes rather than just making tests pass.

## Implementation Guidelines

### 1. P0 Tasks (Day 1) - Critical Blockers

**TASK-001: Fix Enhanced Mock Configuration**
```python
# File: /server/tests/conftest.py
# Find: class EnhancedMockConfig
# Add these attributes to __init__:
self.prefix = ""  # Required by HuggingFace pipeline
self.task = "translation"
self.is_encoder_decoder = True
self.framework = "pt"  # PyTorch

# Critical: Change model_type from invalid value to:
self.model_type = "m2m_100"  # Supported by translation pipeline
```

**Why**: The pipeline validates model type against a whitelist. Our mock was using an unsupported type causing 500 errors.

**TASK-002: Fix E2E ServiceManager Import**
```python
# File: /tests/e2e/utils/service_manager.py
# Create this missing class:

@dataclass
class ServiceConfig:
    name: str
    host: str
    port: int
    health_check_url: str
    startup_timeout: int = 30

class E2EServiceManager:
    def __init__(self):
        self.services = {}
        
    def register_service(self, config: ServiceConfig):
        self.services[config.name] = config
        
    def start_services(self):
        # Implementation for starting services
        pass
        
    def stop_services(self):
        # Implementation for cleanup
        pass
```

**TASK-003: Add UserScript Mock Environment**
```javascript
// File: /userscript/tests/setup.js
// Add before jest setup:

global.GM_addStyle = jest.fn((css) => {
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
});

global.GM_getValue = jest.fn((key, defaultValue) => defaultValue);
global.GM_setValue = jest.fn();
global.GM_registerMenuCommand = jest.fn();
global.GM_xmlhttpRequest = jest.fn((details) => {
    // Mock API responses
    if (details.url.includes('/translate')) {
        details.onload({
            responseText: JSON.stringify({
                translated_text: "Mocked translation",
                detected_language: "en"
            })
        });
    }
});
```

### 2. P1 Tasks (Day 2) - Core Functionality

**TASK-004: Fix Language Detection for Cyrillic**

The current implementation incorrectly returns 'en' for Cyrillic text. Fix:

```python
# File: /server/app/utils/language_detection.py
def detect_language(text: str) -> str:
    # Add proper Unicode range detection
    cyrillic_chars = len([c for c in text if '\u0400' <= c <= '\u04FF'])
    latin_chars = len([c for c in text if 'a' <= c.lower() <= 'z'])
    
    total_alpha = cyrillic_chars + latin_chars
    if total_alpha == 0:
        return 'auto'
        
    if cyrillic_chars / total_alpha > 0.5:
        return 'ru'  # Simplified - could be other Cyrillic languages
    elif latin_chars / total_alpha > 0.5:
        return 'en'  # Simplified - could be other Latin languages
    else:
        return 'auto'  # Mixed content
```

**TASK-005: Fix Character-Based Detection**

```python
# File: /server/app/models/aya_model.py
def _detect_language_from_characters(self, text: str) -> Optional[str]:
    """Detect language based on character analysis."""
    if not text:
        return None
        
    # Unicode block detection
    scripts = {
        'latin': 0,
        'cyrillic': 0,
        'arabic': 0,
        'devanagari': 0,
        'han': 0
    }
    
    for char in text:
        code = ord(char)
        if 0x0041 <= code <= 0x024F:
            scripts['latin'] += 1
        elif 0x0400 <= code <= 0x04FF:
            scripts['cyrillic'] += 1
        elif 0x0600 <= code <= 0x06FF:
            scripts['arabic'] += 1
        elif 0x0900 <= code <= 0x097F:
            scripts['devanagari'] += 1
        elif 0x4E00 <= code <= 0x9FFF:
            scripts['han'] += 1
            
    # Find dominant script
    total = sum(scripts.values())
    if total == 0:
        return None
        
    dominant = max(scripts.items(), key=lambda x: x[1])
    if dominant[1] / total < 0.5:
        return None  # No clear majority
        
    # Map script to language (simplified)
    script_to_lang = {
        'latin': 'en',
        'cyrillic': 'ru',
        'arabic': 'ar',
        'devanagari': 'hi',
        'han': 'zh'
    }
    
    return script_to_lang.get(dominant[0])
```

### 3. P2 Tasks (Day 3) - Validation & Error Handling

**TASK-007: Fix Request Validation Error Codes**

The tests expect 422 for validation errors but get 500/503. Fix:

```python
# File: /server/app/main.py
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": exc.body
        }
    )

# Also ensure model is loaded before handling requests
@app.on_event("startup")
async def startup_event():
    global model, tokenizer
    try:
        # Initialize models
        pass
    except Exception as e:
        logger.error(f"Failed to load models: {e}")
        # Don't exit - tests might be using mocks
```

### 4. Daily Verification Process

After implementing each task:

1. **Run affected tests**:
   ```bash
   # For mock fixes
   cd server && python -m pytest tests/unit/test_request_models.py -v
   
   # For language detection
   cd server && python -m pytest tests/unit/test_*_model.py::*language* -v
   
   # For E2E
   python -m pytest tests/e2e/ -v --tb=short
   ```

2. **Check for regressions**:
   ```bash
   # Run previously passing tests
   cd server && python -m pytest tests/unit/test_model_loader.py -v
   ```

3. **Document any new issues** in `/test_reports/daily_progress.md`

### 5. Common Pitfalls to Avoid

1. **Don't suppress errors** - Fix root causes
2. **Don't modify test assertions** - Fix the implementation
3. **Don't skip tests** - Mark as xfail with clear reason if truly blocked
4. **Don't forget imports** - Update all affected files

### 6. Success Criteria

**Day 1 Success**:
- All test files can be imported without errors
- Basic mock configuration working
- Can run: `pytest tests/` without collection errors

**Day 3 Success**:
- Unit tests: >95% passing
- Integration tests: Running without import errors
- Validation errors return 422, not 500

**Final Success**:
- All tests passing
- No xfailed tests without documented reasons
- Test execution time < 5 minutes
- Coverage > 90%

### 7. Escalation Path

If you encounter blockers:

1. **Architecture issues**: Consult `/docs/testing/test_resolution_plan.md`
2. **Model behavior**: Check `/docs/architecture/multi_model_abstraction.md`
3. **Missing context**: Review git history for recent changes
4. **Fundamental issues**: Document in `/test_reports/blocked_issues.md`

### 8. Tools & Resources

```bash
# Useful commands
pytest --lf  # Run last failed
pytest -x   # Stop on first failure
pytest --pdb # Debug on failure
pytest -k "keyword" # Run tests matching keyword

# Coverage
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Parallel execution
pytest -n auto

# Verbose with short traceback
pytest -vvs --tb=short
```

## Final Notes

Remember: You're not just fixing tests, you're improving system quality. Each test failure is an opportunity to understand the system better and prevent future issues.

Focus on sustainable fixes that will survive future architectural changes. When in doubt, refer to the test resolution plan created by the Senior Test Architect.

Good luck! The team is counting on your expertise to restore confidence in our test suite.