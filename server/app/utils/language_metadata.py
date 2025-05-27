"""
Language metadata utilities for NLLB translation system.
Provides comprehensive language information including names, families, scripts, and popularity rankings.
"""

from typing import Dict, List, Optional
import json

# NLLB-200 Language metadata with comprehensive information
NLLB_LANGUAGES = {
    # Popular European Languages
    "eng_Latn": {
        "code": "eng_Latn",
        "name": "English",
        "native_name": "English",
        "family": "Germanic",
        "script": "Latin",
        "popular": True,
        "region": "Global",
        "rtl": False
    },
    "spa_Latn": {
        "code": "spa_Latn", 
        "name": "Spanish",
        "native_name": "Español",
        "family": "Romance",
        "script": "Latin",
        "popular": True,
        "region": "Global",
        "rtl": False
    },
    "fra_Latn": {
        "code": "fra_Latn",
        "name": "French", 
        "native_name": "Français",
        "family": "Romance",
        "script": "Latin",
        "popular": True,
        "region": "Global",
        "rtl": False
    },
    "deu_Latn": {
        "code": "deu_Latn",
        "name": "German",
        "native_name": "Deutsch", 
        "family": "Germanic",
        "script": "Latin",
        "popular": True,
        "region": "Europe",
        "rtl": False
    },
    "ita_Latn": {
        "code": "ita_Latn",
        "name": "Italian",
        "native_name": "Italiano",
        "family": "Romance", 
        "script": "Latin",
        "popular": True,
        "region": "Europe",
        "rtl": False
    },
    "por_Latn": {
        "code": "por_Latn",
        "name": "Portuguese",
        "native_name": "Português",
        "family": "Romance",
        "script": "Latin", 
        "popular": True,
        "region": "Global",
        "rtl": False
    },
    "rus_Cyrl": {
        "code": "rus_Cyrl",
        "name": "Russian",
        "native_name": "Русский",
        "family": "Slavic",
        "script": "Cyrillic",
        "popular": True,
        "region": "Eastern Europe",
        "rtl": False
    },
    "nld_Latn": {
        "code": "nld_Latn",
        "name": "Dutch",
        "native_name": "Nederlands",
        "family": "Germanic",
        "script": "Latin",
        "popular": True,
        "region": "Europe",
        "rtl": False
    },
    "pol_Latn": {
        "code": "pol_Latn",
        "name": "Polish",
        "native_name": "Polski",
        "family": "Slavic",
        "script": "Latin",
        "popular": True,
        "region": "Europe",
        "rtl": False
    },
    "ukr_Cyrl": {
        "code": "ukr_Cyrl",
        "name": "Ukrainian",
        "native_name": "Українська",
        "family": "Slavic",
        "script": "Cyrillic",
        "popular": True,
        "region": "Eastern Europe",
        "rtl": False
    },
    
    # Popular Asian Languages
    "zho_Hans": {
        "code": "zho_Hans",
        "name": "Chinese (Simplified)",
        "native_name": "简体中文",
        "family": "Sino-Tibetan",
        "script": "Chinese Simplified",
        "popular": True,
        "region": "East Asia",
        "rtl": False
    },
    "zho_Hant": {
        "code": "zho_Hant", 
        "name": "Chinese (Traditional)",
        "native_name": "繁體中文",
        "family": "Sino-Tibetan",
        "script": "Chinese Traditional",
        "popular": True,
        "region": "East Asia",
        "rtl": False
    },
    "jpn_Jpan": {
        "code": "jpn_Jpan",
        "name": "Japanese",
        "native_name": "日本語",
        "family": "Japonic",
        "script": "Japanese",
        "popular": True,
        "region": "East Asia",
        "rtl": False
    },
    "kor_Hang": {
        "code": "kor_Hang",
        "name": "Korean",
        "native_name": "한국어",
        "family": "Koreanic", 
        "script": "Hangul",
        "popular": True,
        "region": "East Asia",
        "rtl": False
    },
    "hin_Deva": {
        "code": "hin_Deva",
        "name": "Hindi",
        "native_name": "हिन्दी",
        "family": "Indo-European",
        "script": "Devanagari",
        "popular": True,
        "region": "South Asia",
        "rtl": False
    },
    "tha_Thai": {
        "code": "tha_Thai",
        "name": "Thai",
        "native_name": "ไทย",
        "family": "Tai-Kadai",
        "script": "Thai",
        "popular": True,
        "region": "Southeast Asia",
        "rtl": False
    },
    "vie_Latn": {
        "code": "vie_Latn",
        "name": "Vietnamese",
        "native_name": "Tiếng Việt",
        "family": "Austroasiatic",
        "script": "Latin",
        "popular": True,
        "region": "Southeast Asia", 
        "rtl": False
    },
    
    # Popular Middle Eastern/North African Languages
    "arb_Arab": {
        "code": "arb_Arab",
        "name": "Arabic",
        "native_name": "العربية",
        "family": "Afro-Asiatic",
        "script": "Arabic",
        "popular": True,
        "region": "Middle East",
        "rtl": True
    },
    "pes_Arab": {
        "code": "pes_Arab",
        "name": "Persian",
        "native_name": "فارسی",
        "family": "Indo-European",
        "script": "Arabic",
        "popular": True,
        "region": "Middle East",
        "rtl": True
    },
    "tur_Latn": {
        "code": "tur_Latn",
        "name": "Turkish",
        "native_name": "Türkçe",
        "family": "Turkic",
        "script": "Latin",
        "popular": True,
        "region": "Middle East",
        "rtl": False
    },
    "heb_Hebr": {
        "code": "heb_Hebr",
        "name": "Hebrew",
        "native_name": "עברית",
        "family": "Afro-Asiatic",
        "script": "Hebrew",
        "popular": True,
        "region": "Middle East",
        "rtl": True
    },
    
    # Additional Popular Languages
    "swe_Latn": {
        "code": "swe_Latn",
        "name": "Swedish",
        "native_name": "Svenska",
        "family": "Germanic",
        "script": "Latin",
        "popular": False,
        "region": "Europe",
        "rtl": False
    },
    "nor_Latn": {
        "code": "nor_Latn",
        "name": "Norwegian",
        "native_name": "Norsk",
        "family": "Germanic",
        "script": "Latin",
        "popular": False,
        "region": "Europe",
        "rtl": False
    },
    "dan_Latn": {
        "code": "dan_Latn",
        "name": "Danish",
        "native_name": "Dansk",
        "family": "Germanic",
        "script": "Latin",
        "popular": False,
        "region": "Europe",
        "rtl": False
    },
    "fin_Latn": {
        "code": "fin_Latn",
        "name": "Finnish",
        "native_name": "Suomi",
        "family": "Uralic",
        "script": "Latin",
        "popular": False,
        "region": "Europe",
        "rtl": False
    },
    "ces_Latn": {
        "code": "ces_Latn", 
        "name": "Czech",
        "native_name": "Čeština",
        "family": "Slavic",
        "script": "Latin",
        "popular": False,
        "region": "Europe",
        "rtl": False
    },
    "hun_Latn": {
        "code": "hun_Latn",
        "name": "Hungarian",
        "native_name": "Magyar",
        "family": "Uralic",
        "script": "Latin",
        "popular": False,
        "region": "Europe",
        "rtl": False
    },
    "ron_Latn": {
        "code": "ron_Latn",
        "name": "Romanian",
        "native_name": "Română",
        "family": "Romance",
        "script": "Latin",
        "popular": False,
        "region": "Europe",
        "rtl": False
    },
    "bul_Cyrl": {
        "code": "bul_Cyrl",
        "name": "Bulgarian",
        "native_name": "Български",
        "family": "Slavic",
        "script": "Cyrillic",
        "popular": False,
        "region": "Europe",
        "rtl": False
    },
    "hrv_Latn": {
        "code": "hrv_Latn",
        "name": "Croatian",
        "native_name": "Hrvatski",
        "family": "Slavic",
        "script": "Latin",
        "popular": False,
        "region": "Europe",
        "rtl": False
    },
    "slv_Latn": {
        "code": "slv_Latn",
        "name": "Slovenian",
        "native_name": "Slovenščina",
        "family": "Slavic",
        "script": "Latin",
        "popular": False,
        "region": "Europe",
        "rtl": False
    },
    
    # Auto-detect option
    "auto": {
        "code": "auto",
        "name": "Auto-detect",
        "native_name": "Auto-detect",
        "family": "Auto",
        "script": "Auto",
        "popular": True,
        "region": "Global",
        "rtl": False
    }
}

# Language families for organizational purposes
LANGUAGE_FAMILIES = {
    "Germanic": ["eng_Latn", "deu_Latn", "nld_Latn", "swe_Latn", "nor_Latn", "dan_Latn"],
    "Romance": ["spa_Latn", "fra_Latn", "ita_Latn", "por_Latn", "ron_Latn"],
    "Slavic": ["rus_Cyrl", "pol_Latn", "ukr_Cyrl", "ces_Latn", "bul_Cyrl", "hrv_Latn", "slv_Latn"],
    "Sino-Tibetan": ["zho_Hans", "zho_Hant"],
    "Japonic": ["jpn_Jpan"],
    "Koreanic": ["kor_Hang"],
    "Indo-European": ["hin_Deva", "pes_Arab"],
    "Afro-Asiatic": ["arb_Arab", "heb_Hebr"],
    "Turkic": ["tur_Latn"],
    "Tai-Kadai": ["tha_Thai"],
    "Austroasiatic": ["vie_Latn"],
    "Uralic": ["fin_Latn", "hun_Latn"],
    "Auto": ["auto"]
}

# Popular languages for quick access
POPULAR_LANGUAGES = [
    "auto", "eng_Latn", "spa_Latn", "fra_Latn", "deu_Latn", "ita_Latn", 
    "por_Latn", "rus_Cyrl", "zho_Hans", "jpn_Jpan", "kor_Hang", 
    "hin_Deva", "arb_Arab", "tha_Thai", "vie_Latn", "tur_Latn"
]

# Popular language pairs for bidirectional translation
POPULAR_LANGUAGE_PAIRS = [
    ("auto", "eng_Latn"),
    ("eng_Latn", "spa_Latn"),
    ("eng_Latn", "fra_Latn"),
    ("eng_Latn", "deu_Latn"),
    ("eng_Latn", "rus_Cyrl"),
    ("eng_Latn", "zho_Hans"),
    ("eng_Latn", "jpn_Jpan"),
    ("eng_Latn", "kor_Hang"),
    ("rus_Cyrl", "ukr_Cyrl"),
    ("zho_Hans", "zho_Hant")
]

def get_all_languages() -> Dict[str, Dict]:
    """Get all supported languages with metadata."""
    return NLLB_LANGUAGES

def get_language_by_code(code: str) -> Optional[Dict]:
    """Get language metadata by language code."""
    return NLLB_LANGUAGES.get(code)

def get_popular_languages() -> List[str]:
    """Get list of popular language codes."""
    return POPULAR_LANGUAGES

def get_language_families() -> Dict[str, List[str]]:
    """Get languages organized by families."""
    return LANGUAGE_FAMILIES

def get_popular_language_pairs() -> List[tuple]:
    """Get popular language pairs for quick selection."""
    return POPULAR_LANGUAGE_PAIRS

def search_languages(query: str) -> List[Dict]:
    """Search languages by name or native name."""
    if not query:
        return []
    
    query = query.lower()
    results = []
    
    for lang_data in NLLB_LANGUAGES.values():
        if (query in lang_data["name"].lower() or 
            query in lang_data["native_name"].lower() or
            query in lang_data["code"].lower()):
            results.append(lang_data)
    
    # Sort by popularity first, then by name
    results.sort(key=lambda x: (not x["popular"], x["name"]))
    return results

def validate_language_code(code: str) -> bool:
    """Validate if language code is supported."""
    return code in NLLB_LANGUAGES

def get_language_metadata() -> Dict:
    """Get complete language metadata for API response."""
    return {
        "languages": list(NLLB_LANGUAGES.values()),
        "families": LANGUAGE_FAMILIES,
        "popular": POPULAR_LANGUAGES,
        "popular_pairs": POPULAR_LANGUAGE_PAIRS,
        "total_count": len(NLLB_LANGUAGES)
    }