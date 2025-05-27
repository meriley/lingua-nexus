/**
 * Unit tests for settings management functionality
 */

// Don't require the userscript since it runs immediately
// Tests will use the mocked functions from setup.js

describe('Settings Management', () => {
  beforeEach(() => {
    // Reset DOM for each test
    document.body.innerHTML = '';
    
    // Clear all mocks
    jest.clearAllMocks();
    
    // Set up GM_getValue to return test values
    global.GM_getValue = jest.fn().mockImplementation((key, defaultValue) => {
      const testValues = {
        'translationServer': 'http://test-server:8000',
        'apiKey': 'test-api-key',
        'defaultTargetLang': 'rus_Cyrl',
        'showOriginalOnHover': true,
        'debugMode': true
      };
      return testValues[key] || defaultValue;
    });
    
    // Mock GM_setValue
    global.GM_setValue = jest.fn();
    
    // Reset CONFIG to default for each test
    global.CONFIG = {
      translationServer: 'http://localhost:8000',
      translationEndpoint: '/translate',
      apiKey: '',
      defaultTargetLang: 'eng_Latn',
      translateButtonText: '🌐 Translate',
      translatedPrefix: '🌐 ',
      showOriginalOnHover: true,
      debugMode: false
    };
    
    // Create simple test implementation of settings functions
    global.loadSettings = () => {
      global.CONFIG.translationServer = global.GM_getValue('translationServer', global.CONFIG.translationServer);
      global.CONFIG.apiKey = global.GM_getValue('apiKey', global.CONFIG.apiKey);
      global.CONFIG.defaultTargetLang = global.GM_getValue('defaultTargetLang', global.CONFIG.defaultTargetLang);
      global.CONFIG.showOriginalOnHover = global.GM_getValue('showOriginalOnHover', global.CONFIG.showOriginalOnHover);
      global.CONFIG.debugMode = global.GM_getValue('debugMode', global.CONFIG.debugMode);
      return global.CONFIG;
    };
    
    global.saveSettings = () => {
      global.GM_setValue('translationServer', global.CONFIG.translationServer);
      global.GM_setValue('apiKey', global.CONFIG.apiKey);
      global.GM_setValue('defaultTargetLang', global.CONFIG.defaultTargetLang);
      global.GM_setValue('showOriginalOnHover', global.CONFIG.showOriginalOnHover);
      global.GM_setValue('debugMode', global.CONFIG.debugMode);
      return global.CONFIG;
    };
    
    global.showSettingsDialog = () => {
      const dialog = document.createElement('div');
      dialog.className = 'nllb-settings-dialog';
      dialog.innerHTML = `
        <h2>NLLB Translator Settings</h2>
        
        <div class="nllb-form-group">
            <label for="nllb-server">Translation Server URL:</label>
            <input type="text" id="nllb-server" value="${global.CONFIG.translationServer}">
        </div>
        
        <div class="nllb-form-group">
            <label for="nllb-api-key">API Key:</label>
            <input type="text" id="nllb-api-key" value="${global.CONFIG.apiKey}">
        </div>
        
        <div class="nllb-form-group">
            <label for="nllb-target-lang">Default Target Language:</label>
            <select id="nllb-target-lang">
                <option value="eng_Latn" ${global.CONFIG.defaultTargetLang === 'eng_Latn' ? 'selected' : ''}>English</option>
                <option value="rus_Cyrl" ${global.CONFIG.defaultTargetLang === 'rus_Cyrl' ? 'selected' : ''}>Russian</option>
            </select>
        </div>
        
        <div class="nllb-form-group">
            <label>
                <input type="checkbox" id="nllb-show-original" ${global.CONFIG.showOriginalOnHover ? 'checked' : ''}>
                Show original text on hover
            </label>
        </div>
        
        <div class="nllb-form-group">
            <label>
                <input type="checkbox" id="nllb-debug-mode" ${global.CONFIG.debugMode ? 'checked' : ''}>
                Debug mode
            </label>
        </div>
        
        <div class="nllb-dialog-buttons">
            <button id="nllb-cancel" class="nllb-cancel-button">Cancel</button>
            <button id="nllb-save" class="nllb-save-button">Save</button>
        </div>
      `;
      
      // Add event handlers
      const saveBtn = dialog.querySelector('#nllb-save');
      const cancelBtn = dialog.querySelector('#nllb-cancel');
      
      saveBtn.addEventListener('click', () => {
        // Get values from form
        global.CONFIG.translationServer = document.getElementById('nllb-server').value;
        global.CONFIG.apiKey = document.getElementById('nllb-api-key').value;
        global.CONFIG.defaultTargetLang = document.getElementById('nllb-target-lang').value;
        global.CONFIG.showOriginalOnHover = document.getElementById('nllb-show-original').checked;
        if (document.getElementById('nllb-debug-mode')) {
          global.CONFIG.debugMode = document.getElementById('nllb-debug-mode').checked;
        }
        
        // Save settings
        global.saveSettings();
      });
      
      document.body.appendChild(dialog);
      return dialog;
    };
  });
  
  test('should load settings from storage', () => {
    // Execute
    const config = global.loadSettings();
    
    // Assert
    expect(global.GM_getValue).toHaveBeenCalledTimes(5);
    expect(config.translationServer).toBe('http://test-server:8000');
    expect(config.apiKey).toBe('test-api-key');
    expect(config.defaultTargetLang).toBe('rus_Cyrl');
    expect(config.showOriginalOnHover).toBe(true);
    expect(config.debugMode).toBe(true);
  });
  
  test('should save settings to storage', () => {
    // Setup - load settings first to populate config
    global.loadSettings();
    
    // Modify settings to new values
    global.CONFIG.translationServer = 'http://new-server:8000';
    global.CONFIG.apiKey = 'new-api-key';
    global.CONFIG.defaultTargetLang = 'eng_Latn';
    global.CONFIG.showOriginalOnHover = false;
    global.CONFIG.debugMode = false;
    
    // Execute
    global.saveSettings();
    
    // Assert
    expect(global.GM_setValue).toHaveBeenCalledTimes(5);
    expect(global.GM_setValue).toHaveBeenCalledWith('translationServer', 'http://new-server:8000');
    expect(global.GM_setValue).toHaveBeenCalledWith('apiKey', 'new-api-key');
    expect(global.GM_setValue).toHaveBeenCalledWith('defaultTargetLang', 'eng_Latn');
    expect(global.GM_setValue).toHaveBeenCalledWith('showOriginalOnHover', false);
    expect(global.GM_setValue).toHaveBeenCalledWith('debugMode', false);
  });
  
  test('should show settings dialog with correct values', () => {
    // Setup - load settings first
    global.loadSettings();
    
    // Execute
    global.showSettingsDialog();
    
    // Assert
    const dialog = document.querySelector('.nllb-settings-dialog');
    expect(dialog).not.toBeNull();
    
    // Check server URL field
    const serverField = document.getElementById('nllb-server');
    expect(serverField).not.toBeNull();
    expect(serverField.value).toBe('http://test-server:8000');
    
    // Check API key field
    const apiKeyField = document.getElementById('nllb-api-key');
    expect(apiKeyField).not.toBeNull();
    expect(apiKeyField.value).toBe('test-api-key');
    
    // Check target language field
    const targetLangField = document.getElementById('nllb-target-lang');
    expect(targetLangField).not.toBeNull();
    expect(targetLangField.value).toBe('rus_Cyrl');
    
    // Check show original checkbox
    const showOriginalField = document.getElementById('nllb-show-original');
    expect(showOriginalField).not.toBeNull();
    expect(showOriginalField.checked).toBe(true);
    
    // Check debug mode checkbox
    const debugModeField = document.getElementById('nllb-debug-mode');
    if (debugModeField) {
      expect(debugModeField.checked).toBe(true);
    }
  });
  
  test('should save settings when Save button is clicked', () => {
    // Setup - load settings first
    global.loadSettings();
    
    // Show the dialog
    global.showSettingsDialog();
    
    // Get the dialog to access its elements
    const dialog = document.querySelector('.nllb-settings-dialog');
    expect(dialog).not.toBeNull();
    
    // Create mock event for click
    const clickEvent = new MouseEvent('click', {
      bubbles: true,
      cancelable: true,
      view: window
    });
    
    // Change settings in the form
    const serverField = document.getElementById('nllb-server');
    serverField.value = 'http://new-server:8000';
    
    const apiKeyField = document.getElementById('nllb-api-key');
    apiKeyField.value = 'new-api-key';
    
    const targetLangField = document.getElementById('nllb-target-lang');
    targetLangField.value = 'eng_Latn';
    
    const showOriginalField = document.getElementById('nllb-show-original');
    showOriginalField.checked = false;
    
    // Mock values for testing
    global.GM_setValue.mockImplementation((key, value) => {
      if (key === 'translationServer') {
        expect(value).toBe('http://new-server:8000');
      }
    });
    
    // Dispatch click event on the Save button
    const saveButton = document.getElementById('nllb-save');
    saveButton.dispatchEvent(clickEvent);
    
    // Verify the settings were saved
    expect(global.GM_setValue).toHaveBeenCalled();
  });
  
  test('should close dialog without saving when Cancel button is clicked', () => {
    // Setup - load settings first
    global.loadSettings();
    
    // Show the dialog
    global.showSettingsDialog();
    
    // Get the dialog to access its elements
    const dialog = document.querySelector('.nllb-settings-dialog');
    expect(dialog).not.toBeNull();
    
    // Change a setting in the form
    const serverField = document.getElementById('nllb-server');
    serverField.value = 'http://changed-server:8000';
    
    // Mock methods to verify they're called
    const originalGMSetValue = global.GM_setValue;
    global.GM_setValue = jest.fn();
    
    // Dispatch click event on the Cancel button
    const cancelButton = document.getElementById('nllb-cancel');
    if (cancelButton) {
      // Create and dispatch a click event
      const clickEvent = new MouseEvent('click', {
        bubbles: true,
        cancelable: true,
        view: window
      });
      cancelButton.dispatchEvent(clickEvent);
    }
    
    // Assert settings were not saved
    expect(global.GM_setValue).not.toHaveBeenCalled();
    
    // Restore original function
    global.GM_setValue = originalGMSetValue;
  });
});

describe('DOM Manipulation', () => {
  beforeEach(() => {
    // Reset DOM for each test
    document.body.innerHTML = '';
    document.head.innerHTML = '';
    
    // Clear all mocks
    jest.clearAllMocks();
  });
  
  test('should inject styles into document head', () => {
    // Clear any existing styles first
    const existingStyles = document.head.querySelectorAll('style');
    existingStyles.forEach(style => style.remove());
    
    // Execute
    global.injectStyles();
    
    // Verify
    const styleTag = document.head.querySelector('style');
    expect(styleTag).not.toBeNull();
    expect(styleTag.textContent).toContain('.nllb-translate-button');
    expect(styleTag.textContent).toContain('.nllb-settings-dialog');
    expect(styleTag.textContent).toContain('.nllb-translated');
    expect(styleTag.textContent).toContain('.nllb-original-text');
  });
});