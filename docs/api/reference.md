# API Reference Documentation

## Overview

The Multi-Model Translation System provides three distinct API implementations to support different use cases and deployment scenarios. This comprehensive reference covers all **21 endpoints** across the system.

## 🏗️ API Architecture

### **API Implementations**

| Implementation | File | Purpose | Endpoints |
|----------------|------|---------|-----------|
| **Legacy NLLB API** | `app/main.py` | Single NLLB model | 4 endpoints |
| **Multi-Model API** | `app/main_multimodel.py` | Dynamic model management | 8 endpoints |
| **Adaptive API** | `app/adaptive/api_endpoints.py` | AI-powered optimization | 9 endpoints |

### **Base URL Structure**

```
Legacy NLLB API:    http://localhost:8000/
Multi-Model API:    http://localhost:8000/
Adaptive API:       http://localhost:8000/adaptive/
```

## 🔐 Authentication

All endpoints require API key authentication via the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-secret-key" \
     -H "Content-Type: application/json" \
     http://localhost:8000/endpoint
```

### **Rate Limiting**

| Endpoint Category | Rate Limit | Scope |
|-------------------|------------|--------|
| Translation | 10 req/min | Per IP |
| Language Info | 30 req/min | Per IP |
| Model Management | 60 req/min | Per IP |
| Batch Operations | 5 req/min | Per IP |

---

## 📝 Core Translation Endpoints

### **1. Standard Translation**

**Available in:** Multi-Model API, Legacy API

#### **POST /translate**

Translate text using the specified or default model.

**Request:**
```json
{
  "text": "Hello, how are you?",
  "source_lang": "en",
  "target_lang": "ru", 
  "model": "nllb"
}
```

**Parameters:**
- `text` (string, required): Text to translate (1-5000 characters)
- `source_lang` (string, optional): Source language ISO code or "auto" (default: "auto")
- `target_lang` (string, required): Target language ISO code
- `model` (string, optional): Model to use ("nllb", "aya") (Multi-Model only)
- `model_options` (object, optional): Model-specific options (Multi-Model only)

**Response:**
```json
{
  "translated_text": "Привет, как дела?",
  "detected_source_lang": "en",
  "processing_time_ms": 245.3,
  "model_used": "nllb",
  "metadata": {
    "source_lang_name": "English",
    "target_lang_name": "Russian",
    "device": "cuda",
    "confidence_score": 0.95
  }
}
```

**Error Responses:**
- `400`: Invalid input parameters
- `403`: Invalid API key
- `404`: Model not found (Multi-Model only)
- `503`: Model not loaded

---

### **2. Batch Translation**

| **Availability** | Multi-Model API |
|------------------|-----------------|
| **Legacy API** | ❌ Not Supported |
| **Multi-Model API** | ✅ Supported |
| **Adaptive API** | ❌ Not Supported |

#### **POST /translate/batch**

Translate multiple texts in a single request with individual error handling.

**Request:**
```json
[
  {
    "text": "Hello",
    "source_lang": "en",
    "target_lang": "ru",
    "model": "nllb"
  },
  {
    "text": "Goodbye", 
    "source_lang": "en",
    "target_lang": "ru",
    "model": "aya"
  }
]
```

**Parameters:**
- Array of translation requests (max 10 items)
- Each item follows the standard translation request format

**Response:**
```json
{
  "results": [
    {
      "index": 0,
      "success": true,
      "result": {
        "translated_text": "Привет",
        "detected_source_lang": "en",
        "processing_time_ms": 123.4,
        "model_used": "nllb"
      }
    }
  ],
  "errors": [
    {
      "index": 1,
      "success": false,
      "error": "Model 'aya' not loaded",
      "status_code": 404
    }
  ],
  "total_processed": 1,
  "total_errors": 1
}
```

---

### **3. Legacy Compatibility Translation**

| **Availability** | Multi-Model API |
|------------------|-----------------|
| **Legacy API** | ❌ Not Supported |
| **Multi-Model API** | ✅ Supported |
| **Adaptive API** | ❌ Not Supported |

#### **POST /translate/legacy**

Legacy endpoint for backward compatibility with NLLB-only systems.

**Request:**
```json
{
  "text": "Hello world",
  "source_lang": "auto",
  "target_lang": "rus_Cyrl"
}
```

**Parameters:**
- Uses NLLB-specific language codes (`eng_Latn`, `rus_Cyrl`)
- Automatically routes to NLLB model
- Returns legacy response format

**Response:**
```json
{
  "translated_text": "Привет мир",
  "detected_source": "eng_Latn",
  "time_ms": 156
}
```

---

## 🧠 Adaptive Translation Endpoints

### **4. Adaptive Translation**

**Available in:** Adaptive API only

#### **POST /adaptive/translate**

High-quality translation with AI-powered optimization and quality assessment.

**Request:**
```json
{
  "text": "Complex technical documentation requiring precise translation with attention to domain-specific terminology and maintaining coherent structure across multiple paragraphs.",
  "source_lang": "en",
  "target_lang": "ru",
  "api_key": "your-secret-key",
  "user_preference": "quality",
  "force_optimization": true,
  "max_optimization_time": 10.0
}
```

**Parameters:**
- `text` (string, required): Text to translate
- `source_lang` (string, required): Source language ISO code
- `target_lang` (string, required): Target language ISO code  
- `api_key` (string, required): API authentication key
- `user_preference` (string, optional): "fast", "balanced", "quality" (default: "balanced")
- `force_optimization` (boolean, optional): Force optimization regardless of initial quality
- `max_optimization_time` (float, optional): Maximum optimization time in seconds (default: 5.0)

**Response:**
```json
{
  "translation": "Сложная техническая документация, требующая точного перевода с вниманием к доменной терминологии и сохранением связной структуры в нескольких абзацах.",
  "original_text": "Complex technical documentation...",
  "quality_score": 0.92,
  "quality_grade": "A",
  "optimization_applied": true,
  "processing_time": 3.45,
  "cache_hit": false,
  "metadata": {
    "chunks_processed": 3,
    "optimization_strategy": "semantic_enhancement",
    "stage_times": {
      "chunking": 0.12,
      "translation": 2.89,
      "optimization": 0.44
    },
    "chunking_metadata": {
      "chunk_count": 3,
      "content_type": "technical",
      "coherence_score": 0.88
    }
  }
}
```

---

### **5. Progressive Translation**

**Available in:** Adaptive API only

#### **POST /adaptive/translate/progressive**

Real-time streaming translation with progressive quality improvements.

**Request:**
```json
{
  "text": "Long document requiring progressive translation with real-time updates...",
  "source_lang": "en",
  "target_lang": "ru",
  "api_key": "your-secret-key",
  "user_preference": "quality"
}
```

**Response:** Server-Sent Events stream
```
data: {"stage": "semantic", "progress": 0.1, "status_message": "Analyzing document structure"}

data: {"stage": "analyzing", "progress": 0.3, "translation": "Partial translation...", "quality_score": 0.75}

data: {"stage": "optimizing", "progress": 0.7, "translation": "Improved translation...", "quality_score": 0.87}

data: {"stage": "completed", "progress": 1.0, "translation": "Final optimized translation...", "quality_score": 0.93, "quality_grade": "A", "processing_time": 4.2}
```

**Stream Format:**
- **Content-Type**: `text/event-stream`
- **Format**: Server-Sent Events (SSE)
- **Encoding**: JSON objects in `data:` lines

**Update Fields:**
- `stage` (string): Current processing stage
- `progress` (float): Completion percentage (0.0-1.0)
- `translation` (string): Current translation (may be partial)
- `quality_score` (float): Current quality assessment
- `status_message` (string): Human-readable status
- `metadata` (object): Stage-specific information

---

### **6. Semantic Chunking**

**Available in:** Adaptive API only

#### **POST /adaptive/chunk**

Intelligent text segmentation with discourse analysis and content type detection.

**Request:**
```json
{
  "text": "Long document with multiple paragraphs, sections, and complex structure that needs intelligent segmentation for optimal translation quality.",
  "source_lang": "en",
  "target_lang": "ru",
  "min_chunk_size": 150,
  "max_chunk_size": 600
}
```

**Parameters:**
- `text` (string, required): Text to chunk
- `source_lang` (string, optional): Source language code (default: "auto")
- `target_lang` (string, optional): Target language code (default: "en")
- `min_chunk_size` (integer, optional): Minimum chunk size (default: 150)
- `max_chunk_size` (integer, optional): Maximum chunk size (default: 600)

**Response:**
```json
{
  "chunks": [
    "Long document with multiple paragraphs, sections, and complex structure",
    "that needs intelligent segmentation for optimal translation quality."
  ],
  "chunk_boundaries": [[0, 78], [79, 140]],
  "content_type": "technical",
  "coherence_score": 0.87,
  "optimal_size_estimate": 245,
  "metadata": {
    "discourse_markers": ["multiple", "complex", "optimal"],
    "sentence_count": 2,
    "paragraph_count": 1,
    "complexity_score": 0.72,
    "chunking_strategy": "semantic_boundary",
    "processing_time_ms": 45.2
  }
}
```

---

### **7. Quality Assessment**

**Available in:** Adaptive API only

#### **POST /adaptive/quality/assess**

Multi-dimensional translation quality evaluation with detailed analysis.

**Request:**
```json
{
  "original": "The quick brown fox jumps over the lazy dog",
  "translation": "Быстрая коричневая лисица прыгает через ленивую собаку",
  "source_lang": "en",
  "target_lang": "ru"
}
```

**Parameters:**
- `original` (string, required): Original text
- `translation` (string, required): Translated text  
- `source_lang` (string, optional): Source language (default: "auto")
- `target_lang` (string, optional): Target language (default: "en")

**Response:**
```json
{
  "overall_score": 0.94,
  "quality_grade": "A",
  "dimension_scores": {
    "fluency": 0.96,
    "adequacy": 0.92,
    "consistency": 0.95,
    "terminology": 0.93,
    "style": 0.94
  },
  "optimization_needed": false,
  "improvement_suggestions": [
    "Consider using more natural word order",
    "Review domain-specific terminology"
  ],
  "confidence_interval": [0.91, 0.97]
}
```

**Quality Dimensions:**
- **Fluency**: Linguistic naturalness and readability
- **Adequacy**: Semantic preservation and completeness
- **Consistency**: Terminology and style consistency
- **Terminology**: Domain-specific accuracy
- **Style**: Appropriate register and tone

---

## 🤖 Model Management Endpoints

### **8. List Models**

**Available in:** Multi-Model API only

#### **GET /models**

Get comprehensive information about all registered models.

**Response:**
```json
[
  {
    "name": "nllb",
    "type": "nllb",
    "available": true,
    "supported_languages": ["en", "ru", "es", "fr", "de"],
    "device": "cuda:0",
    "model_size": "2.4 GB",
    "metadata": {
      "model_path": "facebook/nllb-200-distilled-600M",
      "quantization_type": "none",
      "max_length": 512,
      "languages_count": 200
    }
  },
  {
    "name": "aya",
    "type": "aya", 
    "available": false,
    "supported_languages": [],
    "device": null,
    "model_size": null,
    "metadata": {
      "error": "Model not loaded"
    }
  }
]
```

---

### **9. Load Model**

**Available in:** Multi-Model API only

#### **POST /models/{model_name}/load**

Dynamically load a specific model with optional configuration.

**Parameters:**
- `model_name` (path): Name of model to load ("nllb", "aya")

**Request:**
```json
{
  "config": {
    "device": "cuda",
    "use_quantization": true,
    "temperature": 0.1
  }
}
```

**Response:**
```json
{
  "message": "Model aya loaded successfully",
  "model_info": {
    "name": "aya",
    "type": "aya",
    "available": true,
    "device": "cuda:0",
    "model_size": "5.1 GB",
    "format": "GGUF",
    "quantization": "Q4_K_M"
  }
}
```

---

### **10. Unload Model**

**Available in:** Multi-Model API only

#### **DELETE /models/{model_name}**

Unload a model to free up memory resources.

**Parameters:**
- `model_name` (path): Name of model to unload

**Response:**
```json
{
  "message": "Model nllb unloaded successfully",
  "memory_freed": "2.4 GB"
}
```

---

## 🌍 Language Information Endpoints

### **11. List Supported Languages (Multi-Model)**

**Available in:** Multi-Model API only

#### **GET /languages**

Get supported languages across all loaded models.

**Response:**
```json
[
  {
    "iso_code": "en",
    "name": "English", 
    "models_supporting": ["nllb", "aya"]
  },
  {
    "iso_code": "ru",
    "name": "Russian",
    "models_supporting": ["nllb", "aya"]
  },
  {
    "iso_code": "zh",
    "name": "Chinese",
    "models_supporting": ["nllb"]
  }
]
```

---

### **12. Model-Specific Languages**

**Available in:** Multi-Model API only

#### **GET /languages/{model_name}**

Get supported languages for a specific model.

**Parameters:**
- `model_name` (path): Model identifier

**Response:**
```json
{
  "model": "aya",
  "supported_languages": ["en", "ru", "es", "fr", "de", "it", "pt"],
  "language_names": {
    "en": "English",
    "ru": "Russian", 
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese"
  }
}
```

---

### **13. Comprehensive Language Metadata (Legacy)**

**Available in:** Legacy API only

#### **GET /languages**

Get comprehensive NLLB language metadata with detailed information.

**Response:**
```json
{
  "languages": [
    {
      "code": "eng_Latn",
      "iso_code": "en",
      "name": "English",
      "script": "Latin",
      "family": "Indo-European",
      "popularity_rank": 1
    }
  ],
  "total_languages": 200,
  "cache_headers": {
    "Cache-Control": "public, max-age=3600",
    "ETag": "lang-metadata-v1-200"
  }
}
```

---

### **14. Individual Language Lookup (Legacy)**

**Available in:** Legacy API only  

#### **GET /languages/{language_code}**

Get detailed metadata for a specific NLLB language.

**Parameters:**
- `language_code` (path): NLLB language code or ISO code

**Response:**
```json
{
  "code": "rus_Cyrl",
  "iso_code": "ru", 
  "name": "Russian",
  "native_name": "русский",
  "script": "Cyrillic",
  "family": "Indo-European",
  "subfamily": "Slavic",
  "popularity_rank": 8,
  "speaker_count": 258000000,
  "countries": ["RU", "BY", "KZ", "KG"]
}
```

---

## 📊 System Monitoring Endpoints

### **15. Multi-Model Health Check**

**Available in:** Multi-Model API only

#### **GET /health**

Comprehensive system health status with model information.

**Response:**
```json
{
  "status": "healthy",
  "models_loaded": 2,
  "models_available": ["nllb", "aya"],
  "device": "cuda",
  "memory_usage": "12.3GB",
  "uptime_seconds": 3600,
  "version": "2.0.0"
}
```

**Status Values:**
- `healthy`: All systems operational
- `degraded`: Some issues but functional  
- `unhealthy`: Critical issues

---

### **16. Legacy Health Check**

**Available in:** Legacy API only

#### **GET /health**

Basic health check for NLLB-only system.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "device": "cuda",
  "memory_usage": "2.4GB"
}
```

---

### **17. Adaptive System Health**

**Available in:** Adaptive API only

#### **GET /adaptive/health**

Health status of adaptive translation components.

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "chunker": true,
    "quality_engine": true, 
    "cache_manager": true,
    "adaptive_controller": true,
    "redis": true
  }
}
```

---

## ⚡ Cache Management Endpoints

### **18. Cache Statistics**

**Available in:** Adaptive API only

#### **GET /adaptive/cache/stats**

Detailed cache performance metrics and statistics.

**Response:**
```json
{
  "hit_rate": 0.847,
  "total_requests": 10000,
  "cache_hits": 8470,
  "cache_misses": 1530,
  "memory_usage": {
    "redis_mb": 512,
    "local_mb": 128,
    "total_mb": 640
  },
  "performance_metrics": {
    "avg_hit_time_ms": 23.4,
    "avg_miss_time_ms": 1247.8,
    "cache_efficiency": 0.91
  },
  "cache_distribution": {
    "quality_high": 3200,
    "quality_medium": 4100,
    "quality_low": 1170
  }
}
```

---

### **19. Cache Invalidation**

**Available in:** Adaptive API only

#### **POST /adaptive/cache/invalidate**

Invalidate cache entries matching specified patterns.

**Parameters:**
- `source_lang` (string, required): Source language to invalidate
- `target_lang` (string, required): Target language to invalidate  
- `content_type` (string, optional): Specific content type to invalidate

**Request:**
```json
{
  "source_lang": "en",
  "target_lang": "ru",
  "content_type": "technical"
}
```

**Response:**
```json
{
  "message": "Cache invalidated for en->ru",
  "entries_removed": 245,
  "memory_freed_mb": 32.1
}
```

---

## 📈 Performance Analytics Endpoints

### **20. System Statistics**

**Available in:** Adaptive API only

#### **GET /adaptive/stats**

Comprehensive system performance analytics.

**Response:**
```json
{
  "performance": {
    "requests_per_minute": 45.2,
    "avg_response_time_ms": 1234.5,
    "success_rate": 0.987,
    "error_rate": 0.013
  },
  "translation_stats": {
    "total_translations": 50000,
    "total_characters": 2500000,
    "avg_quality_score": 0.86,
    "optimization_rate": 0.34
  },
  "model_usage": {
    "nllb": {
      "requests": 30000,
      "avg_time_ms": 456.7,
      "success_rate": 0.991
    },
    "aya": {
      "requests": 20000,
      "avg_time_ms": 1678.3,
      "success_rate": 0.982
    }
  },
  "quality_distribution": {
    "grade_a": 0.42,
    "grade_b": 0.35,
    "grade_c": 0.18,
    "grade_d": 0.04,
    "grade_f": 0.01
  },
  "chunking_analytics": {
    "avg_chunks_per_request": 2.3,
    "avg_chunk_size": 287,
    "content_type_distribution": {
      "narrative": 0.45,
      "technical": 0.32,
      "conversational": 0.23
    }
  },
  "cache_analytics": {
    "hit_rate": 0.847,
    "avg_cache_size_mb": 640,
    "invalidation_rate": 0.05
  }
}
```

---

## 🔍 Error Handling

### **Standard Error Response Format**

All endpoints return consistent error responses:

```json
{
  "detail": "Error description",
  "error_code": "TRANSLATION_FAILED",
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_12345"
}
```

### **HTTP Status Codes**

| Code | Meaning | Common Causes |
|------|---------|---------------|
| **200** | Success | Request completed successfully |
| **400** | Bad Request | Invalid parameters, malformed JSON |
| **401** | Unauthorized | Missing or invalid API key |
| **403** | Forbidden | API key lacks required permissions |
| **404** | Not Found | Model not found, endpoint not found |
| **422** | Validation Error | Parameter validation failed |
| **429** | Too Many Requests | Rate limit exceeded |
| **503** | Service Unavailable | Model not loaded, system overloaded |
| **500** | Internal Server Error | System error, model failure |

### **Error Categories**

#### **Translation Errors**
```json
{
  "detail": "Translation failed: Model timeout",
  "error_code": "TRANSLATION_TIMEOUT",
  "model": "aya",
  "source_lang": "en",
  "target_lang": "ru"
}
```

#### **Model Errors**
```json
{
  "detail": "Model 'aya' not found or not loaded",
  "error_code": "MODEL_NOT_AVAILABLE", 
  "available_models": ["nllb"]
}
```

#### **Validation Errors**
```json
{
  "detail": [
    {
      "loc": ["text"],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.any_str.min_length"
    }
  ],
  "error_code": "VALIDATION_ERROR"
}
```

---

## 🛠️ SDK Examples

### **Python SDK Usage**

```python
import requests
import json
from typing import Dict, List, Optional

class MultiModelTranslationClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        })
    
    def translate(self, text: str, target_lang: str, 
                 source_lang: str = "auto", model: str = "nllb") -> Dict:
        """Standard translation"""
        response = self.session.post(f"{self.base_url}/translate", json={
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "model": model
        })
        response.raise_for_status()
        return response.json()
    
    def batch_translate(self, requests: List[Dict]) -> Dict:
        """Batch translation"""
        response = self.session.post(f"{self.base_url}/translate/batch", 
                                   json=requests)
        response.raise_for_status()
        return response.json()
    
    def adaptive_translate(self, text: str, target_lang: str,
                          source_lang: str = "en", 
                          preference: str = "balanced") -> Dict:
        """High-quality adaptive translation"""
        response = self.session.post(f"{self.base_url}/adaptive/translate", json={
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "api_key": self.api_key,
            "user_preference": preference
        })
        response.raise_for_status()
        return response.json()
    
    def progressive_translate(self, text: str, target_lang: str,
                            source_lang: str = "en"):
        """Progressive translation with streaming"""
        response = self.session.post(f"{self.base_url}/adaptive/translate/progressive",
            json={
                "text": text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "api_key": self.api_key
            },
            stream=True
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line.startswith(b'data: '):
                yield json.loads(line[6:])
    
    def assess_quality(self, original: str, translation: str,
                      source_lang: str = "en", target_lang: str = "ru") -> Dict:
        """Assess translation quality"""
        response = self.session.post(f"{self.base_url}/adaptive/quality/assess", json={
            "original": original,
            "translation": translation,
            "source_lang": source_lang,
            "target_lang": target_lang
        })
        response.raise_for_status()
        return response.json()
    
    def list_models(self) -> List[Dict]:
        """Get available models"""
        response = self.session.get(f"{self.base_url}/models")
        response.raise_for_status()
        return response.json()
    
    def load_model(self, model_name: str, config: Optional[Dict] = None) -> Dict:
        """Load a model"""
        response = self.session.post(f"{self.base_url}/models/{model_name}/load",
                                   json=config or {})
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> Dict:
        """Check system health"""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

# Usage example
client = MultiModelTranslationClient("http://localhost:8000", "your-api-key")

# Basic translation
result = client.translate("Hello world", "ru", model="nllb")
print(result["translated_text"])

# High-quality adaptive translation  
result = client.adaptive_translate(
    "Complex technical documentation requiring precise translation",
    "ru", 
    preference="quality"
)
print(f"Translation: {result['translation']}")
print(f"Quality Score: {result['quality_score']}")

# Progressive translation
for update in client.progressive_translate("Long document text...", "ru"):
    print(f"Stage: {update['stage']}, Progress: {update['progress']:.0%}")
    if update.get('translation'):
        print(f"Current: {update['translation'][:100]}...")
```

### **JavaScript/Node.js SDK Usage**

```javascript
class MultiModelTranslationClient {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.apiKey = apiKey;
  }

  async translate(text, targetLang, sourceLang = 'auto', model = 'nllb') {
    const response = await fetch(`${this.baseUrl}/translate`, {
      method: 'POST',
      headers: {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        text,
        source_lang: sourceLang,
        target_lang: targetLang,
        model
      })
    });
    
    if (!response.ok) {
      throw new Error(`Translation failed: ${response.statusText}`);
    }
    
    return response.json();
  }

  async adaptiveTranslate(text, targetLang, sourceLang = 'en', preference = 'balanced') {
    const response = await fetch(`${this.baseUrl}/adaptive/translate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        text,
        source_lang: sourceLang,
        target_lang: targetLang,
        api_key: this.apiKey,
        user_preference: preference
      })
    });
    
    if (!response.ok) {
      throw new Error(`Adaptive translation failed: ${response.statusText}`);
    }
    
    return response.json();
  }

  async *progressiveTranslate(text, targetLang, sourceLang = 'en') {
    const response = await fetch(`${this.baseUrl}/adaptive/translate/progressive`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        text,
        source_lang: sourceLang,
        target_lang: targetLang,
        api_key: this.apiKey
      })
    });

    if (!response.ok) {
      throw new Error(`Progressive translation failed: ${response.statusText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const update = JSON.parse(line.slice(6));
            yield update;
          } catch (e) {
            console.warn('Failed to parse SSE data:', line);
          }
        }
      }
    }
  }

  async listModels() {
    const response = await fetch(`${this.baseUrl}/models`, {
      headers: { 'X-API-Key': this.apiKey }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to list models: ${response.statusText}`);
    }
    
    return response.json();
  }
}

// Usage example
const client = new MultiModelTranslationClient('http://localhost:8000', 'your-api-key');

// Basic translation
try {
  const result = await client.translate('Hello world', 'ru', 'en', 'nllb');
  console.log('Translation:', result.translated_text);
} catch (error) {
  console.error('Translation error:', error.message);
}

// Progressive translation
try {
  for await (const update of client.progressiveTranslate('Long document...', 'ru')) {
    console.log(`Stage: ${update.stage}, Progress: ${(update.progress * 100).toFixed(0)}%`);
    if (update.translation) {
      console.log('Current translation:', update.translation.slice(0, 100) + '...');
    }
  }
} catch (error) {
  console.error('Progressive translation error:', error.message);
}
```

---

## 🔄 Migration Guide

### **From Legacy to Multi-Model API**

**Legacy Format:**
```json
{
  "text": "Hello", 
  "source_lang": "auto",
  "target_lang": "rus_Cyrl"
}
```

**Multi-Model Format:**
```json
{
  "text": "Hello",
  "source_lang": "auto", 
  "target_lang": "ru",
  "model": "nllb"
}
```

**Key Changes:**
- Language codes: NLLB-specific → ISO 639-1
- Model selection: Implicit → Explicit `model` parameter
- Response format: Legacy fields → Modern structured response

### **Migration Script**

```python
def migrate_request(legacy_request):
    """Convert legacy request to multi-model format"""
    # Language code mapping
    lang_map = {
        'eng_Latn': 'en',
        'rus_Cyrl': 'ru',
        'spa_Latn': 'es',
        'fra_Latn': 'fr'
    }
    
    return {
        'text': legacy_request['text'],
        'source_lang': lang_map.get(legacy_request.get('source_lang', 'auto'), 'auto'),
        'target_lang': lang_map[legacy_request['target_lang']],
        'model': 'nllb'  # Default to NLLB for backward compatibility
    }

def migrate_response(modern_response):
    """Convert modern response to legacy format"""
    return {
        'translated_text': modern_response['translated_text'],
        'detected_source': modern_response.get('detected_source_lang', 'auto'),
        'time_ms': int(modern_response['processing_time_ms'])
    }
```

---

## 📚 Additional Resources

### **OpenAPI Specification**

The complete OpenAPI 3.0 specification is available at:
- **Multi-Model API**: `http://localhost:8000/docs`
- **Interactive Documentation**: `http://localhost:8000/redoc`

### **Postman Collection**

Import the Postman collection for easy testing:
```bash
# Download collection
curl -o translation-api.postman_collection.json \
  https://github.com/yourusername/tg-text-translate/raw/main/docs/api/postman_collection.json
```

### **Rate Limiting Headers**

All responses include rate limiting information:
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7  
X-RateLimit-Reset: 1642262400
```

### **Versioning**

- **Current Version**: v2.0.0 (Multi-Model API)
- **Legacy Version**: v1.0.0 (NLLB-only API)
- **API Versioning**: Header-based (`Accept: application/vnd.api.v2+json`)

---

This comprehensive API reference provides complete documentation for all 21 endpoints across the sophisticated multi-model translation system. For additional support, examples, and integration guides, refer to the main documentation or contact the development team.