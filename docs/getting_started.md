# Getting Started

Quick start guide to set up and use the NLLB Translation System.

## Table of Contents

1. [Overview](#overview)
2. [System Requirements](#system-requirements)
3. [Installation Methods](#installation-methods)
4. [Quick Setup](#quick-setup)
5. [First Translation](#first-translation)
6. [Next Steps](#next-steps)

## Overview

The NLLB Translation System provides self-hosted English↔Russian translation with three ways to use it:

- **🐳 Docker** (Recommended): Complete setup with one command
- **🖥️ Manual Setup**: Custom installation for advanced users
- **☁️ Cloud Deployment**: Production-ready cloud hosting

## System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| **OS** | Linux (Ubuntu 20.04+), Windows 10/11, macOS 12+ |
| **CPU** | 4 cores, 2.0 GHz |
| **RAM** | 8 GB |
| **Storage** | 10 GB free space |
| **Network** | Internet connection for model download |

### Recommended Requirements

| Component | Recommendation |
|-----------|----------------|
| **OS** | Ubuntu 22.04 LTS |
| **CPU** | 8+ cores, 3.0 GHz |
| **RAM** | 16 GB |
| **GPU** | NVIDIA GPU with 8+ GB VRAM |
| **Storage** | 20 GB SSD |
| **Network** | 1 Gbps connection |

## Installation Methods

### 🐳 Docker Installation (Recommended)

**Best for**: Most users, easy setup, consistent environment

```bash
# Clone the repository
git clone https://github.com/yourusername/tg-text-translate.git
cd tg-text-translate

# Configure environment
cp server/.env.example server/.env
# Edit .env with your settings (see configuration section)

# Start the service
docker-compose up -d

# Verify it's running
curl http://localhost:8000/health
```

### 🖥️ Manual Installation

**Best for**: Advanced users, development, custom setups

#### Server Setup

```bash
# Install Python 3.9+
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Clone repository
git clone https://github.com/yourusername/tg-text-translate.git
cd tg-text-translate/server

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start server
python server.py
```

#### Client Setup

**Browser UserScript:**
1. Install [Tampermonkey](https://www.tampermonkey.net/) browser extension
2. Create new script with content from `userscript/telegram-nllb-translator.user.js`
3. Configure server URL in script

**Windows Desktop:**
1. Install [AutoHotkey](https://www.autohotkey.com/)
2. Copy `ahk/settings.ini.example` to `ahk/settings.ini`
3. Configure server URL and API key
4. Run `ahk/telegram-nllb-translator.ahk`

### ☁️ Cloud Deployment

**Best for**: Production use, high availability, team access

See [Production Deployment Guide](./deployment/production.md) for cloud hosting options.

## Quick Setup

### Step 1: Basic Configuration

Create and edit your environment file:

```bash
# Copy example configuration
cp server/.env.example server/.env

# Edit configuration
nano server/.env
```

**Essential settings:**
```bash
# Server settings
HOST=0.0.0.0
PORT=8000
API_KEY=your-secret-api-key-here

# Model settings
MODEL_NAME=facebook/nllb-200-distilled-600M

# Optional: GPU settings (if available)
DEVICE=cuda
```

### Step 2: Generate API Key

Create a secure API key for authentication:

```bash
# Generate a random API key
python3 -c "import secrets; print('API_KEY=' + secrets.token_urlsafe(32))"

# Or use OpenSSL
echo "API_KEY=$(openssl rand -base64 32)"
```

Copy the generated key to your `.env` file.

### Step 3: Start the Server

#### Using Docker (Recommended)
```bash
# Start in background
docker-compose up -d

# View logs
docker-compose logs -f nllb-server

# Check status
docker-compose ps
```

#### Using Manual Installation
```bash
# Activate virtual environment
source venv/bin/activate

# Start server
python server.py

# Or with custom settings
HOST=0.0.0.0 PORT=8000 python server.py
```

### Step 4: Verify Installation

```bash
# Check server health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "model_loaded": true,
  "device": "cpu",
  "memory_usage": "2.1GB"
}
```

## First Translation

### Test with curl

```bash
# Replace with your API key
API_KEY="your-api-key-here"

# Test English to Russian
curl -X POST "http://localhost:8000/translate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "text": "Hello, how are you?",
    "target_lang": "rus_Cyrl"
  }'

# Expected response:
{
  "translated_text": "Привет, как дела?",
  "detected_source": "eng_Latn",
  "processing_time_ms": 234
}
```

### Test with Browser UserScript

1. **Setup UserScript**
   - Install Tampermonkey browser extension
   - Create new script
   - Copy content from `userscript/telegram-nllb-translator.user.js`
   - Update server URL: `http://localhost:8000`
   - Update API key: `your-api-key-here`

2. **Test on Telegram Web**
   - Open [web.telegram.org](https://web.telegram.org)
   - Look for "🌐 Translate" buttons next to messages
   - Click button to translate a message

### Test with Windows Desktop

1. **Setup AutoHotkey Script**
   - Install AutoHotkey
   - Copy `ahk/settings.ini.example` to `ahk/settings.ini`
   - Edit settings:
   ```ini
   [Server]
   URL=http://localhost:8000
   APIKey=your-api-key-here
   ```

2. **Test Translation**
   - Run `ahk/telegram-nllb-translator.ahk`
   - Select text in any application
   - Press `Ctrl+Shift+T` to translate

## Next Steps

### Performance Optimization

1. **Enable GPU Support** (if available)
   ```bash
   # Check if CUDA is available
   python3 -c "import torch; print(torch.cuda.is_available())"
   
   # Update .env file
   DEVICE=cuda
   ```

2. **Use Larger Model** (better quality)
   ```bash
   # Edit .env file
   MODEL_NAME=facebook/nllb-200-distilled-1.3B
   ```

3. **Production Setup**
   - Enable HTTPS with SSL certificates
   - Configure reverse proxy (nginx)
   - Set up monitoring and logging
   - Implement backup and recovery

### Security Configuration

1. **Change Default API Key**
   ```bash
   # Generate new secure key
   NEW_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
   echo "Update your .env file with: API_KEY=$NEW_KEY"
   ```

2. **Enable HTTPS** (for remote access)
   ```bash
   # Install SSL certificate
   sudo apt install certbot
   sudo certbot certonly --standalone -d your-domain.com
   ```

3. **Configure Firewall**
   ```bash
   # Allow only necessary ports
   sudo ufw allow 22/tcp    # SSH
   sudo ufw allow 443/tcp   # HTTPS
   sudo ufw enable
   ```

### Advanced Features

1. **Rate Limiting Configuration**
   - Adjust rate limits in server configuration
   - Implement per-user rate limiting
   - Monitor usage patterns

2. **Monitoring Setup**
   - Configure health checks
   - Set up performance monitoring
   - Implement alerting

3. **Backup Configuration**
   - Backup model cache
   - Export configuration settings
   - Document recovery procedures

### Integration Options

1. **API Integration**
   - Integrate with existing applications
   - Build custom clients
   - Implement batch processing

2. **Workflow Automation**
   - Set up automated translation pipelines
   - Integrate with chat systems
   - Build custom UI interfaces

## Troubleshooting Quick Fixes

### Docker Issues

**ImportError: cannot import name 'deprecated' from 'typing_extensions'**
```bash
# Rebuild with latest dependencies
docker compose build --no-cache nllb-server
docker compose up -d
```

**ImportError: Using `low_cpu_mem_usage=True` requires Accelerate**
```bash
# Update to latest version with accelerate library
git pull origin main
docker compose build --no-cache nllb-server
```

**Container exits during startup**
```bash
# Check Docker logs
docker compose logs nllb-server

# Verify adequate resources
docker stats
docker system df
```

### Server Won't Start

```bash
# Check Python version
python3 --version

# Check dependencies
pip list | grep -E "(torch|transformers|fastapi|accelerate|typing_extensions)"

# Check port availability
sudo netstat -tlnp | grep 8000

# Check disk space
df -h
```

### Model Download Issues

```bash
# Manual model download
python3 -c "
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
model_name = 'facebook/nllb-200-distilled-600M'
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
print('Model downloaded successfully')
"
```

### Permission Issues

```bash
# Fix file permissions
sudo chown -R $USER:$USER /path/to/tg-text-translate

# Fix Python permissions
sudo chmod +x server/server.py
```

### Memory Issues

```bash
# Check memory usage
free -h

# Monitor GPU memory (if using CUDA)
nvidia-smi

# Reduce model size in .env
MODEL_NAME=facebook/nllb-200-distilled-600M
```

## Getting Help

- **📖 Documentation**: [Complete User Guide](./user_guide.md)
- **🔧 API Reference**: [API Documentation](./api/reference.md)
- **🏗️ Architecture**: [System Architecture](./architecture/system_architecture.md)
- **🚀 Deployment**: [Production Guide](./deployment/production.md)
- **🐛 Issues**: [GitHub Issues](https://github.com/yourusername/tg-text-translate/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/yourusername/tg-text-translate/discussions)

---

**🎉 Congratulations!** You now have a working NLLB Translation System. Start translating and explore the advanced features in the [User Guide](./user_guide.md).