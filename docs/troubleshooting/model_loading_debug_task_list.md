# Model Loading Connection Reset - Debugging Task List

## Critical Path Tasks (Must Complete in Order)

### Priority 1: Environment Analysis (2 hours)
**Identify compatibility and configuration issues**

1. **TASK-DEBUG-001: Package Compatibility Matrix Check** [30 min]
   - Location: Create `/tests/debug/check_environment.py`
   - Verify PyTorch 2.1.2 + Transformers 4.40.2 compatibility
   - Check tokenizers version compatibility
   - Document CUDA toolkit version and compatibility
   - Success: Clear report of version compatibility status

2. **TASK-DEBUG-002: System Resource Analysis** [30 min]
   - Location: Create `/tests/debug/check_system_resources.py`
   - Check available RAM and swap space
   - Verify GPU memory if CUDA available
   - Check disk space for model cache
   - Success: Resource availability report

3. **TASK-DEBUG-003: Error Pattern Analysis** [1 hour]
   - Location: Document in `/docs/troubleshooting/error_analysis.md`
   - Analyze server logs from failed runs
   - Identify exact point of failure
   - Map connection reset timeline
   - Success: Clear failure pattern documented

### Priority 2: Minimal Reproduction (3 hours)
**Isolate the exact failure point**

4. **TASK-DEBUG-004: Direct Model Loading Test** [1 hour]
   - Location: `/tests/debug/test_direct_model_load.py`
   - Test loading NLLB model directly without service
   - Test transformers pipeline creation
   - Capture any errors or crashes
   - Success: Model loads or specific error identified

5. **TASK-DEBUG-005: Service Without Models Test** [30 min]
   - Location: `/tests/debug/test_service_no_models.py`
   - Start service with models disabled
   - Verify health checks work continuously
   - Success: Service stable without model loading

6. **TASK-DEBUG-006: Incremental Model Loading Test** [1.5 hours]
   - Location: `/tests/debug/test_incremental_loading.py`
   - Load tokenizer only
   - Load model without pipeline
   - Create pipeline separately
   - Success: Identify exact failing component

### Priority 3: Enhanced Debugging (2 hours)
**Add visibility into the failure**

7. **TASK-DEBUG-007: Server-Side Logging Enhancement** [1 hour]
   - Location: Modify `/server/app/models/nllb_model.py`
   - Add detailed exception logging with full traceback
   - Add memory usage logging at each step
   - Add checkpoint logging during initialization
   - Success: Detailed logs showing failure point

8. **TASK-DEBUG-008: Process Monitoring Implementation** [1 hour]
   - Location: `/tests/debug/monitor_service_loading.py`
   - Monitor memory usage during loading
   - Check for OOM killer activation
   - Capture any segmentation faults
   - Success: Resource usage data during failure

### Priority 4: Targeted Fixes (3 hours)
**Implement solutions based on findings**

9. **TASK-DEBUG-009: Memory Optimization Fixes** [1 hour]
   - Location: Update model loading code
   - Implement garbage collection
   - Try different memory settings
   - Test with reduced precision
   - Success: Reduced memory usage verified

10. **TASK-DEBUG-010: Compatibility Fixes** [1 hour]
    - Location: Update package versions
    - Test with transformers 4.36.2
    - Test with different tokenizers version
    - Try CPU-only mode
    - Success: Compatible version set identified

11. **TASK-DEBUG-011: Error Recovery Implementation** [1 hour]
    - Location: Update service startup code
    - Add retry logic for model loading
    - Implement graceful error handling
    - Add model loading timeout
    - Success: Service recovers from loading failures

### Priority 5: Verification (2 hours)
**Ensure fixes work completely**

12. **TASK-DEBUG-012: Basic Test Verification** [30 min]
    - Run `test_basic_e2e.py`
    - Verify health checks work
    - Confirm no connection resets
    - Success: Basic tests pass

13. **TASK-DEBUG-013: Model Loading Test Verification** [30 min]
    - Run NLLB model loading tests
    - Run Aya model loading tests
    - Verify loading times are reasonable
    - Success: Models load successfully

14. **TASK-DEBUG-014: Comprehensive Test Suite Run** [1 hour]
    - Run full NLLB test suite
    - Run full Aya test suite
    - Run multi-model tests
    - Success: All E2E tests pass

### Priority 6: Documentation (1 hour)
**Document findings and solutions**

15. **TASK-DEBUG-015: Root Cause Documentation** [30 min]
    - Location: `/docs/troubleshooting/connection_reset_root_cause.md`
    - Document exact cause of connection resets
    - Explain why the issue occurred
    - Success: Clear explanation of root cause

16. **TASK-DEBUG-016: Solution Documentation** [30 min]
    - Location: `/docs/troubleshooting/connection_reset_solution.md`
    - Document the fix implemented
    - Include prevention guidelines
    - Success: Reproducible solution documented

## Task Dependencies

```
TASK-DEBUG-001 ─┬─→ TASK-DEBUG-004
                └─→ TASK-DEBUG-005

TASK-DEBUG-002 ──→ TASK-DEBUG-008

TASK-DEBUG-003 ──→ TASK-DEBUG-006

TASK-DEBUG-004/005/006 ──→ TASK-DEBUG-007

TASK-DEBUG-007/008 ──→ TASK-DEBUG-009/010/011

TASK-DEBUG-009/010/011 ──→ TASK-DEBUG-012/013/014

TASK-DEBUG-012/013/014 ──→ TASK-DEBUG-015/016
```

## Quick Diagnostic Commands

```bash
# Check system memory
free -h

# Check for OOM killer
dmesg | grep -i "killed process"

# Monitor service memory
ps aux | grep uvicorn

# Check Python package versions
pip list | grep -E "torch|transformers|tokenizers"

# Test direct model import
python -c "from transformers import AutoModelForSeq2SeqLM; print('Import successful')"
```

## Common Issues and Quick Fixes

1. **OOM During Loading**:
   - Add swap space: `sudo fallocate -l 16G /swapfile`
   - Reduce batch size in model config
   - Use `low_cpu_mem_usage=True`

2. **Package Incompatibility**:
   - Downgrade transformers: `pip install transformers==4.36.2`
   - Match tokenizers version: `pip install tokenizers==0.15.0`

3. **CUDA Issues**:
   - Force CPU mode: `export CUDA_VISIBLE_DEVICES=""`
   - Check CUDA version: `nvcc --version`

4. **Process Crashes**:
   - Increase ulimits: `ulimit -n 4096`
   - Check core dumps: `ulimit -c unlimited`

## Time Estimate

- Total estimated time: 13 hours
- Can be parallelized: Some tasks in Priority 3-4
- Critical path: Tasks 1-6, 12-14

## Success Metrics

1. No connection reset errors during model loading
2. Health checks remain responsive throughout
3. Models load within baseline times (NLLB < 5 min, Aya < 60 min)
4. All E2E tests pass without failures
5. Clear documentation of issue and solution