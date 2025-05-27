# UserScript Troubleshooting Guide

Complete troubleshooting guide for the Telegram NLLB Translator UserScript.

## Table of Contents

1. [Common Issues](#common-issues)
2. [Installation Problems](#installation-problems)
3. [Configuration Issues](#configuration-issues)
4. [Translation Problems](#translation-problems)
5. [Pre-Send Translation Issues](#pre-send-translation-issues)
6. [Debugging Steps](#debugging-steps)
7. [Browser Compatibility](#browser-compatibility)

## Common Issues

### Issue 1: UserScript Not Working at All

**Symptoms:**
- No translate buttons appear
- No console messages
- Settings menu not available

**Solutions:**

1. **Check UserScript Manager Installation**
   ```javascript
   // Open browser console (F12) and check:
   console.log('Tampermonkey installed:', typeof GM_setValue !== 'undefined');
   ```

2. **Verify Script is Enabled**
   - Open Tampermonkey dashboard
   - Find "Telegram NLLB Translator"
   - Ensure toggle is ON (green)

3. **Check Script Matches**
   - Verify you're on `web.telegram.org/*`
   - Script should work on `/k/`, `/a/`, and `/z/` versions

4. **Force Reinstall**
   - Delete existing script from Tampermonkey
   - Install the new v2 version
   - Configure settings

### Issue 2: Translate Buttons Don't Appear

**Symptoms:**
- UserScript is running but no buttons show
- Console shows initialization messages

**Solutions:**

1. **Enable Debug Mode**
   - Open settings (Tampermonkey menu → NLLB Translator Settings)
   - Enable "Debug mode"
   - Refresh page and check console

2. **Check Message Detection**
   ```javascript
   // In console, check if messages are found:
   console.log('Messages found:', document.querySelectorAll('.message, .Message, [class*="message"]').length);
   ```

3. **Manual Button Addition**
   ```javascript
   // Test button addition manually:
   const messages = document.querySelectorAll('.message, .Message');
   console.log('Attempting to add buttons to', messages.length, 'messages');
   ```

4. **Telegram Version Compatibility**
   - Try different Telegram Web versions (/k/, /a/, /z/)
   - Clear browser cache and cookies
   - Disable other extensions temporarily

### Issue 3: Translation Fails

**Symptoms:**
- Buttons appear but translation doesn't work
- Error messages appear

**Solutions:**

1. **Check API Configuration**
   ```bash
   # Test server directly:
   curl -X POST "http://localhost:8000/translate" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your-api-key" \
     -d '{"text": "Hello", "target_lang": "rus_Cyrl"}'
   ```

2. **Verify Settings**
   - Server URL format: `http://localhost:8000` (no trailing slash)
   - API key is correctly set
   - Target language is valid (`eng_Latn` or `rus_Cyrl`)

3. **Check Network Issues**
   ```javascript
   // In console, test connectivity:
   fetch('http://localhost:8000/health')
     .then(r => r.json())
     .then(console.log)
     .catch(console.error);
   ```

4. **CORS Issues**
   - Ensure server allows requests from `web.telegram.org`
   - Check server CORS configuration
   - Use HTTPS if accessing from HTTPS Telegram

## Installation Problems

### Problem: Script Won't Install

**Solution Steps:**

1. **Check UserScript Manager**
   - Install Tampermonkey (Chrome) or Greasemonkey (Firefox)
   - Ensure it's enabled and has permissions

2. **Manual Installation**
   - Copy the entire script content
   - Open Tampermonkey dashboard
   - Click "Create new script"
   - Paste content and save

3. **URL Matching Issues**
   ```javascript
   // Verify @match directives:
   // @match        https://web.telegram.org/*
   ```

### Problem: Multiple Versions Installed

**Solution:**
1. Open Tampermonkey dashboard
2. Disable/delete old versions
3. Keep only the latest v2 script
4. Clear browser cache

## Configuration Issues

### Invalid Server URL

**Common Mistakes:**
- `http://localhost:8000/` (trailing slash)
- `localhost:8000` (missing protocol)
- `https://localhost:8000` (wrong protocol for development)

**Correct Format:**
- Development: `http://localhost:8000`
- Production: `https://your-domain.com`

### API Key Problems

**Symptoms:**
- "Invalid API key" errors
- 401 Unauthorized responses

**Solutions:**
1. **Generate New API Key**
   ```bash
   # On server:
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Check Key Format**
   - No spaces or special characters
   - Matches exactly what's in server .env file

3. **Test API Key**
   ```bash
   curl -H "X-API-Key: your-key" http://localhost:8000/health
   ```

## Translation Problems

### Empty Translations

**Causes:**
- Text too short or empty
- Language detection issues
- Server model problems

**Solutions:**
1. **Test with Known Text**
   ```javascript
   // In console:
   // Enable debug mode and try translating "Hello world"
   ```

2. **Check Text Content**
   ```javascript
   // Debug text extraction:
   const textElement = document.querySelector('.text-content');
   console.log('Text:', textElement?.textContent);
   ```

### Slow Translation

**Causes:**
- Large text blocks
- Server overload
- Network latency

**Solutions:**
1. **Check Server Performance**
   ```bash
   curl -w "@-" -o /dev/null -s "http://localhost:8000/health" <<< "
   time_namelookup:  %{time_namelookup}
   time_connect:     %{time_connect}
   time_total:       %{time_total}
   "
   ```

2. **Optimize Text Length**
   - Limit to 1000 characters for best performance
   - Break long messages into chunks

### Translation Quality Issues

**Improvements:**
1. **Specify Source Language**
   - Modify script to detect language better
   - Use explicit language codes instead of "auto"

2. **Model Selection**
   - Use larger model (1.3B) for better quality
   - Ensure model is properly loaded

## Pre-Send Translation Issues

### Toolbar Not Appearing

**Symptoms:**
- Input areas detected but no toolbar
- Console shows input detection

**Solutions:**
1. **Enable Feature**
   - Open settings
   - Enable "Enable pre-send translation toolbar"
   - Refresh page

2. **Check Input Detection**
   ```javascript
   // In console:
   const inputs = document.querySelectorAll('[contenteditable="true"]');
   console.log('Editable inputs found:', inputs.length);
   ```

3. **Manual Toolbar Addition**
   ```javascript
   // Test toolbar creation:
   const input = document.querySelector('.input-message-input');
   if (input) console.log('Input found:', input);
   ```

### Auto-Translation Not Working

**Symptoms:**
- Manual translation works
- Auto-translate toggle is on
- Messages send without translation

**Solutions:**
1. **Check Send Button Detection**
   ```javascript
   // Debug send button finding:
   const sendBtn = document.querySelector('.btn-send, [class*="send"]');
   console.log('Send button:', sendBtn);
   ```

2. **Event Handler Issues**
   - Telegram may override click handlers
   - Try different timing for event attachment

3. **Content Update Issues**
   ```javascript
   // Test input content update:
   const input = document.querySelector('[contenteditable="true"]');
   input.textContent = 'Test';
   input.dispatchEvent(new Event('input', { bubbles: true }));
   ```

## Debugging Steps

### Enable Debug Mode

1. Open UserScript settings
2. Enable "Debug mode"
3. Refresh page
4. Open browser console (F12)
5. Look for `[NLLB v2]` messages

### Console Commands for Testing

```javascript
// Check if script is loaded
console.log('Script loaded:', typeof GM_setValue !== 'undefined');

// Test translation function directly
GM_xmlhttpRequest({
  method: 'POST',
  url: 'http://localhost:8000/translate',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  data: JSON.stringify({
    text: 'Hello world',
    target_lang: 'rus_Cyrl'
  }),
  onload: function(response) {
    console.log('Direct translation test:', response.responseText);
  }
});

// Check message elements
const messages = document.querySelectorAll('.message, .Message');
console.log('Messages found:', messages.length);

// Check input elements
const inputs = document.querySelectorAll('[contenteditable="true"]');
console.log('Input areas found:', inputs.length);

// Test button addition
messages.forEach((msg, i) => {
  console.log(`Message ${i}:`, msg.querySelector('.text-content')?.textContent);
});
```

### Network Debugging

1. **Open Developer Tools** (F12)
2. **Go to Network tab**
3. **Try translation**
4. **Check for:**
   - POST request to `/translate`
   - Request headers (API key)
   - Response status and content
   - CORS errors

### Common Console Errors

**Error: "GM_xmlhttpRequest is not defined"**
- UserScript manager not installed or disabled
- Script not running in userscript context

**Error: "Failed to fetch"**
- Server not running
- Wrong server URL
- CORS issues

**Error: "Invalid API key"**
- API key mismatch
- Missing X-API-Key header

## Browser Compatibility

### Chrome
- ✅ Works with Tampermonkey
- ✅ Full feature support
- ⚠️ May need permissions for localhost

### Firefox
- ✅ Works with Greasemonkey/Tampermonkey
- ✅ Full feature support
- ⚠️ Stricter security policies

### Edge
- ✅ Works with Tampermonkey
- ✅ Full feature support

### Safari
- ❌ Limited userscript support
- 🔄 Consider using browser extension instead

## Advanced Troubleshooting

### Script Injection Issues

```javascript
// Check if script is properly injected
console.log('Script context:', window.location.href);
console.log('GM functions available:', {
  setValue: typeof GM_setValue,
  getValue: typeof GM_getValue,
  xmlhttpRequest: typeof GM_xmlhttpRequest
});
```

### Telegram DOM Changes

```javascript
// Monitor DOM changes
const observer = new MutationObserver((mutations) => {
  console.log('DOM mutations:', mutations.length);
});
observer.observe(document.body, { childList: true, subtree: true });
```

### Performance Issues

```javascript
// Check script performance
console.time('button-addition');
// ... button addition code ...
console.timeEnd('button-addition');
```

## Getting Additional Help

### Information to Provide

When reporting issues, include:

1. **Browser and Version**
2. **UserScript Manager and Version**
3. **Telegram Web Version** (/k/, /a/, or /z/)
4. **Console Errors** (screenshots or copy-paste)
5. **Server Configuration** (redacted API keys)
6. **Steps to Reproduce**

### Debug Information Script

```javascript
// Run this in console to get debug info:
console.log('Debug Information:');
console.log('Browser:', navigator.userAgent);
console.log('URL:', window.location.href);
console.log('UserScript context:', typeof GM_setValue !== 'undefined');
console.log('Messages found:', document.querySelectorAll('.message, .Message').length);
console.log('Input areas found:', document.querySelectorAll('[contenteditable="true"]').length);
console.log('Script elements:', document.querySelectorAll('script[src*="telegram"]').length);
```

---

## Quick Fix Checklist

- [ ] UserScript manager installed and enabled
- [ ] Latest v2 script installed
- [ ] Settings configured (server URL, API key)
- [ ] Debug mode enabled
- [ ] Server running and accessible
- [ ] Browser console checked for errors
- [ ] Page refreshed after configuration changes
- [ ] Other extensions disabled (for testing)
- [ ] Correct Telegram Web version
- [ ] API key tested with curl command

If all else fails, try the v2 userscript provided above, which includes many improvements and better debugging capabilities.