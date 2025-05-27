# API Authentication

Comprehensive guide to authentication and security for the NLLB Translation API.

## Table of Contents

1. [Overview](#overview)
2. [API Key Authentication](#api-key-authentication)
3. [Security Best Practices](#security-best-practices)
4. [Environment Configuration](#environment-configuration)
5. [Client Implementation](#client-implementation)
6. [Troubleshooting](#troubleshooting)

## Overview

The NLLB Translation API uses API key-based authentication to secure access to translation services. This approach provides a balance between security and simplicity, making it suitable for both development and production environments.

### Authentication Methods

- **Primary**: API Key via HTTP header
- **Future**: Bearer token authentication (planned)
- **Development**: Optional authentication bypass (dev mode only)

## API Key Authentication

### How It Works

1. **Server Configuration**: API key is configured in server environment variables
2. **Client Request**: API key is sent in the `X-API-Key` header
3. **Server Validation**: Server validates the key on each request
4. **Access Control**: Valid keys receive full API access

### API Key Format

- **Length**: 32-64 characters (recommended)
- **Characters**: Alphanumeric and special characters
- **Generation**: Use cryptographically secure random generation

### Example API Key
```
your-secret-api-key-12345abcdef
```

## Request Authentication

### Header Format

Include the API key in every request using the `X-API-Key` header:

```http
X-API-Key: your-secret-api-key-12345abcdef
```

### Example Authenticated Request

```bash
curl -X POST "https://your-server:8000/translate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-12345abcdef" \
  -d '{
    "text": "Hello world",
    "target_lang": "rus_Cyrl"
  }'
```

### Authentication Validation

The server validates API keys using middleware that checks every incoming request:

```python
# Server-side validation (FastAPI)
@app.middleware("http")
async def validate_api_key(request: Request, call_next):
    # Skip authentication for health checks
    if request.url.path == "/health":
        return await call_next(request)
    
    api_key = request.headers.get("X-API-Key")
    
    if not api_key:
        return JSONResponse(
            status_code=401,
            content={"detail": "API key required", "error_code": "MISSING_API_KEY"}
        )
    
    if api_key != settings.API_KEY:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid API key", "error_code": "INVALID_API_KEY"}
        )
    
    return await call_next(request)
```

## Security Best Practices

### API Key Management

1. **Generate Strong Keys**
   ```bash
   # Generate a secure API key
   openssl rand -base64 32
   # or
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Store Securely**
   - Use environment variables, not hardcoded values
   - Use secret management systems in production
   - Never commit keys to version control

3. **Rotate Regularly**
   - Change API keys periodically (monthly/quarterly)
   - Implement key rotation without service downtime
   - Monitor for unauthorized key usage

### Transport Security

1. **HTTPS Only**
   ```bash
   # Always use HTTPS in production
   https://your-server:8000/translate
   
   # Never use HTTP with API keys
   # http://your-server:8000/translate  ❌
   ```

2. **TLS Configuration**
   ```nginx
   # nginx SSL configuration
   ssl_protocols TLSv1.2 TLSv1.3;
   ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
   ssl_prefer_server_ciphers off;
   ```

### Network Security

1. **IP Whitelisting** (Optional)
   ```python
   # Server configuration
   ALLOWED_IPS = ["192.168.1.0/24", "10.0.0.0/8"]
   
   @app.middleware("http")
   async def ip_whitelist(request: Request, call_next):
       client_ip = request.client.host
       if not is_ip_allowed(client_ip, ALLOWED_IPS):
           return JSONResponse(status_code=403, content={"detail": "IP not allowed"})
       return await call_next(request)
   ```

2. **Firewall Configuration**
   ```bash
   # Only allow specific ports
   ufw allow 443/tcp   # HTTPS
   ufw allow 22/tcp    # SSH (restrict to admin IPs)
   ufw enable
   ```

### Rate Limiting

Rate limiting is enforced per API key to prevent abuse:

```python
# Per-key rate limiting
@app.post("/translate")
@limiter.limit("10/minute", key_func=get_api_key)
async def translate_text(request: Request, ...):
    # Translation logic
```

## Environment Configuration

### Server Environment Variables

Configure authentication on the server side:

```bash
# .env file
API_KEY=your-secret-api-key-12345abcdef
API_KEY_HEADER_NAME=X-API-Key
DISABLE_AUTH=false  # Only for development
```

### Docker Configuration

```yaml
# docker-compose.yml
version: '3.8'
services:
  nllb-server:
    build: ./server
    environment:
      - API_KEY=${API_KEY}
      - API_KEY_HEADER_NAME=X-API-Key
    env_file:
      - .env
```

### Production Secrets Management

#### Using Docker Secrets
```yaml
# docker-compose.yml (production)
version: '3.8'
services:
  nllb-server:
    build: ./server
    secrets:
      - api_key
    environment:
      - API_KEY_FILE=/run/secrets/api_key

secrets:
  api_key:
    file: ./secrets/api_key.txt
```

#### Using Kubernetes Secrets
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: nllb-api-key
type: Opaque
data:
  api-key: <base64-encoded-key>
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nllb-server
spec:
  template:
    spec:
      containers:
      - name: nllb-server
        env:
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: nllb-api-key
              key: api-key
```

## Client Implementation

### JavaScript/Browser

```javascript
class NLLBClient {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
  }

  async makeRequest(endpoint, data = null) {
    const headers = {
      'Content-Type': 'application/json',
      'X-API-Key': this.apiKey
    };

    const config = {
      method: data ? 'POST' : 'GET',
      headers: headers
    };

    if (data) {
      config.body = JSON.stringify(data);
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, config);

    if (response.status === 401) {
      throw new Error('Authentication failed - check your API key');
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`API Error: ${error.detail}`);
    }

    return await response.json();
  }

  async translate(text, targetLang, sourceLang = 'auto') {
    return await this.makeRequest('/translate', {
      text,
      source_lang: sourceLang,
      target_lang: targetLang
    });
  }
}
```

### Python

```python
import requests
from typing import Optional

class NLLBClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-API-Key': api_key
        })

    def _handle_response(self, response: requests.Response):
        """Handle API response and errors."""
        if response.status_code == 401:
            raise Exception('Authentication failed - check your API key')
        
        if response.status_code == 429:
            raise Exception('Rate limit exceeded - please wait and retry')
        
        if not response.ok:
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', f'HTTP {response.status_code}')
            except:
                error_msg = f'HTTP {response.status_code}'
            raise Exception(f'API Error: {error_msg}')
        
        return response.json()

    def translate(self, text: str, target_lang: str, source_lang: str = 'auto'):
        """Translate text using the API."""
        response = self.session.post(
            f'{self.base_url}/translate',
            json={
                'text': text,
                'source_lang': source_lang,
                'target_lang': target_lang
            }
        )
        return self._handle_response(response)

    def health_check(self):
        """Check API health (no auth required)."""
        response = self.session.get(f'{self.base_url}/health')
        return response.json()
```

### AutoHotkey

```autohotkey
; AutoHotkey API client
global API_KEY := "your-secret-api-key-12345abcdef"
global API_BASE_URL := "https://your-server:8000"

SendTranslationRequest(Text, SourceLang, TargetLang) {
    ; Create JSON request
    JsonData := "{""text"":""" . EscapeJSON(Text) . """,""source_lang"":""" . SourceLang . """,""target_lang"":""" . TargetLang . """}"
    
    try {
        ; Create HTTP request with authentication
        Http := ComObjCreate("WinHttp.WinHttpRequest.5.1")
        Http.Open("POST", API_BASE_URL . "/translate", false)
        Http.SetRequestHeader("Content-Type", "application/json")
        Http.SetRequestHeader("X-API-Key", API_KEY)
        Http.Send(JsonData)
        
        ; Handle response
        if (Http.Status == 401) {
            return "ERROR: Authentication failed - check your API key"
        } else if (Http.Status == 429) {
            return "ERROR: Rate limit exceeded - please wait and retry"
        } else if (Http.Status == 200) {
            ; Parse successful response
            ResponseText := Http.ResponseText
            RegExMatch(ResponseText, """translated_text""\s*:\s*""(.+?)""", Match)
            if (Match1) {
                return UnescapeJSON(Match1)
            } else {
                return "ERROR: Could not parse response"
            }
        } else {
            return "ERROR: Server returned status " . Http.Status
        }
    } catch e {
        return "ERROR: " . e.Message
    }
}
```

## Troubleshooting

### Common Authentication Issues

#### 1. Missing API Key
**Error**: `401 Unauthorized - API key required`

**Solution**:
```bash
# Ensure X-API-Key header is included
curl -H "X-API-Key: your-key" "https://your-server:8000/translate"
```

#### 2. Invalid API Key
**Error**: `401 Unauthorized - Invalid API key`

**Solutions**:
- Verify the API key matches the server configuration
- Check for extra spaces or hidden characters
- Ensure the key hasn't been rotated

#### 3. Wrong Header Name
**Error**: `401 Unauthorized - API key required`

**Solution**:
```bash
# Correct header name
curl -H "X-API-Key: your-key" ...

# Wrong header names:
# curl -H "Authorization: your-key" ...     ❌
# curl -H "API-Key: your-key" ...          ❌
# curl -H "X-Auth-Key: your-key" ...       ❌
```

#### 4. HTTP vs HTTPS
**Error**: SSL/TLS errors or connection issues

**Solution**:
```bash
# Use HTTPS in production
curl https://your-server:8000/translate

# HTTP only for development
curl http://localhost:8000/translate
```

### Testing Authentication

#### 1. Test with curl
```bash
# Test with valid key
curl -H "X-API-Key: valid-key" https://your-server:8000/health

# Test with invalid key
curl -H "X-API-Key: invalid-key" https://your-server:8000/health

# Test without key
curl https://your-server:8000/translate
```

#### 2. Test with Python
```python
import requests

def test_authentication():
    base_url = "https://your-server:8000"
    
    # Test without API key
    response = requests.get(f"{base_url}/translate")
    assert response.status_code == 401
    
    # Test with invalid API key
    headers = {"X-API-Key": "invalid-key"}
    response = requests.post(f"{base_url}/translate", headers=headers)
    assert response.status_code == 401
    
    # Test with valid API key
    headers = {"X-API-Key": "valid-key"}
    response = requests.get(f"{base_url}/health", headers=headers)
    assert response.status_code == 200
    
    print("All authentication tests passed!")

test_authentication()
```

### Security Monitoring

#### Log Analysis
Monitor authentication failures in server logs:

```bash
# Search for authentication failures
grep "401" /var/log/nllb-server/access.log
grep "INVALID_API_KEY" /var/log/nllb-server/app.log

# Monitor for brute force attempts
grep "401" /var/log/nllb-server/access.log | awk '{print $1}' | sort | uniq -c | sort -nr
```

#### Rate Limiting Monitoring
```bash
# Monitor rate limit hits
grep "429" /var/log/nllb-server/access.log
grep "RATE_LIMIT_EXCEEDED" /var/log/nllb-server/app.log
```

### Development Mode

For development environments, authentication can be disabled:

```bash
# Development environment
export DISABLE_AUTH=true
export API_KEY=dev-key-not-required

# Start server in development mode
python server.py
```

**Warning**: Never disable authentication in production environments.

---

## Next Steps

- [API Reference](./reference.md) - Complete API documentation
- [Rate Limiting](./rate_limiting.md) - Detailed rate limiting guide
- [Error Handling](./error_handling.md) - Error codes and handling
- [Deployment Security](../deployment/production.md) - Production security guide