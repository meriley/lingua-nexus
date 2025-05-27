# Aya Model Integration Fix Architecture

## Overview
This document outlines the architectural approach to fix the Aya model integration issues in the multi-model translation system following the SPARC framework.

## Current State
- NLLB model: ✅ Working
- Aya model: ❌ Failing with `torch.get_default_device` error
- Authentication: ✅ HuggingFace token configured
- Dependencies: ⚠️ Partial compatibility issues

## Problem Analysis

### Root Causes
1. **PyTorch API Mismatch**: Code uses `torch.get_default_device` which doesn't exist in PyTorch 2.1
2. **Model Loading Strategy**: Current implementation may not align with Cohere's model requirements
3. **Memory Management**: 8B parameter model requires careful resource allocation
4. **Quantization Configuration**: May need specific setup for Aya model

### Technical Debt
- Hardcoded model configurations
- Lack of compatibility abstraction layer
- Missing comprehensive error handling
- No model-specific health checks

## Proposed Architecture

### 1. Compatibility Layer
Create abstraction for PyTorch version differences:

```
/server/app/utils/
├── model_compat.py      # PyTorch/Transformers compatibility
├── device_manager.py    # Device selection and memory management
└── __init__.py
```

### 2. Model Loading Pipeline
```
[Request] → [Model Registry] → [Compatibility Check] → [Resource Allocation]
                                        ↓
                            [Model Loader] ← [Config Validator]
                                        ↓
                            [Health Check] → [Ready State]
```

### 3. Component Interactions
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Model Registry │────▶│ Aya Model Loader │────▶│ Transformer API │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │                         │
         ▼                       ▼                         ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Config Manager  │     │ Device Manager   │     │ Memory Monitor  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Implementation Design

### Phase 1: Compatibility Foundation
1. Create device management abstraction
2. Implement model loading wrappers
3. Add configuration validation

### Phase 2: Aya Model Refactor
1. Update model initialization
2. Implement proper error handling
3. Add quantization support

### Phase 3: Integration & Testing
1. Update Docker configuration
2. Add comprehensive tests
3. Implement monitoring

## Technical Specifications

### Device Management Module
```python
# app/utils/device_manager.py
class DeviceManager:
    """Manages device selection and memory allocation"""
    
    @staticmethod
    def get_optimal_device(model_size_gb: float, 
                          prefer_gpu: bool = True) -> torch.device:
        """Select optimal device based on available resources"""
        
    @staticmethod
    def check_memory_availability(required_gb: float) -> bool:
        """Verify sufficient memory is available"""
        
    @staticmethod
    def get_device_map(model_config: dict) -> dict:
        """Create device map for model parallelism"""
```

### Model Configuration Schema
```yaml
aya_model:
  model_path: "CohereLabs/aya-expanse-8b"
  model_type: "causal_lm"
  device_strategy: "auto"
  memory_limit_gb: 12
  quantization:
    enabled: true
    bits: 8
    compute_dtype: "float16"
  loading_params:
    trust_remote_code: true
    use_flash_attention_2: false
    torch_dtype: "auto"
```

### Error Handling Strategy
```python
class AyaModelError(Exception):
    """Base exception for Aya model errors"""

class AyaLoadingError(AyaModelError):
    """Raised when model fails to load"""

class AyaInferenceError(AyaModelError):
    """Raised during inference failures"""
```

## Resource Requirements

### Memory Allocation
- Base model: ~16GB (FP16)
- Quantized model: ~8GB (INT8)
- Inference overhead: ~2GB
- Total recommended: 24GB GPU RAM

### Compute Requirements
- GPU: NVIDIA RTX 3090 or better
- CUDA: 11.8+
- CPU fallback: 32GB+ RAM

## Testing Strategy

### Unit Tests
- Device selection logic
- Configuration validation
- Error handling paths

### Integration Tests
- Model loading with various configs
- Memory limit enforcement
- Fallback mechanisms

### Performance Tests
- Loading time benchmarks
- Inference latency
- Memory usage patterns

## Deployment Considerations

### Docker Updates
- Base image: pytorch/pytorch:2.1.2-cuda11.8-cudnn8-runtime
- Additional packages: git-lfs, einops, bitsandbytes
- Environment variables for configuration

### Monitoring
- Model loading status
- Memory usage metrics
- Inference performance
- Error rates

## Risk Assessment

### High Priority Risks
1. Memory exhaustion during model loading
2. Incompatible model format
3. CUDA/PyTorch version conflicts

### Mitigation Strategies
1. Implement staged loading with checkpoints
2. Add model format validation
3. Test on multiple PyTorch versions

## Success Metrics
- Aya model loads successfully in < 2 minutes
- Translation latency < 2 seconds
- Memory usage stays within limits
- Zero model loading failures after fixes

## Dependencies
- PyTorch 2.1.2+
- Transformers 4.40.0+
- CUDA 11.8+
- HuggingFace Hub authentication