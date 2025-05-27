# Ad Hoc Language Selection - Ranked Implementation Tasks

## Task Priority Rankings

### 🔴 Critical Priority (Must Have - Week 1)

#### TASK-001: API Language Metadata Endpoint
- **Complexity**: Low | **Impact**: High | **Effort**: 2-3 hours
- **Dependencies**: None
- **Description**: Create `/languages` endpoint returning all supported NLLB languages
- **Acceptance Criteria**:
  - Returns JSON with language codes, names, native names, families
  - Includes popularity/common language flags
  - Response time < 100ms
  - Proper error handling
- **Files**: `server/main.py`, `server/app/utils/language_detection.py`

#### TASK-002: Language Data Structure Standardization
- **Complexity**: Low | **Impact**: High | **Effort**: 1-2 hours
- **Dependencies**: TASK-001
- **Description**: Define consistent language data format across all components
- **Acceptance Criteria**:
  - Unified language code format (NLLB standard)
  - Language grouping schema (family, script, popularity)
  - Validation functions for language codes
- **Files**: `userscript/language_data.js`, `ahk/language_config.ahk`

#### TASK-003: UserScript Settings Migration
- **Complexity**: Medium | **Impact**: High | **Effort**: 3-4 hours
- **Dependencies**: TASK-002
- **Description**: Migrate from static to dynamic language settings
- **Acceptance Criteria**:
  - Backward compatibility with existing settings
  - New dynamic preferences structure
  - Graceful fallback for missing languages
  - Settings version management
- **Files**: `userscript/telegram-nllb-translator.user.js` (settings section)

### 🟡 High Priority (Core Features - Week 2)

#### TASK-004: UserScript Language Dropdown Component
- **Complexity**: Medium | **Impact**: High | **Effort**: 4-6 hours
- **Dependencies**: TASK-003
- **Description**: Create reusable language selector dropdown
- **Acceptance Criteria**:
  - Search/filter functionality
  - Recent languages prioritized
  - Keyboard navigation (arrow keys, enter, escape)
  - Mobile-responsive design
  - Proper ARIA labels
- **Files**: `userscript/telegram-nllb-translator.user.js` (new LanguageSelector class)

#### TASK-005: Translation Button Language Integration
- **Complexity**: Medium | **Impact**: High | **Effort**: 3-4 hours
- **Dependencies**: TASK-004
- **Description**: Add language selection to existing translate buttons
- **Acceptance Criteria**:
  - Dropdown appears adjacent to translate button
  - Selected language persists for session
  - Visual feedback for language changes
  - Maintains existing button functionality
- **Files**: `userscript/telegram-nllb-translator.user.js` (button creation functions)

#### TASK-006: AutoHotkey v2.0 Hotkey System
- **Complexity**: Medium | **Impact**: Medium | **Effort**: 4-5 hours
- **Dependencies**: TASK-002
- **Description**: Implement keyboard shortcuts for language switching
- **Acceptance Criteria**:
  - Configurable hotkeys for top 10 languages
  - Visual feedback via ToolTip (AHK v2.0 syntax)
  - Settings persistence in INI file
  - No conflicts with existing hotkeys
- **Files**: `ahk/telegram-nllb-translator.ahk` (complete rewrite for v2.0)

### 🟢 Medium Priority (Enhanced UX - Week 3)

#### TASK-007: Recent Languages Tracking
- **Complexity**: Low | **Impact**: Medium | **Effort**: 2-3 hours
- **Dependencies**: TASK-004
- **Description**: Smart tracking and suggestion of recently used languages
- **Acceptance Criteria**:
  - Last 5 used languages stored locally
  - Recent languages appear first in dropdown
  - Cross-session persistence
  - Duplicate prevention
- **Files**: `userscript/telegram-nllb-translator.user.js` (settings management)

#### TASK-008: AutoHotkey v2.0 GUI Language Picker
- **Complexity**: High | **Impact**: Medium | **Effort**: 6-8 hours
- **Dependencies**: TASK-006
- **Description**: Visual language selection interface for AHK
- **Acceptance Criteria**:
  - Searchable language list with Edit control
  - Language family grouping in TreeView
  - Keyboard navigation throughout
  - Remember window position and size
  - Modern Windows 11-style GUI
- **Files**: `ahk/telegram-nllb-translator.ahk` (new GUI functions)

#### TASK-009: Pre-Send Translation Enhancement
- **Complexity**: Medium | **Impact**: Medium | **Effort**: 4-5 hours
- **Dependencies**: TASK-005
- **Description**: Add language selection to input toolbar
- **Acceptance Criteria**:
  - Language dropdown in pre-send toolbar
  - Quick language switching without losing text
  - Multiple target language preview option
  - Maintains existing pre-send functionality
- **Files**: `userscript/telegram-nllb-translator.user.js` (input detection functions)

### 🔵 Lower Priority (Advanced Features - Week 4)

#### TASK-010: Smart Language Suggestions
- **Complexity**: High | **Impact**: Low | **Effort**: 8-10 hours
- **Dependencies**: All core tasks
- **Description**: Context-aware language recommendations
- **Acceptance Criteria**:
  - Conversation context analysis
  - Language detection confidence scores
  - Machine learning-based suggestions
  - User preference learning
- **Files**: New `userscript/language_intelligence.js`

#### TASK-011: Bulk Multi-Language Translation
- **Complexity**: High | **Impact**: Low | **Effort**: 6-8 hours
- **Dependencies**: TASK-005
- **Description**: Translate to multiple languages simultaneously
- **Acceptance Criteria**:
  - Multi-select language interface
  - Side-by-side translation results
  - Export/copy functionality
  - Performance optimization for multiple requests
- **Files**: `userscript/telegram-nllb-translator.user.js` (new bulk translation class)

#### TASK-012: Performance Optimizations
- **Complexity**: Medium | **Impact**: Low | **Effort**: 4-6 hours
- **Dependencies**: All components implemented
- **Description**: Optimize loading, caching, and rendering
- **Acceptance Criteria**:
  - Language data lazy loading
  - API response caching (5-minute TTL)
  - UI rendering optimizations
  - Memory usage monitoring
- **Files**: Multiple files (optimization pass)

### 🟪 Quality Assurance (Week 5)

#### TASK-013: Accessibility Improvements
- **Complexity**: Medium | **Impact**: Low | **Effort**: 4-5 hours
- **Dependencies**: All UI components
- **Description**: WCAG 2.1 AA compliance
- **Acceptance Criteria**:
  - Screen reader compatibility
  - Keyboard-only navigation
  - High contrast mode support
  - Focus management
- **Files**: `userscript/telegram-nllb-translator.user.js` (accessibility pass)

#### TASK-014: Cross-Browser Testing
- **Complexity**: Low | **Impact**: Low | **Effort**: 3-4 hours
- **Dependencies**: All UserScript components
- **Description**: Multi-browser compatibility validation
- **Acceptance Criteria**:
  - Chrome, Firefox, Edge, Safari support
  - Mobile browser testing
  - Documented compatibility matrix
  - Bug fixes for browser-specific issues
- **Files**: Testing documentation

#### TASK-015: Error Handling & Recovery
- **Complexity**: Medium | **Impact**: Medium | **Effort**: 3-4 hours
- **Dependencies**: All components
- **Description**: Robust error handling and user feedback
- **Acceptance Criteria**:
  - Graceful API failure handling
  - User-friendly error messages
  - Automatic retry mechanisms with exponential backoff
  - Fallback to default language on errors
- **Files**: All component files (error handling pass)

## Implementation Schedule

### Week 1: Foundation
**Target**: Basic language switching capability
- TASK-001: API Language Metadata Endpoint
- TASK-002: Language Data Structure Standardization  
- TASK-003: UserScript Settings Migration
**Total Effort**: 6-9 hours

### Week 2: Core Features
**Target**: Full language selection UI operational
- TASK-004: UserScript Language Dropdown Component
- TASK-005: Translation Button Language Integration
- TASK-006: AutoHotkey v2.0 Hotkey System
**Total Effort**: 11-15 hours

### Week 3: Enhanced UX
**Target**: Advanced user experience features
- TASK-007: Recent Languages Tracking
- TASK-008: AutoHotkey v2.0 GUI Language Picker
- TASK-009: Pre-Send Translation Enhancement
**Total Effort**: 12-16 hours

### Week 4: Advanced Features
**Target**: AI-powered features and optimization
- TASK-010: Smart Language Suggestions
- TASK-011: Bulk Multi-Language Translation
- TASK-012: Performance Optimizations
**Total Effort**: 18-24 hours

### Week 5: Quality Assurance
**Target**: Production-ready release
- TASK-013: Accessibility Improvements
- TASK-014: Cross-Browser Testing
- TASK-015: Error Handling & Recovery
**Total Effort**: 10-13 hours

## Risk Mitigation

### High-Risk Tasks
- **TASK-006**: AutoHotkey v2.0 syntax changes may require extensive research
- **TASK-008**: GUI complexity in AHK v2.0 significantly different from v1.1
- **TASK-010**: AI features may be overengineered for initial release

### Mitigation Strategies
1. **Incremental Development**: Complete and test each task before moving to next
2. **Parallel Development**: Work on UserScript and AHK components simultaneously
3. **Early Testing**: Test with real Telegram conversations throughout development
4. **Feature Flags**: Implement toggle switches for new features during rollout
5. **Rollback Plan**: Maintain backward compatibility for quick rollbacks

## Success Metrics

### User Experience
- **Language Selection Time**: < 3 seconds from click to selection
- **Setup Reduction**: 50% faster than current settings-based approach
- **Feature Adoption**: 80% of users try ad hoc selection within first week

### Technical Performance
- **API Response**: < 100ms for language metadata
- **UI Responsiveness**: < 200ms for dropdown rendering
- **Memory Overhead**: < 5MB additional browser memory

### Quality Assurance
- **Error Rate**: < 1% for language selection operations
- **Accessibility Score**: WCAG 2.1 AA compliance
- **Browser Support**: 99% feature parity across major browsers

## Testing Strategy

### Per-Task Testing
- **Unit Tests**: Individual function testing for each task
- **Integration Tests**: Cross-component communication testing
- **User Acceptance**: Real-world usage scenario testing

### Continuous Testing
- **Regression Tests**: Ensure existing functionality not broken
- **Performance Tests**: Monitor metrics throughout development
- **Accessibility Tests**: Automated and manual accessibility validation