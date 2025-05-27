# Development Environment Setup

Complete guide for setting up a development environment for the NLLB Translation System.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Server Development](#server-development)
4. [UserScript Development](#userscript-development)
5. [AutoHotkey Development](#autohotkey-development)
6. [Testing Setup](#testing-setup)
7. [IDE Configuration](#ide-configuration)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

| Software | Version | Purpose | Installation |
|----------|---------|---------|-------------|
| **Git** | 2.30+ | Version control | [git-scm.com](https://git-scm.com/) |
| **Python** | 3.9+ | Server development | [python.org](https://www.python.org/) |
| **Node.js** | 16+ | UserScript development | [nodejs.org](https://nodejs.org/) |
| **Docker** | 20.10+ | Containerization | [docker.com](https://www.docker.com/) |
| **Docker Compose** | 2.0+ | Multi-container setup | Included with Docker Desktop |

### Optional Software

| Software | Purpose | Installation |
|----------|---------|-------------|
| **AutoHotkey** | Windows client development | [autohotkey.com](https://www.autohotkey.com/) |
| **VS Code** | Recommended IDE | [code.visualstudio.com](https://code.visualstudio.com/) |
| **PyCharm** | Alternative Python IDE | [jetbrains.com](https://www.jetbrains.com/pycharm/) |
| **Postman** | API testing | [postman.com](https://www.postman.com/) |

### System Requirements

#### Minimum Requirements
- **OS**: Windows 10/11, macOS 10.15+, Ubuntu 20.04+
- **CPU**: 4 cores
- **RAM**: 8 GB
- **Storage**: 20 GB free space
- **Network**: Stable internet connection

#### Recommended Requirements
- **OS**: Ubuntu 22.04 LTS or Windows 11
- **CPU**: 8+ cores
- **RAM**: 16 GB
- **GPU**: NVIDIA GPU with 8+ GB VRAM (for model development)
- **Storage**: 50 GB SSD
- **Network**: High-speed internet for model downloads

## Environment Setup

### 1. Clone Repository

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/tg-text-translate.git
cd tg-text-translate

# Add upstream remote
git remote add upstream https://github.com/original-owner/tg-text-translate.git

# Verify remotes
git remote -v
```

### 2. Docker Development Environment

The fastest way to get started is using Docker:

```bash
# Copy environment template
cp server/.env.example server/.env

# Edit environment variables
nano server/.env

# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# Verify services are running
docker-compose -f docker-compose.dev.yml ps

# View logs
docker-compose -f docker-compose.dev.yml logs -f nllb-server
```

#### Development Docker Compose

Create `docker-compose.dev.yml`:

```yaml
version: '3.8'

services:
  nllb-server:
    build:
      context: ./server
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
      - "5678:5678"  # Debugger port
    environment:
      - API_KEY=dev-api-key
      - MODEL_NAME=facebook/nllb-200-distilled-600M
      - DEVICE=cpu
      - LOG_LEVEL=DEBUG
      - RELOAD=true
    volumes:
      - ./server:/app
      - dev_model_cache:/app/models
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: nllb_dev
      POSTGRES_PASSWORD: dev_password
      POSTGRES_DB: nllb_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  dev_model_cache:
  redis_data:
  postgres_data:
```

### 3. Native Development Setup

For direct development without Docker:

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt update
sudo apt install -y python3-dev python3-venv nodejs npm build-essential

# Install system dependencies (macOS)
brew install python@3.11 node npm

# Install system dependencies (Windows)
# Download and install Python, Node.js manually
```

## Server Development

### 1. Python Environment Setup

```bash
cd server

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Verify installation
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import transformers; print(f'Transformers: {transformers.__version__}')"
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

Example `.env` file:

```bash
# Server Configuration
HOST=0.0.0.0
PORT=8000
RELOAD=true
LOG_LEVEL=DEBUG

# API Configuration
API_KEY=dev-api-key-12345
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Model Configuration
MODEL_NAME=facebook/nllb-200-distilled-600M
DEVICE=cpu
MODEL_CACHE_DIR=./models

# Database Configuration (optional)
DATABASE_URL=postgresql://nllb_dev:dev_password@localhost:5432/nllb_dev
REDIS_URL=redis://localhost:6379

# Development Settings
ENABLE_SWAGGER=true
ENABLE_PROFILING=true
```

### 3. Development Tools Setup

```bash
# Install pre-commit hooks
pre-commit install

# Install additional development tools
pip install ipython jupyter notebook

# Set up debugging (optional)
pip install debugpy
```

### 4. Start Development Server

```bash
# Start with auto-reload
python server.py

# Or with uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# With debugging support
python -m debugpy --listen 5678 --wait-for-client server.py
```

### 5. Verify Server Setup

```bash
# Check health endpoint
curl http://localhost:8000/health

# Check API documentation
open http://localhost:8000/docs

# Test translation endpoint
curl -X POST "http://localhost:8000/translate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{"text": "Hello world", "target_lang": "rus_Cyrl"}'
```

## UserScript Development

### 1. Node.js Environment

```bash
cd userscript

# Install dependencies
npm install

# Install development dependencies
npm install --save-dev jest @types/jest eslint prettier

# Verify installation
node --version
npm --version
```

### 2. Development Scripts

Add to `package.json`:

```json
{
  "scripts": {
    "dev": "nodemon --watch src --exec 'npm run build'",
    "build": "node build.js",
    "test": "jest",
    "test:watch": "jest --watch",
    "lint": "eslint src/",
    "format": "prettier --write src/",
    "serve": "http-server dist/ -p 8080"
  }
}
```

### 3. Build System

Create `build.js`:

```javascript
const fs = require('fs');
const path = require('path');

// Read main userscript file
const mainScript = fs.readFileSync('telegram-nllb-translator.user.js', 'utf8');

// Read module file
const modules = fs.readFileSync('telegram-nllb-translator.modules.js', 'utf8');

// Combine and output
const combined = mainScript.replace(
  '// @require telegram-nllb-translator.modules.js',
  `// Embedded modules:\n${modules}`
);

// Ensure dist directory exists
if (!fs.existsSync('dist')) {
  fs.mkdirSync('dist');
}

// Write combined file
fs.writeFileSync('dist/telegram-nllb-translator.user.js', combined);

console.log('UserScript built successfully!');
```

### 4. Testing Setup

Create `jest.config.js`:

```javascript
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/tests/setup.js'],
  testMatch: ['<rootDir>/tests/**/*.test.js'],
  collectCoverageFrom: [
    'src/**/*.js',
    '!src/**/*.test.js'
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html']
};
```

### 5. Development Workflow

```bash
# Start development server
npm run dev

# Run tests
npm test

# Run tests in watch mode
npm run test:watch

# Build for production
npm run build

# Lint code
npm run lint

# Format code
npm run format
```

## AutoHotkey Development

### 1. Setup (Windows Only)

```bash
# Download and install AutoHotkey
# From: https://www.autohotkey.com/

# Copy settings template
cd ahk
cp settings.ini.example settings.ini

# Edit settings
notepad settings.ini
```

### 2. Development Configuration

Edit `settings.ini`:

```ini
[Server]
URL=http://localhost:8000
APIKey=dev-api-key-12345
Timeout=10000

[Languages]
DefaultTarget=rus_Cyrl
AutoDetectSource=1

[Hotkeys]
TranslateSelection=^+t
TranslateClipboard=^+c
ShowSettings=^+s

[Development]
DebugMode=1
LogLevel=2
LogFile=debug.log
```

### 3. Development Tools

Create `debug.ahk` for development:

```autohotkey
; Development helper script
#Include telegram-nllb-translator.ahk

; Debug hotkey
F12::
    ; Show debug information
    MsgBox, 0, Debug Info, 
    (
    Server: %CONFIG.TranslationServer%
    API Key: %CONFIG.ApiKey%
    Debug Mode: %CONFIG.DebugMode%
    )
return

; Reload script hotkey
Ctrl+F12::
    Reload
return
```

### 4. Testing AutoHotkey Scripts

Create `test_runner.ahk`:

```autohotkey
; Simple test runner for AutoHotkey
#NoEnv
#SingleInstance Force

; Test cases
TestCases := []
TestCases.Push({name: "Test URL Validation", func: "TestUrlValidation"})
TestCases.Push({name: "Test JSON Escaping", func: "TestJsonEscaping"})

; Run tests
RunTests()

TestUrlValidation() {
    ; Test valid URLs
    Assert(IsValidUrl("http://localhost:8000"), "localhost URL should be valid")
    Assert(IsValidUrl("https://api.example.com"), "HTTPS URL should be valid")
    Assert(!IsValidUrl("invalid-url"), "Invalid URL should be rejected")
}

TestJsonEscaping() {
    ; Test JSON escaping
    result := EscapeJSON("Hello ""world""")
    Assert(InStr(result, "Hello \""world\"""), "Quotes should be escaped")
}

Assert(condition, message) {
    if (!condition) {
        MsgBox, 16, Test Failed, %message%
        ExitApp, 1
    }
}

RunTests() {
    passed := 0
    failed := 0
    
    for index, test in TestCases {
        try {
            %test.func%()
            passed++
        } catch e {
            failed++
            MsgBox, 16, Test Failed, %test.name%: %e.message%
        }
    }
    
    MsgBox, 64, Test Results, Passed: %passed%`nFailed: %failed%
}
```

## Testing Setup

### 1. Unit Testing

```bash
cd server

# Run unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_language_detection.py -v
```

### 2. Integration Testing

```bash
# Start test services
docker-compose -f docker-compose.test.yml up -d

# Run integration tests
pytest tests/integration/ -v

# Clean up
docker-compose -f docker-compose.test.yml down
```

### 3. E2E Testing

```bash
cd userscript

# Install Playwright
npx playwright install

# Run E2E tests
npm run test:e2e

# Run with headed browser
npm run test:e2e -- --headed
```

## IDE Configuration

### VS Code Setup

Install recommended extensions by creating `.vscode/extensions.json`:

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "ms-python.isort",
    "ms-python.flake8",
    "ms-python.mypy-type-checker",
    "ms-vscode.vscode-json",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-typescript-next"
  ]
}
```

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "./server/venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/.pytest_cache": true,
    "**/node_modules": true
  }
}
```

Create `.vscode/launch.json` for debugging:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI Server",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/server/server.py",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}/server",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/server"
      }
    },
    {
      "name": "Python: Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["tests/", "-v"],
      "cwd": "${workspaceFolder}/server",
      "console": "integratedTerminal"
    }
  ]
}
```

### PyCharm Setup

1. **Create Project**: Open the `server` directory as a PyCharm project
2. **Configure Interpreter**: Set Python interpreter to `server/venv/bin/python`
3. **Mark Source Root**: Mark `server/app` as source root
4. **Configure Testing**: Set default test runner to pytest
5. **Install Plugins**: Install Docker, Markdown, and any other useful plugins

## Troubleshooting

### Common Issues

#### Python Environment Issues

```bash
# Issue: ModuleNotFoundError
# Solution: Ensure virtual environment is activated
source venv/bin/activate
pip list  # Verify packages are installed

# Issue: Permission denied
# Solution: Check file permissions
chmod +x server.py

# Issue: Port already in use
# Solution: Find and kill process using port
lsof -i :8000
kill -9 <PID>
```

#### Docker Issues

```bash
# Issue: Container won't start
# Solution: Check logs
docker-compose logs nllb-server

# Issue: Port conflicts
# Solution: Change ports in docker-compose.yml
ports:
  - "8001:8000"  # Change host port

# Issue: Volume mount issues
# Solution: Check permissions and paths
docker-compose down -v  # Remove volumes
docker-compose up -d    # Recreate
```

#### Model Download Issues

```bash
# Issue: Model download fails
# Solution: Download manually
python -c "
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
model_name = 'facebook/nllb-200-distilled-600M'
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
print('Model downloaded successfully')
"

# Issue: Insufficient disk space
# Solution: Clean up space
docker system prune -a
pip cache purge
```

#### UserScript Issues

```bash
# Issue: npm install fails
# Solution: Clear cache and reinstall
npm cache clean --force
rm -rf node_modules package-lock.json
npm install

# Issue: Build fails
# Solution: Check Node.js version
node --version  # Should be 16+
npm --version
```

### Getting Help

1. **Check Documentation**: Review relevant documentation sections
2. **Search Issues**: Look for similar issues on GitHub
3. **Enable Debug Mode**: Set `LOG_LEVEL=DEBUG` for detailed logs
4. **Create Minimal Reproduction**: Isolate the problem
5. **Ask for Help**: Create a GitHub issue with:
   - Clear description of the problem
   - Steps to reproduce
   - Environment details
   - Error messages and logs

### Performance Optimization

#### Development Performance

```bash
# Use smaller model for development
export MODEL_NAME=facebook/nllb-200-distilled-600M

# Enable model caching
export MODEL_CACHE_DIR=./models

# Use CPU for development (faster startup)
export DEVICE=cpu

# Enable development mode optimizations
export PYTHONOPTIMIZE=0  # Disable optimizations for debugging
export PYTHONDONTWRITEBYTECODE=1  # Don't create .pyc files
```

#### Testing Performance

```bash
# Run tests in parallel
pytest -n auto

# Skip slow tests during development
pytest -m "not slow"

# Use test-specific configuration
export TEST_MODEL_NAME=facebook/nllb-200-distilled-600M
export TEST_DEVICE=cpu
```

---

## Next Steps

Once your development environment is set up:

1. **Read the Code**: Familiarize yourself with the codebase structure
2. **Run Tests**: Ensure everything works correctly
3. **Make Changes**: Start with small improvements or bug fixes
4. **Submit PR**: Follow the contribution guidelines

For more information, see:
- [Contributing Guidelines](../CONTRIBUTING.md)
- [Coding Standards](./coding_standards.md)
- [Testing Guide](../testing/testing_strategy.md)
- [Architecture Overview](../architecture/system_architecture.md)