# Connection Reset Solution

## Root Cause Summary

The connection reset errors are caused by **bitsandbytes quantization library missing CUDA dependencies**, not model type issues. The service crashes during Aya model loading when trying to apply 8-bit quantization.

## Specific Error
```
OSError: libcusparse.so.11: cannot open shared object file: No such file or directory
AttributeError: 'NoneType' object has no attribute 'cint8_vector_quant'
```

## Solution Options

### Option 1: Fix CUDA Libraries (Recommended for Production)

1. **Install missing CUDA libraries**:
   ```bash
   # For Ubuntu/Debian
   sudo apt update
   sudo apt install libcusparse-dev-11-8
   
   # Or download directly from NVIDIA
   wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/libcusparse-dev-11-8_11.7.5.86-1_amd64.deb
   sudo dpkg -i libcusparse-dev-11-8_11.7.5.86-1_amd64.deb
   ```

2. **Set LD_LIBRARY_PATH**:
   ```bash
   export LD_LIBRARY_PATH=/usr/local/cuda-11.8/lib64:$LD_LIBRARY_PATH
   ```

3. **Reinstall bitsandbytes**:
   ```bash
   pip uninstall bitsandbytes
   pip install bitsandbytes
   ```

### Option 2: Disable Quantization (Quick Fix)

Modify the Aya model configuration to disable quantization:

```python
# In server/app/models/aya_model.py
def _get_quantization_config(self):
    """Get quantization configuration - DISABLED for compatibility."""
    # Temporarily disable quantization to fix CUDA library issues
    return None
```

Or set environment variable:
```bash
export DISABLE_MODEL_QUANTIZATION=true
```

### Option 3: Use CPU-Only Mode

```bash
export CUDA_VISIBLE_DEVICES=""
export FORCE_CPU_MODE=true
```

## Implementation

### Quick Fix: Disable Quantization

1. **Update AyaModel to handle missing bitsandbytes gracefully**:

```python
# In server/app/models/aya_model.py, modify _get_quantization_config method:

def _get_quantization_config(self):
    """Get quantization configuration based on settings and availability."""
    if not self.use_quantization:
        return None
    
    # Check if bitsandbytes is properly installed
    try:
        import bitsandbytes as bnb
        # Test if CUDA libraries are available
        test_tensor = torch.tensor([1.0], dtype=torch.float16)
        if torch.cuda.is_available():
            # Try a simple bitsandbytes operation to verify it works
            try:
                bnb.functional.int8_vectorwise_quant(test_tensor.cuda())
            except Exception as e:
                logger.warning(f"bitsandbytes CUDA test failed: {e}")
                logger.info("Disabling quantization due to bitsandbytes issues")
                return None
    except ImportError:
        logger.warning("bitsandbytes not available, disabling quantization")
        return None
    except Exception as e:
        logger.warning(f"bitsandbytes validation failed: {e}")
        return None
    
    # Continue with original quantization logic...
```

2. **Add fallback configuration**:

```python
# In model loading section, add fallback
try:
    # Original model loading with quantization
    self.model = AutoModelForCausalLM.from_pretrained(...)
except Exception as e:
    if "bitsandbytes" in str(e) or "cint8_vector_quant" in str(e):
        logger.warning("Quantization failed, retrying without quantization")
        # Retry without quantization
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
            device_map="auto" if self.device != "cpu" else None,
            trust_remote_code=True
        )
    else:
        raise
```

## Test the Fix

After implementing the fix:

```bash
# Test direct model loading
cd tests/debug
HF_TOKEN="your-token" python test_aya_model_fix.py

# Test service integration
cd ../e2e
HF_TOKEN="your-token" python test_basic_e2e.py

# Test full Aya functionality
HF_TOKEN="your-token" pytest test_aya_model_e2e.py -v
```

## Prevention Guidelines

1. **Environment Setup**: Always verify CUDA library compatibility
2. **Graceful Degradation**: Quantization should be optional, not required
3. **Error Handling**: Catch and handle quantization failures gracefully
4. **Documentation**: Document CUDA requirements clearly
5. **Testing**: Test both with and without quantization support

## Performance Impact

- **With Quantization**: ~8GB GPU memory for Aya 8B model
- **Without Quantization**: ~16GB GPU memory for Aya 8B model
- **Fallback to CPU**: Slower inference but works on any system

## Long-term Recommendations

1. **Container Deployment**: Use Docker with properly configured CUDA
2. **Environment Testing**: Add startup checks for all dependencies
3. **Monitoring**: Monitor model loading success rates
4. **Documentation**: Update deployment docs with CUDA requirements

This solution addresses the immediate issue while providing a path for proper CUDA setup in production environments.