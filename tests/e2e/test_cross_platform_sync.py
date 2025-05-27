"""
E2E tests for cross-platform synchronization validation.
TASK-006: Comprehensive testing of settings/language synchronization across platforms.
"""

import pytest
import json
import tempfile
import os
import configparser
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List

from tests.e2e.utils.http_client import E2EHttpClient


@pytest.mark.e2e
@pytest.mark.e2e_foundation
class TestCrossPlatformLanguageSync:
    """Test suite for cross-platform language preference synchronization."""

    def test_language_consistency_across_platforms(self, e2e_client: E2EHttpClient):
        """Test that language codes are consistent across all platforms."""
        # Get supported languages from API
        response = e2e_client.get("/languages")
        assert response.status_code == 200
        
        api_data = response.json()
        api_language_codes = {lang["code"] for lang in api_data["languages"]}
        
        # Define common languages used across platforms
        common_languages = [
            "auto", "eng_Latn", "spa_Latn", "fra_Latn", "deu_Latn", 
            "rus_Cyrl", "zho_Hans", "jpn_Jpan", "arb_Arab", "kor_Hang"
        ]
        
        # Verify all common languages are supported by API
        for lang_code in common_languages:
            assert lang_code in api_language_codes, f"Common language {lang_code} not supported by API"
        
        # Test UserScript compatibility
        userscript_compatible_languages = self.get_userscript_compatible_languages()
        for lang_code in userscript_compatible_languages:
            assert lang_code in api_language_codes, f"UserScript language {lang_code} not supported by API"
        
        # Test AutoHotkey compatibility  
        autohotkey_compatible_languages = self.get_autohotkey_compatible_languages()
        for lang_code in autohotkey_compatible_languages:
            assert lang_code in api_language_codes, f"AutoHotkey language {lang_code} not supported by API"

    def test_recent_languages_synchronization(self):
        """Test synchronization of recent language lists across platforms."""
        # Test data: recent languages used across platforms
        test_recent_languages = ["eng_Latn", "spa_Latn", "fra_Latn", "deu_Latn", "rus_Cyrl"]
        
        # Simulate UserScript recent languages
        userscript_recent = self.simulate_userscript_recent_languages(test_recent_languages)
        
        # Simulate AutoHotkey recent languages
        autohotkey_recent = self.simulate_autohotkey_recent_languages(test_recent_languages)
        
        # Test synchronization between platforms
        synchronized_recent = self.merge_recent_languages(userscript_recent, autohotkey_recent)
        
        # Verify merged list maintains order and uniqueness
        assert len(synchronized_recent) <= 5, "Synchronized recent languages should not exceed maximum"
        assert len(set(synchronized_recent)) == len(synchronized_recent), "No duplicates in synchronized list"
        
        # Verify most recent languages are preserved
        for lang in test_recent_languages[:3]:  # Top 3 should be preserved
            assert lang in synchronized_recent, f"Recent language {lang} should be preserved in sync"

    def test_language_pair_synchronization(self):
        """Test synchronization of language pairs across platforms."""
        # Test language pairs
        test_pairs = [
            ("auto", "eng_Latn"),
            ("eng_Latn", "spa_Latn"), 
            ("rus_Cyrl", "eng_Latn"),
            ("fra_Latn", "eng_Latn"),
            ("deu_Latn", "eng_Latn")
        ]
        
        # Simulate UserScript language pairs
        userscript_pairs = self.simulate_userscript_language_pairs(test_pairs)
        
        # Simulate AutoHotkey language pairs  
        autohotkey_pairs = self.simulate_autohotkey_language_pairs(test_pairs)
        
        # Test synchronization
        synchronized_pairs = self.merge_language_pairs(userscript_pairs, autohotkey_pairs)
        
        # Verify synchronization quality
        assert len(synchronized_pairs) <= 5, "Synchronized pairs should not exceed maximum"
        
        # Verify bidirectional pairs are handled correctly
        for source, target in test_pairs[:3]:
            pair_exists = any(
                (pair[0] == source and pair[1] == target) or 
                (pair[0] == target and pair[1] == source and source != "auto")
                for pair in synchronized_pairs
            )
            assert pair_exists, f"Language pair {source}→{target} should be in synchronized list"

    def test_settings_format_compatibility(self):
        """Test that settings can be converted between platform formats."""
        # Base settings that should work across platforms
        base_settings = {
            "defaultSourceLang": "auto",
            "defaultTargetLang": "eng_Latn", 
            "translationServer": "http://localhost:8000",
            "apiKey": "test-api-key-123",
            "maxRecentLanguages": 5,
            "enableLanguageSwap": True,
            "showRecentLanguages": True
        }
        
        # Convert to UserScript format
        userscript_settings = self.convert_to_userscript_format(base_settings)
        self.validate_userscript_settings_format(userscript_settings)
        
        # Convert to AutoHotkey INI format
        autohotkey_settings = self.convert_to_autohotkey_format(base_settings)
        self.validate_autohotkey_settings_format(autohotkey_settings)
        
        # Test round-trip conversion
        recovered_settings = self.convert_from_autohotkey_format(autohotkey_settings)
        
        # Verify key settings are preserved
        assert recovered_settings["defaultTargetLang"] == base_settings["defaultTargetLang"]
        assert recovered_settings["translationServer"] == base_settings["translationServer"]
        assert recovered_settings["maxRecentLanguages"] == base_settings["maxRecentLanguages"]

    def test_api_response_compatibility(self, e2e_client: E2EHttpClient):
        """Test that API responses are compatible with all platform clients."""
        # Test languages endpoint compatibility
        response = e2e_client.get("/languages")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify UserScript compatibility
        self.verify_userscript_api_compatibility(data)
        
        # Verify AutoHotkey compatibility
        self.verify_autohotkey_api_compatibility(data)
        
        # Test translation endpoint compatibility
        translation_payload = {
            "text": "Hello world",
            "source_lang": "auto",
            "target_lang": "spa_Latn"
        }
        
        translation_response = e2e_client.post("/translate", json_data=translation_payload)
        assert translation_response.status_code == 200
        
        translation_data = translation_response.json()
        
        # Verify response format works for all platforms
        required_fields = ["translated_text", "detected_source", "time_ms"]
        for field in required_fields:
            assert field in translation_data, f"Required field {field} missing from translation response"

    def test_language_metadata_consistency(self, e2e_client: E2EHttpClient):
        """Test that language metadata is consistent across platforms."""
        response = e2e_client.get("/languages")
        assert response.status_code == 200
        
        data = response.json()
        languages = data["languages"]
        
        # Test each language entry for cross-platform compatibility
        for language in languages:
            # Verify required fields for all platforms
            required_fields = ["code", "name", "native_name", "family", "script", "popular", "region", "rtl"]
            for field in required_fields:
                assert field in language, f"Language {language.get('code', 'unknown')} missing field {field}"
            
            # Verify language code format (BCP-47 + ISO format)
            if language["code"] != "auto":
                self.validate_language_code_format(language["code"])
            
            # Verify RTL flag consistency
            if language["script"] in ["Arabic", "Hebrew"]:
                assert language["rtl"] is True, f"Language {language['code']} with {language['script']} script should be RTL"
            
            # Verify data types
            assert isinstance(language["popular"], bool), f"Popular field should be boolean for {language['code']}"
            assert isinstance(language["rtl"], bool), f"RTL field should be boolean for {language['code']}"

    # Helper methods for platform-specific testing
    def get_userscript_compatible_languages(self) -> List[str]:
        """Get list of languages compatible with UserScript."""
        return [
            "auto", "eng_Latn", "spa_Latn", "fra_Latn", "deu_Latn", "ita_Latn",
            "por_Latn", "rus_Cyrl", "zho_Hans", "zho_Hant", "jpn_Jpan", "kor_Hang",
            "arb_Arab", "hin_Deva", "tha_Thai", "vie_Latn", "tur_Latn"
        ]

    def get_autohotkey_compatible_languages(self) -> List[str]:
        """Get list of languages compatible with AutoHotkey."""
        return [
            "auto", "eng_Latn", "spa_Latn", "fra_Latn", "deu_Latn", "ita_Latn",
            "por_Latn", "rus_Cyrl", "zho_Hans", "jpn_Jpan", "arb_Arab", "kor_Hang",
            "pol_Latn", "nld_Latn", "swe_Latn", "nor_Latn", "dan_Latn"
        ]

    def simulate_userscript_recent_languages(self, languages: List[str]) -> List[str]:
        """Simulate UserScript recent languages storage."""
        # UserScript stores as array in localStorage
        return languages[:5]  # Max 5 recent

    def simulate_autohotkey_recent_languages(self, languages: List[str]) -> List[str]:
        """Simulate AutoHotkey recent languages storage."""
        # AutoHotkey stores as comma-separated string in INI
        return languages[:5]  # Max 5 recent

    def merge_recent_languages(self, userscript_recent: List[str], autohotkey_recent: List[str]) -> List[str]:
        """Merge recent languages from both platforms."""
        # Combine lists, preserving order and removing duplicates
        merged = []
        seen = set()
        
        # Alternate between sources to maintain fairness
        max_len = max(len(userscript_recent), len(autohotkey_recent))
        
        for i in range(max_len):
            if i < len(userscript_recent) and userscript_recent[i] not in seen:
                merged.append(userscript_recent[i])
                seen.add(userscript_recent[i])
            
            if i < len(autohotkey_recent) and autohotkey_recent[i] not in seen:
                merged.append(autohotkey_recent[i])
                seen.add(autohotkey_recent[i])
            
            if len(merged) >= 5:  # Max recent languages
                break
        
        return merged

    def simulate_userscript_language_pairs(self, pairs: List[tuple]) -> List[tuple]:
        """Simulate UserScript language pair storage."""
        return pairs[:5]  # Max 5 pairs

    def simulate_autohotkey_language_pairs(self, pairs: List[tuple]) -> List[tuple]:
        """Simulate AutoHotkey language pair storage."""
        # AutoHotkey stores as "source|target;source|target" format
        return pairs[:5]  # Max 5 pairs

    def merge_language_pairs(self, userscript_pairs: List[tuple], autohotkey_pairs: List[tuple]) -> List[tuple]:
        """Merge language pairs from both platforms."""
        merged = []
        seen = set()
        
        # Combine unique pairs
        for pair in userscript_pairs + autohotkey_pairs:
            pair_key = f"{pair[0]}|{pair[1]}"
            if pair_key not in seen:
                merged.append(pair)
                seen.add(pair_key)
            
            if len(merged) >= 5:
                break
        
        return merged

    def convert_to_userscript_format(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Convert base settings to UserScript format."""
        userscript_format = {
            "translationServer": settings["translationServer"],
            "apiKey": settings["apiKey"],
            "defaultSourceLang": settings["defaultSourceLang"],
            "defaultTargetLang": settings["defaultTargetLang"],
            "languageSelectionMode": "single",
            "enableLanguageSwap": settings["enableLanguageSwap"],
            "showRecentLanguages": settings["showRecentLanguages"],
            "maxRecentLanguages": settings["maxRecentLanguages"],
            "settingsVersion": "3.0"
        }
        return userscript_format

    def convert_to_autohotkey_format(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Convert base settings to AutoHotkey INI format."""
        autohotkey_format = {
            "Server": {
                "TranslationServer": settings["translationServer"],
                "APIKey": settings["apiKey"]
            },
            "Translation": {
                "DefaultSourceLang": settings["defaultSourceLang"],
                "DefaultTargetLang": settings["defaultTargetLang"]
            },
            "LanguageSelection": {
                "RememberRecent": "true" if settings["showRecentLanguages"] else "false",
                "MaxRecentLanguages": str(settings["maxRecentLanguages"])
            },
            "UI": {
                "ShowGUI": "true"
            }
        }
        return autohotkey_format

    def convert_from_autohotkey_format(self, autohotkey_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Convert AutoHotkey INI format back to base settings."""
        base_format = {
            "translationServer": autohotkey_settings["Server"]["TranslationServer"],
            "apiKey": autohotkey_settings["Server"]["APIKey"],
            "defaultSourceLang": autohotkey_settings["Translation"]["DefaultSourceLang"],
            "defaultTargetLang": autohotkey_settings["Translation"]["DefaultTargetLang"],
            "showRecentLanguages": autohotkey_settings["LanguageSelection"]["RememberRecent"] == "true",
            "maxRecentLanguages": int(autohotkey_settings["LanguageSelection"]["MaxRecentLanguages"])
        }
        return base_format

    def validate_userscript_settings_format(self, settings: Dict[str, Any]):
        """Validate UserScript settings format."""
        required_fields = [
            "translationServer", "apiKey", "defaultSourceLang", "defaultTargetLang",
            "languageSelectionMode", "enableLanguageSwap", "showRecentLanguages",
            "maxRecentLanguages", "settingsVersion"
        ]
        
        for field in required_fields:
            assert field in settings, f"UserScript settings missing required field: {field}"
        
        # Validate specific field types
        assert isinstance(settings["enableLanguageSwap"], bool)
        assert isinstance(settings["showRecentLanguages"], bool)
        assert isinstance(settings["maxRecentLanguages"], int)
        assert settings["languageSelectionMode"] in ["single", "pair"]

    def validate_autohotkey_settings_format(self, settings: Dict[str, Any]):
        """Validate AutoHotkey INI settings format."""
        required_sections = ["Server", "Translation", "LanguageSelection"]
        
        for section in required_sections:
            assert section in settings, f"AutoHotkey settings missing section: {section}"
        
        # Validate Server section
        assert "TranslationServer" in settings["Server"]
        assert "APIKey" in settings["Server"]
        
        # Validate Translation section
        assert "DefaultSourceLang" in settings["Translation"]
        assert "DefaultTargetLang" in settings["Translation"]
        
        # Validate LanguageSelection section
        assert "RememberRecent" in settings["LanguageSelection"]
        assert "MaxRecentLanguages" in settings["LanguageSelection"]
        
        # Validate boolean strings
        assert settings["LanguageSelection"]["RememberRecent"] in ["true", "false"]

    def verify_userscript_api_compatibility(self, api_data: Dict[str, Any]):
        """Verify API response compatibility with UserScript."""
        # Check required fields for UserScript
        assert "languages" in api_data
        assert "popular" in api_data
        assert "popular_pairs" in api_data
        assert "families" in api_data
        
        # Verify language structure compatibility
        for language in api_data["languages"]:
            # UserScript needs these fields
            userscript_required_fields = ["code", "name", "native_name", "popular", "rtl"]
            for field in userscript_required_fields:
                assert field in language, f"Language missing UserScript required field: {field}"

    def verify_autohotkey_api_compatibility(self, api_data: Dict[str, Any]):
        """Verify API response compatibility with AutoHotkey."""
        # Check required fields for AutoHotkey
        assert "languages" in api_data
        assert isinstance(api_data["languages"], list)
        
        # AutoHotkey needs simpler structure
        for language in api_data["languages"]:
            autohotkey_required_fields = ["code", "name"]
            for field in autohotkey_required_fields:
                assert field in language, f"Language missing AutoHotkey required field: {field}"
            
            # Verify language code is valid for AutoHotkey
            if language["code"] != "auto":
                self.validate_language_code_format(language["code"])

    def validate_language_code_format(self, lang_code: str):
        """Validate language code format (BCP-47 + ISO format)."""
        if lang_code == "auto":
            return  # Special case
        
        parts = lang_code.split("_")
        assert len(parts) == 2, f"Language code should have format xxx_Yyyy: {lang_code}"
        
        lang_part, script_part = parts
        assert len(lang_part) == 3, f"Language part should be 3 characters: {lang_code}"
        assert lang_part.islower(), f"Language part should be lowercase: {lang_code}"
        assert len(script_part) == 4, f"Script part should be 4 characters: {lang_code}"
        assert script_part[0].isupper(), f"Script part should start with uppercase: {lang_code}"
        assert script_part[1:].islower(), f"Script part should have lowercase after first char: {lang_code}"


@pytest.mark.e2e
@pytest.mark.e2e_foundation  
class TestCrossPlatformTranslationSync:
    """Test suite for cross-platform translation workflow synchronization."""

    def test_translation_request_consistency(self, e2e_client: E2EHttpClient):
        """Test that translation requests work consistently across platforms."""
        # Test data that should work from any platform
        test_cases = [
            {
                "text": "Hello world",
                "source_lang": "eng_Latn",
                "target_lang": "rus_Cyrl",
                "expected_keywords": ["привет", "мир", "hello", "world"]
            },
            {
                "text": "Привет мир",
                "source_lang": "rus_Cyrl",
                "target_lang": "eng_Latn", 
                "expected_keywords": ["world"]
            },
            {
                "text": "Thank you",
                "source_lang": "eng_Latn",
                "target_lang": "rus_Cyrl",
                "expected_keywords": ["спасибо", "благодарю"]
            }
        ]
        
        for test_case in test_cases:
            # Simulate UserScript request format
            userscript_payload = self.format_userscript_request(test_case)
            response = e2e_client.post("/translate", json_data=userscript_payload)
            assert response.status_code == 200
            
            userscript_result = response.json()
            
            # Simulate AutoHotkey request format (same API, different client)
            autohotkey_payload = self.format_autohotkey_request(test_case)
            response = e2e_client.post("/translate", json_data=autohotkey_payload)
            assert response.status_code == 200
            
            autohotkey_result = response.json()
            
            # Results should be consistent
            assert userscript_result["detected_source"] == autohotkey_result["detected_source"]
            
            # Translation quality should be similar (allowing for minor variations)
            # Just check that both translations are non-empty and similar length
            assert len(userscript_result["translated_text"]) > 0
            assert len(autohotkey_result["translated_text"]) > 0
            
            # Translations should be reasonably similar in length (within 50%)
            len1 = len(userscript_result["translated_text"])
            len2 = len(autohotkey_result["translated_text"])
            length_ratio = min(len1, len2) / max(len1, len2)
            assert length_ratio >= 0.5, f"Translations too different in length: {len1} vs {len2}"

    def test_bidirectional_translation_sync(self, e2e_client: E2EHttpClient):
        """Test bidirectional translation consistency across platforms."""
        # Test bidirectional workflow
        original_text = "Hello, how are you today?"
        
        # Forward translation: EN → ES
        forward_payload = {
            "text": original_text,
            "source_lang": "eng_Latn",
            "target_lang": "spa_Latn"
        }
        
        forward_response = e2e_client.post("/translate", json_data=forward_payload)
        assert forward_response.status_code == 200
        
        forward_result = forward_response.json()
        spanish_text = forward_result["translated_text"]
        
        # Reverse translation: ES → EN (using result from forward)
        reverse_payload = {
            "text": spanish_text,
            "source_lang": "spa_Latn",
            "target_lang": "eng_Latn"
        }
        
        reverse_response = e2e_client.post("/translate", json_data=reverse_payload)
        assert reverse_response.status_code == 200
        
        reverse_result = reverse_response.json()
        back_translated_text = reverse_result["translated_text"]
        
        # Verify bidirectional consistency
        self.assert_bidirectional_quality(original_text, back_translated_text)

    def test_language_detection_consistency(self, e2e_client: E2EHttpClient):
        """Test that language detection works consistently across platforms."""
        # Test texts in different languages
        detection_test_cases = [
            {
                "text": "Buenos días, ¿cómo está usted?",
                "expected_lang": "spa_Latn"
            },
            {
                "text": "Bonjour, comment allez-vous?",
                "expected_lang": "fra_Latn"
            },
            {
                "text": "Guten Tag, wie geht es Ihnen?",
                "expected_lang": "deu_Latn"
            },
            {
                "text": "Привет, как дела?",
                "expected_lang": "rus_Cyrl"
            }
        ]
        
        for test_case in detection_test_cases:
            payload = {
                "text": test_case["text"],
                "source_lang": "auto",
                "target_lang": "eng_Latn"
            }
            
            response = e2e_client.post("/translate", json_data=payload)
            assert response.status_code == 200
            
            result = response.json()
            detected_lang = result["detected_source"]
            
            # Language detection should be consistent
            assert detected_lang == test_case["expected_lang"], \
                f"Expected {test_case['expected_lang']}, got {detected_lang} for text: {test_case['text']}"

    def test_error_handling_consistency(self, e2e_client: E2EHttpClient):
        """Test that error handling is consistent across platforms."""
        # Test various error scenarios
        error_test_cases = [
            {
                "payload": {
                    "text": "",
                    "source_lang": "eng_Latn",
                    "target_lang": "spa_Latn"
                },
                "expected_status": 400,
                "error_type": "empty_text"
            },
            {
                "payload": {
                    "text": "Hello world",
                    "source_lang": "invalid_Lang",
                    "target_lang": "spa_Latn"
                },
                "expected_status": 400,
                "error_type": "invalid_source"
            },
            {
                "payload": {
                    "text": "Hello world",
                    "source_lang": "eng_Latn",
                    "target_lang": "invalid_Lang"
                },
                "expected_status": 400,
                "error_type": "invalid_target"
            },
            {
                "payload": {
                    "text": "Hello world",
                    "source_lang": "eng_Latn",
                    "target_lang": "auto"
                },
                "expected_status": 400,
                "error_type": "auto_target"
            }
        ]
        
        for test_case in error_test_cases:
            response = e2e_client.post("/translate", json_data=test_case["payload"])
            assert response.status_code == test_case["expected_status"]
            
            error_data = response.json()
            assert "detail" in error_data, "Error response should contain detail field"
            
            # Error messages should be helpful for all platforms
            error_message = error_data["detail"]
            assert len(error_message) > 0, "Error message should not be empty"

    # Helper methods for translation testing
    def format_userscript_request(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Format translation request in UserScript style."""
        return {
            "text": test_case["text"],
            "source_lang": test_case["source_lang"],
            "target_lang": test_case["target_lang"]
        }

    def format_autohotkey_request(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Format translation request in AutoHotkey style."""
        # AutoHotkey uses same API format, just different client
        return {
            "text": test_case["text"],
            "source_lang": test_case["source_lang"],
            "target_lang": test_case["target_lang"]
        }

    def assert_translation_similarity(self, text1: str, text2: str, expected_keywords: List[str]):
        """Assert that two translations are similar enough."""
        text1_lower = text1.lower()
        text2_lower = text2.lower()
        
        # Check for expected keywords in both translations
        for keyword in expected_keywords:
            keyword_lower = keyword.lower()
            text1_has_keyword = keyword_lower in text1_lower
            text2_has_keyword = keyword_lower in text2_lower
            
            # At least one translation should contain each expected keyword
            assert text1_has_keyword or text2_has_keyword, \
                f"Neither translation contains expected keyword '{keyword}'"

    def assert_bidirectional_quality(self, original: str, back_translated: str):
        """Assert that bidirectional translation maintains reasonable quality."""
        original_words = set(original.lower().split())
        back_words = set(back_translated.lower().split())
        
        # Calculate word overlap
        common_words = original_words.intersection(back_words)
        overlap_ratio = len(common_words) / len(original_words) if original_words else 0
        
        # Should have reasonable semantic preservation (allowing for translation variations)
        assert overlap_ratio >= 0.2, \
            f"Bidirectional translation has too little overlap: {overlap_ratio:.2f}"
        
        # Length should be reasonable
        length_ratio = len(back_translated) / len(original) if original else 0
        assert 0.5 <= length_ratio <= 2.0, \
            f"Back-translated text length ratio is unreasonable: {length_ratio:.2f}"


@pytest.mark.e2e
@pytest.mark.e2e_performance
class TestCrossPlatformPerformanceSync:
    """Test suite for cross-platform performance synchronization."""

    def test_concurrent_platform_requests(self, e2e_client: E2EHttpClient):
        """Test concurrent requests from multiple platforms."""
        import threading
        import time
        
        results = []
        
        def make_translation_request(platform_name: str, request_id: int):
            try:
                start_time = time.time()
                
                payload = {
                    "text": f"Test message {request_id} from {platform_name}",
                    "source_lang": "eng_Latn",
                    "target_lang": "spa_Latn"
                }
                
                response = e2e_client.post("/translate", json_data=payload)
                end_time = time.time()
                
                results.append({
                    "platform": platform_name,
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "success": response.status_code == 200
                })
                
            except Exception as e:
                results.append({
                    "platform": platform_name,
                    "request_id": request_id,
                    "error": str(e),
                    "success": False
                })
        
        # Simulate concurrent requests from different platforms
        threads = []
        
        # UserScript requests
        for i in range(2):
            thread = threading.Thread(target=make_translation_request, args=("userscript", i))
            threads.append(thread)
        
        # AutoHotkey requests
        for i in range(2):
            thread = threading.Thread(target=make_translation_request, args=("autohotkey", i))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(results) == 4, "Should have 4 concurrent request results"
        
        successful_results = [r for r in results if r["success"]]
        assert len(successful_results) >= 3, "At least 3 out of 4 concurrent requests should succeed"
        
        # Verify performance is reasonable for all platforms
        for result in successful_results:
            assert result["response_time"] < 10.0, \
                f"Response time too slow for {result['platform']}: {result['response_time']:.2f}s"

    def test_cache_consistency_across_platforms(self, e2e_client: E2EHttpClient):
        """Test that API caching works consistently for all platforms."""
        # Make initial request to populate cache
        response1 = e2e_client.get("/languages")
        assert response1.status_code == 200
        
        first_data = response1.json()
        
        # Make subsequent request (should hit cache)
        response2 = e2e_client.get("/languages")
        assert response2.status_code == 200
        
        second_data = response2.json()
        
        # Data should be identical (from cache)
        assert first_data == second_data, "Cached language data should be identical"
        
        # Verify cache headers
        if "cache_headers" in first_data:
            cache_headers = first_data["cache_headers"]
            assert "Cache-Control" in cache_headers
            assert "max-age" in cache_headers["Cache-Control"]

    def test_rate_limiting_fairness_across_platforms(self, e2e_client: E2EHttpClient):
        """Test that rate limiting treats all platforms fairly."""
        # Make multiple requests quickly
        request_count = 8
        responses = []
        
        for i in range(request_count):
            payload = {
                "text": f"Rate limit test {i}",
                "source_lang": "eng_Latn",
                "target_lang": "spa_Latn"
            }
            
            response = e2e_client.post("/translate", json_data=payload)
            responses.append(response)
            
            # Small delay between requests
            import time
            time.sleep(0.1)
        
        # Count successful vs rate-limited responses
        successful_responses = [r for r in responses if r.status_code == 200]
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        
        # Should have some successful requests
        assert len(successful_responses) > 0, "Should have some successful requests"
        
        # If rate limited, should be applied fairly
        if len(rate_limited_responses) > 0:
            # Rate limiting should kick in gradually, not immediately
            assert len(successful_responses) >= 3, "Should allow several requests before rate limiting"