// ==UserScript==
// @name         Telegram NLLB Translator
// @namespace    https://github.com/yourusername/tg-text-translate
// @version      3.0.0
// @description  NLLB translation for Telegram Web with bidirectional language selection
// @author       Your Name
// @match        https://web.telegram.org/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_registerMenuCommand
// @grant        GM_addStyle
// @require      https://cdn.jsdelivr.net/gh/yourusername/tg-text-translate@main/userscript/telegram-nllb-translator.modules.js
// @run-at       document-end
// ==/UserScript==

(function() {
    'use strict';
    
    // Configuration with bidirectional support
    const CONFIG = {
        translationServer: 'http://localhost:8001',
        translationEndpoint: '/translate',
        languagesEndpoint: '/languages',
        apiKey: '1234567',
        defaultSourceLang: 'auto',
        defaultTargetLang: 'en',
        languageSelectionMode: 'single', // 'single' or 'pair'
        translateButtonText: '🌐',
        translatedPrefix: '🌐 ',
        showOriginalOnHover: true,
        debugMode: true,
        enablePreSendTranslation: true,
        autoTranslateInput: false,
        enableLanguageSwap: true,
        showRecentLanguages: true,
        maxRecentLanguages: 5
    };
    
    // State management with language selection
    const state = {
        translatedMessages: new Map(),
        observer: null,
        initialized: false,
        processedMessages: new Set(),
        languageManager: null,
        currentSourceLang: 'auto',
        currentTargetLang: 'eng_Latn',
        languageSelectors: new Map()
    };
    
    // Make CONFIG globally available for modules
    window.NLLB_CONFIG = CONFIG;
    
    // Load user settings with migration support
    function loadSettings() {
        // Load current settings
        CONFIG.translationServer = GM_getValue('translationServer', CONFIG.translationServer);
        CONFIG.apiKey = GM_getValue('apiKey', CONFIG.apiKey);
        CONFIG.defaultSourceLang = GM_getValue('defaultSourceLang', CONFIG.defaultSourceLang);
        CONFIG.defaultTargetLang = GM_getValue('defaultTargetLang', CONFIG.defaultTargetLang);
        CONFIG.languageSelectionMode = GM_getValue('languageSelectionMode', CONFIG.languageSelectionMode);
        CONFIG.showOriginalOnHover = GM_getValue('showOriginalOnHover', CONFIG.showOriginalOnHover);
        CONFIG.debugMode = GM_getValue('debugMode', CONFIG.debugMode);
        CONFIG.enablePreSendTranslation = GM_getValue('enablePreSendTranslation', CONFIG.enablePreSendTranslation);
        CONFIG.autoTranslateInput = GM_getValue('autoTranslateInput', CONFIG.autoTranslateInput);
        CONFIG.enableLanguageSwap = GM_getValue('enableLanguageSwap', CONFIG.enableLanguageSwap);
        CONFIG.showRecentLanguages = GM_getValue('showRecentLanguages', CONFIG.showRecentLanguages);
        CONFIG.maxRecentLanguages = GM_getValue('maxRecentLanguages', CONFIG.maxRecentLanguages);
        
        // Migrate from old settings format
        migrateSettings();
        
        // Update state
        state.currentSourceLang = CONFIG.defaultSourceLang;
        state.currentTargetLang = CONFIG.defaultTargetLang;
        
        log('Settings loaded:', CONFIG);
    }
    
    // Save user settings
    function saveSettings() {
        GM_setValue('translationServer', CONFIG.translationServer);
        GM_setValue('apiKey', CONFIG.apiKey);
        GM_setValue('defaultSourceLang', CONFIG.defaultSourceLang);
        GM_setValue('defaultTargetLang', CONFIG.defaultTargetLang);
        GM_setValue('languageSelectionMode', CONFIG.languageSelectionMode);
        GM_setValue('showOriginalOnHover', CONFIG.showOriginalOnHover);
        GM_setValue('debugMode', CONFIG.debugMode);
        GM_setValue('enablePreSendTranslation', CONFIG.enablePreSendTranslation);
        GM_setValue('autoTranslateInput', CONFIG.autoTranslateInput);
        GM_setValue('enableLanguageSwap', CONFIG.enableLanguageSwap);
        GM_setValue('showRecentLanguages', CONFIG.showRecentLanguages);
        GM_setValue('maxRecentLanguages', CONFIG.maxRecentLanguages);
        GM_setValue('settingsVersion', '3.0');
        log('Settings saved');
    }
    
    // Migrate settings from older versions
    function migrateSettings() {
        const version = GM_getValue('settingsVersion', '1.0');
        
        if (version === '1.0' || version === '2.0') {
            // Migrate from v1.0/2.0 to v3.0
            log('Migrating settings from version', version, 'to 3.0');
            
            // Set new defaults for bidirectional support
            if (!GM_getValue('defaultSourceLang')) {
                CONFIG.defaultSourceLang = 'auto';
            }
            
            if (!GM_getValue('languageSelectionMode')) {
                CONFIG.languageSelectionMode = 'single';
            }
            
            // Set new feature flags to enabled by default
            CONFIG.enableLanguageSwap = true;
            CONFIG.showRecentLanguages = true;
            CONFIG.maxRecentLanguages = 5;
            
            // Save migrated settings
            saveSettings();
        }
    }
    
    // Inject CSS styles
    function injectStyles() {
        GM_addStyle(`
            .nllb-translate-button {
                cursor: pointer;
                color: #3390ec;
                background: rgba(51, 144, 236, 0.1);
                border: 1px solid rgba(51, 144, 236, 0.3);
                border-radius: 8px;
                padding: 2px 6px;
                margin: 0 4px;
                font-size: 11px;
                display: inline-block;
                transition: all 0.2s ease;
                user-select: none;
                vertical-align: middle;
            }
            
            .nllb-translate-button:hover {
                background: rgba(51, 144, 236, 0.2);
                border-color: rgba(51, 144, 236, 0.5);
                transform: scale(1.05);
            }
            
            .nllb-translating {
                opacity: 0.7;
                pointer-events: none;
            }
            
            .nllb-translated {
                position: relative;
                background: rgba(51, 144, 236, 0.05);
                border-radius: 4px;
                padding: 2px 4px;
                margin: -2px -4px;
                border-left: 3px solid rgba(51, 144, 236, 0.3);
            }
            
            .nllb-original-text {
                display: none;
                position: absolute;
                bottom: 100%;
                left: 0;
                background: rgba(0, 0, 0, 0.9);
                color: white;
                padding: 8px 12px;
                border-radius: 8px;
                font-size: 13px;
                z-index: 10000;
                max-width: 400px;
                word-break: break-word;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                white-space: pre-wrap;
                line-height: 1.4;
            }
            
            .nllb-original-text::before {
                content: '';
                position: absolute;
                top: 100%;
                left: 20px;
                border: 6px solid transparent;
                border-top-color: rgba(0, 0, 0, 0.9);
            }
            
            .nllb-translated:hover .nllb-original-text {
                display: block;
            }
            
            .nllb-error {
                color: #d14836;
                font-size: 11px;
                margin: 4px 0;
                padding: 4px 8px;
                background: rgba(209, 72, 54, 0.1);
                border-radius: 4px;
                border-left: 3px solid #d14836;
                max-width: 300px;
            }
            
            .nllb-input-toolbar {
                display: flex;
                align-items: center;
                margin-top: 4px;
                gap: 8px;
                padding: 4px 8px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            .nllb-input-translate-btn {
                background: #3390ec;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .nllb-input-translate-btn:hover {
                background: #2b7cd3;
                transform: scale(1.05);
            }
            
            .nllb-input-translate-btn:disabled {
                background: #ccc;
                cursor: not-allowed;
                transform: none;
            }
            
            .nllb-settings-dialog {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: white;
                border-radius: 12px;
                padding: 24px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                z-index: 10001;
                width: 420px;
                max-width: 90vw;
                max-height: 80vh;
                overflow-y: auto;
            }
            
            .nllb-settings-dialog h2 {
                margin: 0 0 20px 0;
                color: #333;
                font-size: 20px;
            }
            
            /* Language Selector Styles */
            .nllb-language-selector {
                position: relative;
                display: inline-block;
                margin: 0 4px;
                font-family: inherit;
            }
            
            .nllb-language-button {
                background: rgba(51, 144, 236, 0.1);
                border: 1px solid rgba(51, 144, 236, 0.3);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                color: #3390ec;
                cursor: pointer;
                transition: all 0.2s ease;
                user-select: none;
                min-width: 60px;
                text-align: center;
            }
            
            .nllb-language-button:hover {
                background: rgba(51, 144, 236, 0.2);
                border-color: rgba(51, 144, 236, 0.5);
                transform: scale(1.05);
            }
            
            .nllb-language-pair-container {
                display: flex;
                align-items: center;
                gap: 4px;
            }
            
            .nllb-swap-button {
                background: rgba(51, 144, 236, 0.1);
                border: 1px solid rgba(51, 144, 236, 0.3);
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 12px;
                color: #3390ec;
                cursor: pointer;
                transition: all 0.2s ease;
                user-select: none;
                min-width: 20px;
                text-align: center;
            }
            
            .nllb-swap-button:hover {
                background: rgba(51, 144, 236, 0.3);
                transform: scale(1.1);
            }
            
            .nllb-language-dropdown {
                position: absolute;
                top: 100%;
                left: 0;
                min-width: 280px;
                max-height: 400px;
                background: var(--color-background, white);
                border: 1px solid var(--color-borders, #e1e8ed);
                border-radius: 8px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
                z-index: 9999;
                overflow: hidden;
                margin-top: 2px;
            }
            
            .nllb-language-search {
                width: 100%;
                padding: 12px;
                border: none;
                border-bottom: 1px solid var(--color-borders, #e1e8ed);
                font-size: 14px;
                outline: none;
                background: var(--color-background, white);
                color: var(--color-text, #000);
            }
            
            .nllb-language-search::placeholder {
                color: var(--color-text-secondary, #707579);
            }
            
            .nllb-language-results {
                max-height: 340px;
                overflow-y: auto;
            }
            
            .nllb-language-section {
                border-bottom: 1px solid var(--color-borders-light, #f0f2f5);
            }
            
            .nllb-language-section:last-child {
                border-bottom: none;
            }
            
            .nllb-language-section-header {
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
                color: var(--color-text-secondary, #707579);
                background: var(--color-background-secondary, #f8f9fa);
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .nllb-language-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 16px;
                cursor: pointer;
                transition: background-color 0.2s ease;
                border-bottom: 1px solid var(--color-borders-light, #f0f2f5);
            }
            
            .nllb-language-item:last-child {
                border-bottom: none;
            }
            
            .nllb-language-item:hover {
                background: var(--color-background-secondary, #f8f9fa);
            }
            
            .nllb-language-item.selected {
                background: rgba(51, 144, 236, 0.1);
                color: #3390ec;
            }
            
            .nllb-language-item.recent::before {
                content: '🕒';
                margin-right: 8px;
                font-size: 14px;
            }
            
            .nllb-language-item.popular::after {
                content: '⭐';
                opacity: 0.7;
                font-size: 12px;
            }
            
            .nllb-language-item.pair .nllb-language-name {
                font-weight: 500;
            }
            
            .nllb-language-name {
                font-size: 14px;
                font-weight: 400;
                color: var(--color-text, #000);
            }
            
            .nllb-language-native {
                font-size: 12px;
                color: var(--color-text-secondary, #707579);
                text-align: right;
            }
            
            /* Dark mode support */
            @media (prefers-color-scheme: dark) {
                .nllb-language-dropdown {
                    background: var(--color-background, #1e1e1e);
                    border-color: var(--color-borders, #3e3e3e);
                }
                
                .nllb-language-search {
                    background: var(--color-background, #1e1e1e);
                    color: var(--color-text, #ffffff);
                }
                
                .nllb-language-section-header {
                    background: var(--color-background-secondary, #2a2a2a);
                }
                
                .nllb-language-item:hover {
                    background: var(--color-background-secondary, #2a2a2a);
                }
            }
            
            .nllb-form-group {
                margin-bottom: 16px;
            }
            
            .nllb-form-group label {
                display: block;
                margin-bottom: 6px;
                font-weight: 500;
                color: #555;
            }
            
            .nllb-form-group input[type="text"],
            .nllb-form-group select {
                width: 100%;
                padding: 10px;
                border: 2px solid #e1e5e9;
                border-radius: 6px;
                font-size: 14px;
                transition: border-color 0.2s ease;
                box-sizing: border-box;
            }
            
            .nllb-form-group input[type="text"]:focus,
            .nllb-form-group select:focus {
                outline: none;
                border-color: #3390ec;
            }
            
            .nllb-form-group input[type="checkbox"] {
                margin-right: 8px;
                transform: scale(1.1);
            }
            
            .nllb-dialog-buttons {
                display: flex;
                justify-content: flex-end;
                gap: 12px;
                margin-top: 24px;
                padding-top: 16px;
                border-top: 1px solid #e1e5e9;
            }
            
            .nllb-dialog-buttons button {
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .nllb-save-button {
                background: #3390ec;
                color: white;
            }
            
            .nllb-save-button:hover {
                background: #2b7cd3;
            }
            
            .nllb-cancel-button {
                background: #f1f3f4;
                color: #5f6368;
            }
            
            .nllb-cancel-button:hover {
                background: #e8eaed;
            }
            
            .nllb-backdrop {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5);
                z-index: 10000;
            }
            
            .nllb-status {
                font-size: 11px;
                color: #666;
                margin-left: 8px;
            }
            
            .nllb-status.success {
                color: #0f9d58;
            }
            
            .nllb-status.error {
                color: #d73527;
            }
            
            /* Translation Toolbar */
            .nllb-translation-toolbar {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                margin: 0 4px;
                vertical-align: middle;
            }
        `);
    }
    
    // Utility function for logging
    function log(...args) {
        if (CONFIG.debugMode) {
            console.log('[NLLB]', ...args);
        }
    }
    
    // Get translation from server
    async function getTranslation(text, sourceLang = 'auto', targetLang = null) {
        return new Promise((resolve, reject) => {
            if (!CONFIG.apiKey) {
                reject(new Error('API key not configured'));
                return;
            }
            
            if (!text.trim()) {
                reject(new Error('Empty text'));
                return;
            }
            
            log('Requesting translation for:', text.substring(0, 50) + '...');
            
            GM_xmlhttpRequest({
                method: 'POST',
                url: `${CONFIG.translationServer}${CONFIG.translationEndpoint}`,
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': CONFIG.apiKey
                },
                data: JSON.stringify({
                    text: text.trim(),
                    source_lang: sourceLang,
                    target_lang: targetLang || CONFIG.defaultTargetLang
                }),
                timeout: 15000,
                onload: function(response) {
                    try {
                        log('Translation response:', response.status);
                        if (response.status >= 200 && response.status < 300) {
                            const result = JSON.parse(response.responseText);
                            resolve(result.translated_text);
                        } else {
                            const errorData = response.responseText ? JSON.parse(response.responseText) : {};
                            reject(new Error(`Server error ${response.status}: ${errorData.detail || 'Unknown error'}`));
                        }
                    } catch (e) {
                        reject(new Error(`Parse error: ${e.message}`));
                    }
                },
                onerror: function(error) {
                    reject(new Error(`Network error: ${error.error || 'Connection failed'}`));
                },
                ontimeout: function() {
                    reject(new Error('Request timeout'));
                }
            });
        });
    }
    
    // Find message text element - Updated for current Telegram DOM
    function findMessageText(bubbleElement) {
        const messageContent = bubbleElement.querySelector('.message');
        if (messageContent && messageContent.textContent.trim()) {
            return messageContent;
        }
        return null;
    }
    
    // Get clean text content without time stamps
    function getCleanText(messageElement) {
        const clone = messageElement.cloneNode(true);
        const timeElement = clone.querySelector('.time');
        if (timeElement) {
            timeElement.remove();
        }
        return clone.textContent.trim();
    }
    
    // Add translation button to a message bubble
    async function addTranslateButton(bubbleElement) {
        const messageId = bubbleElement.getAttribute('data-mid') || 
                         bubbleElement.getAttribute('data-message-id') || 
                         Date.now().toString();
        
        // Skip if already processed
        if (state.processedMessages.has(messageId) || 
            bubbleElement.querySelector('.nllb-translate-button')) {
            return;
        }
        
        const messageElement = findMessageText(bubbleElement);
        if (!messageElement) {
            return;
        }
        
        const text = getCleanText(messageElement);
        if (!text || text.length < 3) {
            return;
        }
        
        // Mark as processed
        state.processedMessages.add(messageId);
        
        // Create translation toolbar container
        const toolbarContainer = document.createElement('div');
        toolbarContainer.className = 'nllb-translation-toolbar';
        
        // Create translate button
        const translateButton = document.createElement('span');
        translateButton.className = 'nllb-translate-button';
        translateButton.textContent = CONFIG.translateButtonText;
        translateButton.title = 'Translate message';
        
        // Create language selector if not already initialized for this message
        if (!state.languageSelectors.has(messageId)) {
            try {
                const languageSelector = new LanguageSelector({
                    languageManager: state.languageManager,
                    mode: CONFIG.languageSelectionMode,
                    defaultSource: state.currentSourceLang,
                    defaultTarget: state.currentTargetLang,
                    onLanguageChange: (targetLang) => {
                        state.currentTargetLang = targetLang;
                        CONFIG.defaultTargetLang = targetLang;
                        saveSettings();
                        log('Target language changed to:', targetLang);
                    },
                    onLanguagePairChange: (sourceLang, targetLang) => {
                        state.currentSourceLang = sourceLang;
                        state.currentTargetLang = targetLang;
                        CONFIG.defaultSourceLang = sourceLang;
                        CONFIG.defaultTargetLang = targetLang;
                        saveSettings();
                        log('Language pair changed to:', sourceLang, '→', targetLang);
                    }
                });
                
                const selectorElement = await languageSelector.create();
                state.languageSelectors.set(messageId, languageSelector);
                toolbarContainer.appendChild(selectorElement);
            } catch (error) {
                log('Failed to create language selector:', error);
                // Continue without language selector
            }
        }
        
        translateButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            translateMessage(bubbleElement, messageElement, messageId);
        });
        
        toolbarContainer.appendChild(translateButton);
        
        // Find the time element to place the toolbar next to it
        const timeElement = messageElement.querySelector('.time');
        if (timeElement) {
            timeElement.parentNode.insertBefore(toolbarContainer, timeElement);
            log('Added translation toolbar to message:', messageId);
        } else {
            messageElement.appendChild(toolbarContainer);
            log('Added translation toolbar (fallback) to message:', messageId);
        }
    }
    
    // Translate message text
    async function translateMessage(bubbleElement, messageElement, messageId) {
        const text = getCleanText(messageElement);
        
        // Skip if already translated
        if (state.translatedMessages.has(messageId)) {
            restoreOriginalMessage(bubbleElement, messageElement, messageId);
            return;
        }
        
        // Show loading state
        messageElement.classList.add('nllb-translating');
        const button = bubbleElement.querySelector('.nllb-translate-button');
        if (button) {
            button.textContent = '⏳';
            button.disabled = true;
        }
        
        try {
            log('Translating message:', messageId, text.substring(0, 50) + '...');
            const translatedText = await getTranslation(text, state.currentSourceLang, state.currentTargetLang);
            
            // Store original content
            const timeElement = messageElement.querySelector('.time');
            const originalHTML = messageElement.innerHTML;
            
            state.translatedMessages.set(messageId, { 
                original: text,
                originalHTML: originalHTML,
                translated: translatedText 
            });
            
            // Replace content while preserving time element
            if (timeElement) {
                const timeHTML = timeElement.outerHTML;
                messageElement.innerHTML = `${CONFIG.translatedPrefix}${translatedText}${timeHTML}`;
            } else {
                messageElement.innerHTML = `${CONFIG.translatedPrefix}${translatedText}`;
            }
            
            messageElement.classList.add('nllb-translated');
            
            // Add hover element with original text if enabled
            if (CONFIG.showOriginalOnHover) {
                const originalElement = document.createElement('div');
                originalElement.className = 'nllb-original-text';
                originalElement.textContent = text;
                messageElement.appendChild(originalElement);
            }
            
            // Update button
            if (button) {
                button.textContent = '↩️';
                button.title = 'Show original';
                button.disabled = false;
            }
            
            log('Message translated successfully:', messageId);
            
        } catch (error) {
            log('Translation error:', error);
            showTranslationError(bubbleElement, error.message);
        } finally {
            // Remove loading state
            messageElement.classList.remove('nllb-translating');
            if (button && button.textContent === '⏳') {
                button.textContent = CONFIG.translateButtonText;
                button.disabled = false;
            }
        }
    }
    
    // Restore original message
    function restoreOriginalMessage(bubbleElement, messageElement, messageId) {
        const stored = state.translatedMessages.get(messageId);
        if (!stored) return;
        
        // Restore original HTML
        messageElement.innerHTML = stored.originalHTML;
        messageElement.classList.remove('nllb-translated');
        
        // Update button
        const button = bubbleElement.querySelector('.nllb-translate-button');
        if (button) {
            button.textContent = CONFIG.translateButtonText;
            button.title = 'Translate message';
        }
        
        // Remove from translated messages
        state.translatedMessages.delete(messageId);
        log('Restored original message:', messageId);
    }
    
    // Show translation error
    function showTranslationError(bubbleElement, errorMessage) {
        const existingError = bubbleElement.querySelector('.nllb-error');
        if (existingError) {
            existingError.remove();
        }
        
        const errorElement = document.createElement('div');
        errorElement.className = 'nllb-error';
        errorElement.textContent = `Translation failed: ${errorMessage}`;
        
        const bubbleContent = bubbleElement.querySelector('.bubble-content');
        if (bubbleContent) {
            bubbleContent.appendChild(errorElement);
        } else {
            bubbleElement.appendChild(errorElement);
        }
        
        setTimeout(() => {
            if (errorElement.parentNode) {
                errorElement.remove();
            }
        }, 5000);
    }
    
    // Process new elements
    function processNewElements(mutations) {
        for (const mutation of mutations) {
            if (mutation.type === 'childList') {
                for (const node of mutation.addedNodes) {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        let bubbles = [];
                        
                        if (node.classList && node.classList.contains('bubble')) {
                            bubbles.push(node);
                        }
                        
                        if (node.querySelectorAll) {
                            const foundBubbles = node.querySelectorAll('.bubble');
                            bubbles.push(...Array.from(foundBubbles));
                        }
                        
                        bubbles.forEach(bubble => {
                            if (!bubble.classList.contains('is-system') && 
                                bubble.querySelector('.message')) {
                                addTranslateButton(bubble);
                            }
                        });
                        
                        // Handle input areas if pre-send translation is enabled
                        if (CONFIG.enablePreSendTranslation) {
                            const inputs = findInputAreas(node);
                            inputs.forEach(addInputTranslationToolbar);
                        }
                    }
                }
            }
        }
    }
    
    // Find input areas
    function findInputAreas(container = document) {
        const selectors = [
            '.input-message-input',
            '[contenteditable="true"]'
        ];
        
        const inputs = [];
        for (const selector of selectors) {
            const elements = container.querySelectorAll(selector);
            for (const element of elements) {
                if (isMessageInput(element)) {
                    inputs.push(element);
                }
            }
        }
        
        return inputs;
    }
    
    // Check if element is a message input
    function isMessageInput(element) {
        const parent = element.closest('.input-message, .composer-wrapper, [class*="input"]');
        if (!parent) return false;
        
        const excludeClasses = ['search', 'filter', 'username', 'phone'];
        for (const cls of excludeClasses) {
            if (element.className.toLowerCase().includes(cls) || 
                parent.className.toLowerCase().includes(cls)) {
                return false;
            }
        }
        
        return true;
    }
    
    // Add translation toolbar to input
    function addInputTranslationToolbar(inputElement) {
        if (inputElement.parentNode.querySelector('.nllb-input-toolbar')) {
            return;
        }
        
        const toolbar = document.createElement('div');
        toolbar.className = 'nllb-input-toolbar';
        
        const translateBtn = document.createElement('button');
        translateBtn.className = 'nllb-input-translate-btn';
        translateBtn.textContent = 'Translate';
        translateBtn.title = 'Translate and replace text in input';
        
        const status = document.createElement('span');
        status.className = 'nllb-status';
        
        translateBtn.addEventListener('click', () => {
            translateInputText(inputElement, status);
        });
        
        toolbar.appendChild(translateBtn);
        toolbar.appendChild(status);
        
        const inputContainer = inputElement.closest('.input-message, .composer-wrapper') || inputElement.parentNode;
        inputContainer.appendChild(toolbar);
        
        log('Added input translation toolbar');
    }
    
    // Translate input text
    async function translateInputText(inputElement, statusElement) {
        const text = inputElement.textContent || inputElement.value || '';
        
        if (!text.trim()) {
            statusElement.textContent = 'No text to translate';
            statusElement.className = 'nllb-status error';
            return;
        }
        
        statusElement.textContent = 'Translating...';
        statusElement.className = 'nllb-status';
        
        try {
            const translatedText = await getTranslation(text);
            
            if (inputElement.contentEditable === 'true') {
                inputElement.textContent = translatedText;
                inputElement.dispatchEvent(new Event('input', { bubbles: true }));
            } else {
                inputElement.value = translatedText;
                inputElement.dispatchEvent(new Event('input', { bubbles: true }));
            }
            
            statusElement.textContent = 'Translated!';
            statusElement.className = 'nllb-status success';
            
            inputElement.focus();
            
            log('Input text translated successfully');
            
        } catch (error) {
            log('Input translation error:', error);
            statusElement.textContent = `Error: ${error.message}`;
            statusElement.className = 'nllb-status error';
        }
    }
    
    // Setup mutation observer
    function setupObserver() {
        if (state.observer) {
            state.observer.disconnect();
        }
        
        state.observer = new MutationObserver(processNewElements);
        
        const observeTargets = [
            document.querySelector('.bubbles-group-container'),
            document.querySelector('.chat-container'),
            document.querySelector('#column-center'),
            document.body
        ].filter(Boolean);
        
        const target = observeTargets[0] || document.body;
        
        state.observer.observe(target, {
            childList: true,
            subtree: true
        });
        
        log('Mutation observer setup on:', target.className || target.tagName);
    }
    
    // Setup existing content
    function setupExistingContent() {
        const bubbles = document.querySelectorAll('.bubble');
        log(`Found ${bubbles.length} existing message bubbles`);
        
        bubbles.forEach(bubble => {
            if (!bubble.classList.contains('is-system') && bubble.querySelector('.message')) {
                addTranslateButton(bubble);
            }
        });
        
        if (CONFIG.enablePreSendTranslation) {
            const inputs = findInputAreas();
            log(`Found ${inputs.length} input areas`);
            inputs.forEach(addInputTranslationToolbar);
        }
    }
    
    // Show settings dialog
    function showSettingsDialog() {
        const existingDialog = document.querySelector('.nllb-settings-dialog');
        const existingBackdrop = document.querySelector('.nllb-backdrop');
        if (existingDialog) existingDialog.remove();
        if (existingBackdrop) existingBackdrop.remove();
        
        const backdrop = document.createElement('div');
        backdrop.className = 'nllb-backdrop';
        
        const dialog = document.createElement('div');
        dialog.className = 'nllb-settings-dialog';
        dialog.innerHTML = `
            <h2>🌐 NLLB Translator Settings</h2>
            
            <div class="nllb-form-group">
                <label for="nllb-server">Translation Server URL:</label>
                <input type="text" id="nllb-server" value="${CONFIG.translationServer}" placeholder="http://localhost:8000">
            </div>
            
            <div class="nllb-form-group">
                <label for="nllb-api-key">API Key:</label>
                <input type="text" id="nllb-api-key" value="${CONFIG.apiKey}" placeholder="your-api-key">
            </div>
            
            <div class="nllb-form-group">
                <label for="nllb-target-lang">Default Target Language:</label>
                <select id="nllb-target-lang">
                    <option value="eng_Latn" ${CONFIG.defaultTargetLang === 'eng_Latn' ? 'selected' : ''}>English</option>
                    <option value="rus_Cyrl" ${CONFIG.defaultTargetLang === 'rus_Cyrl' ? 'selected' : ''}>Russian</option>
                </select>
            </div>
            
            <div class="nllb-form-group">
                <label>
                    <input type="checkbox" id="nllb-show-original" ${CONFIG.showOriginalOnHover ? 'checked' : ''}>
                    Show original text on hover
                </label>
            </div>
            
            <div class="nllb-form-group">
                <label>
                    <input type="checkbox" id="nllb-pre-send" ${CONFIG.enablePreSendTranslation ? 'checked' : ''}>
                    Enable pre-send translation toolbar
                </label>
            </div>
            
            <div class="nllb-form-group">
                <label>
                    <input type="checkbox" id="nllb-debug-mode" ${CONFIG.debugMode ? 'checked' : ''}>
                    Debug mode (console logging)
                </label>
            </div>
            
            <div class="nllb-dialog-buttons">
                <button class="nllb-cancel-button" id="nllb-cancel">Cancel</button>
                <button class="nllb-save-button" id="nllb-save">Save Settings</button>
            </div>
        `;
        
        document.body.appendChild(backdrop);
        document.body.appendChild(dialog);
        
        backdrop.addEventListener('click', () => {
            dialog.remove();
            backdrop.remove();
        });
        
        document.getElementById('nllb-cancel').addEventListener('click', () => {
            dialog.remove();
            backdrop.remove();
        });
        
        document.getElementById('nllb-save').addEventListener('click', () => {
            CONFIG.translationServer = document.getElementById('nllb-server').value.trim();
            CONFIG.apiKey = document.getElementById('nllb-api-key').value.trim();
            CONFIG.defaultTargetLang = document.getElementById('nllb-target-lang').value;
            CONFIG.showOriginalOnHover = document.getElementById('nllb-show-original').checked;
            CONFIG.enablePreSendTranslation = document.getElementById('nllb-pre-send').checked;
            CONFIG.debugMode = document.getElementById('nllb-debug-mode').checked;
            
            saveSettings();
            dialog.remove();
            backdrop.remove();
            
            log('Settings updated and saved');
            
            state.processedMessages.clear();
            state.translatedMessages.clear();
            setupExistingContent();
        });
        
        document.getElementById('nllb-server').focus();
    }
    
    // Initialize the script
    function initialize() {
        if (state.initialized) {
            return;
        }
        
        log('Initializing NLLB Translator');
        
        loadSettings();
        injectStyles();
        
        // Initialize language manager
        if (!state.languageManager) {
            state.languageManager = new LanguageManager();
            state.languageManager.loadRecentLanguages();
            state.languageManager.loadRecentLanguagePairs();
            log('Language manager initialized');
        }
        
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                setTimeout(initialize, 1000);
            });
            return;
        }
        
        setTimeout(() => {
            setupObserver();
            setupExistingContent();
            
            GM_registerMenuCommand('🌐 NLLB Translator Settings', showSettingsDialog);
            
            state.initialized = true;
            log('NLLB Translator initialized successfully');
            
            if (!CONFIG.apiKey) {
                setTimeout(() => {
                    if (confirm('NLLB Translator: No API key configured. Open settings?')) {
                        showSettingsDialog();
                    }
                }, 2000);
            }
        }, 2000);
    }
    
    // Start initialization
    initialize();
    
    // Re-initialize on navigation
    let lastUrl = location.href;
    new MutationObserver(() => {
        const url = location.href;
        if (url !== lastUrl) {
            lastUrl = url;
            log('Navigation detected, reinitializing...');
            state.initialized = false;
            state.processedMessages.clear();
            setTimeout(initialize, 1000);
        }
    }).observe(document, { subtree: true, childList: true });
    
})();