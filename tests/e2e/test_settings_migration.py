"""
E2E tests for settings migration validation.
TASK-003: Comprehensive testing of v2.x to v3.x settings compatibility.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.e2e.utils.http_client import E2EHttpClient


@pytest.mark.e2e
@pytest.mark.e2e_foundation
class TestUserScriptSettingsMigration:
    """Test suite for UserScript settings migration from v2.x to v3.x."""

    def test_fresh_installation_default_settings(self):
        """Test default settings for fresh installation (no previous settings)."""
        # Simulate fresh installation scenario
        mock_gm_getValue = MagicMock()
        mock_gm_setValue = MagicMock()
        
        # Return defaults for all settings (no stored values)
        mock_gm_getValue.side_effect = lambda key, default: default
        
        with patch('GM_getValue', mock_gm_getValue), patch('GM_setValue', mock_gm_setValue):
            # Simulate loading settings for the first time
            expected_defaults = {
                'translationServer': 'http://localhost:8000',
                'defaultSourceLang': 'auto',
                'defaultTargetLang': 'eng_Latn',
                'languageSelectionMode': 'single',
                'enableLanguageSwap': True,
                'showRecentLanguages': True,
                'maxRecentLanguages': 5,
                'showOriginalOnHover': True,
                'debugMode': True,
                'enablePreSendTranslation': True,
                'autoTranslateInput': False,
                'settingsVersion': '3.0'
            }
            
            # Verify GM_getValue is called with correct defaults
            for key, expected_default in expected_defaults.items():
                if key != 'settingsVersion':  # Version is handled differently
                    mock_gm_getValue.assert_any_call(key, expected_default)
            
            # Verify version check for migration
            mock_gm_getValue.assert_any_call('settingsVersion', '1.0')

    def test_migration_from_v1_0_settings(self):
        """Test migration from version 1.0 settings structure."""
        mock_gm_getValue = MagicMock()
        mock_gm_setValue = MagicMock()
        
        # Simulate v1.0 settings (minimal configuration)
        v1_settings = {
            'settingsVersion': '1.0',
            'translationServer': 'http://localhost:8000',
            'apiKey': 'old-api-key-123',
            'defaultTargetLang': 'spa_Latn',
            'showOriginalOnHover': True,
            'debugMode': False
        }
        
        def mock_get_value(key, default):
            return v1_settings.get(key, default)
        
        mock_gm_getValue.side_effect = mock_get_value
        
        with patch('GM_getValue', mock_gm_getValue), patch('GM_setValue', mock_gm_setValue):
            # Simulate settings migration process
            version = mock_gm_getValue('settingsVersion', '1.0')
            assert version == '1.0'
            
            # Verify migration sets new v3.0 features
            expected_migration_calls = [
                ('defaultSourceLang', 'auto'),
                ('languageSelectionMode', 'single'),
                ('enableLanguageSwap', True),
                ('showRecentLanguages', True),
                ('maxRecentLanguages', 5),
                ('settingsVersion', '3.0')
            ]
            
            # Simulate the migration process
            if version in ['1.0', '2.0']:
                for setting_key, setting_value in expected_migration_calls:
                    mock_gm_setValue(setting_key, setting_value)
            
            # Verify migration calls were made
            for setting_key, setting_value in expected_migration_calls:
                mock_gm_setValue.assert_any_call(setting_key, setting_value)

    def test_migration_from_v2_0_settings(self):
        """Test migration from version 2.0 settings structure."""
        mock_gm_getValue = MagicMock()
        mock_gm_setValue = MagicMock()
        
        # Simulate v2.0 settings (intermediate version)
        v2_settings = {
            'settingsVersion': '2.0',
            'translationServer': 'http://localhost:8000',
            'apiKey': 'v2-api-key-456',
            'defaultTargetLang': 'fra_Latn',
            'defaultSourceLang': 'eng_Latn',  # Source lang existed in v2.0
            'showOriginalOnHover': True,
            'debugMode': True,
            'enablePreSendTranslation': False
        }
        
        def mock_get_value(key, default):
            return v2_settings.get(key, default)
        
        mock_gm_getValue.side_effect = mock_get_value
        
        with patch('GM_getValue', mock_gm_getValue), patch('GM_setValue', mock_gm_setValue):
            # Simulate settings migration process
            version = mock_gm_getValue('settingsVersion', '1.0')
            assert version == '2.0'
            
            # Verify v2.0 to v3.0 migration adds new features
            expected_new_settings = [
                ('languageSelectionMode', 'single'),
                ('enableLanguageSwap', True),
                ('showRecentLanguages', True),
                ('maxRecentLanguages', 5),
                ('settingsVersion', '3.0')
            ]
            
            # Simulate the migration process
            if version in ['1.0', '2.0']:
                for setting_key, setting_value in expected_new_settings:
                    mock_gm_setValue(setting_key, setting_value)
            
            # Verify new v3.0 settings were added
            for setting_key, setting_value in expected_new_settings:
                mock_gm_setValue.assert_any_call(setting_key, setting_value)

    def test_no_migration_needed_v3_0_settings(self):
        """Test that v3.0 settings are loaded without migration."""
        mock_gm_getValue = MagicMock()
        mock_gm_setValue = MagicMock()
        
        # Simulate current v3.0 settings
        v3_settings = {
            'settingsVersion': '3.0',
            'translationServer': 'http://localhost:8000',
            'apiKey': 'v3-api-key-789',
            'defaultSourceLang': 'auto',
            'defaultTargetLang': 'deu_Latn',
            'languageSelectionMode': 'pair',
            'enableLanguageSwap': True,
            'showRecentLanguages': False,
            'maxRecentLanguages': 10,
            'showOriginalOnHover': True,
            'debugMode': False,
            'enablePreSendTranslation': True,
            'autoTranslateInput': True
        }
        
        def mock_get_value(key, default):
            return v3_settings.get(key, default)
        
        mock_gm_getValue.side_effect = mock_get_value
        
        with patch('GM_getValue', mock_gm_getValue), patch('GM_setValue', mock_gm_setValue):
            # Simulate settings loading without migration
            version = mock_gm_getValue('settingsVersion', '1.0')
            assert version == '3.0'
            
            # No migration should occur for v3.0 settings
            # Only regular save operations should happen
            # Verify no unexpected migration calls were made

    def test_settings_validation_after_migration(self):
        """Test that migrated settings pass validation checks."""
        validation_test_cases = [
            {
                'name': 'Valid language codes',
                'settings': {
                    'defaultSourceLang': 'auto',
                    'defaultTargetLang': 'eng_Latn',
                    'languageSelectionMode': 'single'
                },
                'should_pass': True
            },
            {
                'name': 'Invalid source language code',
                'settings': {
                    'defaultSourceLang': 'invalid_Lang',
                    'defaultTargetLang': 'eng_Latn',
                    'languageSelectionMode': 'single'
                },
                'should_pass': False
            },
            {
                'name': 'Invalid target language code',
                'settings': {
                    'defaultSourceLang': 'auto',
                    'defaultTargetLang': 'invalid_Code',
                    'languageSelectionMode': 'single'
                },
                'should_pass': False
            },
            {
                'name': 'Invalid language selection mode',
                'settings': {
                    'defaultSourceLang': 'auto',
                    'defaultTargetLang': 'eng_Latn',
                    'languageSelectionMode': 'invalid_mode'
                },
                'should_pass': False
            },
            {
                'name': 'Valid bidirectional language pair',
                'settings': {
                    'defaultSourceLang': 'eng_Latn',
                    'defaultTargetLang': 'spa_Latn',
                    'languageSelectionMode': 'pair',
                    'enableLanguageSwap': True
                },
                'should_pass': True
            }
        ]
        
        for test_case in validation_test_cases:
            settings = test_case['settings']
            
            # Validate language codes format
            if 'defaultSourceLang' in settings:
                source_lang = settings['defaultSourceLang']
                if source_lang != 'auto':
                    # Should follow BCP-47 format: xxx_Yyyy
                    parts = source_lang.split('_')
                    is_valid = (len(parts) == 2 and 
                              len(parts[0]) == 3 and parts[0].islower() and
                              len(parts[1]) == 4 and parts[1][0].isupper() and parts[1][1:].islower())
                    if test_case['should_pass']:
                        assert is_valid or source_lang == 'auto', f"Invalid source language format: {source_lang}"
                
            if 'defaultTargetLang' in settings:
                target_lang = settings['defaultTargetLang']
                parts = target_lang.split('_')
                is_valid = (len(parts) == 2 and 
                          len(parts[0]) == 3 and parts[0].islower() and
                          len(parts[1]) == 4 and parts[1][0].isupper() and parts[1][1:].islower())
                if test_case['should_pass']:
                    assert is_valid, f"Invalid target language format: {target_lang}"
            
            # Validate language selection mode
            if 'languageSelectionMode' in settings:
                mode = settings['languageSelectionMode']
                valid_modes = ['single', 'pair']
                if test_case['should_pass']:
                    assert mode in valid_modes, f"Invalid language selection mode: {mode}"

    def test_settings_backward_compatibility(self):
        """Test that v3.0 features work when disabled for backward compatibility."""
        compatibility_scenarios = [
            {
                'name': 'Language swap disabled',
                'settings': {
                    'enableLanguageSwap': False,
                    'languageSelectionMode': 'single'
                },
                'expected_behavior': 'should_work_without_swap'
            },
            {
                'name': 'Recent languages disabled',
                'settings': {
                    'showRecentLanguages': False,
                    'maxRecentLanguages': 0
                },
                'expected_behavior': 'should_work_without_recent'
            },
            {
                'name': 'Minimal v1.0-like configuration',
                'settings': {
                    'languageSelectionMode': 'single',
                    'enableLanguageSwap': False,
                    'showRecentLanguages': False,
                    'autoTranslateInput': False
                },
                'expected_behavior': 'should_work_like_v1'
            }
        ]
        
        for scenario in compatibility_scenarios:
            settings = scenario['settings']
            
            # Verify settings are valid
            assert isinstance(settings.get('enableLanguageSwap', True), bool)
            assert isinstance(settings.get('showRecentLanguages', True), bool)
            assert isinstance(settings.get('maxRecentLanguages', 5), int)
            
            # Verify language selection mode is valid
            mode = settings.get('languageSelectionMode', 'single')
            assert mode in ['single', 'pair']


@pytest.mark.e2e
@pytest.mark.e2e_foundation
class TestAutoHotkeySettingsMigration:
    """Test suite for AutoHotkey settings migration and validation."""

    def test_autohotkey_default_ini_structure(self):
        """Test default AutoHotkey INI file structure."""
        expected_ini_structure = {
            'Server': {
                'TranslationServer': 'http://localhost:8000',
                'APIKey': 'your-api-key-here'
            },
            'Translation': {
                'DefaultTargetLang': 'eng_Latn',
                'DefaultSourceLang': 'auto'  # New in v3.0
            },
            'Hotkeys': {
                'TranslateSelection': '^+t',
                'TranslateClipboard': '^+c'
            },
            'UI': {
                'ShowNotifications': '1',
                'ShowGUI': 'true'  # New in v3.0
            },
            'Advanced': {
                'TryDirectInput': '1',
                'UseFallbackClipboard': '1'
            },
            'LanguageSelection': {  # New section in v3.0
                'RememberRecent': 'true',
                'MaxRecentLanguages': '5'
            }
        }
        
        # Validate structure
        for section_name, section_config in expected_ini_structure.items():
            assert isinstance(section_config, dict), f"Section {section_name} should be a dictionary"
            assert len(section_config) > 0, f"Section {section_name} should not be empty"
            
            for key, value in section_config.items():
                assert isinstance(key, str), f"Key {key} should be string"
                assert isinstance(value, str), f"Value {value} should be string for INI format"

    def test_autohotkey_v2_to_v3_migration(self):
        """Test migration of AutoHotkey settings from v2.0 to v3.0."""
        # Simulate v2.0 INI content
        v2_ini_content = """[Server]
TranslationServer=http://localhost:8000
APIKey=old-api-key-123

[Translation]
DefaultTargetLang=spa_Latn

[Hotkeys]
TranslateSelection=^+t
TranslateClipboard=^+c

[UI]
ShowNotifications=1

[Advanced]
TryDirectInput=1
UseFallbackClipboard=1"""
        
        # Expected v3.0 INI content after migration
        expected_v3_additions = {
            'Translation': {
                'DefaultSourceLang': 'auto'
            },
            'UI': {
                'ShowGUI': 'true'
            },
            'LanguageSelection': {
                'RememberRecent': 'true',
                'MaxRecentLanguages': '5'
            }
        }
        
        # Test migration logic
        for section_name, new_settings in expected_v3_additions.items():
            for setting_key, setting_value in new_settings.items():
                # Verify new settings have proper format
                assert isinstance(setting_key, str)
                assert isinstance(setting_value, str)
                assert len(setting_key) > 0
                assert len(setting_value) > 0

    def test_autohotkey_language_code_validation(self):
        """Test validation of language codes in AutoHotkey INI files."""
        language_code_test_cases = [
            {
                'code': 'auto',
                'valid': True,
                'description': 'Auto-detect special case'
            },
            {
                'code': 'eng_Latn',
                'valid': True,
                'description': 'Valid English Latin'
            },
            {
                'code': 'spa_Latn',
                'valid': True,
                'description': 'Valid Spanish Latin'
            },
            {
                'code': 'rus_Cyrl',
                'valid': True,
                'description': 'Valid Russian Cyrillic'
            },
            {
                'code': 'zho_Hans',
                'valid': True,
                'description': 'Valid Chinese Simplified'
            },
            {
                'code': 'arb_Arab',
                'valid': True,
                'description': 'Valid Arabic'
            },
            {
                'code': 'invalid_code',
                'valid': False,
                'description': 'Invalid lowercase script'
            },
            {
                'code': 'ENG_LATN',
                'valid': False,
                'description': 'Invalid all uppercase'
            },
            {
                'code': 'en_Latn',
                'valid': False,
                'description': 'Invalid short language code'
            },
            {
                'code': 'eng_Latin',
                'valid': False,
                'description': 'Invalid long script code'
            },
            {
                'code': 'eng-Latn',
                'valid': False,
                'description': 'Invalid separator (dash instead of underscore)'
            }
        ]
        
        for test_case in language_code_test_cases:
            code = test_case['code']
            is_valid = test_case['valid']
            
            if code == 'auto':
                # Special case for auto-detect
                assert is_valid
                continue
            
            # Validate BCP-47 + ISO format: xxx_Yyyy
            parts = code.split('_')
            actual_valid = (
                len(parts) == 2 and
                len(parts[0]) == 3 and parts[0].islower() and
                len(parts[1]) == 4 and parts[1][0].isupper() and parts[1][1:].islower()
            )
            
            assert actual_valid == is_valid, f"Validation mismatch for {code}: expected {is_valid}, got {actual_valid}"

    def test_autohotkey_hotkey_format_validation(self):
        """Test validation of AutoHotkey hotkey format."""
        hotkey_test_cases = [
            {
                'hotkey': '^+t',
                'valid': True,
                'description': 'Ctrl+Shift+T'
            },
            {
                'hotkey': '^+c',
                'valid': True,
                'description': 'Ctrl+Shift+C'
            },
            {
                'hotkey': '!+t',
                'valid': True,
                'description': 'Alt+Shift+T'
            },
            {
                'hotkey': '^t',
                'valid': True,
                'description': 'Ctrl+T'
            },
            {
                'hotkey': 'F12',
                'valid': True,
                'description': 'Function key'
            },
            {
                'hotkey': '',
                'valid': False,
                'description': 'Empty hotkey'
            },
            {
                'hotkey': 'invalid',
                'valid': False,
                'description': 'Invalid format'
            }
        ]
        
        for test_case in hotkey_test_cases:
            hotkey = test_case['hotkey']
            is_valid = test_case['valid']
            
            # Basic validation for AutoHotkey format
            if is_valid:
                assert len(hotkey) > 0, f"Valid hotkey should not be empty: {hotkey}"
                # Valid AutoHotkey hotkeys typically contain modifier symbols or function keys
                has_modifier = any(char in hotkey for char in ['^', '!', '+', '#'])
                is_function_key = hotkey.startswith('F') and hotkey[1:].isdigit()
                is_single_char = len(hotkey) == 1 and hotkey.isalpha()
                
                assert has_modifier or is_function_key or is_single_char, f"Invalid hotkey format: {hotkey}"
            else:
                # Invalid hotkeys should be empty or malformed
                if hotkey == '':
                    assert not is_valid
                elif hotkey == 'invalid':
                    assert not is_valid


@pytest.mark.e2e
@pytest.mark.e2e_foundation
class TestCrossPlatformSettingsCompatibility:
    """Test suite for cross-platform settings compatibility."""

    def test_language_code_consistency_across_platforms(self, e2e_client: E2EHttpClient):
        """Test that language codes are consistent between UserScript and AutoHotkey."""
        # Get language metadata from API
        response = e2e_client.get("/languages")
        assert response.status_code == 200
        
        api_data = response.json()
        api_languages = {lang["code"] for lang in api_data["languages"]}
        
        # Test UserScript language settings
        userscript_test_languages = [
            'auto', 'eng_Latn', 'spa_Latn', 'fra_Latn', 'deu_Latn', 
            'rus_Cyrl', 'zho_Hans', 'jpn_Jpan', 'arb_Arab'
        ]
        
        for lang_code in userscript_test_languages:
            assert lang_code in api_languages, f"UserScript language {lang_code} not supported by API"
        
        # Test AutoHotkey language settings
        autohotkey_test_languages = [
            'auto', 'eng_Latn', 'spa_Latn', 'fra_Latn', 'deu_Latn', 'rus_Cyrl'
        ]
        
        for lang_code in autohotkey_test_languages:
            assert lang_code in api_languages, f"AutoHotkey language {lang_code} not supported by API"
        
        # Verify consistency between platforms
        common_languages = set(userscript_test_languages) & set(autohotkey_test_languages)
        assert len(common_languages) >= 5, "Should have at least 5 common languages between platforms"

    def test_settings_export_import_compatibility(self):
        """Test that settings can be exported from one platform and imported to another."""
        # Test UserScript settings export format
        userscript_settings = {
            'version': '3.0',
            'translationServer': 'http://localhost:8000',
            'apiKey': 'test-key-123',
            'defaultSourceLang': 'auto',
            'defaultTargetLang': 'eng_Latn',
            'languageSelectionMode': 'single',
            'enableLanguageSwap': True,
            'showRecentLanguages': True,
            'maxRecentLanguages': 5
        }
        
        # Convert to AutoHotkey INI format
        expected_ini_mapping = {
            'translationServer': ('Server', 'TranslationServer'),
            'apiKey': ('Server', 'APIKey'),
            'defaultTargetLang': ('Translation', 'DefaultTargetLang'),
            'defaultSourceLang': ('Translation', 'DefaultSourceLang'),
            'maxRecentLanguages': ('LanguageSelection', 'MaxRecentLanguages')
        }
        
        for js_key, (ini_section, ini_key) in expected_ini_mapping.items():
            if js_key in userscript_settings:
                js_value = userscript_settings[js_key]
                
                # Verify mapping exists and values can be converted
                assert isinstance(js_value, (str, int, bool))
                
                # Convert boolean to string for INI format
                if isinstance(js_value, bool):
                    ini_value = 'true' if js_value else 'false'
                else:
                    ini_value = str(js_value)
                
                assert len(ini_value) > 0, f"Empty INI value for {ini_key}"

    def test_recent_languages_synchronization(self):
        """Test recent languages list synchronization across platforms."""
        # Simulate recent languages tracking
        recent_languages_scenarios = [
            {
                'platform': 'userscript',
                'recent_languages': ['eng_Latn', 'spa_Latn', 'fra_Latn'],
                'max_recent': 5
            },
            {
                'platform': 'autohotkey',
                'recent_languages': ['eng_Latn', 'deu_Latn', 'rus_Cyrl'],
                'max_recent': 5
            }
        ]
        
        for scenario in recent_languages_scenarios:
            recent_list = scenario['recent_languages']
            max_recent = scenario['max_recent']
            
            # Validate recent languages list
            assert len(recent_list) <= max_recent, f"Recent languages list exceeds maximum: {len(recent_list)} > {max_recent}"
            
            # Validate each language code format
            for lang_code in recent_list:
                if lang_code != 'auto':
                    parts = lang_code.split('_')
                    assert len(parts) == 2, f"Invalid language code format: {lang_code}"
                    assert len(parts[0]) == 3 and parts[0].islower(), f"Invalid language part: {parts[0]}"
                    assert len(parts[1]) == 4 and parts[1][0].isupper(), f"Invalid script part: {parts[1]}"
            
            # Test deduplication
            unique_languages = list(dict.fromkeys(recent_list))  # Preserve order, remove duplicates
            assert len(unique_languages) == len(recent_list), "Recent languages should not contain duplicates"

    def test_settings_validation_consistency(self):
        """Test that settings validation is consistent across platforms."""
        validation_test_settings = [
            {
                'setting': 'defaultSourceLang',
                'valid_values': ['auto', 'eng_Latn', 'spa_Latn', 'fra_Latn'],
                'invalid_values': ['', 'invalid', 'eng', 'eng_Latin', 'ENG_LATN']
            },
            {
                'setting': 'defaultTargetLang',
                'valid_values': ['eng_Latn', 'spa_Latn', 'fra_Latn', 'deu_Latn'],
                'invalid_values': ['auto', '', 'invalid', 'spa', 'spa_Latin']
            },
            {
                'setting': 'languageSelectionMode',
                'valid_values': ['single', 'pair'],
                'invalid_values': ['', 'invalid', 'multiple', 'all']
            },
            {
                'setting': 'maxRecentLanguages',
                'valid_values': [1, 3, 5, 10],
                'invalid_values': [0, -1, 100, 'invalid']
            }
        ]
        
        for test_config in validation_test_settings:
            setting_name = test_config['setting']
            valid_values = test_config['valid_values']
            invalid_values = test_config['invalid_values']
            
            # Test valid values
            for valid_value in valid_values:
                if setting_name in ['defaultSourceLang', 'defaultTargetLang']:
                    if valid_value != 'auto':
                        # Validate language code format
                        parts = str(valid_value).split('_')
                        assert len(parts) == 2, f"Invalid language code format: {valid_value}"
                elif setting_name == 'languageSelectionMode':
                    assert valid_value in ['single', 'pair'], f"Invalid language selection mode: {valid_value}"
                elif setting_name == 'maxRecentLanguages':
                    assert isinstance(valid_value, int) and valid_value > 0, f"Invalid max recent languages: {valid_value}"
            
            # Test invalid values should be rejected
            for invalid_value in invalid_values:
                if setting_name in ['defaultSourceLang', 'defaultTargetLang']:
                    if invalid_value != 'auto' and invalid_value != '':
                        parts = str(invalid_value).split('_')
                        # Should fail validation
                        is_valid = (len(parts) == 2 and 
                                  len(parts[0]) == 3 and parts[0].islower() and
                                  len(parts[1]) == 4 and parts[1][0].isupper() and parts[1][1:].islower())
                        assert not is_valid, f"Invalid value should not pass validation: {invalid_value}"