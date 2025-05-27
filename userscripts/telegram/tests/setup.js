// Mock LanguageManager class
global.LanguageManager = class {
  constructor() {
    this.languages = new Map();
    this.recentLanguages = [];
    this.recentLanguagePairs = [];
    this.favorites = [];
    this.favoritePairs = [];
  }

  loadRecentLanguages() {
    // Mock implementation
    this.recentLanguages = ['eng_Latn', 'fra_Latn', 'spa_Latn'];
  }

  loadRecentLanguagePairs() {
    // Mock implementation
    this.recentLanguagePairs = [
      { source: 'eng_Latn', target: 'fra_Latn' },
      { source: 'fra_Latn', target: 'eng_Latn' }
    ];
  }

  async loadLanguages() {
    // Mock implementation
    return {
      languages: [
        { code: 'eng_Latn', name: 'English' },
        { code: 'fra_Latn', name: 'French' },
        { code: 'spa_Latn', name: 'Spanish' }
      ]
    };
  }

  getLanguageName(code) {
    const names = {
      'eng_Latn': 'English',
      'fra_Latn': 'French',
      'spa_Latn': 'Spanish'
    };
    return names[code] || code;
  }

  addRecentLanguage(code) {
    if (!this.recentLanguages.includes(code)) {
      this.recentLanguages.unshift(code);
      if (this.recentLanguages.length > 5) {
        this.recentLanguages.pop();
      }
    }
  }

  addRecentLanguagePair(source, target) {
    const pair = { source, target };
    const existingIndex = this.recentLanguagePairs.findIndex(
      p => p.source === source && p.target === target
    );
    if (existingIndex >= 0) {
      this.recentLanguagePairs.splice(existingIndex, 1);
    }
    this.recentLanguagePairs.unshift(pair);
    if (this.recentLanguagePairs.length > 5) {
      this.recentLanguagePairs.pop();
    }
  }

  saveRecentLanguages() {
    // Mock implementation
  }

  saveRecentLanguagePairs() {
    // Mock implementation
  }
};

// Mock Greasemonkey/Tampermonkey functions
global.GM_addStyle = jest.fn((css) => {
  const style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);
});

global.GM_xmlhttpRequest = jest.fn((details) => {
  // Mock API responses
  if (details.url && details.url.includes('/translate')) {
    if (details.onload) {
      setTimeout(() => {
        details.onload({
          status: 200,
          responseText: JSON.stringify({
            translated_text: 'Mocked translation',
            detected_language: 'en',
            detected_source: 'eng_Latn',
            time_ms: 100
          })
        });
      }, 10); // Use a shorter timeout for tests
    }
  } else if (details.onerror) {
    // Simulate error for non-translation endpoints
    setTimeout(() => {
      details.onerror(new Error('Unknown endpoint'));
    }, 10);
  }
  return {};
});

global.GM_setValue = jest.fn();
global.GM_getValue = jest.fn((key, defaultValue) => defaultValue);
global.GM_registerMenuCommand = jest.fn();

// Set up global CONFIG object for testing
global.CONFIG = {
  translationServer: 'http://localhost:8000',
  translationEndpoint: '/translate',
  apiKey: 'test-api-key',
  defaultTargetLang: 'eng_Latn',
  translateButtonText: '🌐 Translate',
  translatedPrefix: '🌐 ',
  showOriginalOnHover: true,
  debugMode: false
};

// Global helper for logging
global.log = jest.fn();

// Global Map for translated messages
global.translatedMessages = new Map();

// Make handleTranslationError, injectStyles and getTranslation available globally
global.handleTranslationError = (messageElement, textElement, error) => {
  // Create error message element
  const errorElement = document.createElement('div');
  errorElement.className = 'nllb-error';
  errorElement.textContent = 'Translation failed. Try again.';
  
  // Add error details in debug mode
  if (global.CONFIG.debugMode) {
    errorElement.textContent += ` Error: ${error.message || error}`;
  }
  
  // Add error message to the message element
  messageElement.appendChild(errorElement);
  
  // Remove error message after 3 seconds
  setTimeout(() => {
    if (errorElement && errorElement.parentNode) {
      errorElement.parentNode.removeChild(errorElement);
    }
  }, 3000);
};

global.injectStyles = () => {
  const style = document.createElement('style');
  style.textContent = `
    .nllb-translate-button {
      cursor: pointer;
      color: #3390ec;
      margin-left: 6px;
      font-size: 13px;
    }
    
    .nllb-translate-button:hover {
      text-decoration: underline;
    }
    
    .nllb-translating {
      opacity: 0.7;
    }
    
    .nllb-translated {
      position: relative;
    }
    
    .nllb-original-text {
      display: none;
      position: absolute;
      bottom: 100%;
      left: 0;
      background: rgba(0, 0, 0, 0.8);
      color: white;
      padding: 5px 10px;
      border-radius: 6px;
      font-size: 14px;
      z-index: 100;
      max-width: 300px;
      word-break: break-word;
    }
    
    .nllb-translated:hover .nllb-original-text {
      display: block;
    }
    
    .nllb-error {
      color: #d14836;
      font-size: 12px;
      margin-top: 4px;
    }
    
    .nllb-settings-dialog {
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: white;
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
      z-index: 9999;
      width: 400px;
      max-width: 90%;
    }
  `;
  document.head.appendChild(style);
};

global.getTranslation = async (text) => {
  return new Promise((resolve, reject) => {
    GM_xmlhttpRequest({
      method: 'POST',
      url: `${CONFIG.translationServer}${CONFIG.translationEndpoint}`,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': CONFIG.apiKey
      },
      data: JSON.stringify({
        text: text,
        source_lang: 'auto',
        target_lang: CONFIG.defaultTargetLang
      }),
      onload: function(response) {
        try {
          if (response.status >= 200 && response.status < 300) {
            const result = JSON.parse(response.responseText);
            resolve(result.translated_text);
          } else {
            reject(new Error(`Server responded with status ${response.status}: ${response.responseText}`));
          }
        } catch (e) {
          reject(e);
        }
      },
      onerror: function(error) {
        reject(new Error('Network error: ' + error));
      }
    });
  });
};

// Fix translateMessage
global.translateMessage = async (messageElement, textElement) => {
  // Get unique ID for this message 
  const messageId = messageElement.getAttribute('data-message-id') || 
                     messageElement.getAttribute('data-mid') ||
                     messageElement.getAttribute('id') ||
                     Date.now().toString();
  const text = textElement.textContent.trim();
  
  // Skip if already translated or empty
  if (!text || global.translatedMessages.has(messageId)) {
    return;
  }
  
  // Show loading state
  textElement.classList.add('nllb-translating');
  
  try {
    const translatedText = await global.getTranslation(text);
    
    // Store original text
    const originalText = text;
    global.translatedMessages.set(messageId, { original: originalText, translated: translatedText });
    
    // Clear existing text completely
    textElement.textContent = "";
    
    // Add the translated text to the element
    textElement.textContent = `${CONFIG.translatedPrefix}${translatedText}`;
    
    // Mark as translated
    textElement.classList.add('nllb-translated');
    
    // Add hover element with original text if enabled
    if (CONFIG.showOriginalOnHover) {
      const originalElement = document.createElement('div');
      originalElement.className = 'nllb-original-text';
      originalElement.textContent = originalText;
      textElement.appendChild(originalElement);
    }
    
  } catch (error) {
    global.log('Translation error:', error);
    global.handleTranslationError(messageElement, textElement, error);
  } finally {
    // Remove loading state
    textElement.classList.remove('nllb-translating');
  }
};

// Mock DOM methods not available in jsdom
window.matchMedia = window.matchMedia || function() {
  return {
    matches: false,
    addListener: function() {},
    removeListener: function() {}
  };
};

// Add MutationObserver mock
global.MutationObserver = class {
  constructor(callback) {
    this.callback = callback;
  }
  
  observe() {
    // Do nothing in tests
  }
  
  disconnect() {
    // Do nothing in tests
  }
  
  // Helper method to simulate mutations
  simulateMutations(mutations) {
    this.callback(mutations);
  }
};

// Set up document for tests
document.body.innerHTML = `
  <div class="messages-container">
    <div class="message" data-message-id="12345">
      <div class="message-content">
        <div class="text-content">Hello world</div>
        <div class="time">12:34</div>
      </div>
    </div>
  </div>
`;

// Mock console methods
global.console = {
  ...console,
  log: jest.fn(),
  error: jest.fn(),
  warn: jest.fn()
};

// Mock setTimeout
jest.useFakeTimers();

// Create document.createRange if needed
if (!document.createRange) {
  document.createRange = () => ({
    setStart: () => {},
    setEnd: () => {},
    commonAncestorContainer: {
      nodeName: 'BODY',
      ownerDocument: document,
    },
  });
}

// Inject styles into the document at startup
global.injectStyles();

// Increase default timeout for tests
jest.setTimeout(30000);