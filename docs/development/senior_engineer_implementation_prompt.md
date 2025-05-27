# Senior Engineer Implementation Prompt: Multi-Model Translation Architecture

## Project Overview

You are tasked with refactoring our NLLB-based translation system to support multiple translation models, with Aya 8B as the primary new target. This involves creating an abstraction layer that allows seamless switching between translation backends while maintaining backward compatibility.

## Current System Analysis

### Existing Codebase Structure
```
server/
├── app/
│   ├── main.py              # FastAPI application
│   └── utils/
│       ├── language_detection.py  # Language detection logic
│       └── model_loader.py        # NLLB model loading
├── server.py                # Legacy server entry point
└── requirements.txt
```

### Key Files to Understand
1. **`server/app/main.py`**: Main FastAPI application with `/translate` endpoint
2. **`server/app/utils/model_loader.py`**: NLLB model loading and inference
3. **`server/app/utils/language_detection.py`**: Language detection utilities
4. **`userscript/telegram-nllb-translator-standalone.user.js`**: Frontend client

### Current Limitations
- Hard-coded NLLB language codes (`eng_Latn`, `rus_Cyrl`)
- Direct model loading without abstraction
- Fixed API response format
- No model selection capabilities

## Your Mission

### Primary Objective
Create a flexible, extensible translation architecture that:
1. **Abstracts** model implementations behind common interfaces
2. **Supports** NLLB (existing) and Aya 8B (new) models
3. **Maintains** backward compatibility with existing clients
4. **Enables** easy addition of future models (OpenAI, Google Translate, etc.)

### Success Criteria
- [ ] Existing NLLB functionality works unchanged
- [ ] Aya 8B model can translate text with acceptable quality  
- [ ] API supports model selection via parameter
- [ ] New models can be added with minimal code changes
- [ ] Performance within 50% of current NLLB speed
- [ ] Comprehensive test coverage for new architecture

## Implementation Strategy

### Phase 1: Core Abstraction (Start Here)

#### 1.1 Create Abstract Base Classes
Create `server/app/models/base.py`:

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
import time

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
    
    def __init__(self, config: Dict):
        self.config = config
        self.model_name = config.get('name', 'unknown')
    
    @abstractmethod
    async def translate(self, request: TranslationRequest) -> TranslationResponse:
        """Perform translation"""
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Return list of supported language codes in ISO 639-1 format"""
        pass
    
    @abstractmethod
    async def detect_language(self, text: str) -> str:
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

#### 1.2 Create Language Code Converter
Create `server/app/utils/language_codes.py`:

```python
class LanguageCodeConverter:
    """Convert between ISO 639-1 and model-specific language codes"""
    
    # Standard ISO 639-1 codes as the common format
    ISO_TO_NAME = {
        "en": "English",
        "ru": "Russian", 
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "zh": "Chinese",
        "ja": "Japanese",
        "ar": "Arabic"
    }
    
    # Model-specific mappings
    NLLB_MAPPING = {
        "en": "eng_Latn",
        "ru": "rus_Cyrl", 
        "es": "spa_Latn",
        "fr": "fra_Latn",
        "de": "deu_Latn",
        "zh": "zho_Hans",
        "ja": "jpn_Jpan",
        "ar": "arb_Arab"
    }
    
    AYA_MAPPING = {
        "en": "english",
        "ru": "russian",
        "es": "spanish", 
        "fr": "french",
        "de": "german",
        "zh": "chinese",
        "ja": "japanese",
        "ar": "arabic"
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
    
    @classmethod
    def get_language_name(cls, iso_code: str) -> str:
        """Get human-readable language name"""
        return cls.ISO_TO_NAME.get(iso_code, iso_code.capitalize())
```

#### 1.3 Create Model Registry
Create `server/app/models/registry.py`:

```python
from typing import Dict, List, Optional
from .base import TranslationModel

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
            available = list(self._models.keys())
            raise ValueError(f"Model '{model_name}' not found. Available: {available}")
        return self._models[model_name]
    
    def list_models(self) -> List[str]:
        """List available model names"""
        return list(self._models.keys())
    
    def get_default_model(self) -> str:
        """Get default model name"""
        return self._default_model
    
    def set_default_model(self, name: str):
        """Set default model"""
        if name not in self._models:
            raise ValueError(f"Model '{name}' not registered")
        self._default_model = name
```

### Phase 2: NLLB Refactoring

#### 2.1 Refactor Existing NLLB Code
Create `server/app/models/nllb_model.py`:

```python
import time
from typing import Dict, List
from ..utils.language_codes import LanguageCodeConverter
from .base import TranslationModel, TranslationRequest, TranslationResponse

class NLLBModel(TranslationModel):
    """NLLB model implementation"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.model_path = config.get('model_path', 'facebook/nllb-200-distilled-600M')
        self.device = config.get('device', 'cpu')
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """Load NLLB model and tokenizer"""
        # Move existing model loading logic from model_loader.py here
        # Make sure to handle errors gracefully
        try:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_path)
            
            if self.device == 'cuda':
                self.model = self.model.cuda()
                
        except Exception as e:
            raise RuntimeError(f"Failed to load NLLB model: {e}")
    
    async def translate(self, request: TranslationRequest) -> TranslationResponse:
        """Translate text using NLLB"""
        start_time = time.time()
        
        # Convert ISO codes to NLLB format
        source_lang = request.source_lang
        if source_lang and source_lang != 'auto':
            source_lang = LanguageCodeConverter.to_model_code(source_lang, 'nllb')
        
        target_lang = LanguageCodeConverter.to_model_code(request.target_lang, 'nllb')
        
        # Handle auto-detection
        detected_source = None
        if not source_lang or source_lang == 'auto':
            detected_source = await self.detect_language(request.text)
            source_lang = LanguageCodeConverter.to_model_code(detected_source, 'nllb')
        
        try:
            # NLLB translation logic (adapt from existing code)
            inputs = self.tokenizer(request.text, return_tensors="pt")
            if self.device == 'cuda':
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            outputs = self.model.generate(
                **inputs,
                forced_bos_token_id=self.tokenizer.lang_code_to_id[target_lang],
                max_length=512
            )
            
            translated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            processing_time = (time.time() - start_time) * 1000
            
            return TranslationResponse(
                translated_text=translated_text,
                detected_source_lang=detected_source,
                processing_time_ms=processing_time,
                model_used=self.model_name,
                metadata={"source_lang_code": source_lang, "target_lang_code": target_lang}
            )
            
        except Exception as e:
            raise RuntimeError(f"NLLB translation failed: {e}")
    
    def get_supported_languages(self) -> List[str]:
        """Return supported ISO language codes"""
        return list(LanguageCodeConverter.NLLB_MAPPING.keys())
    
    async def detect_language(self, text: str) -> str:
        """Detect language using existing logic"""
        # Adapt from existing language_detection.py
        # Return ISO code, not NLLB code
        pass
    
    def is_available(self) -> bool:
        """Check if model is loaded and ready"""
        return self.model is not None and self.tokenizer is not None
    
    def get_model_info(self) -> Dict:
        """Return model metadata"""
        return {
            "name": self.model_name,
            "type": "nllb",
            "model_path": self.model_path,
            "device": self.device,
            "available": self.is_available()
        }
```

### Phase 3: Aya 8B Implementation

#### 3.1 Research Aya 8B Integration
**Your research tasks:**

1. **Understand Aya 8B**:
   - Model: `CohereForAI/aya-23-8B` 
   - Documentation: https://huggingface.co/CohereForAI/aya-23-8B
   - Capabilities: Multilingual text generation, instruction following

2. **Determine Integration Method**:
   - Option A: Hugging Face Transformers (local inference)
   - Option B: API endpoint (if available)
   - Option C: vLLM or similar inference server

3. **Prompt Engineering**:
   - Design translation prompts for Aya
   - Test different prompt formats for best quality
   - Handle language detection via prompting

#### 3.2 Implement Aya Model
Create `server/app/models/aya_model.py`:

```python
import time
import json
from typing import Dict, List
from ..utils.language_codes import LanguageCodeConverter
from .base import TranslationModel, TranslationRequest, TranslationResponse

class AyaModel(TranslationModel):
    """Aya 8B model implementation"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.model_path = config.get('model_path', 'CohereForAI/aya-23-8B')
        self.api_endpoint = config.get('api_endpoint')
        self.max_tokens = config.get('max_tokens', 512)
        self.temperature = config.get('temperature', 0.1)
        
        if self.api_endpoint:
            self._init_api_client()
        else:
            self._init_local_model()
    
    def _init_local_model(self):
        """Initialize local Aya model"""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16,
                device_map="auto"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load Aya model: {e}")
    
    def _init_api_client(self):
        """Initialize API client for Aya"""
        # Implement if using API endpoint
        pass
    
    async def translate(self, request: TranslationRequest) -> TranslationResponse:
        """Translate using Aya 8B"""
        start_time = time.time()
        
        # Build translation prompt
        prompt = self._build_translation_prompt(
            request.text,
            request.source_lang or "auto",
            request.target_lang
        )
        
        try:
            if self.api_endpoint:
                translated_text = await self._translate_via_api(prompt)
            else:
                translated_text = await self._translate_local(prompt)
            
            processing_time = (time.time() - start_time) * 1000
            
            return TranslationResponse(
                translated_text=translated_text,
                detected_source_lang=request.source_lang,  # Aya doesn't separate detection
                processing_time_ms=processing_time,
                model_used=self.model_name,
                metadata={"prompt_used": prompt}
            )
            
        except Exception as e:
            raise RuntimeError(f"Aya translation failed: {e}")
    
    def _build_translation_prompt(self, text: str, source_lang: str, target_lang: str) -> str:
        """Build Aya-specific translation prompt"""
        source_name = LanguageCodeConverter.get_language_name(source_lang) if source_lang != "auto" else "the source language"
        target_name = LanguageCodeConverter.get_language_name(target_lang)
        
        return f"""Translate the following text from {source_name} to {target_name}. Only return the translation, nothing else.

Text to translate: {text}

Translation:"""
    
    async def _translate_local(self, prompt: str) -> str:
        """Translate using local Aya model"""
        inputs = self.tokenizer(prompt, return_tensors="pt")
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.max_tokens,
                temperature=self.temperature,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract just the translation part
        translation = full_response[len(prompt):].strip()
        return translation
    
    async def _translate_via_api(self, prompt: str) -> str:
        """Translate using API endpoint"""
        # Implement API call if using external endpoint
        pass
    
    def get_supported_languages(self) -> List[str]:
        """Return supported ISO language codes"""
        return list(LanguageCodeConverter.AYA_MAPPING.keys())
    
    async def detect_language(self, text: str) -> str:
        """Detect language using Aya"""
        prompt = f"What language is this text written in? Only respond with the language name.\n\nText: {text}\n\nLanguage:"
        
        if self.api_endpoint:
            response = await self._translate_via_api(prompt)
        else:
            response = await self._translate_local(prompt)
        
        # Convert response to ISO code (you'll need to implement this mapping)
        return self._response_to_iso_code(response.strip().lower())
    
    def _response_to_iso_code(self, language_name: str) -> str:
        """Convert language name response to ISO code"""
        name_to_iso = {v.lower(): k for k, v in LanguageCodeConverter.ISO_TO_NAME.items()}
        return name_to_iso.get(language_name, 'en')  # Default to English
    
    def is_available(self) -> bool:
        """Check if model is ready"""
        if self.api_endpoint:
            return True  # Assume API is available
        return hasattr(self, 'model') and self.model is not None
    
    def get_model_info(self) -> Dict:
        """Return model metadata"""
        return {
            "name": self.model_name,
            "type": "aya",
            "model_path": self.model_path,
            "api_endpoint": self.api_endpoint,
            "available": self.is_available()
        }
```

### Phase 4: API Integration

#### 4.1 Update FastAPI Application
Update `server/app/main.py`:

```python
from fastapi import FastAPI, HTTPException, Query
from .models.registry import ModelRegistry
from .models.base import TranslationRequest, TranslationResponse
from .models.nllb_model import NLLBModel
from .models.aya_model import AyaModel
import asyncio

app = FastAPI(title="Multi-Model Translation API")

# Initialize model registry
registry = ModelRegistry()

@app.on_event("startup")
async def startup_event():
    """Initialize models on startup"""
    try:
        # Register NLLB model
        nllb_config = {
            "name": "nllb",
            "model_path": "facebook/nllb-200-distilled-600M",
            "device": "cpu"
        }
        nllb_model = NLLBModel(nllb_config)
        registry.register_model("nllb", nllb_model)
        
        # Register Aya model (configure based on your setup)
        aya_config = {
            "name": "aya",
            "model_path": "CohereForAI/aya-23-8B",
            "max_tokens": 512,
            "temperature": 0.1
        }
        aya_model = AyaModel(aya_config)
        registry.register_model("aya", aya_model)
        
    except Exception as e:
        print(f"Failed to initialize models: {e}")

@app.post("/translate", response_model=TranslationResponse)
async def translate_text(
    request: TranslationRequest,
    model_name: str = Query(None, description="Model to use for translation")
):
    """Translate text using specified or default model"""
    try:
        model = registry.get_model(model_name)
        
        if not model.is_available():
            raise HTTPException(status_code=503, detail=f"Model {model.model_name} is not available")
            
        return await model.translate(request)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

@app.get("/models")
async def list_models():
    """List available translation models"""
    models = []
    for model_name in registry.list_models():
        model = registry.get_model(model_name)
        info = model.get_model_info()
        info['supported_languages'] = model.get_supported_languages()
        models.append(info)
    
    return {
        "models": models,
        "default": registry.get_default_model()
    }

@app.get("/languages")
async def get_supported_languages(model_name: str = Query(None)):
    """Get supported languages for a model"""
    model = registry.get_model(model_name)
    return {
        "model": model.model_name,
        "languages": model.get_supported_languages()
    }

# Maintain backward compatibility
@app.post("/api/translate")
async def legacy_translate(
    text: str,
    source_lang: str = "auto",
    target_lang: str = "en"
):
    """Legacy endpoint for backward compatibility"""
    request = TranslationRequest(
        text=text,
        source_lang=source_lang if source_lang != "auto" else None,
        target_lang=target_lang
    )
    
    # Use NLLB for legacy requests
    model = registry.get_model("nllb")
    response = await model.translate(request)
    
    # Return in legacy format
    return {
        "translated_text": response.translated_text,
        "detected_source": response.detected_source_lang,
        "time_ms": response.processing_time_ms
    }
```

## Implementation Guidelines

### Code Quality Standards
1. **Type Hints**: Use comprehensive type hints throughout
2. **Error Handling**: Graceful error handling with specific exceptions
3. **Async/Await**: Use async patterns for I/O operations
4. **Logging**: Add structured logging for debugging
5. **Tests**: Write unit tests for each component

### Testing Strategy
```python
# Example test structure
def test_nllb_model_translation():
    """Test NLLB model translation"""
    pass

def test_aya_model_translation():
    """Test Aya model translation"""
    pass

def test_model_registry():
    """Test model registry functionality"""
    pass

def test_language_code_conversion():
    """Test language code conversion"""
    pass
```

### Performance Considerations
1. **Lazy Loading**: Load models only when needed
2. **Caching**: Cache model outputs for identical inputs
3. **Async Operations**: Use async for I/O to prevent blocking
4. **Memory Management**: Monitor memory usage with multiple models

### Configuration Example
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
    api_endpoint: null  # Use local model
    max_tokens: 512
    temperature: 0.1
    enabled: true

default_model: "nllb"
```

## Deliverables Checklist

### Phase 1 Deliverables
- [ ] Abstract base classes (`TranslationModel`, `TranslationRequest`, `TranslationResponse`)
- [ ] Language code converter with NLLB and Aya mappings
- [ ] Model registry and factory classes
- [ ] Unit tests for core abstractions

### Phase 2 Deliverables  
- [ ] Refactored NLLB model implementing new interface
- [ ] Backward compatibility maintained
- [ ] All existing tests pass
- [ ] Updated API with model selection

### Phase 3 Deliverables
- [ ] Working Aya 8B model implementation
- [ ] Prompt engineering for optimal translation quality
- [ ] Performance benchmarking against NLLB
- [ ] Integration tests for Aya model

### Phase 4 Deliverables
- [ ] Updated FastAPI application with multi-model support
- [ ] Model listing and selection endpoints
- [ ] Comprehensive error handling
- [ ] Documentation for API changes

## Getting Started

1. **Start with Phase 1**: Create the abstract base classes first
2. **Test Incrementally**: Write tests as you implement each component
3. **Maintain Compatibility**: Ensure existing functionality continues working
4. **Document Changes**: Update API documentation as you progress
5. **Benchmark Performance**: Monitor translation speed and quality

## Questions & Support

If you need clarification on any aspect of this implementation:

1. **Architecture Questions**: Refer to the architecture document for design rationale
2. **Model Integration**: Research Aya 8B documentation and examples
3. **Performance Issues**: Profile code and optimize bottlenecks
4. **Testing Challenges**: Focus on unit tests first, then integration tests

## Success Metrics

Your implementation will be considered successful when:
- [ ] All existing NLLB functionality works unchanged
- [ ] Aya 8B model produces reasonable translations
- [ ] API allows model selection and switching
- [ ] System is easily extensible for new models
- [ ] Performance regression is less than 50%
- [ ] Test coverage is above 80%

Good luck with the implementation! This is a significant architectural change that will make the system much more flexible and future-proof.