# Connection Reset Root Cause Analysis

## Executive Summary

The E2E test failures and connection reset errors are caused by **incorrect model type usage for the Aya model**. The Aya Expanse 8B model is a Cohere-based causal language model, not a sequence-to-sequence model, but the codebase is trying to load it using `AutoModelForSeq2SeqLM`.

## Root Cause Details

### Primary Issue: Wrong Model Type for Aya
- **Problem**: Code attempts to load `CohereForAI/aya-expanse-8b` using `AutoModelForSeq2SeqLM`
- **Reality**: Aya Expanse 8B is a Cohere model that requires `AutoModelForCausalLM` 
- **Error**: `ValueError: Unrecognized configuration class <class 'transformers.models.cohere.configuration_cohere.CohereConfig'> for this kind of AutoModel: AutoModelForSeq2SeqLM`
- **Impact**: Service crashes during model initialization, causing connection resets

### Secondary Issues Identified

1. **Memory Constraints for Aya Model**
   - Available RAM: 14.1 GB
   - Aya requirement: ~16 GB minimum
   - Status: Borderline - may work with optimization

2. **NLLB Model Loading Works**
   - Direct loading test: ✅ SUCCESS
   - Loads in <1 second
   - Uses 2.3 GB GPU memory
   - Translation works correctly

3. **Service Layer Path Issues**
   - Service manager has hardcoded relative paths
   - Fails when run from different directories
   - Affects test reliability

## Error Timeline

1. **Service Startup**: ✅ Service starts successfully
2. **Health Check Initial**: ✅ Returns healthy status  
3. **Model Loading Begins**: ⚠️ Starts loading models
4. **Aya Model Loading**: ❌ Crashes with ValueError
5. **Service Process Dies**: ❌ Connection reset occurs
6. **Health Checks Fail**: ❌ Connection refused

## Evidence

### Direct Model Loading Test Results
```
NLLB: ✅ SUCCESS
- Tokenizer: 0.74s
- Model: 0.95s  
- Pipeline: 3.73s
- Translation: 0.43s ("Hello world" → "Hola mundo")

Aya: ❌ FAILED
- Tokenizer: ✅ 1.33s
- Model: ❌ ValueError (wrong AutoModel type)
```

### System Resources
```
RAM: 14.1 GB available (sufficient for NLLB, borderline for Aya)
GPU: 8.9 GB free (sufficient for both models)
Swap: 4 GB available
```

### Package Compatibility
```
PyTorch: 2.1.2+cu118 ✅
Transformers: 4.40.2 ✅ 
Tokenizers: 0.19.1 ✅
No critical compatibility issues
```

## Impact Assessment

- **NLLB Model**: Fully functional, no issues
- **Aya Model**: Completely broken due to wrong model class
- **Multi-model Service**: Crashes when Aya is included
- **E2E Tests**: Fail when testing Aya functionality
- **Production Risk**: High - service crashes under Aya load

## Next Steps

1. **Immediate Fix**: Update Aya model loading to use `AutoModelForCausalLM`
2. **Architecture Fix**: Implement separate handling for causal vs seq2seq models
3. **Memory Optimization**: Add memory management for large models
4. **Service Robustness**: Add error recovery for model loading failures
5. **Path Fixes**: Make service manager work from any directory

## Lessons Learned

1. **Model Architecture Matters**: Cannot assume all models are seq2seq
2. **Direct Testing Essential**: Service layer can mask underlying issues
3. **Resource Monitoring Critical**: Memory constraints cause subtle failures
4. **Error Isolation Important**: Test components independently

This analysis shows the issue is **architectural** (wrong model type) rather than **environmental** (memory, packages, etc.).