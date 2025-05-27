// ==UserScript==
// @name         Telegram NLLB Translator (Standalone)
// @namespace    https://github.com/telegram-nllb-translator
// @version      3.0.1
// @description  NLLB translation for Telegram Web with bidirectional language selection (standalone version)
// @author       NLLB Translator
// @match        https://web.telegram.org/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_registerMenuCommand
// @grant        GM_addStyle
// @run-at       document-end
// ==/UserScript==

(function() {
    'use strict';
    
    // ===== LANGUAGE MANAGEMENT MODULE =====
    class LanguageManager {
        constructor() {
            this.languages = new Map();
            this.recentLanguages = [];
            this.recentLanguagePairs = [];
            this.favorites = [];
            this.favoritePairs = [];
            this.cache = {
                languageData: null,
                lastFetch: 0,
                ttl: 3600000 // 1 hour
            };
        }

        /**
         * Load language data from API with caching
         */
        async loadLanguages() {
            try {
                // Check cache first
                const now = Date.now();
                if (this.cache.languageData && (now - this.cache.lastFetch) < this.cache.ttl) {
                    return this.cache.languageData;
                }

                const response = await this.fetchWithAuth('/languages');
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                
                // Update cache
                this.cache.languageData = data;
                this.cache.lastFetch = now;
                
                // Update internal maps
                this.languages.clear();
                data.languages.forEach(lang => {
                    this.languages.set(lang.code, lang);
                });

                return data;
            } catch (error) {
                console.error('Language loading failed:', error);
                const defaultData = this.getDefaultLanguages();
                
                // Update cache and internal maps with default data
                this.cache.languageData = defaultData;
                this.cache.lastFetch = Date.now();
                
                this.languages.clear();
                defaultData.languages.forEach(lang => {
                    this.languages.set(lang.code, lang);
                });
                
                return defaultData;
            }
        }

        /**
         * Get default languages for fallback
         */
        getDefaultLanguages() {
            return {
                languages: [
                    {
                        code: "auto",
                        name: "Auto-detect",
                        native_name: "Auto-detect",
                        family: "Auto",
                        script: "Auto",
                        popular: true,
                        region: "Global",
                        rtl: false
                    },
                    {
                        code: "eng_Latn",
                        name: "English",
                        native_name: "English",
                        family: "Germanic",
                        script: "Latin",
                        popular: true,
                        region: "Global",
                        rtl: false
                    },
                    {
                        code: "spa_Latn",
                        name: "Spanish",
                        native_name: "Español",
                        family: "Romance",
                        script: "Latin",
                        popular: true,
                        region: "Global",
                        rtl: false
                    },
                    {
                        code: "fra_Latn",
                        name: "French",
                        native_name: "Français",
                        family: "Romance",
                        script: "Latin",
                        popular: true,
                        region: "Global",
                        rtl: false
                    },
                    {
                        code: "deu_Latn",
                        name: "German",
                        native_name: "Deutsch",
                        family: "Germanic",
                        script: "Latin",
                        popular: true,
                        region: "Europe",
                        rtl: false
                    },
                    {
                        code: "rus_Cyrl",
                        name: "Russian",
                        native_name: "Русский",
                        family: "Slavic",
                        script: "Cyrillic",
                        popular: true,
                        region: "Eastern Europe",
                        rtl: false
                    },
                    {
                        code: "zho_Hans",
                        name: "Chinese (Simplified)",
                        native_name: "简体中文",
                        family: "Sino-Tibetan",
                        script: "Chinese Simplified",
                        popular: true,
                        region: "East Asia",
                        rtl: false
                    },
                    {
                        code: "jpn_Jpan",
                        name: "Japanese",
                        native_name: "日本語",
                        family: "Japonic",
                        script: "Japanese",
                        popular: true,
                        region: "East Asia",
                        rtl: false
                    },
                    {
                        code: "arb_Arab",
                        name: "Arabic",
                        native_name: "العربية",
                        family: "Afro-Asiatic",
                        script: "Arabic",
                        popular: true,
                        region: "Middle East",
                        rtl: true
                    }
                ],
                families: {
                    "Auto": ["auto"],
                    "Germanic": ["eng_Latn", "deu_Latn"],
                    "Romance": ["spa_Latn", "fra_Latn"],
                    "Slavic": ["rus_Cyrl"],
                    "Sino-Tibetan": ["zho_Hans"],
                    "Japonic": ["jpn_Jpan"],
                    "Afro-Asiatic": ["arb_Arab"]
                },
                popular: ["auto", "eng_Latn", "spa_Latn", "fra_Latn", "deu_Latn", "rus_Cyrl"],
                popular_pairs: [["auto", "eng_Latn"], ["eng_Latn", "spa_Latn"], ["eng_Latn", "fra_Latn"]],
                total_count: 9
            };
        }

        /**
         * Fetch with API authentication
         */
        async fetchWithAuth(endpoint) {
            const config = window.NLLB_CONFIG || {};
            const url = `${config.translationServer}${endpoint}`;
            
            return fetch(url, {
                headers: {
                    'X-API-Key': config.apiKey,
                    'Content-Type': 'application/json'
                },
                timeout: 5000
            });
        }

        /**
         * Search languages by query
         */
        searchLanguages(query) {
            if (!query) return [];
            
            query = query.toLowerCase();
            const results = [];
            
            for (const lang of this.languages.values()) {
                if (lang.name.toLowerCase().includes(query) ||
                    lang.native_name.toLowerCase().includes(query) ||
                    lang.code.toLowerCase().includes(query)) {
                    results.push(lang);
                }
            }
            
            // Sort by popularity first, then by name
            results.sort((a, b) => {
                if (a.popular !== b.popular) return b.popular - a.popular;
                return a.name.localeCompare(b.name);
            });
            
            return results;
        }

        /**
         * Get language by code
         */
        getLanguage(code) {
            return this.languages.get(code);
        }

        /**
         * Get popular languages
         */
        getPopularLanguages() {
            return this.cache.languageData?.popular || ["auto", "eng_Latn", "spa_Latn", "fra_Latn", "rus_Cyrl"];
        }

        /**
         * Add to recent languages
         */
        addToRecentLanguages(langCode) {
            const recent = this.recentLanguages.filter(code => code !== langCode);
            recent.unshift(langCode);
            this.recentLanguages = recent.slice(0, 5);
            this.saveRecentLanguages();
        }

        /**
         * Load recent languages from storage
         */
        loadRecentLanguages() {
            try {
                const stored = localStorage.getItem('nllb_recent_languages');
                this.recentLanguages = stored ? JSON.parse(stored) : [];
            } catch (error) {
                console.warn('Failed to load recent languages:', error);
                this.recentLanguages = [];
            }
        }

        /**
         * Save recent languages to storage
         */
        saveRecentLanguages() {
            try {
                localStorage.setItem('nllb_recent_languages', JSON.stringify(this.recentLanguages));
            } catch (error) {
                console.warn('Failed to save recent languages:', error);
            }
        }
    }

    // ===== LANGUAGE SELECTOR COMPONENT =====
    class LanguageSelector {
        constructor(options = {}) {
            this.languageManager = options.languageManager;
            this.onLanguageChange = options.onLanguageChange;
            this.position = options.position || 'inline';
            this.mode = options.mode || 'single';
            this.currentTargetLang = options.defaultTarget || 'eng_Latn';
            
            this.container = null;
            this.dropdown = null;
            this.isOpen = false;
            this.selectedIndex = -1;
            this.filteredLanguages = [];
        }

        /**
         * Create the language selector UI
         */
        async create() {
            await this.languageManager.loadLanguages();
            log('Language selector created, available languages:', this.languageManager.languages.size);
            
            this.container = document.createElement('div');
            this.container.className = 'nllb-language-selector';
            
            this.createSingleLanguageSelector();
            
            return this.container;
        }

        /**
         * Create single language selector (target only)
         */
        createSingleLanguageSelector() {
            const button = document.createElement('button');
            button.className = 'nllb-language-button';
            button.type = 'button';
            
            this.updateSingleLanguageButton(button);
            
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleDropdown();
            });
            
            this.container.appendChild(button);
            this.createDropdown();
        }

        /**
         * Update single language button display
         */
        updateSingleLanguageButton(button) {
            const langInfo = this.languageManager.getLanguage(this.currentTargetLang);
            if (langInfo) {
                button.textContent = langInfo.name;
                button.title = langInfo.native_name;
            } else {
                button.textContent = this.currentTargetLang;
            }
        }

        /**
         * Create dropdown for language selection
         */
        createDropdown() {
            this.dropdown = document.createElement('div');
            this.dropdown.className = 'nllb-language-dropdown';
            this.dropdown.style.display = 'none';
            
            // Create language list
            this.populateDropdown();
            
            this.container.appendChild(this.dropdown);
            
            // Close dropdown when clicking outside
            document.addEventListener('click', (e) => {
                if (!this.container.contains(e.target)) {
                    this.closeDropdown();
                }
            });
        }

        /**
         * Populate dropdown with languages
         */
        populateDropdown() {
            this.dropdown.innerHTML = '';
            
            // Get languages to display
            const popular = this.languageManager.getPopularLanguages();
            const allLanguages = Array.from(this.languageManager.languages.values());
            
            log('Populating dropdown - popular:', popular.length, 'all:', allLanguages.length);
            
            // Popular languages section
            if (popular.length > 0) {
                const popularSection = document.createElement('div');
                popularSection.className = 'nllb-language-section';
                
                const popularTitle = document.createElement('div');
                popularTitle.className = 'nllb-language-section-title';
                popularTitle.textContent = 'Popular Languages';
                popularSection.appendChild(popularTitle);
                
                popular.forEach(langCode => {
                    const lang = this.languageManager.getLanguage(langCode);
                    if (lang) {
                        const option = this.createLanguageOption(lang);
                        popularSection.appendChild(option);
                    }
                });
                
                this.dropdown.appendChild(popularSection);
            }
            
            // All languages section
            if (allLanguages.length > 0) {
                const allSection = document.createElement('div');
                allSection.className = 'nllb-language-section';
                
                const allTitle = document.createElement('div');
                allTitle.className = 'nllb-language-section-title';
                allTitle.textContent = 'All Languages';
                allSection.appendChild(allTitle);
                
                allLanguages.forEach(lang => {
                    if (!popular.includes(lang.code)) {
                        const option = this.createLanguageOption(lang);
                        allSection.appendChild(option);
                    }
                });
                
                this.dropdown.appendChild(allSection);
            }
        }

        /**
         * Create language option element
         */
        createLanguageOption(lang) {
            const option = document.createElement('div');
            option.className = 'nllb-language-option';
            option.dataset.langCode = lang.code;
            
            const nameSpan = document.createElement('span');
            nameSpan.className = 'nllb-lang-name';
            nameSpan.textContent = lang.name;
            
            const nativeSpan = document.createElement('span');
            nativeSpan.className = 'nllb-lang-native';
            nativeSpan.textContent = lang.native_name;
            
            option.appendChild(nameSpan);
            if (lang.name !== lang.native_name) {
                option.appendChild(nativeSpan);
            }
            
            option.addEventListener('click', () => {
                this.selectLanguage(lang.code);
            });
            
            return option;
        }

        /**
         * Toggle dropdown visibility
         */
        toggleDropdown() {
            if (this.isOpen) {
                this.closeDropdown();
            } else {
                this.openDropdown();
            }
        }

        /**
         * Open dropdown
         */
        openDropdown() {
            this.dropdown.style.display = 'block';
            this.isOpen = true;
        }

        /**
         * Close dropdown
         */
        closeDropdown() {
            this.dropdown.style.display = 'none';
            this.isOpen = false;
        }

        /**
         * Select language
         */
        selectLanguage(langCode) {
            this.currentTargetLang = langCode;
            this.languageManager.addToRecentLanguages(langCode);
            
            // Update button
            const button = this.container.querySelector('.nllb-language-button');
            if (button) {
                this.updateSingleLanguageButton(button);
            }
            
            // Close dropdown
            this.closeDropdown();
            
            // Trigger callback
            if (this.onLanguageChange) {
                this.onLanguageChange(langCode);
            }
        }
    }

    // ===== MAIN USERSCRIPT CONFIGURATION =====
    
    // Configuration with bidirectional support and adaptive translation
    const CONFIG = {
        translationServer: 'http://localhost:8001',
        translationEndpoint: '/translate',
        adaptiveEndpoint: '/adaptive/translate',
        progressiveEndpoint: '/adaptive/translate/progressive',
        languagesEndpoint: '/languages',
        apiKey: '1234567',
        defaultSourceLang: 'auto',
        defaultTargetLang: 'eng_Latn',
        languageSelectionMode: 'single', // 'single' or 'pair'
        translateButtonText: '🌐',
        translatedPrefix: '🌐 ',
        showOriginalOnHover: true,
        debugMode: true,
        enablePreSendTranslation: true,
        autoTranslateInput: false,
        enableLanguageSwap: true,
        showRecentLanguages: true,
        maxRecentLanguages: 5,
        // Adaptive translation settings
        enableAdaptiveTranslation: true,
        userPreference: 'balanced', // 'fast', 'balanced', 'quality'
        enableProgressiveUI: true,
        qualityThreshold: 0.8,
        adaptiveForLongText: 500, // Enable adaptive for text longer than 500 chars
        maxOptimizationTime: 5.0
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
            
            .nllb-language-selector {
                position: relative;
                display: inline-block;
                margin: 0 4px;
            }
            
            .nllb-language-button {
                background: #3390ec;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                cursor: pointer;
                transition: all 0.2s ease;
                min-width: 60px;
            }
            
            .nllb-language-button:hover {
                background: #2980d9;
                transform: scale(1.05);
            }
            
            .nllb-language-dropdown {
                position: absolute;
                top: 100%;
                left: 0;
                background: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                z-index: 999999;
                max-height: 300px;
                min-width: 200px;
                overflow-y: auto;
            }
            
            .nllb-language-section {
                padding: 8px 0;
            }
            
            .nllb-language-section-title {
                font-weight: bold;
                padding: 4px 12px;
                font-size: 12px;
                color: #666;
                border-bottom: 1px solid #eee;
                margin-bottom: 4px;
            }
            
            .nllb-language-option {
                padding: 8px 12px;
                cursor: pointer;
                display: flex;
                justify-content: space-between;
                transition: background-color 0.2s ease;
            }
            
            .nllb-language-option:hover {
                background: #f5f5f5;
            }
            
            .nllb-lang-name {
                font-weight: 500;
            }
            
            .nllb-lang-native {
                color: #666;
                font-size: 12px;
            }
        `);
    }
    
    // Logging function
    function log(...args) {
        if (CONFIG.debugMode) {
            console.log('[NLLB Translator]', ...args);
        }
    }
    
    // Translate text using the API
    async function translateText(text, sourceLang = 'auto', targetLang = null, useAdaptive = null) {
        if (!targetLang) {
            targetLang = state.currentTargetLang;
        }
        
        if (!CONFIG.apiKey) {
            throw new Error('API key not configured');
        }
        
        if (!text.trim()) {
            throw new Error('No text to translate');
        }
        
        // Determine if adaptive translation should be used
        const shouldUseAdaptive = useAdaptive !== null ? useAdaptive : 
            (CONFIG.enableAdaptiveTranslation && text.length > CONFIG.adaptiveForLongText);
        
        log('Translating:', text, 'from', sourceLang, 'to', targetLang, 'adaptive:', shouldUseAdaptive);
        
        try {
            if (shouldUseAdaptive) {
                return await translateWithAdaptive(text, sourceLang, targetLang);
            } else {
                return await translateWithStandard(text, sourceLang, targetLang);
            }
        } catch (error) {
            log('Translation error:', error);
            throw error;
        }
    }

    async function translateWithStandard(text, sourceLang, targetLang) {
        const response = await fetch(`${CONFIG.translationServer}${CONFIG.translationEndpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': CONFIG.apiKey
            },
            body: JSON.stringify({
                text: text,
                source_lang: sourceLang,
                target_lang: targetLang
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(`Translation failed: ${response.status} ${response.statusText}${errorData.detail ? ': ' + errorData.detail : ''}`);
        }
        
        const data = await response.json();
        log('Standard translation result:', data);
        
        return {
            translatedText: data.translated_text,
            detectedSource: data.detected_source,
            timeMs: data.time_ms,
            qualityScore: null,
            optimizationApplied: false,
            cacheHit: false
        };
    }

    async function translateWithAdaptive(text, sourceLang, targetLang) {
        const response = await fetch(`${CONFIG.translationServer}${CONFIG.adaptiveEndpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': CONFIG.apiKey
            },
            body: JSON.stringify({
                text: text,
                source_lang: sourceLang,
                target_lang: targetLang,
                api_key: CONFIG.apiKey,
                user_preference: CONFIG.userPreference,
                force_optimization: false,
                max_optimization_time: CONFIG.maxOptimizationTime
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(`Adaptive translation failed: ${response.status} ${response.statusText}${errorData.detail ? ': ' + errorData.detail : ''}`);
        }
        
        const data = await response.json();
        log('Adaptive translation result:', data);
        
        return {
            translatedText: data.translation,
            detectedSource: sourceLang, // Adaptive API doesn't return detected source yet
            timeMs: Math.round(data.processing_time * 1000),
            qualityScore: data.quality_score,
            qualityGrade: data.quality_grade,
            optimizationApplied: data.optimization_applied,
            cacheHit: data.cache_hit,
            metadata: data.metadata
        };
    }
    
    // Progressive translation with real-time updates
    async function translateWithProgressive(text, sourceLang, targetLang, onUpdate) {
        if (!CONFIG.enableProgressiveUI) {
            return await translateText(text, sourceLang, targetLang, true);
        }

        const response = await fetch(`${CONFIG.translationServer}${CONFIG.progressiveEndpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': CONFIG.apiKey
            },
            body: JSON.stringify({
                text: text,
                source_lang: sourceLang,
                target_lang: targetLang,
                api_key: CONFIG.apiKey,
                user_preference: CONFIG.userPreference,
                force_optimization: false,
                max_optimization_time: CONFIG.maxOptimizationTime
            })
        });

        if (!response.ok) {
            throw new Error(`Progressive translation failed: ${response.status} ${response.statusText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let finalResult = null;

        try {
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                
                // Process complete lines
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Keep incomplete line in buffer
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            if (data.stage === 'completed') {
                                finalResult = {
                                    translatedText: data.translation,
                                    detectedSource: sourceLang,
                                    timeMs: Math.round(data.processing_time * 1000),
                                    qualityScore: data.quality_score,
                                    qualityGrade: data.quality_grade,
                                    optimizationApplied: data.optimization_applied,
                                    cacheHit: data.cache_hit,
                                    metadata: data.metadata
                                };
                            } else if (data.stage === 'error') {
                                throw new Error(data.error);
                            }
                            
                            // Call update callback
                            if (onUpdate) {
                                onUpdate(data);
                            }
                        } catch (parseError) {
                            log('Failed to parse SSE data:', parseError, line);
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }

        return finalResult || { translatedText: text, error: 'No final result received' };
    }

    // Create translate button with progressive UI support
    function createTranslateButton(messageElement, text) {
        const button = document.createElement('span');
        button.className = 'nllb-translate-button';
        button.textContent = CONFIG.translateButtonText;
        button.title = 'Translate this message';
        
        // Add quality indicator if adaptive translation is enabled
        const shouldUseAdaptive = CONFIG.enableAdaptiveTranslation && text.length > CONFIG.adaptiveForLongText;
        if (shouldUseAdaptive) {
            button.title += ' (with quality optimization)';
            button.style.background = 'linear-gradient(45deg, #4CAF50, #2196F3)';
            button.style.color = 'white';
            button.style.borderRadius = '3px';
            button.style.padding = '2px 4px';
        }
        
        button.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            if (button.classList.contains('nllb-translating')) {
                return;
            }
            
            button.classList.add('nllb-translating');
            
            try {
                if (shouldUseAdaptive && CONFIG.enableProgressiveUI) {
                    await handleProgressiveTranslation(messageElement, text, button);
                } else {
                    button.textContent = '⏳';
                    const result = await translateText(text);
                    displayTranslation(messageElement, text, result.translatedText, result);
                    button.remove();
                }
            } catch (error) {
                button.classList.remove('nllb-translating');
                button.textContent = CONFIG.translateButtonText;
                showError(messageElement, error.message);
            }
        });
        
        return button;
    }

    // Handle progressive translation with real-time updates
    async function handleProgressiveTranslation(messageElement, text, button) {
        let currentTranslation = '';
        let progressElement = null;
        let qualityElement = null;
        
        // Create progress indicators
        const createProgressUI = () => {
            const container = document.createElement('div');
            container.className = 'nllb-progress-container';
            container.style.cssText = `
                margin: 4px 0;
                padding: 6px 8px;
                background: #f0f2f5;
                border-radius: 8px;
                font-size: 12px;
                border-left: 3px solid #2196F3;
            `;
            
            progressElement = document.createElement('div');
            progressElement.className = 'nllb-progress-text';
            progressElement.style.cssText = `
                color: #65676B;
                margin-bottom: 4px;
            `;
            
            qualityElement = document.createElement('div');
            qualityElement.className = 'nllb-quality-indicator';
            qualityElement.style.cssText = `
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 11px;
            `;
            
            container.appendChild(progressElement);
            container.appendChild(qualityElement);
            
            // Insert after the message
            messageElement.parentNode.insertBefore(container, messageElement.nextSibling);
            
            return container;
        };
        
        const progressContainer = createProgressUI();
        
        const updateProgress = (data) => {
            log('Progressive update:', data);
            
            // Update button appearance
            if (data.stage === 'semantic') {
                button.textContent = '🚀';
                button.title = 'Fast translation complete';
                progressElement.textContent = `📝 ${data.status_message || 'Semantic translation...'}`;
            } else if (data.stage === 'analyzing') {
                button.textContent = '🔍';
                button.title = 'Analyzing quality';
                progressElement.textContent = `🔍 ${data.status_message || 'Analyzing quality...'}`;
            } else if (data.stage === 'optimizing') {
                button.textContent = '⚡';
                button.title = 'Optimizing quality';
                progressElement.textContent = `⚡ ${data.status_message || 'Optimizing translation...'}`;
            } else if (data.stage === 'optimized' || data.stage === 'completed') {
                button.textContent = '✅';
                button.title = 'Translation complete';
                progressElement.textContent = `✅ ${data.status_message || 'Translation complete'}`;
            }
            
            // Update translation if available
            if (data.translation && data.translation !== currentTranslation) {
                currentTranslation = data.translation;
                displayTranslation(messageElement, text, currentTranslation, data, true);
            }
            
            // Update quality indicator
            if (data.quality_score !== undefined && qualityElement) {
                const grade = data.quality_grade || getQualityGrade(data.quality_score);
                const gradeColor = getQualityColor(grade);
                const isOptimized = data.stage === 'optimized' || data.optimization_applied;
                
                qualityElement.innerHTML = `
                    <span style="color: ${gradeColor}; font-weight: bold;">Quality: ${grade}</span>
                    <span style="color: #65676B;">(${(data.quality_score * 100).toFixed(0)}%)</span>
                    ${isOptimized ? '<span style="color: #4CAF50;">⚡ Optimized</span>' : ''}
                    ${data.cache_hit ? '<span style="color: #FF9800;">💾 Cached</span>' : ''}
                `;
            }
            
            // Update progress bar
            if (data.progress !== undefined) {
                const progressBar = progressElement.querySelector('.progress-bar');
                if (!progressBar) {
                    const bar = document.createElement('div');
                    bar.className = 'progress-bar';
                    bar.style.cssText = `
                        height: 2px;
                        background: #e3f2fd;
                        border-radius: 1px;
                        margin-top: 4px;
                        overflow: hidden;
                    `;
                    const fill = document.createElement('div');
                    fill.style.cssText = `
                        height: 100%;
                        background: #2196F3;
                        transition: width 0.3s ease;
                        width: ${data.progress * 100}%;
                    `;
                    bar.appendChild(fill);
                    progressElement.appendChild(bar);
                } else {
                    progressBar.firstChild.style.width = `${data.progress * 100}%`;
                }
            }
        };
        
        try {
            const result = await translateWithProgressive(
                text, 
                state.currentSourceLang || 'auto', 
                state.currentTargetLang,
                updateProgress
            );
            
            // Final update
            if (result && result.translatedText) {
                displayTranslation(messageElement, text, result.translatedText, result);
            }
            
            // Clean up progress UI after delay
            setTimeout(() => {
                if (progressContainer && progressContainer.parentNode) {
                    progressContainer.remove();
                }
                if (button && button.parentNode) {
                    button.remove();
                }
            }, 2000);
            
        } catch (error) {
            progressElement.textContent = `❌ Error: ${error.message}`;
            progressElement.style.color = '#f44336';
            setTimeout(() => {
                if (progressContainer && progressContainer.parentNode) {
                    progressContainer.remove();
                }
            }, 3000);
            throw error;
        }
    }

    // Helper functions for quality display
    function getQualityGrade(score) {
        if (score >= 0.9) return 'A';
        if (score >= 0.8) return 'B';
        if (score >= 0.7) return 'C';
        if (score >= 0.6) return 'D';
        return 'F';
    }

    function getQualityColor(grade) {
        const colors = {
            'A': '#4CAF50',
            'B': '#8BC34A',
            'C': '#FFC107',
            'D': '#FF9800',
            'F': '#f44336'
        };
        return colors[grade] || '#65676B';
    }
    
    // Create language selector for message
    function createLanguageSelector(messageElement) {
        const selector = new LanguageSelector({
            languageManager: state.languageManager,
            defaultTarget: state.currentTargetLang,
            onLanguageChange: (langCode) => {
                state.currentTargetLang = langCode;
                CONFIG.defaultTargetLang = langCode;
                saveSettings();
                log('Target language changed to:', langCode);
            }
        });
        
        selector.create().then(element => {
            const buttonContainer = messageElement.querySelector('.nllb-button-container');
            if (buttonContainer) {
                buttonContainer.appendChild(element);
            }
        });
        
        return selector;
    }
    
    // Display translation
    function displayTranslation(messageElement, originalText, translatedText, result = null, isProgressive = false) {
        const messageContent = messageElement.querySelector('.message-content, .text-content');
        if (!messageContent) return;
        
        let textElement = messageContent.querySelector('span:not(.nllb-translated)');
        let translatedWrapper = messageContent.querySelector('.nllb-translated');
        
        // For progressive updates, reuse existing wrapper if available
        if (isProgressive && translatedWrapper) {
            // Update existing translation
            const textSpan = translatedWrapper.querySelector('.nllb-translation-text') || translatedWrapper;
            textSpan.textContent = CONFIG.translatedPrefix + translatedText;
            
            // Update quality indicator if available
            let qualityIndicator = translatedWrapper.querySelector('.nllb-quality-badge');
            if (result && (result.qualityScore !== undefined || result.qualityGrade)) {
                if (!qualityIndicator) {
                    qualityIndicator = document.createElement('span');
                    qualityIndicator.className = 'nllb-quality-badge';
                    qualityIndicator.style.cssText = `
                        margin-left: 4px;
                        padding: 1px 4px;
                        border-radius: 2px;
                        font-size: 10px;
                        font-weight: bold;
                        color: white;
                    `;
                    translatedWrapper.appendChild(qualityIndicator);
                }
                
                const grade = result.qualityGrade || getQualityGrade(result.qualityScore);
                const color = getQualityColor(grade);
                qualityIndicator.style.backgroundColor = color;
                qualityIndicator.textContent = grade;
                qualityIndicator.title = `Quality: ${grade} (${result.qualityScore ? (result.qualityScore * 100).toFixed(0) : 'N/A'}%)`;
            }
            
            return;
        }
        
        if (!textElement && !translatedWrapper) return;
        
        // Create translated wrapper
        if (!translatedWrapper) {
            translatedWrapper = document.createElement('span');
            translatedWrapper.className = 'nllb-translated';
        }
        
        // Create translation text container
        const translationTextSpan = document.createElement('span');
        translationTextSpan.className = 'nllb-translation-text';
        translationTextSpan.textContent = CONFIG.translatedPrefix + translatedText;
        translatedWrapper.appendChild(translationTextSpan);
        
        // Add quality badge for adaptive translations
        if (result && (result.qualityScore !== undefined || result.qualityGrade)) {
            const qualityBadge = document.createElement('span');
            qualityBadge.className = 'nllb-quality-badge';
            qualityBadge.style.cssText = `
                margin-left: 4px;
                padding: 1px 4px;
                border-radius: 2px;
                font-size: 10px;
                font-weight: bold;
                color: white;
            `;
            
            const grade = result.qualityGrade || getQualityGrade(result.qualityScore);
            const color = getQualityColor(grade);
            qualityBadge.style.backgroundColor = color;
            qualityBadge.textContent = grade;
            qualityBadge.title = `Quality: ${grade} (${result.qualityScore ? (result.qualityScore * 100).toFixed(0) : 'N/A'}%)`;
            
            // Add optimization indicator
            if (result.optimizationApplied) {
                qualityBadge.title += ' - Optimized';
                qualityBadge.style.background = `linear-gradient(45deg, ${color}, #4CAF50)`;
            }
            
            // Add cache indicator
            if (result.cacheHit) {
                qualityBadge.title += ' - Cached';
                const cacheIcon = document.createElement('span');
                cacheIcon.textContent = '💾';
                cacheIcon.style.fontSize = '8px';
                cacheIcon.style.marginLeft = '2px';
                qualityBadge.appendChild(cacheIcon);
            }
            
            translatedWrapper.appendChild(qualityBadge);
        }
        
        // Create original text tooltip
        if (CONFIG.showOriginalOnHover) {
            const originalTooltip = document.createElement('span');
            originalTooltip.className = 'nllb-original-text';
            originalTooltip.textContent = originalText;
            translatedWrapper.appendChild(originalTooltip);
        }
        
        // Replace original text if not already replaced
        if (textElement && textElement.parentNode) {
            textElement.replaceWith(translatedWrapper);
        } else if (!messageContent.contains(translatedWrapper)) {
            messageContent.appendChild(translatedWrapper);
        }
        
        // Store translation with metadata
        state.translatedMessages.set(messageElement, {
            original: originalText,
            translated: translatedText,
            timestamp: Date.now(),
            qualityScore: result?.qualityScore,
            qualityGrade: result?.qualityGrade,
            optimizationApplied: result?.optimizationApplied,
            cacheHit: result?.cacheHit,
            processingTime: result?.timeMs
        });
    }
    
    // Show error message
    function showError(messageElement, errorMessage) {
        const errorElement = document.createElement('div');
        errorElement.className = 'nllb-error';
        errorElement.textContent = 'Translation error: ' + errorMessage;
        
        const messageContent = messageElement.querySelector('.message-content, .text-content');
        if (messageContent) {
            messageContent.appendChild(errorElement);
            
            // Remove error after 5 seconds
            setTimeout(() => {
                errorElement.remove();
            }, 5000);
        }
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
        
        // Create simple language selector button
        if (!state.languageSelectors.has(messageId)) {
            try {
                const langButton = document.createElement('span');
                langButton.className = 'nllb-language-button';
                langButton.textContent = CONFIG.defaultTargetLang === 'eng_Latn' ? 'EN' : 'RU';
                langButton.title = 'Click to change target language';
                
                langButton.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    // Toggle between English and Russian
                    if (state.currentTargetLang === 'eng_Latn') {
                        state.currentTargetLang = 'rus_Cyrl';
                        langButton.textContent = 'RU';
                    } else {
                        state.currentTargetLang = 'eng_Latn';
                        langButton.textContent = 'EN';
                    }
                    CONFIG.defaultTargetLang = state.currentTargetLang;
                    saveSettings();
                    log('Target language changed to:', state.currentTargetLang);
                });
                
                state.languageSelectors.set(messageId, { button: langButton });
                toolbarContainer.appendChild(langButton);
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
            const result = await translateText(text, state.currentSourceLang, state.currentTargetLang);
            const translatedText = result.translatedText;
            
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
    
    // Find and process messages  
    function findAndProcessMessages() {
        const bubbles = document.querySelectorAll('.bubble');
        log(`Found ${bubbles.length} message bubbles`);
        
        bubbles.forEach(bubble => {
            if (!bubble.classList.contains('is-system') && 
                !bubble.classList.contains('own') &&
                bubble.querySelector('.message')) {
                addTranslateButton(bubble);
            }
        });
        
        // Handle input areas if pre-send translation is enabled
        if (CONFIG.enablePreSendTranslation) {
            const inputs = findInputAreas();
            inputs.forEach(addInputTranslationToolbar);
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
            const result = await translateText(text);
            const translatedText = result.translatedText;
            
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
    
    // Initialize the translator
    async function initialize() {
        if (state.initialized) return;
        
        log('Initializing NLLB Translator...');
        
        // Load settings
        loadSettings();
        
        // Initialize language manager
        state.languageManager = new LanguageManager();
        await state.languageManager.loadLanguages();
        state.languageManager.loadRecentLanguages();
        
        // Inject styles
        injectStyles();
        
        // Process existing messages
        findAndProcessMessages();
        
        // Set up observer for new messages
        state.observer = new MutationObserver((mutations) => {
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
                                    !bubble.classList.contains('own') &&
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
        });
        
        state.observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        state.initialized = true;
        log('NLLB Translator initialized successfully');
    }
    
    // Settings menu
    function createSettingsMenu() {
        GM_registerMenuCommand('Configure NLLB Translator', () => {
            const apiKey = prompt('Enter your API key:', CONFIG.apiKey);
            if (apiKey !== null) {
                CONFIG.apiKey = apiKey;
                saveSettings();
                alert('API key saved successfully!');
            }
        });
        
        GM_registerMenuCommand('Set Translation Server', () => {
            const server = prompt('Enter translation server URL:', CONFIG.translationServer);
            if (server !== null) {
                CONFIG.translationServer = server.replace(/\/$/, ''); // Remove trailing slash
                saveSettings();
                alert('Translation server updated successfully!');
            }
        });
        
        GM_registerMenuCommand('Toggle Debug Mode', () => {
            CONFIG.debugMode = !CONFIG.debugMode;
            saveSettings();
            alert(`Debug mode ${CONFIG.debugMode ? 'enabled' : 'disabled'}`);
        });
    }
    
    // Wait for page to load and initialize
    function waitForPageLoad() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initialize);
        } else {
            // Page is already loaded
            setTimeout(initialize, 1000);
        }
    }
    
    // Start the translator
    createSettingsMenu();
    waitForPageLoad();
    
})();