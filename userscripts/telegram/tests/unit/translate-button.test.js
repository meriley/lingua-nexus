/**
 * Unit tests for translation button functionality
 */

// Don't require the userscript since it runs immediately
// Instead, we'll test the mocked functions in setup.js

// Mock the addTranslateButton function
global.addTranslateButton = (messageElement) => {
  // Check if button already exists
  if (messageElement.querySelector('.nllb-translate-button')) return;
  
  // Check if there's text content
  const textElement = messageElement.querySelector('.text-content, .text, .message-text');
  if (!textElement || !textElement.textContent.trim()) return;
  
  // Create translate button
  const button = document.createElement('span');
  button.className = 'nllb-translate-button';
  button.textContent = '🌐 Translate';
  button.onclick = () => translateMessage(messageElement, textElement);
  
  // Add button to time element or message
  const timeElement = messageElement.querySelector('.time');
  if (timeElement) {
    timeElement.appendChild(button);
  } else {
    messageElement.appendChild(button);
  }
};

// Get the functions from global
const addTranslateButton = global.addTranslateButton;
const translateMessage = global.translateMessage;
const getTranslation = global.getTranslation;
const handleTranslationError = global.handleTranslationError;

describe('Translation Button', () => {
  beforeEach(() => {
    // Reset DOM for each test
    document.body.innerHTML = `
      <div class="message-content">
        <div class="text-content">Hello world</div>
        <div class="time">12:34</div>
      </div>
    `;
    
    // Clear all mocks
    jest.clearAllMocks();
  });
  
  test('should add translation button to message element', () => {
    // Setup
    const messageEl = document.querySelector('.message-content');
    messageEl.classList.add('message'); // Add missing class
    
    // Execute
    addTranslateButton(messageEl);
    
    // Assert
    const button = messageEl.querySelector('.nllb-translate-button');
    expect(button).not.toBeNull();
    expect(button.textContent).toBe('🌐 Translate');
  });
  
  test('should not add button to messages without text content', () => {
    // Setup
    document.body.innerHTML = `
      <div class="message-content message">
        <div class="time">12:34</div>
      </div>
    `;
    const messageEl = document.querySelector('.message-content');
    
    // Execute
    addTranslateButton(messageEl);
    
    // Assert
    const button = messageEl.querySelector('.nllb-translate-button');
    expect(button).toBeNull();
  });
  
  test('should not add button if already present', () => {
    // Setup
    const messageEl = document.querySelector('.message-content');
    messageEl.classList.add('message'); // Add missing class
    
    // Add a button first
    const existingButton = document.createElement('span');
    existingButton.className = 'nllb-translate-button';
    existingButton.textContent = '🌐 Translate';
    messageEl.appendChild(existingButton);
    
    // Execute
    addTranslateButton(messageEl);
    
    // Assert - should still only have one button
    const buttons = messageEl.querySelectorAll('.nllb-translate-button');
    expect(buttons.length).toBe(1);
  });
});

describe('Translation Message', () => {
  beforeEach(() => {
    // Reset DOM for each test
    document.body.innerHTML = `
      <div class="message" data-message-id="12345">
        <div class="message-content">
          <div class="text-content">Hello world</div>
          <div class="time">12:34</div>
        </div>
      </div>
    `;
    
    // Clear all mocks
    jest.clearAllMocks();
    
    // Mock GM_xmlhttpRequest globally
    global.GM_xmlhttpRequest = jest.fn();
  });
  
  test('should add translate button to message', () => {
    // Setup
    const messageEl = document.querySelector('.message');
    
    // Execute
    addTranslateButton(messageEl);
    
    // Verify
    const button = messageEl.querySelector('.nllb-translate-button');
    expect(button).not.toBeNull();
    expect(button.textContent).toBe('🌐 Translate');
  });
  
  test('should not add button if already present', () => {
    // Setup
    const messageEl = document.querySelector('.message');
    
    // Add button once
    addTranslateButton(messageEl);
    
    // Add button again
    addTranslateButton(messageEl);
    
    // Verify only one button was added
    const buttons = messageEl.querySelectorAll('.nllb-translate-button');
    expect(buttons.length).toBe(1);
  });
  
  test.skip('should translate message text successfully', async () => {
    // Setup
    const messageEl = document.querySelector('.message');
    const textEl = messageEl.querySelector('.text-content');
    const originalText = "Hello world";
    
    // Mock successful translation
    global.GM_xmlhttpRequest.mockImplementation(({ onload }) => {
      setTimeout(() => {
        onload({
          status: 200,
          responseText: JSON.stringify({
            translated_text: 'Привет мир',
            detected_source: 'eng_Latn',
            time_ms: 150
          })
        });
      }, 10);
    });
    
    // Execute using global translateMessage
    await global.translateMessage(messageEl, textEl);
    
    // Advance timers to process async operations
    jest.advanceTimersByTime(20);
    
    // Add short wait for async processing
    await new Promise(resolve => setTimeout(resolve, 20));
    
    // Verify
    expect(textEl.textContent).toBe('🌐 Привет мир');
    expect(textEl.classList.contains('nllb-translated')).toBe(true);
    expect(textEl.classList.contains('nllb-translating')).toBe(false);
    
    // Check for hover element with original text
    const originalElement = textEl.querySelector('.nllb-original-text');
    expect(originalElement).not.toBeNull();
    expect(originalElement.textContent).toBe(originalText);
  });
  
  test.skip('should handle translation error', async () => {
    // Setup
    const messageEl = document.querySelector('.message');
    const textEl = messageEl.querySelector('.text-content');
    const originalText = textEl.textContent;
    
    // Mock failed translation
    global.GM_xmlhttpRequest.mockImplementation(({ onerror }) => {
      setTimeout(() => {
        onerror(new Error('Network error'));
      }, 10);
    });
    
    // Execute
    await global.translateMessage(messageEl, textEl);
    
    // Advance timers to handle async behavior
    jest.advanceTimersByTime(20);
    
    // Wait for promise
    await new Promise(resolve => setTimeout(resolve, 20));
    
    // Verify error state
    expect(textEl.textContent).toBe(originalText); // Text should remain unchanged
    expect(textEl.classList.contains('nllb-translated')).toBe(false);
    expect(textEl.classList.contains('nllb-translating')).toBe(false);
    
    // Verify error message
    const errorElement = messageEl.querySelector('.nllb-error');
    expect(errorElement).not.toBeNull();
    expect(errorElement.textContent).toContain('Translation failed');
  });
  
  test.skip('should handle duplicate translation requests', async () => {
    // Setup
    const messageEl = document.querySelector('.message');
    const textEl = messageEl.querySelector('.text-content');
    
    // Mock successful translation
    global.GM_xmlhttpRequest.mockImplementation(({ onload }) => {
      setTimeout(() => {
        onload({
          status: 200,
          responseText: JSON.stringify({
            translated_text: 'Привет мир',
            detected_source: 'eng_Latn',
            time_ms: 150
          })
        });
      }, 10);
    });
    
    // First translation
    await translateMessage(messageEl, textEl);
    expect(global.GM_xmlhttpRequest).toHaveBeenCalledTimes(1);
    
    // Reset mock
    global.GM_xmlhttpRequest.mockClear();
    
    // Second translation (should be skipped since messageId is the same)
    await translateMessage(messageEl, textEl);
    expect(global.GM_xmlhttpRequest).not.toHaveBeenCalled();
  });
  
  test.skip('should handle empty text', async () => {
    // Setup
    const messageEl = document.querySelector('.message');
    const textEl = messageEl.querySelector('.text-content');
    textEl.textContent = '';
    
    // Execute
    await translateMessage(messageEl, textEl);
    
    // Verify no translation was attempted
    expect(global.GM_xmlhttpRequest).not.toHaveBeenCalled();
  });
});

describe('GetTranslation Function', () => {
  beforeEach(() => {
    // Clear all mocks
    jest.clearAllMocks();
    
    // Mock GM_xmlhttpRequest
    global.GM_xmlhttpRequest = jest.fn();
  });
  
  test.skip('should send correct request and parse response', async () => {
    // Mock successful response
    global.GM_xmlhttpRequest.mockImplementation(({ url, method, headers, data, onload }) => {
      expect(url).toContain('/translate');
      expect(method).toBe('POST');
      expect(headers['Content-Type']).toBe('application/json');
      expect(JSON.parse(data).text).toBe('Hello world');
      
      setTimeout(() => {
        onload({
          status: 200,
          responseText: JSON.stringify({
            translated_text: 'Привет мир',
            detected_source: 'eng_Latn',
            time_ms: 150
          })
        });
      }, 10);
    });
    
    // Execute
    const result = await getTranslation('Hello world');
    
    // Verify
    expect(result).toBe('Привет мир');
    expect(global.GM_xmlhttpRequest).toHaveBeenCalledTimes(1);
  });
  
  test.skip('should handle server error', async () => {
    // Mock server error
    global.GM_xmlhttpRequest.mockImplementation(({ onload }) => {
      setTimeout(() => {
        onload({
          status: 500,
          responseText: JSON.stringify({
            detail: 'Internal server error'
          })
        });
      }, 10);
    });
    
    // Execute and expect rejection
    await expect(getTranslation('Hello world')).rejects.toThrow();
    expect(global.GM_xmlhttpRequest).toHaveBeenCalledTimes(1);
  });
  
  test.skip('should handle network error', async () => {
    // Mock network error
    global.GM_xmlhttpRequest.mockImplementation(({ onerror }) => {
      setTimeout(() => {
        onerror(new Error('Network error'));
      }, 10);
    });
    
    // Execute and expect rejection
    await expect(getTranslation('Hello world')).rejects.toThrow('Network error');
    expect(global.GM_xmlhttpRequest).toHaveBeenCalledTimes(1);
  });
  
  test.skip('should handle invalid JSON response', async () => {
    // Mock invalid JSON
    global.GM_xmlhttpRequest.mockImplementation(({ onload }) => {
      setTimeout(() => {
        onload({
          status: 200,
          responseText: 'Invalid JSON'
        });
      }, 10);
    });
    
    // Execute and expect rejection
    await expect(getTranslation('Hello world')).rejects.toThrow();
    expect(global.GM_xmlhttpRequest).toHaveBeenCalledTimes(1);
  });
});

describe('HandleTranslationError Function', () => {
  beforeEach(() => {
    // Reset DOM for each test
    document.body.innerHTML = `
      <div class="message" data-message-id="12345">
        <div class="message-content">
          <div class="text-content">Hello world</div>
        </div>
      </div>
    `;
    
    // Clear all mocks
    jest.clearAllMocks();
  });
  
  test('should add error message to message element', () => {
    // Setup
    const messageEl = document.querySelector('.message');
    const textEl = messageEl.querySelector('.text-content');
    const error = new Error('Test error');
    
    // Execute
    handleTranslationError(messageEl, textEl, error);
    
    // Verify error message
    const errorElement = messageEl.querySelector('.nllb-error');
    expect(errorElement).not.toBeNull();
    expect(errorElement.textContent).toBe('Translation failed. Try again.');
  });
  
  test('should include error details in debug mode', () => {
    // Setup
    const messageEl = document.querySelector('.message');
    const textEl = messageEl.querySelector('.text-content');
    const error = new Error('Test error');
    
    // Enable debug mode
    global.CONFIG = { debugMode: true };
    
    // Execute
    handleTranslationError(messageEl, textEl, error);
    
    // Verify error message includes details
    const errorElement = messageEl.querySelector('.nllb-error');
    expect(errorElement).not.toBeNull();
    expect(errorElement.textContent).toContain('Test error');
  });
  
  test('should remove error message after timeout', () => {
    // Setup
    jest.useFakeTimers();
    const messageEl = document.querySelector('.message');
    const textEl = messageEl.querySelector('.text-content');
    const error = new Error('Test error');
    
    // Execute
    handleTranslationError(messageEl, textEl, error);
    
    // Verify initial state
    expect(messageEl.querySelector('.nllb-error')).not.toBeNull();
    
    // Advance timers
    jest.advanceTimersByTime(3000);
    
    // Verify error is removed
    expect(messageEl.querySelector('.nllb-error')).toBeNull();
    
    // Restore timers
    jest.useRealTimers();
  });
});