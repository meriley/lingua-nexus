/**
 * NLLB Translation UserScript - Modular Components
 * Language management, settings, and UI components for bidirectional translation
 */

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
            return this.getDefaultLanguages();
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
                    code: "rus_Cyrl",
                    name: "Russian",
                    native_name: "Русский",
                    family: "Slavic",
                    script: "Cyrillic",
                    popular: true,
                    region: "Eastern Europe",
                    rtl: false
                }
            ],
            families: {
                "Auto": ["auto"],
                "Germanic": ["eng_Latn"],
                "Slavic": ["rus_Cyrl"]
            },
            popular: ["auto", "eng_Latn", "rus_Cyrl"],
            popular_pairs: [["auto", "eng_Latn"], ["eng_Latn", "rus_Cyrl"]],
            total_count: 3
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
        return this.cache.languageData?.popular || ["auto", "eng_Latn", "rus_Cyrl"];
    }

    /**
     * Get popular language pairs
     */
    getPopularLanguagePairs() {
        return this.cache.languageData?.popular_pairs || [["auto", "eng_Latn"]];
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
     * Add to recent language pairs
     */
    addToRecentLanguagePairs(sourceLang, targetLang) {
        const pairKey = `${sourceLang}|${targetLang}`;
        const recent = this.recentLanguagePairs.filter(pair => pair !== pairKey);
        recent.unshift(pairKey);
        this.recentLanguagePairs = recent.slice(0, 5);
        this.saveRecentLanguagePairs();
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

    /**
     * Load recent language pairs from storage
     */
    loadRecentLanguagePairs() {
        try {
            const stored = localStorage.getItem('nllb_recent_language_pairs');
            this.recentLanguagePairs = stored ? JSON.parse(stored) : [];
        } catch (error) {
            console.warn('Failed to load recent language pairs:', error);
            this.recentLanguagePairs = [];
        }
    }

    /**
     * Save recent language pairs to storage
     */
    saveRecentLanguagePairs() {
        try {
            localStorage.setItem('nllb_recent_language_pairs', JSON.stringify(this.recentLanguagePairs));
        } catch (error) {
            console.warn('Failed to save recent language pairs:', error);
        }
    }

    /**
     * Parse language pair key
     */
    parseLanguagePair(pairKey) {
        const [source, target] = pairKey.split('|');
        return { source, target };
    }

    /**
     * Format language pair for display
     */
    formatLanguagePair(sourceLang, targetLang) {
        const sourceInfo = this.getLanguage(sourceLang);
        const targetInfo = this.getLanguage(targetLang);
        
        if (!sourceInfo || !targetInfo) return `${sourceLang} → ${targetLang}`;
        
        return `${sourceInfo.name} → ${targetInfo.name}`;
    }
}

// ===== LANGUAGE SELECTOR COMPONENT =====
class LanguageSelector {
    constructor(options = {}) {
        this.languageManager = options.languageManager;
        this.onLanguageChange = options.onLanguageChange;
        this.onLanguagePairChange = options.onLanguagePairChange;
        this.position = options.position || 'inline';
        this.mode = options.mode || 'single'; // 'single', 'pair'
        this.currentSourceLang = options.defaultSource || 'auto';
        this.currentTargetLang = options.defaultTarget || 'eng_Latn';
        
        this.container = null;
        this.dropdown = null;
        this.isOpen = false;
        this.searchInput = null;
        this.selectedIndex = -1;
        this.filteredLanguages = [];
    }

    /**
     * Create the language selector UI
     */
    async create() {
        await this.languageManager.loadLanguages();
        
        this.container = document.createElement('div');
        this.container.className = 'nllb-language-selector';
        
        if (this.mode === 'pair') {
            this.createLanguagePairSelector();
        } else {
            this.createSingleLanguageSelector();
        }
        
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
     * Create language pair selector (source + target)
     */
    createLanguagePairSelector() {
        const pairContainer = document.createElement('div');
        pairContainer.className = 'nllb-language-pair-container';
        
        // Source language button
        const sourceButton = document.createElement('button');
        sourceButton.className = 'nllb-language-button nllb-source-lang';
        sourceButton.type = 'button';
        this.updateLanguageButton(sourceButton, this.currentSourceLang);
        
        // Swap button
        const swapButton = document.createElement('button');
        swapButton.className = 'nllb-swap-button';
        swapButton.type = 'button';
        swapButton.innerHTML = '⇄';
        swapButton.title = 'Swap languages';
        
        // Target language button
        const targetButton = document.createElement('button');
        targetButton.className = 'nllb-language-button nllb-target-lang';
        targetButton.type = 'button';
        this.updateLanguageButton(targetButton, this.currentTargetLang);
        
        // Event listeners
        sourceButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.openLanguagePicker('source');
        });
        
        targetButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.openLanguagePicker('target');
        });
        
        swapButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.swapLanguages();
        });
        
        pairContainer.appendChild(sourceButton);
        pairContainer.appendChild(swapButton);
        pairContainer.appendChild(targetButton);
        
        this.container.appendChild(pairContainer);
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
     * Update language button display
     */
    updateLanguageButton(button, langCode) {
        const langInfo = this.languageManager.getLanguage(langCode);
        if (langInfo) {
            button.textContent = langInfo.name;
            button.title = langInfo.native_name;
        } else {
            button.textContent = langCode;
        }
    }

    /**
     * Create dropdown for language selection
     */
    createDropdown() {
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'nllb-language-dropdown';
        this.dropdown.style.display = 'none';
        
        // Search input
        this.searchInput = document.createElement('input');
        this.searchInput.type = 'text';
        this.searchInput.className = 'nllb-language-search';
        this.searchInput.placeholder = 'Search languages...';
        
        // Results container
        this.resultsContainer = document.createElement('div');
        this.resultsContainer.className = 'nllb-language-results';
        
        this.dropdown.appendChild(this.searchInput);
        this.dropdown.appendChild(this.resultsContainer);
        
        // Event listeners
        this.searchInput.addEventListener('input', (e) => {
            this.filterLanguages(e.target.value);
        });
        
        this.searchInput.addEventListener('keydown', (e) => {
            this.handleKeyboardNavigation(e);
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.closeDropdown();
            }
        });
        
        this.container.appendChild(this.dropdown);
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
        this.isOpen = true;
        this.dropdown.style.display = 'block';
        this.searchInput.focus();
        this.filterLanguages('');
    }

    /**
     * Close dropdown
     */
    closeDropdown() {
        this.isOpen = false;
        this.dropdown.style.display = 'none';
        this.searchInput.value = '';
        this.selectedIndex = -1;
    }

    /**
     * Filter languages based on search term
     */
    filterLanguages(searchTerm) {
        // Get recent languages first
        const recentLangs = this.mode === 'pair' 
            ? this.getRecentLanguagePairsForDisplay()
            : this.getRecentLanguagesForDisplay();
        
        // Get popular languages
        const popularLangs = this.getPopularLanguagesForDisplay();
        
        // Get search results
        const searchResults = searchTerm 
            ? this.languageManager.searchLanguages(searchTerm)
            : [];
        
        this.filteredLanguages = [];
        this.resultsContainer.innerHTML = '';
        
        // Add recent languages section
        if (recentLangs.length > 0 && !searchTerm) {
            this.addLanguageSection('Recently Used', recentLangs, true);
        }
        
        // Add popular languages section
        if (popularLangs.length > 0 && !searchTerm) {
            this.addLanguageSection('Popular', popularLangs, false);
        }
        
        // Add search results
        if (searchResults.length > 0) {
            this.addLanguageSection(searchTerm ? 'Search Results' : 'All Languages', searchResults, false);
        }
        
        // Update selection
        this.selectedIndex = -1;
        this.updateSelection();
    }

    /**
     * Get recent languages for display
     */
    getRecentLanguagesForDisplay() {
        return this.languageManager.recentLanguages
            .map(code => this.languageManager.getLanguage(code))
            .filter(lang => lang);
    }

    /**
     * Get recent language pairs for display
     */
    getRecentLanguagePairsForDisplay() {
        return this.languageManager.recentLanguagePairs
            .map(pairKey => {
                const { source, target } = this.languageManager.parseLanguagePair(pairKey);
                const sourceLang = this.languageManager.getLanguage(source);
                const targetLang = this.languageManager.getLanguage(target);
                if (sourceLang && targetLang) {
                    return {
                        code: pairKey,
                        name: this.languageManager.formatLanguagePair(source, target),
                        native_name: `${sourceLang.native_name} → ${targetLang.native_name}`,
                        isPair: true,
                        source,
                        target
                    };
                }
                return null;
            })
            .filter(pair => pair);
    }

    /**
     * Get popular languages for display
     */
    getPopularLanguagesForDisplay() {
        return this.languageManager.getPopularLanguages()
            .map(code => this.languageManager.getLanguage(code))
            .filter(lang => lang);
    }

    /**
     * Add language section to results
     */
    addLanguageSection(title, languages, isRecent) {
        if (languages.length === 0) return;
        
        const section = document.createElement('div');
        section.className = 'nllb-language-section';
        
        const header = document.createElement('div');
        header.className = 'nllb-language-section-header';
        header.textContent = title;
        section.appendChild(header);
        
        languages.forEach(lang => {
            const item = this.createLanguageItem(lang, isRecent);
            section.appendChild(item);
            this.filteredLanguages.push(lang);
        });
        
        this.resultsContainer.appendChild(section);
    }

    /**
     * Create language item element
     */
    createLanguageItem(lang, isRecent) {
        const item = document.createElement('div');
        item.className = 'nllb-language-item';
        
        if (isRecent) item.classList.add('recent');
        if (lang.popular) item.classList.add('popular');
        if (lang.isPair) item.classList.add('pair');
        
        const nameEl = document.createElement('span');
        nameEl.className = 'nllb-language-name';
        nameEl.textContent = lang.name;
        
        const nativeEl = document.createElement('span');
        nativeEl.className = 'nllb-language-native';
        nativeEl.textContent = lang.native_name;
        
        item.appendChild(nameEl);
        item.appendChild(nativeEl);
        
        // Click handler
        item.addEventListener('click', () => {
            this.selectLanguage(lang);
        });
        
        return item;
    }

    /**
     * Select a language
     */
    selectLanguage(lang) {
        if (this.mode === 'pair') {
            if (lang.isPair) {
                this.currentSourceLang = lang.source;
                this.currentTargetLang = lang.target;
                this.languageManager.addToRecentLanguagePairs(lang.source, lang.target);
                this.updateLanguagePairDisplay();
                if (this.onLanguagePairChange) {
                    this.onLanguagePairChange(lang.source, lang.target);
                }
            }
        } else {
            this.currentTargetLang = lang.code;
            this.languageManager.addToRecentLanguages(lang.code);
            this.updateSingleLanguageDisplay();
            if (this.onLanguageChange) {
                this.onLanguageChange(lang.code);
            }
        }
        
        this.closeDropdown();
    }

    /**
     * Update language pair display
     */
    updateLanguagePairDisplay() {
        const sourceButton = this.container.querySelector('.nllb-source-lang');
        const targetButton = this.container.querySelector('.nllb-target-lang');
        
        if (sourceButton) this.updateLanguageButton(sourceButton, this.currentSourceLang);
        if (targetButton) this.updateLanguageButton(targetButton, this.currentTargetLang);
    }

    /**
     * Update single language display
     */
    updateSingleLanguageDisplay() {
        const button = this.container.querySelector('.nllb-language-button');
        if (button) this.updateSingleLanguageButton(button);
    }

    /**
     * Swap source and target languages
     */
    swapLanguages() {
        if (this.currentSourceLang === 'auto') {
            // Can't swap from auto-detect
            return;
        }
        
        const temp = this.currentSourceLang;
        this.currentSourceLang = this.currentTargetLang;
        this.currentTargetLang = temp;
        
        this.languageManager.addToRecentLanguagePairs(this.currentSourceLang, this.currentTargetLang);
        this.updateLanguagePairDisplay();
        
        if (this.onLanguagePairChange) {
            this.onLanguagePairChange(this.currentSourceLang, this.currentTargetLang);
        }
    }

    /**
     * Handle keyboard navigation
     */
    handleKeyboardNavigation(event) {
        switch (event.key) {
            case 'ArrowDown':
                this.selectedIndex = Math.min(this.selectedIndex + 1, this.filteredLanguages.length - 1);
                this.updateSelection();
                event.preventDefault();
                break;
            case 'ArrowUp':
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                this.updateSelection();
                event.preventDefault();
                break;
            case 'Enter':
                if (this.selectedIndex >= 0 && this.filteredLanguages[this.selectedIndex]) {
                    this.selectLanguage(this.filteredLanguages[this.selectedIndex]);
                }
                event.preventDefault();
                break;
            case 'Escape':
                this.closeDropdown();
                event.preventDefault();
                break;
        }
    }

    /**
     * Update visual selection
     */
    updateSelection() {
        const items = this.resultsContainer.querySelectorAll('.nllb-language-item');
        items.forEach((item, index) => {
            item.classList.toggle('selected', index === this.selectedIndex);
        });
        
        // Scroll selected item into view
        if (this.selectedIndex >= 0 && items[this.selectedIndex]) {
            items[this.selectedIndex].scrollIntoView({
                block: 'nearest',
                behavior: 'smooth'
            });
        }
    }

    /**
     * Open language picker for specific position (source/target)
     */
    openLanguagePicker(position) {
        this.pickerPosition = position;
        this.openDropdown();
    }

    /**
     * Get current language pair
     */
    getCurrentLanguagePair() {
        return {
            source: this.currentSourceLang,
            target: this.currentTargetLang
        };
    }

    /**
     * Set current language pair
     */
    setCurrentLanguagePair(sourceLang, targetLang) {
        this.currentSourceLang = sourceLang;
        this.currentTargetLang = targetLang;
        
        if (this.mode === 'pair') {
            this.updateLanguagePairDisplay();
        } else {
            this.updateSingleLanguageDisplay();
        }
    }

    /**
     * Switch between single and pair mode
     */
    switchMode(newMode) {
        if (this.mode === newMode) return;
        
        this.mode = newMode;
        this.container.innerHTML = '';
        
        if (this.mode === 'pair') {
            this.createLanguagePairSelector();
        } else {
            this.createSingleLanguageSelector();
        }
        
        this.createDropdown();
    }

    /**
     * Destroy the selector
     */
    destroy() {
        if (this.container && this.container.parentNode) {
            this.container.parentNode.removeChild(this.container);
        }
    }
}

// Export for use in main userscript
if (typeof window !== 'undefined') {
    window.LanguageManager = LanguageManager;
    window.LanguageSelector = LanguageSelector;
}