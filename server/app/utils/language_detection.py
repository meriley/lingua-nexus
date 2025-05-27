"""Language Detection Utilities

Basic language detection module for the translation system.
Provides simple heuristic-based language detection for supported languages.

⚠️  LIMITATION: This is a simplified implementation for development/testing.
For production systems, consider integrating proper language detection libraries
like langdetect, fasttext, or cloud-based language detection APIs.

Supported Detection:
- Russian (Cyrillic script)
- English (Latin script)
- Mixed/unclear content detection

Integration with Multi-Model System:
- Used by legacy NLLB API for auto-detection
- Modern multi-model system supports more sophisticated detection
- Can be extended to support additional model-specific language sets
"""

def detect_language(text):
    """Detect if text is Russian or English based on character analysis.
    
    This is a basic heuristic-based language detector that analyzes
    character distribution to determine the most likely language.
    
    Algorithm:
    1. Count Cyrillic characters (Russian indicator)
    2. Count Latin characters (English indicator)
    3. Calculate proportions to determine dominant script
    4. Return language code based on majority script
    
    Limitations:
    - Only supports Russian/English detection
    - Script-based detection (doesn't consider vocabulary/grammar)
    - May misclassify other Cyrillic/Latin languages
    - No confidence scoring
    
    Args:
        text (str): Text to analyze for language detection
        
    Returns:
        str: Language code:
            - 'ru': Russian (majority Cyrillic characters)
            - 'en': English (majority Latin characters) 
            - 'auto': Mixed/unclear content or no alphabetic characters
            
    Example:
        >>> detect_language("Привет мир")  # Russian
        'ru'
        >>> detect_language("Hello world")  # English
        'en'
        >>> detect_language("123 !@#")  # No letters
        'auto'
        
    Production Recommendation:
        Replace with proper language detection:
        ```python
        from langdetect import detect
        language = detect(text)  # Returns ISO 639-1 codes
        ```
    """
    # Handle empty or whitespace-only input
    if not text or not text.strip():
        return "auto"  # Default for empty/whitespace strings
    
    # Unicode range detection for script identification
    # Cyrillic Unicode block: U+0400–U+04FF (Cyrillic)
    cyrillic_chars = len([c for c in text if '\u0400' <= c <= '\u04FF'])
    
    # Basic Latin characters: a-z, A-Z
    # Note: Doesn't include extended Latin (accented characters)
    latin_chars = len([c for c in text if 'a' <= c.lower() <= 'z'])
    
    # Calculate total alphabetic characters for proportion analysis
    total_alpha = cyrillic_chars + latin_chars
    
    # If no alphabetic characters found, cannot determine language
    if total_alpha == 0:
        return 'auto'  # Numbers, punctuation, or other scripts only
        
    # Determine language based on character script majority (>50%)
    if cyrillic_chars / total_alpha > 0.5:
        return 'ru'  # Russian (or other Cyrillic languages like Ukrainian, Bulgarian)
    elif latin_chars / total_alpha > 0.5:
        return 'en'  # English (or other Latin script languages)
    else:
        return 'auto'  # Mixed content or no clear majority


def detect_language_nllb_format(text):
    """Detect language and return NLLB-formatted language codes.
    
    This function bridges the simple language detection with NLLB model
    requirements by converting basic language codes to NLLB's specific format.
    
    NLLB Language Code Format:
    - Uses format: language_script (e.g., 'eng_Latn', 'rus_Cyrl')
    - Language: ISO 639-3 three-letter code
    - Script: ISO 15924 four-letter script code
    
    Integration Notes:
    - Used by legacy NLLB API for auto-detection
    - Multi-model system has more sophisticated language code conversion
    - See app/utils/language_codes.py for comprehensive cross-model mapping
    
    Args:
        text (str): Text to analyze for language detection
        
    Returns:
        str: NLLB-formatted language code:
            - 'rus_Cyrl': Russian with Cyrillic script
            - 'eng_Latn': English with Latin script (also default for 'auto')
            
    Example:
        >>> detect_language_nllb_format("Привет")
        'rus_Cyrl'
        >>> detect_language_nllb_format("Hello")
        'eng_Latn'
        >>> detect_language_nllb_format("123")
        'eng_Latn'  # Defaults to English for unclear content
        
    Related:
        - detect_language(): Basic language detection
        - app/utils/language_codes.py: Cross-model language mapping
        - app/utils/language_metadata.py: Comprehensive language information
    """
    # Get basic language detection result
    simple_code = detect_language(text)
    
    # Map basic language codes to NLLB's language_script format
    # NLLB uses ISO 639-3 (3-letter) language codes with ISO 15924 script codes
    code_mapping = {
        'ru': 'rus_Cyrl',    # Russian with Cyrillic script
        'en': 'eng_Latn',    # English with Latin script
        'auto': 'eng_Latn'   # Default to English for unclear/mixed content
    }
    
    # Return mapped code with fallback to English
    # This ensures compatibility with NLLB model expectations
    return code_mapping.get(simple_code, 'eng_Latn')