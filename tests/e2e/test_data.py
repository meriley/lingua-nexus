"""
Test data management for E2E tests.

This module provides test data for E2E tests that don't assert exact translations
but rather verify the system is working correctly.
"""

E2E_TEST_TRANSLATIONS = [
    {
        "text": "Hello",
        "source": "en",
        "target": "es",
        "min_length": 3,
        "keywords": ["hola"],  # Flexible validation
        "description": "Basic greeting"
    },
    {
        "text": "Good morning",
        "source": "en",
        "target": "fr",
        "min_length": 5,
        "keywords": ["bon", "jour"],
        "description": "Morning greeting"
    },
    {
        "text": "Thank you",
        "source": "en",
        "target": "de",
        "min_length": 4,
        "keywords": ["dank"],
        "description": "Expression of gratitude"
    },
    {
        "text": "How are you?",
        "source": "en",
        "target": "ru",
        "min_length": 5,
        "keywords": ["как"],
        "description": "Common question"
    },
    {
        "text": "Welcome",
        "source": "en",
        "target": "zh",
        "min_length": 2,
        "keywords": [],  # Chinese characters may not match simple keywords
        "description": "Welcome greeting"
    }
]

E2E_BATCH_TRANSLATIONS = [
    {"text": "One", "source": "en", "target": "es"},
    {"text": "Two", "source": "en", "target": "es"},
    {"text": "Three", "source": "en", "target": "es"},
    {"text": "Four", "source": "en", "target": "es"}
]

E2E_LANGUAGE_DETECTION_TESTS = [
    {
        "text": "Bonjour le monde",
        "expected_lang": "fr",
        "target": "en",
        "description": "French detection"
    },
    {
        "text": "Hola mundo",
        "expected_lang": "es",
        "target": "en",
        "description": "Spanish detection"
    },
    {
        "text": "Привет мир",
        "expected_lang": "ru",
        "target": "en",
        "description": "Russian detection"
    }
]

E2E_ERROR_CASES = [
    {
        "text": "Test",
        "source": "en",
        "target": "invalid_lang",
        "expected_status": 400,
        "description": "Invalid target language"
    },
    {
        "text": "",
        "source": "en",
        "target": "es",
        "expected_status": 422,
        "description": "Empty text"
    },
    {
        "text": "Test",
        "source": "invalid_lang",
        "target": "en",
        "expected_status": 400,
        "description": "Invalid source language"
    }
]

def validate_translation(result, expected):
    """Validate translation result against expected criteria."""
    if "min_length" in expected:
        if len(result) < expected["min_length"]:
            return False, f"Translation too short: {len(result)} < {expected['min_length']}"
    
    if "keywords" in expected and expected["keywords"]:
        result_lower = result.lower()
        for keyword in expected["keywords"]:
            if keyword.lower() in result_lower:
                return True, "Keywords found"
        return False, f"Keywords {expected['keywords']} not found in translation"
    
    # If no specific validation, just check it's not empty
    if len(result.strip()) == 0:
        return False, "Empty translation"
    
    return True, "Valid translation"