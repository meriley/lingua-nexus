# Contributing to NLLB Translation System

Thank you for your interest in contributing to the NLLB Translation System! This guide will help you get started with contributing to the project.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Contributing Workflow](#contributing-workflow)
5. [Coding Standards](#coding-standards)
6. [Testing Guidelines](#testing-guidelines)
7. [Documentation Standards](#documentation-standards)
8. [Pull Request Process](#pull-request-process)
9. [Release Process](#release-process)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

### Our Standards

- **Be respectful**: Treat everyone with respect and kindness
- **Be inclusive**: Welcome contributions from people of all backgrounds
- **Be collaborative**: Work together constructively
- **Be patient**: Help newcomers learn and grow
- **Be professional**: Maintain a professional atmosphere

### Unacceptable Behavior

- Harassment, discrimination, or inappropriate comments
- Personal attacks or insults
- Spam or promotional content
- Sharing private information without permission

## Getting Started

### Prerequisites

- **Git**: Version control system
- **Python 3.9+**: For server development
- **Node.js 16+**: For userscript development
- **Docker**: For containerized development
- **AutoHotkey**: For Windows client development (optional)

### First-Time Setup

1. **Fork the Repository**
   ```bash
   # Fork on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/tg-text-translate.git
   cd tg-text-translate
   
   # Add upstream remote
   git remote add upstream https://github.com/original-owner/tg-text-translate.git
   ```

2. **Set Up Development Environment**
   ```bash
   # Quick setup with Docker
   docker-compose -f docker-compose.dev.yml up -d
   
   # Or manual setup
   cd server
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements-dev.txt
   ```

3. **Verify Setup**
   ```bash
   # Run tests to ensure everything works
   pytest tests/unit/
   
   # Start development server
   python server.py
   ```

## Development Setup

### Server Development

```bash
# Navigate to server directory
cd server

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Copy environment template
cp .env.example .env
# Edit .env with your settings

# Run in development mode
python server.py
```

### UserScript Development

```bash
# Navigate to userscript directory
cd userscript

# Install dependencies
npm install

# Run tests
npm test

# Run development server with hot reload
npm run dev

# Build for production
npm run build
```

### AutoHotkey Development

```bash
# Copy settings template
cd ahk
cp settings.ini.example settings.ini
# Edit settings.ini with your configuration

# Install AutoHotkey (Windows only)
# Download from: https://www.autohotkey.com/

# Run the script
telegram-nllb-translator.ahk
```

### Docker Development

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Rebuild after changes
docker-compose -f docker-compose.dev.yml build

# Run tests in container
docker-compose -f docker-compose.dev.yml exec nllb-server pytest
```

## Contributing Workflow

### 1. Choose an Issue

- Look for issues labeled `good first issue` for beginners
- Check `help wanted` label for areas needing assistance
- Comment on the issue to express interest

### 2. Create a Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-description
```

### 3. Make Changes

- Follow coding standards (see below)
- Write tests for new functionality
- Update documentation as needed
- Commit frequently with clear messages

### 4. Test Your Changes

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run linting
flake8 app/
black app/ --check

# Run type checking
mypy app/

# Test UserScript (if applicable)
cd userscript && npm test
```

### 5. Submit Pull Request

```bash
# Push changes to your fork
git push origin feature/your-feature-name

# Create pull request on GitHub
# Fill out the PR template completely
```

## Coding Standards

### Python (Server)

#### Code Style

```python
# Use Black for formatting
black app/ tests/

# Use isort for import sorting
isort app/ tests/

# Follow PEP 8 with line length of 88 characters
# Use type hints for all functions
def translate_text(text: str, target_lang: str) -> dict:
    """Translate text to target language.
    
    Args:
        text: The text to translate
        target_lang: Target language code
        
    Returns:
        Translation result dictionary
    """
    pass
```

#### Project Structure

```
server/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── models/              # Pydantic models
│   ├── services/            # Business logic
│   ├── utils/               # Utility functions
│   └── config.py            # Configuration
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
└── requirements.txt
```

#### Error Handling

```python
# Use specific exception types
class TranslationError(Exception):
    """Raised when translation fails."""
    pass

# Provide helpful error messages
def validate_language_code(lang_code: str) -> None:
    if lang_code not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language code: {lang_code}. "
            f"Supported codes: {', '.join(SUPPORTED_LANGUAGES)}"
        )

# Use logging instead of print statements
import logging
logger = logging.getLogger(__name__)

def process_translation(text: str) -> str:
    logger.info(f"Processing translation for {len(text)} characters")
    try:
        result = translate(text)
        logger.info("Translation completed successfully")
        return result
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        raise
```

### JavaScript (UserScript)

#### Code Style

```javascript
// Use ES6+ features
const CONFIG = {
    serverUrl: 'http://localhost:8000',
    apiKey: 'your-api-key'
};

// Use async/await for asynchronous operations
async function translateText(text, targetLang) {
    try {
        const response = await fetch(`${CONFIG.serverUrl}/translate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': CONFIG.apiKey
            },
            body: JSON.stringify({ text, target_lang: targetLang })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Translation failed:', error);
        throw error;
    }
}

// Use JSDoc for documentation
/**
 * Adds translation button to a message element
 * @param {HTMLElement} messageElement - The message container
 * @param {string} text - The text to translate
 */
function addTranslateButton(messageElement, text) {
    // Implementation
}
```

#### UserScript Structure

```
userscript/
├── telegram-nllb-translator.user.js    # Main userscript
├── telegram-nllb-translator.modules.js # Modular components
├── tests/
│   ├── unit/
│   └── integration/
├── package.json
└── jest.config.js
```

### AutoHotkey (Windows Client)

#### Code Style

```autohotkey
; Use descriptive variable names
global CONFIG := {}
CONFIG.TranslationServer := "http://localhost:8000"
CONFIG.ApiKey := "your-api-key"

; Use functions for reusable code
TranslateSelectedText() {
    ; Get selected text
    PreviousClipboard := ClipboardAll
    Clipboard := ""
    Send, ^c
    ClipWait, 2
    
    if (ErrorLevel) {
        ShowNotification("Error", "No text selected")
        return
    }
    
    TextToTranslate := Clipboard
    Clipboard := PreviousClipboard
    
    ; Translate and handle result
    TranslateAndHandleText(TextToTranslate, true)
}

; Use error handling
SendTranslationRequest(Text, SourceLang, TargetLang) {
    try {
        ; HTTP request logic
        Http := ComObjCreate("WinHttp.WinHttpRequest.5.1")
        ; ... implementation
    } catch e {
        return "ERROR: " . e.Message
    }
}
```

## Testing Guidelines

### Test Categories

1. **Unit Tests**: Test individual functions and classes
2. **Integration Tests**: Test API endpoints and service interactions
3. **E2E Tests**: Test complete user workflows
4. **Performance Tests**: Test response times and throughput

### Writing Good Tests

```python
# Test naming convention: test_what_when_then
def test_translate_english_to_russian_returns_correct_translation():
    # Arrange
    text = "Hello, world!"
    source_lang = "eng_Latn"
    target_lang = "rus_Cyrl"
    
    # Act
    result = translate_text(text, source_lang, target_lang)
    
    # Assert
    assert result["translated_text"] is not None
    assert result["detected_source"] == source_lang
    assert len(result["translated_text"]) > 0

# Use fixtures for common setup
@pytest.fixture
def translation_client():
    return TranslationClient(api_key="test-key")

def test_client_authentication(translation_client):
    # Test uses the fixture
    pass

# Test edge cases
@pytest.mark.parametrize("text,expected", [
    ("", ValueError),
    ("x" * 6000, ValueError),
    ("Hello", None),  # Valid case
])
def test_text_validation(text, expected):
    if expected:
        with pytest.raises(expected):
            validate_text_length(text)
    else:
        validate_text_length(text)  # Should not raise
```

### Test Coverage

- Maintain minimum 80% code coverage
- Focus on critical paths and error handling
- Use coverage reports to identify gaps

```bash
# Generate coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Documentation Standards

### Code Documentation

```python
def translate_text(text: str, source_lang: str, target_lang: str) -> TranslationResult:
    """Translate text from source language to target language.
    
    This function uses the NLLB model to perform neural machine translation
    between supported language pairs.
    
    Args:
        text: The input text to translate (1-5000 characters)
        source_lang: Source language code (e.g., 'eng_Latn', 'rus_Cyrl', 'auto')
        target_lang: Target language code (e.g., 'eng_Latn', 'rus_Cyrl')
    
    Returns:
        TranslationResult containing:
            - translated_text: The translated text
            - detected_source: Detected or specified source language
            - confidence: Translation confidence score (0.0-1.0)
            - processing_time_ms: Processing time in milliseconds
    
    Raises:
        ValueError: If text is empty or exceeds maximum length
        LanguageNotSupportedError: If language codes are not supported
        TranslationError: If translation fails due to model issues
    
    Example:
        >>> result = translate_text("Hello world", "eng_Latn", "rus_Cyrl")
        >>> print(result.translated_text)
        "Привет мир"
    """
```

### API Documentation

- Use OpenAPI/Swagger for API documentation
- Include request/response examples
- Document error codes and responses
- Provide client code examples

### User Documentation

- Write clear, step-by-step instructions
- Include screenshots and examples
- Test documentation with new users
- Keep documentation up-to-date with code changes

## Pull Request Process

### Before Submitting

- [ ] Code follows project standards
- [ ] Tests pass locally
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated (for significant changes)
- [ ] No merge conflicts with main branch

### PR Template

```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that causes existing functionality to change)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No security vulnerabilities introduced
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs tests and quality checks
2. **Code Review**: At least one maintainer reviews the code
3. **Testing**: Reviewers test the changes if needed
4. **Approval**: PR is approved and ready for merge
5. **Merge**: Maintainer merges the PR

### After Merge

- Delete feature branch
- Update local main branch
- Close related issues

## Release Process

### Version Numbering

We use [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Workflow

1. **Prepare Release**
   ```bash
   # Update version numbers
   # Update CHANGELOG.md
   # Create release branch
   git checkout -b release/v1.2.0
   ```

2. **Test Release**
   ```bash
   # Run full test suite
   pytest
   
   # Test deployment
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Create Release**
   ```bash
   # Tag release
   git tag -a v1.2.0 -m "Release version 1.2.0"
   git push origin v1.2.0
   
   # Create GitHub release with changelog
   ```

4. **Deploy Release**
   ```bash
   # Deploy to production
   # Update documentation
   # Announce release
   ```

## Getting Help

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and community discussion
- **Documentation**: Check existing docs first
- **Code Review**: Ask specific questions in PR comments

### Types of Help Available

- **Bug Reports**: Use issue templates
- **Feature Requests**: Describe use case and requirements
- **Development Questions**: Ask in discussions
- **Documentation Issues**: Create issues for unclear docs

### How to Ask for Help

1. **Search First**: Check existing issues and discussions
2. **Be Specific**: Provide detailed information and context
3. **Include Examples**: Show what you tried and what happened
4. **Be Patient**: Maintainers are volunteers with limited time

## Recognition

### Contributors

All contributors are recognized in:
- README.md contributors section
- GitHub contributors graph
- Release notes (for significant contributions)

### Types of Contributions

- Code contributions (features, bug fixes)
- Documentation improvements
- Testing and quality assurance
- Issue reporting and triage
- Community support and mentoring

## License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project (MIT License).

---

Thank you for contributing to the NLLB Translation System! Your efforts help make this project better for everyone.