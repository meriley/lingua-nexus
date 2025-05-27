# Multi-Model Translation UserScript

This UserScript integrates with the **Multi-Model Translation System** to provide advanced translation functionality directly in the Telegram Web interface. It supports multiple AI translation models including NLLB, Aya Expanse 8B, and adaptive AI-powered optimization.

## 🚀 Features

### **Core Translation Capabilities**
- **Multi-Model Support**: Choose between NLLB, Aya Expanse 8B, or let the system auto-select
- **Adaptive Translation**: AI-powered optimization for high-quality results
- **Progressive Translation**: Real-time streaming for long texts with quality improvements
- **Smart Language Detection**: Automatic source language identification
- **Bidirectional Language Selection**: Intuitive language pair management

### **User Experience**
- **One-Click Translation**: Adds translation buttons to Telegram messages
- **Platform Support**: Compatible with web.telegram.org/k/, web.telegram.org/a/, and web.telegram.org/z/
- **Original Text Preservation**: Hover to see original content
- **Quality Indicators**: Visual feedback on translation quality (A-F grades)
- **Recent Languages**: Quick access to frequently used language pairs
- **Keyboard Shortcuts**: Power user hotkey support

### **Advanced Features**
- **Quality Assessment**: Real-time translation quality scoring
- **Batch Processing**: Translate multiple messages efficiently
- **Semantic Chunking**: Intelligent text segmentation for optimal results
- **Caching**: Smart caching for improved performance
- **Offline Fallback**: Graceful degradation when server unavailable

## 📋 Requirements

- **Browser**: Chrome, Firefox, Safari, or Edge with userscript extension
- **Extension**: Tampermonkey, Greasemonkey, or Violentmonkey
- **Server**: Access to a running Multi-Model Translation System

## Installation

1. Install the Tampermonkey or Greasemonkey extension for your browser:
   - Chrome: [Tampermonkey](https://chrome.google.com/webstore/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo)
   - Firefox: [Greasemonkey](https://addons.mozilla.org/en-US/firefox/addon/greasemonkey/)

2. Click on the extension icon and select "Create a new script"

3. Delete any default content and paste the entire content of `telegram-nllb-translator.user.js`

4. Save the script (Ctrl+S or Cmd+S)

5. Navigate to Telegram Web (https://web.telegram.org/) and verify the script is working

## ⚙️ Configuration

### **Access Settings**
1. Click on the Tampermonkey/Greasemonkey icon in your browser
2. Select **"Multi-Model Translator Settings"** from the menu
3. Configure your preferences using the comprehensive settings panel

### **Server Configuration**
- **Translation Server URL**: Your Multi-Model Translation Server (e.g., `http://localhost:8000`)
- **API Key**: Authentication key for your server instance
- **API Endpoint**: Choose your API implementation:
  - **Multi-Model API**: Full model selection and advanced features
  - **Legacy NLLB API**: Backward compatibility mode
  - **Adaptive API**: AI-powered optimization (recommended)

### **Translation Preferences**
- **Default Model**: Choose primary translation model:
  - **Auto-Select**: Intelligent model selection based on content
  - **NLLB**: Fast, efficient translations (200 languages)
  - **Aya Expanse 8B**: High-quality multilingual model
- **Quality Preference**: Balance speed vs. quality:
  - **Fast**: Quick translations with good quality
  - **Balanced**: Optimal speed/quality trade-off (recommended)
  - **Quality**: Maximum quality with longer processing time
- **Language Settings**:
  - **Default Source Language**: Auto-detect or specific language
  - **Default Target Language**: Your preferred translation target
  - **Language Selection Mode**: Single language vs. language pairs

### **Advanced Features**
- **Adaptive Translation**: Enable AI-powered optimization for complex texts
- **Progressive Translation**: Real-time streaming for long content
- **Quality Indicators**: Show A-F quality grades
- **Recent Languages**: Quick access to frequently used language pairs
- **Batch Processing**: Translate multiple messages simultaneously
- **Semantic Chunking**: Intelligent text segmentation
- **Smart Caching**: Improve performance with intelligent caching

## 📱 Usage

### **Basic Translation**
1. **Open Telegram Web**: Navigate to https://web.telegram.org/ in your browser
2. **Translate Messages**: Click the **🌐 Translate** button next to any message
3. **View Results**: The message will be translated with quality indicators
4. **Access Original**: Hover over translated text to see the original content

### **Advanced Features**

#### **Model Selection**
- **Smart Mode**: Click and hold the translate button for model selection menu
- **Quick Switch**: Use keyboard shortcuts to switch between models
- **Auto-Select**: Let the system choose optimal model based on content type

#### **Language Management**
- **Language Pairs**: Configure source-target language combinations
- **Recent Languages**: Access frequently used language pairs from quick menu
- **Language Swap**: Instantly swap source and target languages
- **Bulk Selection**: Select languages for batch translation tasks

#### **Quality Features**
- **Progressive Translation**: Watch real-time improvements for long texts
- **Quality Grades**: See A-F quality ratings with detailed breakdowns
- **Optimization**: Enable adaptive optimization for technical content
- **Chunking**: Automatic intelligent text segmentation for optimal results

#### **Keyboard Shortcuts**
- **Ctrl+Alt+T**: Quick translate selected text
- **Ctrl+Shift+L**: Open language selector
- **Ctrl+Shift+M**: Switch translation model
- **Ctrl+Shift+Q**: Toggle quality mode

### **API Integration Examples**

#### **Multi-Model API Usage**
```javascript
// Standard translation with model selection
const result = await translate({
  text: "Hello world",
  source_lang: "en",
  target_lang: "ru", 
  model: "aya"  // or "nllb"
});
```

#### **Adaptive API Usage**
```javascript
// High-quality adaptive translation
const result = await adaptiveTranslate({
  text: "Complex technical documentation...",
  source_lang: "en",
  target_lang: "ru",
  user_preference: "quality",
  force_optimization: true
});
```

## 🔧 Troubleshooting

### **Common Issues**

#### **Translation Button Missing**
- **Solution**: Refresh the page and verify script is enabled in extension menu
- **Alternative**: Check Telegram Web version compatibility (k/, a/, z/ variants)
- **Debug**: Enable debug mode to see console initialization messages

#### **Translation Failures**
- **Server Connection**: Verify server URL is correct and accessible
- **API Authentication**: Check API key configuration and permissions
- **Model Availability**: Ensure selected model is loaded on server
- **Language Support**: Verify language pair is supported by selected model

#### **Performance Issues**
- **Slow Translations**: Switch to "fast" quality preference or NLLB model
- **High Memory Usage**: Disable progressive translation for shorter texts
- **Server Overload**: Enable smart caching and reduce concurrent requests

#### **Quality Problems**
- **Poor Results**: Switch to Aya model or enable adaptive optimization
- **Inconsistent Terminology**: Use quality mode with semantic chunking
- **Context Loss**: Enable progressive translation for long texts

### **Advanced Diagnostics**

#### **Enable Debug Mode**
1. Open settings panel
2. Enable "Debug Mode" 
3. Open browser console (F12)
4. Attempt translation and review console output

#### **Test Server Connection**
```javascript
// Test basic connectivity
fetch('http://localhost:8000/health')
  .then(r => r.json())
  .then(data => console.log('Server status:', data));
```

#### **Validate API Configuration**
```javascript
// Test API authentication
fetch('http://localhost:8000/models', {
  headers: { 'X-API-Key': 'your-key' }
})
.then(r => r.json())
.then(models => console.log('Available models:', models));
```

### **Browser Compatibility**
- **Chrome/Chromium**: Full support for all features
- **Firefox**: Full support with Greasemonkey/Tampermonkey
- **Safari**: Limited support, use Tampermonkey
- **Edge**: Full support with Tampermonkey

### **Error Reference**

| Error Code | Meaning | Solution |
|------------|---------|----------|
| **AUTH_FAILED** | Invalid API key | Check API key in settings |
| **MODEL_NOT_LOADED** | Model unavailable | Verify model is loaded on server |
| **RATE_LIMITED** | Too many requests | Wait and retry or upgrade plan |
| **LANG_NOT_SUPPORTED** | Language pair invalid | Check language support for selected model |
| **SERVER_ERROR** | Internal server error | Check server logs and restart if needed |

### **Getting Help**
- **Documentation**: Check API reference for endpoint details
- **Logs**: Enable debug mode and check browser console
- **Server Status**: Verify health endpoint returns "healthy"
- **Community**: Report issues with detailed error information and configuration