# Multi-Model Translation Architecture

## Overview

This document outlines the architectural changes needed to abstract the translation system from NLLB-specific implementations to support multiple translation models including Aya 8B, OpenAI models, and other future backends.

## Current Architecture Limitations

The existing system is tightly coupled to NLLB:
- Hard-coded NLLB language codes (`eng_Latn`, `rus_Cyrl`)
- NLLB-specific model loading and inference
- Fixed API response format based on NLLB outputs
- Direct dependency on NLLB's language detection capabilities

## Proposed Architecture

### 1. Translation Service Abstraction Layer

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class TranslationRequest:
    text: str
    source_lang: Optional[str] = None  # None for auto-detection
    target_lang: str = "en"
    model_options: Dict = None

@dataclass
class TranslationResponse:
    translated_text: str
    detected_source_lang: Optional[str] = None
    confidence_score: Optional[float] = None
    processing_time_ms: float = 0
    model_used: str = ""
    metadata: Dict = None

class TranslationModel(ABC):
    """Abstract base class for all translation models"""
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Return list of supported language codes in ISO 639-1 format"""
        pass
    
    @abstractmethod
    def translate(self, request: TranslationRequest) -> TranslationResponse:
        """Perform translation"""
        pass
    
    @abstractmethod
    def detect_language(self, text: str) -> str:
        """Detect language of input text"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if model is ready for inference"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict:
        """Return model metadata"""
        pass
```

### 2. Model Registry and Factory

```python
class ModelRegistry:
    """Registry for managing available translation models"""
    
    def __init__(self):
        self._models: Dict[str, TranslationModel] = {}
        self._default_model: Optional[str] = None
    
    def register_model(self, name: str, model: TranslationModel):
        """Register a translation model"""
        self._models[name] = model
        if self._default_model is None:
            self._default_model = name
    
    def get_model(self, name: Optional[str] = None) -> TranslationModel:
        """Get model by name or default"""
        model_name = name or self._default_model
        if model_name not in self._models:
            raise ValueError(f"Model {model_name} not found")
        return self._models[model_name]
    
    def list_models(self) -> List[str]:
        """List available model names"""
        return list(self._models.keys())

class ModelFactory:
    """Factory for creating translation model instances"""
    
    @staticmethod
    def create_nllb_model(config: Dict) -> 'NLLBModel':
        """Create NLLB model instance"""
        pass
    
    @staticmethod
    def create_aya_model(config: Dict) -> 'AyaModel':
        """Create Aya 8B model instance"""
        pass
    
    @staticmethod
    def create_openai_model(config: Dict) -> 'OpenAIModel':
        """Create OpenAI model instance"""
        pass
```

### 3. Language Code Standardization

```python
class LanguageCodeConverter:
    """Convert between different language code formats"""
    
    # Standard ISO 639-1 codes as the common format
    STANDARD_CODES = {
        "en": "English",
        "ru": "Russian", 
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "zh": "Chinese",
        "ja": "Japanese",
        "ar": "Arabic"
    }
    
    # Model-specific code mappings
    NLLB_MAPPING = {
        "en": "eng_Latn",
        "ru": "rus_Cyrl", 
        "es": "spa_Latn",
        "fr": "fra_Latn"
    }
    
    AYA_MAPPING = {
        "en": "english",
        "ru": "russian",
        "es": "spanish", 
        "fr": "french"
    }
    
    @classmethod
    def to_model_code(cls, iso_code: str, model_type: str) -> str:
        """Convert ISO code to model-specific code"""
        mapping = getattr(cls, f"{model_type.upper()}_MAPPING", {})
        return mapping.get(iso_code, iso_code)
    
    @classmethod
    def from_model_code(cls, model_code: str, model_type: str) -> str:
        """Convert model-specific code to ISO code"""
        mapping = getattr(cls, f"{model_type.upper()}_MAPPING", {})
        reverse_mapping = {v: k for k, v in mapping.items()}
        return reverse_mapping.get(model_code, model_code)
```

### 4. Specific Model Implementations

#### NLLB Model Implementation
```python
class NLLBModel(TranslationModel):
    def __init__(self, model_path: str, device: str = "cpu"):
        self.model_path = model_path
        self.device = device
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def translate(self, request: TranslationRequest) -> TranslationResponse:
        # Convert ISO codes to NLLB format
        source_lang = LanguageCodeConverter.to_model_code(
            request.source_lang or "auto", "nllb"
        )
        target_lang = LanguageCodeConverter.to_model_code(
            request.target_lang, "nllb"
        )
        
        # Existing NLLB translation logic
        # ...
```

#### Aya 8B Model Implementation
```python
class AyaModel(TranslationModel):
    def __init__(self, model_path: str, api_endpoint: Optional[str] = None):
        self.model_path = model_path
        self.api_endpoint = api_endpoint
        self.model = None
        self._load_model()
    
    def translate(self, request: TranslationRequest) -> TranslationResponse:
        # Aya-specific translation using prompt engineering
        prompt = self._build_translation_prompt(
            request.text, 
            request.source_lang, 
            request.target_lang
        )
        
        # Call Aya model with prompt
        # ...
    
    def _build_translation_prompt(self, text: str, source: str, target: str) -> str:
        """Build Aya-specific translation prompt"""
        return f"Translate the following text from {source} to {target}:\n{text}\n\nTranslation:"
```

### 5. Configuration System

```yaml
# config/models.yaml
models:
  nllb:
    type: "nllb"
    model_path: "facebook/nllb-200-distilled-600M"
    device: "cpu"
    enabled: true
    
  aya:
    type: "aya"
    model_path: "CohereForAI/aya-23-8B"
    api_endpoint: "http://localhost:8080/generate"
    enabled: false
    
  openai:
    type: "openai"
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-3.5-turbo"
    enabled: false

default_model: "nllb"

language_preferences:
  primary_languages: ["en", "ru", "es", "fr"]
  auto_detect_threshold: 0.8
```

### 6. API Layer Updates

```python
from fastapi import FastAPI, HTTPException
from .models import ModelRegistry, TranslationRequest, TranslationResponse

app = FastAPI()
registry = ModelRegistry()

@app.post("/translate", response_model=TranslationResponse)
async def translate_text(
    request: TranslationRequest,
    model_name: Optional[str] = None
):
    try:
        model = registry.get_model(model_name)
        return model.translate(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def list_models():
    return {
        "models": registry.list_models(),
        "default": registry._default_model
    }

@app.get("/languages/{model_name}")
async def get_supported_languages(model_name: str):
    model = registry.get_model(model_name)
    return {"languages": model.get_supported_languages()}
```

## Migration Strategy

### Phase 1: Abstract Current NLLB Implementation
1. Create abstract base classes and interfaces
2. Refactor existing NLLB code to implement new interfaces
3. Maintain backward compatibility with existing API

### Phase 2: Add Model Registry and Configuration
1. Implement model registry and factory patterns
2. Add configuration system for multiple models
3. Update API to support model selection

### Phase 3: Implement Aya 8B Support
1. Create Aya-specific model implementation
2. Add Aya language code mappings
3. Test Aya integration thoroughly

### Phase 4: Frontend Updates
1. Update userscript to support model selection
2. Add UI for switching between models
3. Handle model-specific features and limitations

### Phase 5: Additional Models
1. Add OpenAI/Azure OpenAI support
2. Add local transformer models support
3. Add Google Translate API support

## Benefits

1. **Flexibility**: Easy to add new translation models
2. **Maintainability**: Clear separation of concerns
3. **Testability**: Each model can be tested independently
4. **Performance**: Can choose optimal model for specific use cases
5. **Reliability**: Fallback to different models if one fails
6. **User Choice**: Users can select preferred models

## Considerations

1. **Performance**: Model switching overhead
2. **Memory**: Multiple models loaded simultaneously
3. **Complexity**: Increased codebase complexity
4. **Testing**: Need comprehensive test coverage for all models
5. **Documentation**: Clear documentation for adding new models

## Future Enhancements

1. **Model Ensemble**: Combine multiple models for better quality
2. **Adaptive Selection**: Automatically choose best model per language pair
3. **Caching**: Cache translations across models
4. **Quality Metrics**: Compare model outputs and quality scores
5. **Cost Optimization**: Route to cheapest model meeting quality requirements