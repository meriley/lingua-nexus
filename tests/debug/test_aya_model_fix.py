#!/usr/bin/env python3
"""
Test proper Aya model loading using the correct model class.
"""

import os
import gc
import torch
import time
from transformers import AutoTokenizer, AutoModelForCausalLM


def test_aya_with_correct_model_class():
    """Test loading Aya model with the correct AutoModelForCausalLM."""
    print("Testing Aya with Correct Model Class")
    print("=" * 50)
    
    model_name = "CohereForAI/aya-expanse-8b"
    
    # Set HF token
    if "HF_TOKEN" not in os.environ:
        os.environ["HF_TOKEN"] = "test-hf-token-placeholder"
    
    try:
        print("1. Loading tokenizer...")
        start_time = time.time()
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        print(f"   ✓ Tokenizer loaded in {time.time() - start_time:.2f}s")
        
        # Set pad token if needed
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        print("2. Loading model with AutoModelForCausalLM...")
        start_time = time.time()
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
            device_map="auto" if torch.cuda.is_available() else None,
            trust_remote_code=True
        )
        print(f"   ✓ Model loaded in {time.time() - start_time:.2f}s")
        
        print("3. Testing translation with chat template...")
        start_time = time.time()
        
        # Create translation prompt
        messages = [
            {"role": "system", "content": "You are a helpful translation assistant."},
            {"role": "user", "content": "Translate this text from English to Spanish: Hello, how are you?"}
        ]
        
        # Apply chat template
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt")
        
        # Move to device if model is on GPU
        if hasattr(model, 'device'):
            inputs = {k: v.to(model.device) for k, v in inputs.items()}
        
        # Generate response
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=50,
                do_sample=True,
                temperature=0.7,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # Decode response
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"   ✓ Generation completed in {time.time() - start_time:.2f}s")
        print(f"   Full response: {response}")
        
        # Extract just the assistant's response
        if "<|assistant|>" in response:
            assistant_response = response.split("<|assistant|>")[-1].strip()
            print(f"   Translation: {assistant_response}")
        
        print("\n✅ Aya model loading and generation: SUCCESS")
        return True
        
    except Exception as e:
        print(f"\n❌ Aya model test FAILED: {type(e).__name__}: {e}")
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
        except:
            pass


def test_direct_aya_api_usage():
    """Test the Aya model using the project's AyaModel class."""
    print("\n" + "=" * 50)
    print("Testing Project's AyaModel Class")
    print("=" * 50)
    
    import sys
    import os
    
    # Add server path
    server_path = os.path.join(os.path.dirname(__file__), "..", "..", "server")
    sys.path.insert(0, server_path)
    
    try:
        from app.models.aya_model import AyaModel
        from app.models.base import TranslationRequest
        
        print("1. Creating AyaModel instance...")
        config = {
            "model_path": "CohereForAI/aya-expanse-8b",
            "device": "auto",
            "use_quantization": True,
            "load_in_8bit": True,
            "cache_dir": os.path.expanduser("~/.cache/huggingface/transformers"),
        }
        
        # Set HF token
        os.environ["HF_TOKEN"] = "test-hf-token-placeholder"
        
        start_time = time.time()
        aya_model = AyaModel(config)
        print(f"   ✓ AyaModel created in {time.time() - start_time:.2f}s")
        
        print("2. Testing translation...")
        request = TranslationRequest(
            text="Hello, how are you?",
            source_lang="eng",
            target_lang="spa"
        )
        
        start_time = time.time()
        response = aya_model.translate(request)
        print(f"   ✓ Translation completed in {time.time() - start_time:.2f}s")
        print(f"   Result: {response.translated_text}")
        
        print("\n✅ Project AyaModel: SUCCESS")
        return True
        
    except Exception as e:
        print(f"\n❌ Project AyaModel FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test execution."""
    print("Aya Model Compatibility Test")
    print("=" * 60)
    
    # Test 1: Direct model loading with correct class
    test1_success = test_aya_with_correct_model_class()
    
    # Test 2: Project's AyaModel class
    test2_success = test_direct_aya_api_usage()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"  Direct AutoModelForCausalLM: {'✅ SUCCESS' if test1_success else '❌ FAILED'}")
    print(f"  Project AyaModel class:      {'✅ SUCCESS' if test2_success else '❌ FAILED'}")
    
    if test1_success and test2_success:
        print("\n✓ Aya model works correctly - issue is in service integration")
    elif test1_success:
        print("\n⚠️  Direct loading works but project class fails")
    else:
        print("\n✗ Fundamental issue with Aya model loading")


if __name__ == "__main__":
    main()