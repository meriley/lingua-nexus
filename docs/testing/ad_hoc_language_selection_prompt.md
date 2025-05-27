# Ad Hoc Language Selection Implementation Prompt

## Project Context

You are implementing ad hoc destination language selection for the NLLB Translation System. This enhancement allows users to dynamically select target languages instead of using fixed settings.

## Current System Overview

### Existing Components
- **FastAPI Server**: Translation API with PyTorch/HuggingFace NLLB model
- **UserScript**: Tampermonkey script for Telegram Web translation
- **AutoHotkey Script**: Windows automation for system-wide translation
- **Docker Deployment**: Containerized server deployment

### Current Limitations
- Fixed destination language in settings
- No contextual language selection
- Poor UX for multilingual conversations
- Static configuration requiring script restarts

## Implementation Objectives

### Primary Goals
1. **Dynamic Language Selection**: Users can select both source and target languages on-demand
2. **Bidirectional Translation**: Support for translating in both directions with language swap functionality
3. **Improved User Experience**: Intuitive language switching interface with quick language pair toggles
4. **Cross-Platform Consistency**: Unified language selection across UserScript and AutoHotkey
5. **Performance Optimization**: Minimal impact on translation speed
6. **Backward Compatibility**: Existing settings and workflows preserved

### Success Criteria
- Language selection time < 3 seconds
- 50% reduction in translation setup time
- 80% user adoption within first week
- < 1% error rate for language operations
- WCAG 2.1 AA accessibility compliance

## Technical Requirements

### Architecture Documents
- **Primary**: `docs/architecture/ad_hoc_language_selection.md`
- **Task List**: `docs/testing/ad_hoc_language_selection_tasks.md`
- **System Architecture**: `docs/architecture/system_architecture.md`

### Technology Stack
- **Server**: Python 3.10+, FastAPI, PyTorch, HuggingFace Transformers
- **UserScript**: Vanilla JavaScript, Tampermonkey API, DOM manipulation
- **AutoHotkey**: AutoHotkey v2.0 (important: NOT v1.1)
- **API**: RESTful with JSON, authentication via X-API-Key

### Key AutoHotkey v2.0 Syntax Updates
```autohotkey
; v2.0 Changes from v1.1:
ToolTip("message")          ; was ToolTip, message
SetTimer(Function, Period)  ; was SetTimer, Function, Period
MsgBox("text", "title")     ; was MsgBox, text, title, options
; All function calls now use parentheses
```

## Implementation Strategy

### Phase-Based Development
1. **Week 1 - Foundation**: API endpoint, data structures, settings migration
2. **Week 2 - Core Features**: UserScript dropdown, translation integration, AHK hotkeys
3. **Week 3 - Enhanced UX**: Recent languages, GUI picker, pre-send enhancement
4. **Week 4 - Advanced**: Smart suggestions, bulk translation, optimizations
5. **Week 5 - QA**: Accessibility, cross-browser testing, error handling

### Critical Path Tasks (Must Complete First)
1. **TASK-001**: API Language Metadata Endpoint
2. **TASK-002**: Language Data Structure Standardization with Language Pairs
3. **TASK-003**: UserScript Settings Migration with Bidirectional Support
4. **TASK-004**: UserScript Language Dropdown Component with Pair Selection
5. **TASK-005**: Language Swap Functionality Implementation

## Component-Specific Guidelines

### FastAPI Server Enhancements

#### New Endpoint Requirements
```python
@app.get("/languages")
async def get_supported_languages():
    """Return comprehensive language metadata"""
    return {
        "languages": [
            {
                "code": "eng_Latn",
                "name": "English", 
                "native_name": "English",
                "family": "Germanic",
                "script": "Latin",
                "popular": True,
                "region": "Global"
            }
            # ... more languages
        ],
        "families": ["Germanic", "Romance", "Slavic", ...],
        "popular": ["eng_Latn", "spa_Latn", "fra_Latn", ...],
        "total_count": 200
    }
```

#### Performance Requirements
- Response time < 100ms
- Proper caching headers
- Gzip compression enabled
- Error handling with appropriate HTTP status codes

### UserScript Development

#### Language Dropdown Component Design
```javascript
class LanguageSelector {
    constructor(options = {}) {
        this.languages = [];
        this.recentLanguages = this.loadRecentLanguages();
        this.recentLanguagePairs = this.loadRecentLanguagePairs();
        this.onLanguageChange = options.onLanguageChange;
        this.position = options.position || 'inline';
        this.mode = options.mode || 'target'; // 'source', 'target', or 'pair'
        this.currentSourceLang = options.defaultSource || 'auto';
        this.currentTargetLang = options.defaultTarget || 'eng_Latn';
    }
    
    async loadLanguages() {
        // Fetch from API with caching
        // Handle network errors gracefully
    }
    
    createDropdown() {
        // Create accessible dropdown with search
        // Implement keyboard navigation
        // Add proper ARIA labels
        // Include language swap button for bidirectional translation
    }
    
    createLanguagePairSelector() {
        // Create dual dropdown for source/target selection
        // Include swap button for bidirectional translation
        // Show recent language pairs
    }
    
    swapLanguages() {
        // Swap source and target languages
        // Update UI and notify parent component
        // Save new language pair to recent pairs
    }
    
    filterLanguages(searchTerm) {
        // Implement search/filter functionality
        // Prioritize recent and popular languages
    }
}
```

#### Integration Requirements
- Must not break existing translation buttons
- Maintain DOM mutation observer functionality
- Preserve user settings and preferences
- Handle Telegram DOM changes gracefully

### AutoHotkey v2.0 Development

#### GUI Implementation Requirements
```autohotkey
CreateLanguageGUI() {
    ; Use Gui() constructor (v2.0 syntax)
    myGui := Gui("+Resize", "Language Selection")
    
    ; Add controls with proper v2.0 syntax
    myGui.Add("Edit", "vSearchBox w300")
    myGui.Add("TreeView", "vLanguageTree w300 h400")
    myGui.Add("Button", "w100 h30", "Select").OnEvent("Click", SelectLanguage)
    
    ; Show GUI
    myGui.Show()
}
```

#### Hotkey Configuration
- Use configurable hotkeys (Ctrl+Alt+1-9 for target languages, Ctrl+Shift+1-9 for language pairs)
- Implement language swap hotkey (Ctrl+Alt+S)
- Implement ToolTip feedback with v2.0 syntax showing current language pair
- Save preferences in INI file including recent language pairs
- Handle conflicts with existing system hotkeys

## User Experience Design

### Language Selection Patterns

#### Primary: Inline Language Pair Selector
- Compact dual dropdown for source/target languages adjacent to translate button
- Language swap button (⇄) for bidirectional translation
- Recent language pairs at top (max 5)
- Search functionality for full language list
- Visual indicators for popular languages

#### Secondary: Inline Single Language Selector
- Single dropdown for target language only (source auto-detected)
- Recent languages at top (max 5)
- Quick access to bidirectional mode

#### Tertiary: Modal Selector  
- Full-screen language picker for complex selection
- Organized by language families and regions
- Favorites section for user-pinned languages
- Language pair presets and history
- Keyboard shortcuts for common languages

#### Quaternary: Quick Actions
- Hotkey-based selection (Ctrl+Alt+Number for targets, Ctrl+Shift+Number for pairs)
- Context menu options with language swap
- Smart suggestions based on conversation context

### Visual Design Requirements
```css
.language-selector {
    position: relative;
    display: inline-block;
    font-family: inherit;
}

.language-dropdown {
    min-width: 220px;
    max-height: 320px;
    overflow-y: auto;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    background: var(--bg-color);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 9999;
}

.language-item {
    padding: 8px 12px;
    display: flex;
    justify-content: space-between;
    cursor: pointer;
    transition: background-color 0.2s;
}

.language-item:hover {
    background: var(--hover-bg);
}

.language-item.recent::before {
    content: "🕒";
    margin-right: 6px;
}

.language-item.popular::after {
    content: "⭐";
    opacity: 0.7;
}
```

## Data Management Strategy

### Language Data Structure
```javascript
const LANGUAGE_METADATA = {
    // Core language information
    languages: Map([
        ['eng_Latn', {
            code: 'eng_Latn',
            name: 'English',
            nativeName: 'English', 
            family: 'Germanic',
            script: 'Latin',
            popular: true,
            region: 'Global',
            rtl: false
        }]
        // ... more languages
    ]),
    
    // Organizational structures
    families: {
        'Germanic': ['eng_Latn', 'deu_Latn', 'nld_Latn'],
        'Romance': ['spa_Latn', 'fra_Latn', 'ita_Latn'],
        'Slavic': ['rus_Cyrl', 'pol_Latn', 'ces_Latn']
    },
    
    popular: ['eng_Latn', 'spa_Latn', 'fra_Latn', 'deu_Latn'],
    
    // User preferences
    recent: [], // Last 5 used languages
    recentPairs: [], // Last 5 used language pairs
    favorites: [], // User-pinned languages
    favoritePairs: [], // User-pinned language pairs
    defaults: {
        source: 'auto', // Auto-detect
        target: 'eng_Latn', // Default target
        mode: 'single' // 'single' or 'pair' selector mode
    }
};
```

### Storage Strategy
- **LocalStorage**: User preferences, recent languages, recent language pairs, favorites
- **SessionStorage**: Current session selections and temporary data
- **API Cache**: Language metadata with 1-hour TTL
- **INI Files**: AutoHotkey configuration persistence including language pairs

## Testing Requirements

### Unit Testing
```javascript
// Example test structure
describe('LanguageSelector', () => {
    test('should load language data from API', async () => {
        // Mock API response
        // Test data loading and caching
    });
    
    test('should filter languages by search term', () => {
        // Test search functionality
        // Verify prioritization logic
    });
    
    test('should track recent language usage', () => {
        // Test recent language storage
        // Verify duplicate prevention
    });
});
```

### Integration Testing
- API endpoint response validation
- Cross-component communication testing
- Settings migration verification
- Error handling and recovery testing

### User Acceptance Testing
- Real Telegram conversation scenarios
- Multiple language switching workflows
- Performance under realistic usage
- Accessibility with screen readers

## Error Handling Requirements

### API Communication
```javascript
async function fetchLanguages() {
    try {
        const response = await fetch(`${CONFIG.apiUrl}/languages`, {
            headers: { 'X-API-Key': CONFIG.apiKey },
            timeout: 5000
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Language loading failed:', error);
        // Fallback to cached data or default languages
        return getDefaultLanguages();
    }
}
```

### User Feedback
- Clear error messages for network failures
- Loading states during API calls
- Graceful degradation when features unavailable
- Retry mechanisms with exponential backoff

## Performance Optimization

### Caching Strategy
- **Language Metadata**: Cache for 1 hour, refresh in background
- **User Preferences**: Immediate localStorage updates
- **API Responses**: Cache successful translations for session
- **DOM Elements**: Reuse dropdown instances when possible

### Memory Management
- Lazy load language data on first use
- Debounce search input to prevent excessive filtering
- Clean up event listeners on component destruction
- Monitor memory usage in development

## Accessibility Requirements

### WCAG 2.1 AA Compliance
- **Keyboard Navigation**: Full functionality via keyboard only
- **Screen Readers**: Proper ARIA labels and descriptions
- **Focus Management**: Clear focus indicators and logical tab order
- **Color Contrast**: Minimum 4.5:1 contrast ratio
- **Text Scaling**: Readable at 200% zoom level

### Implementation
```javascript
// Example accessible dropdown
createDropdown() {
    const dropdown = document.createElement('div');
    dropdown.setAttribute('role', 'listbox');
    dropdown.setAttribute('aria-label', 'Select target language');
    dropdown.setAttribute('aria-expanded', 'false');
    
    // Add keyboard event handlers
    dropdown.addEventListener('keydown', this.handleKeyboardNavigation.bind(this));
    
    return dropdown;
}

handleKeyboardNavigation(event) {
    switch (event.key) {
        case 'ArrowDown':
            this.selectNext();
            event.preventDefault();
            break;
        case 'ArrowUp':
            this.selectPrevious(); 
            event.preventDefault();
            break;
        case 'Enter':
            this.confirmSelection();
            event.preventDefault();
            break;
        case 'Escape':
            this.closeDropdown();
            event.preventDefault();
            break;
    }
}
```

## Security Considerations

### API Security
- Validate all language codes against known NLLB languages
- Sanitize user input in search functionality
- Rate limiting for language metadata requests
- Secure API key storage and transmission

### Client Security
- XSS prevention in DOM manipulation
- CSP compliance for UserScript
- Secure settings storage (no sensitive data in localStorage)
- Input validation for all user-provided data

## Migration Strategy

### Backward Compatibility
```javascript
// Settings migration example
function migrateSettings(currentSettings) {
    const version = currentSettings.version || '1.0';
    
    if (version === '1.0') {
        // Migrate from static to dynamic settings
        return {
            ...currentSettings,
            version: '2.0',
            languagePreferences: {
                default: currentSettings.targetLanguage || 'eng_Latn',
                recent: [currentSettings.targetLanguage].filter(Boolean),
                favorites: []
            }
        };
    }
    
    return currentSettings;
}
```

### Deployment Strategy
1. **Feature Flags**: Enable new features gradually
2. **A/B Testing**: Test with subset of users first  
3. **Rollback Plan**: Quick revert to previous version if issues
4. **User Communication**: Clear documentation of new features

## Final Implementation Notes

### AutoHotkey v2.0 Critical Differences
- All function calls require parentheses: `MsgBox("text")` not `MsgBox, text`
- `ToolTip("message")` instead of `ToolTip, message`
- `SetTimer(Function, Period)` instead of `SetTimer, Function, Period`
- Variable declarations and assignments use different syntax
- GUI creation uses constructor syntax: `Gui(Options, Title)`

### Development Best Practices
1. **Test Early and Often**: Test each component individually before integration
2. **Progressive Enhancement**: Ensure basic functionality works before adding advanced features
3. **User-Centered Design**: Prioritize user experience over technical complexity
4. **Documentation**: Document all new APIs and configuration options
5. **Performance Monitoring**: Track metrics throughout development

### Delivery Expectations
- **Working Code**: All implementations must be functional and tested
- **Clear Documentation**: Code comments and user documentation
- **Error Handling**: Robust error handling with user feedback
- **Performance**: Meet specified performance requirements
- **Accessibility**: Full keyboard navigation and screen reader support

This prompt provides the comprehensive context needed to implement ad hoc language selection across all components of the NLLB Translation System. Follow the task prioritization and technical requirements for successful implementation.