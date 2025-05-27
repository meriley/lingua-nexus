# Ad Hoc Destination Language Selection Architecture

## Overview

This document outlines the architecture for implementing dynamic destination language selection across all components of the NLLB Translation System. This enhancement allows users to select target languages on-demand rather than using fixed settings.

## Current State Analysis

### Existing Components
- **UserScript**: Fixed destination language in settings
- **AutoHotkey**: Hardcoded language configuration
- **API Server**: Supports dynamic language parameters
- **Settings**: Static language configuration

### Limitations
- Users cannot quickly translate to different languages
- No contextual language selection
- Poor user experience for multilingual conversations
- Limited flexibility for diverse translation needs

## Proposed Architecture

### 1. UserScript Enhancements

#### Language Selection UI Components

```javascript
// Language dropdown component
class LanguageSelector {
    constructor(onLanguageChange) {
        this.languages = SUPPORTED_LANGUAGES;
        this.onLanguageChange = onLanguageChange;
        this.recentLanguages = this.loadRecentLanguages();
    }
    
    createDropdown(position = 'inline') {
        // Create dropdown with search functionality
        // Show recent languages at top
        // Group by language families
    }
}
```

#### Integration Points
- **Translation Button**: Add language selector dropdown next to translate button
- **Input Toolbar**: Include language selection in pre-send translation
- **Bulk Translation**: Multi-language selection for batch operations
- **Context Menu**: Right-click language selection option

#### Settings Management
```javascript
const LanguageSettings = {
    defaultLanguage: 'eng_Latn', // English as fallback
    recentLanguages: [], // Last 5 used languages
    favoriteLanguages: [], // User-pinned languages
    autoDetectContext: true, // Smart language suggestions
    showLanguageCodes: false, // Display codes vs names
};
```

### 2. AutoHotkey Script Updates

#### Hotkey-Based Language Selection (AutoHotkey v2.0)
```autohotkey
; Language selection hotkeys
^!1::SetTargetLanguage("spa_Latn")  ; Spanish
^!2::SetTargetLanguage("fra_Latn")  ; French
^!3::SetTargetLanguage("deu_Latn")  ; German
^!4::ShowLanguageMenu()             ; Dynamic menu

SetTargetLanguage(langCode) {
    global currentTargetLanguage
    currentTargetLanguage := langCode
    ToolTip("Target: " . GetLanguageName(langCode))
    SetTimer(HideToolTip, 2000)
}

HideToolTip() {
    ToolTip()
}
```

#### GUI Language Selector
- Popup window with language list
- Search/filter functionality
- Recent languages section
- Keyboard navigation support

### 3. API Server Enhancements

#### Enhanced Translation Endpoint
```python
@app.post("/translate")
async def translate_text(request: TranslationRequest):
    # Already supports dynamic src_lang and tgt_lang
    # Add language validation and suggestions
    pass

@app.get("/languages")
async def get_supported_languages():
    """Return list of supported languages with metadata"""
    return {
        "languages": [
            {
                "code": "eng_Latn",
                "name": "English",
                "native_name": "English",
                "family": "Germanic",
                "script": "Latin",
                "popular": True
            },
            # ... more languages
        ],
        "language_families": ["Germanic", "Romance", "Slavic", ...],
        "popular_languages": ["eng_Latn", "spa_Latn", "fra_Latn", ...]
    }
```

#### Language Intelligence Features
- **Auto-detection**: Improve source language detection
- **Context-aware suggestions**: Suggest languages based on conversation history
- **Translation confidence**: Return confidence scores for suggestions

### 4. UI/UX Design Patterns

#### Language Selection Patterns

1. **Inline Dropdown** (Primary)
   - Compact dropdown next to translate button
   - Shows recent + popular languages
   - Search functionality for full list

2. **Modal Selector** (Secondary)
   - Full-screen language picker
   - Organized by families/regions
   - Favorites and recent sections

3. **Quick Actions** (Tertiary)
   - Keyboard shortcuts
   - Gesture-based selection
   - Voice commands (future)

#### Visual Design
```css
.language-selector {
    position: relative;
    display: inline-block;
}

.language-dropdown {
    min-width: 200px;
    max-height: 300px;
    overflow-y: auto;
    border: 1px solid #ccc;
    border-radius: 4px;
    background: white;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.language-item {
    padding: 8px 12px;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
}

.language-item:hover {
    background: #f5f5f5;
}

.language-item.recent {
    border-left: 3px solid #007bff;
}

.language-item.favorite {
    color: #ffc107;
}
```

### 5. Data Management

#### Language Data Structure
```javascript
const LANGUAGE_DATA = {
    popular: ['eng_Latn', 'spa_Latn', 'fra_Latn', 'deu_Latn', 'ita_Latn'],
    families: {
        'Germanic': ['eng_Latn', 'deu_Latn', 'nld_Latn'],
        'Romance': ['spa_Latn', 'fra_Latn', 'ita_Latn', 'por_Latn'],
        'Slavic': ['rus_Cyrl', 'pol_Latn', 'ces_Latn'],
        // ... more families
    },
    scripts: {
        'Latin': ['eng_Latn', 'spa_Latn', 'fra_Latn'],
        'Cyrillic': ['rus_Cyrl', 'bul_Cyrl'],
        'Arabic': ['ara_Arab', 'fas_Arab'],
        // ... more scripts
    }
};
```

#### Storage Strategy
- **LocalStorage**: User preferences and recent languages
- **SessionStorage**: Current session language selections
- **API Cache**: Language metadata and validation

### 6. Implementation Phases

#### Phase 1: Core Infrastructure
1. Create language data structures
2. Implement basic dropdown component
3. Add API language endpoint
4. Update settings management

#### Phase 2: UserScript Integration
1. Add language selector to translation buttons
2. Implement recent languages tracking
3. Create language preferences UI
4. Add keyboard shortcuts

#### Phase 3: AutoHotkey Enhancement
1. Add hotkey-based language selection
2. Create GUI language picker
3. Implement tooltip feedback
4. Add configuration management

#### Phase 4: Advanced Features
1. Smart language suggestions
2. Conversation context awareness
3. Bulk translation with multiple targets
4. Performance optimizations

### 7. Technical Considerations

#### Performance
- **Lazy Loading**: Load language data on demand
- **Caching**: Cache frequently used language metadata
- **Debouncing**: Prevent excessive API calls during typing

#### Accessibility
- **Keyboard Navigation**: Full keyboard support for dropdowns
- **Screen Readers**: Proper ARIA labels and descriptions
- **High Contrast**: Support for accessibility themes

#### Cross-Platform Compatibility
- **Browser Support**: Test across major browsers
- **Mobile Responsive**: Touch-friendly interface design
- **OS Integration**: Native feel on different platforms

### 8. Migration Strategy

#### Settings Migration
```javascript
// Migrate old static settings to new dynamic structure
function migrateLanguageSettings(oldSettings) {
    return {
        ...oldSettings,
        defaultLanguage: oldSettings.targetLanguage || 'eng_Latn',
        recentLanguages: [oldSettings.targetLanguage].filter(Boolean),
        favoriteLanguages: [],
        version: '2.0'
    };
}
```

#### Backward Compatibility
- Maintain support for existing configuration
- Graceful fallback to default language
- Clear migration path for users

### 9. Testing Strategy

#### Unit Tests
- Language data validation
- Dropdown component behavior
- Settings management logic

#### Integration Tests
- API language endpoint
- Cross-component communication
- Settings persistence

#### User Experience Tests
- Language selection workflows
- Performance under load
- Accessibility compliance

### 10. Success Metrics

#### User Experience
- Reduction in translation setup time
- Increase in translation frequency
- User satisfaction with language selection

#### Technical Performance
- API response times for language data
- UI responsiveness during selection
- Memory usage optimization

## Conclusion

This architecture provides a comprehensive foundation for implementing ad hoc destination language selection across all components of the NLLB Translation System. The phased approach ensures incremental delivery of value while maintaining system stability and user experience quality.

The design prioritizes user experience through intuitive interfaces, performance through efficient data management, and maintainability through modular architecture patterns.