# TG-Text-Translate API Endpoint Inventory

## Overview

The TG-Text-Translate system provides three distinct API implementations with sophisticated translation capabilities:

1. **Legacy NLLB API** (`main.py`) - Original single-model implementation
2. **Multi-Model API** (`main_multimodel.py`) - Modern multi-model architecture
3. **Adaptive Translation API** (`adaptive/api_endpoints.py`) - AI-powered optimization system

## Authentication

All endpoints require API key authentication via header:
```
X-API-Key: your-api-key-here
```

Default development key: `development-key`

## Rate Limiting

- Standard endpoints: 10-60 requests/minute
- Language metadata: 30 requests/minute  
- Batch operations: 5 requests/minute
- Health checks: Unlimited

---

## Core Translation Endpoints

### 1. Legacy Translation
**Endpoint:** `POST /translate`  
**Implementation:** Legacy NLLB API  
**Rate Limit:** 10/minute

#### Request Model
```json
{
  "text": "string (1-5000 chars, required)",
  "source_lang": "string (optional, default: 'auto')",
  "target_lang": "string (required)"
}
```

#### Response Model
```json
{
  "translated_text": "string",
  "detected_source": "string",
  "time_ms": "integer"
}
```

#### Features
- Auto language detection
- NLLB-200 model translation
- Processing time tracking
- Error handling with detailed messages

---

### 2. Multi-Model Translation
**Endpoint:** `POST /translate`  
**Implementation:** Multi-Model API  
**Rate Limit:** 10/minute

#### Request Model
```json
{
  "text": "string (1-5000 chars, required)",
  "source_lang": "string (optional, default: 'auto')",
  "target_lang": "string (required)",
  "model": "string (optional, default: 'nllb')",
  "model_options": "object (optional)"
}
```

#### Response Model
```json
{
  "translated_text": "string",
  "detected_source_lang": "string",
  "processing_time_ms": "float",
  "model_used": "string",
  "metadata": "object"
}
```

#### Supported Models
- `nllb` - NLLB-200 multilingual model
- `aya` - Aya Expanse 8B instruction-following model
- Additional models configurable via registry

---

### 3. Batch Translation
**Endpoint:** `POST /translate/batch`  
**Implementation:** Multi-Model API  
**Rate Limit:** 5/minute

#### Request Model
```json
[
  {
    "text": "string",
    "source_lang": "string",
    "target_lang": "string",
    "model": "string"
  }
]
```

#### Response Model
```json
{
  "results": [
    {
      "index": "integer",
      "success": "boolean",
      "result": "TranslationResponse"
    }
  ],
  "errors": [
    {
      "index": "integer", 
      "success": "boolean",
      "error": "string",
      "status_code": "integer"
    }
  ],
  "total_processed": "integer",
  "total_errors": "integer"
}
```

#### Features
- Process up to 10 translations simultaneously
- Individual error handling per request
- Atomic operation with rollback support

---

### 4. Legacy Compatibility
**Endpoint:** `POST /translate/legacy`  
**Implementation:** Multi-Model API  
**Rate Limit:** 10/minute

#### Purpose
Provides backward compatibility for legacy client applications.

#### Features
- Accepts legacy request format
- Returns legacy response format
- Automatically routes to NLLB model
- Transparent format conversion

---

## Adaptive Translation Endpoints

### 5. Adaptive Translation
**Endpoint:** `POST /adaptive/translate`  
**Implementation:** Adaptive API  
**Rate Limit:** 10/minute

#### Request Model
```json
{
  "text": "string (required)",
  "source_lang": "string (required)",
  "target_lang": "string (required)",
  "api_key": "string (required)",
  "user_preference": "string (optional: 'fast', 'balanced', 'quality')",
  "force_optimization": "boolean (optional)",
  "max_optimization_time": "float (optional, default: 5.0)"
}
```

#### Response Model
```json
{
  "translation": "string",
  "original_text": "string",
  "quality_score": "float",
  "quality_grade": "string",
  "optimization_applied": "boolean",
  "processing_time": "float",
  "cache_hit": "boolean",
  "metadata": "object"
}
```

#### Features
- AI-powered quality optimization
- Intelligent caching
- Performance preference tuning
- Real-time quality assessment

---

### 6. Progressive Translation
**Endpoint:** `POST /adaptive/translate/progressive`  
**Implementation:** Adaptive API  
**Rate Limit:** 5/minute

#### Response Type
Server-Sent Events (SSE) stream

#### Event Format
```json
{
  "stage": "string",
  "translation": "string",
  "progress": "float",
  "status_message": "string",
  "quality_score": "float",
  "quality_grade": "string",
  "metadata": "object"
}
```

#### Features
- Real-time translation updates
- Progressive quality improvement
- Stage-by-stage progress tracking
- WebSocket-like experience over HTTP

---

### 7. Semantic Chunking
**Endpoint:** `POST /adaptive/chunk`  
**Implementation:** Adaptive API  
**Rate Limit:** 30/minute

#### Request Model
```json
{
  "text": "string (required)",
  "source_lang": "string (default: 'auto')",
  "target_lang": "string (default: 'en')",
  "min_chunk_size": "integer (default: 150)",
  "max_chunk_size": "integer (default: 600)"
}
```

#### Response Model
```json
{
  "chunks": ["string"],
  "chunk_boundaries": ["tuple"],
  "content_type": "string",
  "coherence_score": "float",
  "optimal_size_estimate": "integer",
  "metadata": "object"
}
```

#### Features
- AI-powered semantic analysis
- Content type detection
- Coherence scoring
- Optimal chunk size recommendations

---

### 8. Quality Assessment
**Endpoint:** `POST /adaptive/quality/assess`  
**Implementation:** Adaptive API  
**Rate Limit:** 30/minute

#### Request Model
```json
{
  "original": "string (required)",
  "translation": "string (required)",
  "source_lang": "string (default: 'auto')",
  "target_lang": "string (default: 'en')"
}
```

#### Response Model
```json
{
  "overall_score": "float",
  "quality_grade": "string",
  "dimension_scores": "object",
  "optimization_needed": "boolean",
  "improvement_suggestions": ["string"],
  "confidence_interval": "tuple"
}
```

#### Quality Dimensions
- Fluency
- Adequacy
- Coherence
- Cultural appropriateness
- Technical accuracy

---

## Model Management Endpoints

### 9. List Models
**Endpoint:** `GET /models`  
**Implementation:** Multi-Model API  
**Rate Limit:** 30/minute

#### Response Model
```json
[
  {
    "name": "string",
    "type": "string",
    "available": "boolean",
    "supported_languages": ["string"],
    "device": "string",
    "model_size": "string",
    "metadata": "object"
  }
]
```

#### Features
- Real-time model status
- Device allocation information
- Language support details
- Memory usage statistics

---

### 10. Load Model
**Endpoint:** `POST /models/{model_name}/load`  
**Implementation:** Multi-Model API  
**Rate Limit:** 5/minute

#### Response Model
```json
{
  "message": "string"
}
```

#### Features
- Dynamic model loading
- Resource allocation management
- Load balancing support
- Error recovery mechanisms

---

### 11. Unload Model
**Endpoint:** `DELETE /models/{model_name}`  
**Implementation:** Multi-Model API  
**Rate Limit:** 5/minute

#### Features
- Memory cleanup
- Resource deallocation
- Graceful shutdown
- Service continuity

---

## Language Information Endpoints

### 12. Language Metadata (Legacy)
**Endpoint:** `GET /languages`  
**Implementation:** Legacy NLLB API  
**Rate Limit:** 30/minute

#### Response Model
```json
{
  "languages": ["object"],
  "families": "object",
  "popular": ["string"],
  "popular_pairs": ["tuple"],
  "total_count": "integer",
  "cache_headers": "object"
}
```

#### Features
- Comprehensive NLLB language support
- Language family organization
- Popular language shortcuts
- Caching optimization

---

### 13. Multi-Model Language Support
**Endpoint:** `GET /languages`  
**Implementation:** Multi-Model API  
**Rate Limit:** 30/minute

#### Response Model
```json
[
  {
    "iso_code": "string",
    "name": "string",
    "models_supporting": ["string"]
  }
]
```

#### Features
- Cross-model language support
- ISO 639-1 standardization
- Model compatibility matrix
- Real-time availability

---

### 14. Model-Specific Languages
**Endpoint:** `GET /languages/{model_name}`  
**Implementation:** Multi-Model API  
**Rate Limit:** 60/minute

#### Response Model
```json
{
  "model": "string",
  "supported_languages": ["string"],
  "language_names": "object"
}
```

#### Features
- Model-specific language lists
- Human-readable language names
- Bi-directional support validation

---

### 15. Individual Language Info
**Endpoint:** `GET /languages/{language_code}`  
**Implementation:** Legacy NLLB API  
**Rate Limit:** 60/minute

#### Response Model
```json
{
  "code": "string",
  "name": "string",
  "native_name": "string",
  "family": "string",
  "script": "string",
  "popular": "boolean",
  "region": "string",
  "rtl": "boolean"
}
```

#### Features
- Detailed language metadata
- Script and writing direction
- Regional classification
- Popularity indicators

---

## System Monitoring Endpoints

### 16. Health Check (Legacy)
**Endpoint:** `GET /health`  
**Implementation:** Legacy NLLB API  
**Rate Limit:** Unlimited

#### Response Model
```json
{
  "status": "string",
  "model_loaded": "boolean",
  "device": "string",
  "memory_usage": "string"
}
```

---

### 17. Health Check (Multi-Model)
**Endpoint:** `GET /health`  
**Implementation:** Multi-Model API  
**Rate Limit:** Unlimited

#### Response Model
```json
{
  "status": "string",
  "models_loaded": "integer",
  "models_available": ["string"],
  "device": "string",
  "memory_usage": "string"
}
```

---

### 18. Adaptive System Health
**Endpoint:** `GET /adaptive/health`  
**Implementation:** Adaptive API  
**Rate Limit:** Unlimited

#### Response Model
```json
{
  "status": "string",
  "components": {
    "chunker": "boolean",
    "quality_engine": "boolean",
    "cache_manager": "boolean",
    "adaptive_controller": "boolean",
    "redis": "boolean"
  }
}
```

#### Features
- Component-level health monitoring
- Redis connectivity status
- Service degradation detection
- Automated failover support

---

## Cache Management Endpoints

### 19. Cache Statistics
**Endpoint:** `GET /adaptive/cache/stats`  
**Implementation:** Adaptive API  
**Rate Limit:** 30/minute

#### Response Model
```json
{
  "hit_rate": "float",
  "total_requests": "integer",
  "cache_hits": "integer",
  "cache_misses": "integer",
  "memory_usage": "object"
}
```

#### Features
- Real-time cache performance
- Hit/miss ratio tracking
- Memory usage monitoring
- Performance optimization insights

---

### 20. Cache Invalidation
**Endpoint:** `POST /adaptive/cache/invalidate`  
**Implementation:** Adaptive API  
**Rate Limit:** 10/minute

#### Parameters
- `source_lang`: Source language code
- `target_lang`: Target language code  
- `content_type`: Optional content type filter

#### Features
- Selective cache clearing
- Pattern-based invalidation
- Model update support
- Performance impact mitigation

---

### 21. System Statistics
**Endpoint:** `GET /adaptive/stats`  
**Implementation:** Adaptive API  
**Rate Limit:** 30/minute

#### Response Model
```json
{
  "translation_count": "integer",
  "average_quality_score": "float",
  "optimization_success_rate": "float",
  "cache_performance": "object",
  "model_usage_stats": "object",
  "performance_metrics": "object"
}
```

#### Features
- Comprehensive system analytics
- Performance trend analysis
- Model utilization statistics
- Quality improvement tracking

---

## Error Handling

### Standard Error Responses

#### 400 Bad Request
```json
{
  "detail": "string",
  "validation_errors": ["object"]
}
```

#### 403 Forbidden
```json
{
  "detail": "Invalid API Key"
}
```

#### 429 Rate Limit Exceeded
```json
{
  "detail": "Rate limit exceeded"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "string",
  "error_code": "string"
}
```

#### 503 Service Unavailable
```json
{
  "detail": "Model not loaded yet",
  "retry_after": "integer"
}
```

### Model-Specific Errors

#### Translation Errors
- `UnsupportedLanguageError`: Language not supported by model
- `TranslationError`: Translation operation failed
- `LanguageDetectionError`: Auto-detection failed

#### System Errors
- `ModelInitializationError`: Model failed to load
- `CacheError`: Cache operation failed
- `QualityAssessmentError`: Quality analysis failed

---

## Integration Examples

### Basic Translation
```python
import requests

response = requests.post(
    "http://localhost:8000/translate",
    headers={"X-API-Key": "your-key"},
    json={
        "text": "Hello, world!",
        "source_lang": "en",
        "target_lang": "es"
    }
)
```

### Multi-Model Translation
```python
response = requests.post(
    "http://localhost:8000/translate",
    headers={"X-API-Key": "your-key"},
    json={
        "text": "Hello, world!",
        "source_lang": "en", 
        "target_lang": "es",
        "model": "aya",
        "model_options": {"temperature": 0.7}
    }
)
```

### Adaptive Translation
```python
response = requests.post(
    "http://localhost:8000/adaptive/translate",
    headers={"X-API-Key": "your-key"},
    json={
        "text": "Complex technical documentation...",
        "source_lang": "en",
        "target_lang": "es", 
        "api_key": "your-key",
        "user_preference": "quality",
        "force_optimization": True
    }
)
```

### Progressive Translation (SSE)
```python
import requests

with requests.post(
    "http://localhost:8000/adaptive/translate/progressive",
    headers={"X-API-Key": "your-key"},
    json={...},
    stream=True
) as response:
    for line in response.iter_lines():
        if line.startswith(b'data: '):
            event = json.loads(line[6:])
            print(f"Stage: {event['stage']}, Progress: {event['progress']}")
```

---

## Performance Characteristics

### Response Times
- Simple translation: 100-500ms
- Multi-model translation: 200-800ms
- Adaptive translation: 500-2000ms
- Progressive translation: Real-time streaming

### Throughput
- Legacy API: ~100 requests/minute
- Multi-model API: ~80 requests/minute  
- Adaptive API: ~40 requests/minute
- Batch processing: ~200 texts/minute

### Resource Usage
- Memory: 2-8GB per model
- GPU Memory: 4-12GB per model
- CPU: 2-8 cores recommended
- Storage: 1-5GB per model

---

## Deployment Considerations

### Docker Configuration
```yaml
services:
  translation-api:
    image: tg-text-translate:latest
    environment:
      - MODELS_TO_LOAD=nllb,aya
      - API_KEY=your-production-key
      - REDIS_URL=redis://redis:6379
    ports:
      - "8000:8000"
```

### Load Balancing
- Use sticky sessions for progressive translation
- Distribute model loading across instances
- Configure Redis for shared caching

### Monitoring
- Health check endpoints for load balancer
- Prometheus metrics integration
- Custom alerting for model failures

This comprehensive inventory provides a complete reference for integrating with the TG-Text-Translate API ecosystem, covering all implementations and their sophisticated capabilities.