#!/usr/bin/env python3
"""
Test direct model loading without service to isolate failure points.
"""

import os
import gc
import torch
import time
import psutil
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline


def log_memory_usage(stage: str):
    """Log current memory usage."""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    virtual_memory = psutil.virtual_memory()
    
    print(f"[{stage}] Memory Usage:")
    print(f"  Process RSS: {memory_info.rss / 1024**3:.2f} GB")
    print(f"  System Available: {virtual_memory.available / 1024**3:.2f} GB")
    if torch.cuda.is_available():
        print(f"  GPU Memory: {torch.cuda.memory_allocated() / 1024**3:.2f} GB allocated")
        print(f"  GPU Memory: {torch.cuda.memory_reserved() / 1024**3:.2f} GB reserved")


def test_nllb_direct_loading():
    """Test loading NLLB model directly."""
    print("\n" + "="*50)
    print("Testing NLLB Direct Model Loading")
    print("="*50)
    
    model_name = "facebook/nllb-200-distilled-600M"
    
    try:
        log_memory_usage("Initial")
        
        # Step 1: Load tokenizer
        print("\n1. Loading tokenizer...")
        start_time = time.time()
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        print(f"   ✓ Tokenizer loaded in {time.time() - start_time:.2f}s")
        log_memory_usage("After tokenizer")
        
        # Step 2: Load model
        print("\n2. Loading model...")
        start_time = time.time()
        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=True
        )
        print(f"   ✓ Model loaded in {time.time() - start_time:.2f}s")
        log_memory_usage("After model")
        
        # Step 3: Create pipeline
        print("\n3. Creating pipeline...")
        start_time = time.time()
        translator = pipeline(
            "translation",
            model=model,
            tokenizer=tokenizer,
            device=0 if torch.cuda.is_available() else -1
        )
        print(f"   ✓ Pipeline created in {time.time() - start_time:.2f}s")
        log_memory_usage("After pipeline")
        
        # Step 4: Test translation
        print("\n4. Testing translation...")
        start_time = time.time()
        result = translator("Hello world", src_lang="eng_Latn", tgt_lang="spa_Latn")
        print(f"   ✓ Translation completed in {time.time() - start_time:.2f}s")
        print(f"   Result: {result}")
        log_memory_usage("After translation")
        
        print("\n✅ NLLB direct loading: SUCCESS")
        return True
        
    except Exception as e:
        print(f"\n❌ NLLB direct loading FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        try:
            del translator, model, tokenizer
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            log_memory_usage("After cleanup")
        except:
            pass


def test_aya_direct_loading():
    """Test loading Aya model directly."""
    print("\n" + "="*50)
    print("Testing Aya Direct Model Loading")
    print("="*50)
    
    model_name = "CohereForAI/aya-expanse-8b"
    
    # Set HF token
    if "HF_TOKEN" not in os.environ:
        os.environ["HF_TOKEN"] = "test-hf-token-placeholder"
    
    try:
        log_memory_usage("Initial")
        
        # Step 1: Load tokenizer
        print("\n1. Loading tokenizer...")
        start_time = time.time()
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        print(f"   ✓ Tokenizer loaded in {time.time() - start_time:.2f}s")
        log_memory_usage("After tokenizer")
        
        # Step 2: Load model with memory optimization
        print("\n2. Loading model (this may take several minutes)...")
        start_time = time.time()
        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,  # Use half precision
            low_cpu_mem_usage=True,
            device_map="auto" if torch.cuda.is_available() else None
        )
        print(f"   ✓ Model loaded in {time.time() - start_time:.2f}s")
        log_memory_usage("After model")
        
        # Step 3: Test simple generation
        print("\n3. Testing simple generation...")
        start_time = time.time()
        inputs = tokenizer("Hello world", return_tensors="pt")
        with torch.no_grad():
            outputs = model.generate(**inputs, max_length=20)
        result = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"   ✓ Generation completed in {time.time() - start_time:.2f}s")
        print(f"   Result: {result}")
        log_memory_usage("After generation")
        
        print("\n✅ Aya direct loading: SUCCESS")
        return True
        
    except Exception as e:
        print(f"\n❌ Aya direct loading FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        try:
            del model, tokenizer
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            log_memory_usage("After cleanup")
        except:
            pass


def main():
    """Main test execution."""
    print("Direct Model Loading Test")
    print("=" * 60)
    
    # Test NLLB first (smaller model)
    nllb_success = test_nllb_direct_loading()
    
    # Only test Aya if we have enough memory
    available_gb = psutil.virtual_memory().available / (1024**3)
    if available_gb >= 12.0:  # Reduced requirement
        aya_success = test_aya_direct_loading()
    else:
        print(f"\n⚠️  Skipping Aya test: Only {available_gb:.1f}GB available, need 12GB+")
        aya_success = None
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"  NLLB: {'✅ SUCCESS' if nllb_success else '❌ FAILED'}")
    if aya_success is not None:
        print(f"  Aya:  {'✅ SUCCESS' if aya_success else '❌ FAILED'}")
    else:
        print(f"  Aya:  ⏭️  SKIPPED (insufficient memory)")
    
    if nllb_success:
        print("\n✓ Basic model loading works - issue may be in service layer")
    else:
        print("\n✗ Model loading fails even directly - compatibility issue")


if __name__ == "__main__":
    main()