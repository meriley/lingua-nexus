"""
Language code conversion utilities for multi-model translation system.

This module provides standardized language code conversion between ISO 639-1 
and model-specific formats, enabling seamless model switching while maintaining
a common language interface.
"""

from typing import Dict, Optional, Set
import logging

logger = logging.getLogger(__name__)


class LanguageCodeConverter:
    """Convert between ISO 639-1 and model-specific language codes."""
    
    # Standard ISO 639-1 codes as the common format
    ISO_TO_NAME = {
        "en": "English",
        "ru": "Russian", 
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "zh": "Chinese",
        "ja": "Japanese",
        "ar": "Arabic",
        "pt": "Portuguese",
        "it": "Italian",
        "nl": "Dutch",
        "ko": "Korean",
        "hi": "Hindi",
        "tr": "Turkish",
        "pl": "Polish",
        "cs": "Czech",
        "sv": "Swedish",
        "da": "Danish",
        "no": "Norwegian",
        "fi": "Finnish"
    }
    
    # NLLB model-specific language codes
    NLLB_MAPPING = {
        "en": "eng_Latn",
        "ru": "rus_Cyrl", 
        "es": "spa_Latn",
        "fr": "fra_Latn",
        "de": "deu_Latn",
        "zh": "zho_Hans",
        "ja": "jpn_Jpan",
        "ar": "arb_Arab",
        "pt": "por_Latn",
        "it": "ita_Latn",
        "nl": "nld_Latn",
        "ko": "kor_Hang",
        "hi": "hin_Deva",
        "tr": "tur_Latn",
        "pl": "pol_Latn",
        "cs": "ces_Latn",
        "sv": "swe_Latn",
        "da": "dan_Latn",
        "no": "nob_Latn",
        "fi": "fin_Latn"
    }
    
    # Aya model language names (instruction-following format)
    AYA_MAPPING = {
        "en": "English",
        "ru": "Russian",
        "es": "Spanish", 
        "fr": "French",
        "de": "German",
        "zh": "Chinese",
        "ja": "Japanese",
        "ar": "Arabic",
        "pt": "Portuguese",
        "it": "Italian",
        "nl": "Dutch",
        "ko": "Korean",
        "hi": "Hindi",
        "tr": "Turkish",
        "pl": "Polish",
        "cs": "Czech",
        "sv": "Swedish",
        "da": "Danish",
        "no": "Norwegian",
        "fi": "Finnish"
    }
    
    # OpenAI model language codes (for future use)
    OPENAI_MAPPING = {
        "en": "en",
        "ru": "ru",
        "es": "es",
        "fr": "fr",
        "de": "de",
        "zh": "zh",
        "ja": "ja",
        "ar": "ar",
        "pt": "pt",
        "it": "it",
        "nl": "nl",
        "ko": "ko",
        "hi": "hi",
        "tr": "tr",
        "pl": "pl",
        "cs": "cs",
        "sv": "sv",
        "da": "da",
        "no": "no",
        "fi": "fi"
    }
    
    @classmethod
    def to_model_code(cls, iso_code: str, model_type: str) -> str:
        """
        Convert ISO 639-1 code to model-specific code.
        
        Args:
            iso_code: ISO 639-1 language code (e.g., 'en', 'ru')
            model_type: Model type ('nllb', 'aya', 'openai')
            
        Returns:
            Model-specific language code
            
        Raises:
            ValueError: If model type is not supported
        """
        model_type = model_type.upper()
        mapping_attr = f"{model_type}_MAPPING"
        
        if not hasattr(cls, mapping_attr):
            raise ValueError(f"Unsupported model type: {model_type}")
            
        mapping = getattr(cls, mapping_attr)
        result = mapping.get(iso_code, iso_code)
        
        if result == iso_code and iso_code not in mapping:
            logger.warning(f"No mapping found for {iso_code} in {model_type}, using as-is")
            
        return result
    
    @classmethod
    def from_model_code(cls, model_code: str, model_type: str) -> str:
        """
        Convert model-specific code to ISO 639-1 code.
        
        Args:
            model_code: Model-specific language code
            model_type: Model type ('nllb', 'aya', 'openai')
            
        Returns:
            ISO 639-1 language code
            
        Raises:
            ValueError: If model type is not supported
        """
        model_type = model_type.upper()
        mapping_attr = f"{model_type}_MAPPING"
        
        if not hasattr(cls, mapping_attr):
            raise ValueError(f"Unsupported model type: {model_type}")
            
        mapping = getattr(cls, mapping_attr)
        reverse_mapping = {v: k for k, v in mapping.items()}
        result = reverse_mapping.get(model_code, model_code)
        
        if result == model_code and model_code not in reverse_mapping:
            logger.warning(f"No reverse mapping found for {model_code} in {model_type}, using as-is")
            
        return result
    
    @classmethod
    def get_language_name(cls, iso_code: str) -> str:
        """
        Get human-readable language name from ISO code.
        
        Args:
            iso_code: ISO 639-1 language code
            
        Returns:
            Human-readable language name
        """
        return cls.ISO_TO_NAME.get(iso_code, iso_code.capitalize())
    
    @classmethod
    def get_supported_languages(cls, model_type: str) -> Set[str]:
        """
        Get set of supported ISO language codes for a model type.
        
        Args:
            model_type: Model type ('nllb', 'aya', 'openai')
            
        Returns:
            Set of supported ISO 639-1 language codes
            
        Raises:
            ValueError: If model type is not supported
        """
        model_type = model_type.upper()
        mapping_attr = f"{model_type}_MAPPING"
        
        if not hasattr(cls, mapping_attr):
            raise ValueError(f"Unsupported model type: {model_type}")
            
        mapping = getattr(cls, mapping_attr)
        return set(mapping.keys())
    
    @classmethod
    def is_valid_iso_code(cls, iso_code: str) -> bool:
        """
        Check if an ISO code is valid and supported.
        
        Args:
            iso_code: ISO 639-1 language code to validate
            
        Returns:
            True if valid and supported, False otherwise
        """
        return iso_code in cls.ISO_TO_NAME
    
    @classmethod
    def detect_model_type_from_code(cls, lang_code: str) -> Optional[str]:
        """
        Attempt to detect model type from language code format.
        
        Args:
            lang_code: Language code to analyze
            
        Returns:
            Model type if detected, None otherwise
        """
        # Check NLLB format (contains underscore and script)
        if '_' in lang_code and len(lang_code) > 3:
            nllb_codes = set(cls.NLLB_MAPPING.values())
            if lang_code in nllb_codes:
                return 'nllb'
        
        # Check if it's a simple ISO code
        if lang_code in cls.ISO_TO_NAME:
            return 'iso'
            
        # Check if it's a language name (Aya format)
        aya_codes = set(cls.AYA_MAPPING.values())
        if lang_code in aya_codes:
            return 'aya'
            
        return None
    
    @classmethod
    def normalize_language_code(cls, lang_code: str, target_model: str) -> str:
        """
        Normalize a language code to the target model format.
        
        This method attempts to automatically detect the source format
        and convert to the target model format.
        
        Args:
            lang_code: Language code in any supported format
            target_model: Target model type ('nllb', 'aya', 'openai')
            
        Returns:
            Language code in target model format
            
        Raises:
            ValueError: If conversion is not possible
        """
        # First, try to convert to ISO format
        source_type = cls.detect_model_type_from_code(lang_code)
        
        if source_type == 'iso':
            iso_code = lang_code
        elif source_type:
            iso_code = cls.from_model_code(lang_code, source_type)
        else:
            # Try fuzzy matching against language names
            lang_code_lower = lang_code.lower()
            for iso, name in cls.ISO_TO_NAME.items():
                if name.lower() == lang_code_lower:
                    iso_code = iso
                    break
            else:
                raise ValueError(f"Cannot normalize language code: {lang_code}")
        
        # Convert to target format
        return cls.to_model_code(iso_code, target_model)