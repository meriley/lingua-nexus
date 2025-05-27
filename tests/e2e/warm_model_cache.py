#!/usr/bin/env python3
"""
Model cache warming script for E2E tests.

This script pre-downloads and caches models to speed up subsequent E2E test runs.
Run this before running E2E tests to ensure models are cached locally.
"""

import os
import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_cache_directories():
    """Set up cache directories with proper permissions."""
    cache_dirs = [
        os.path.expanduser("~/.cache/huggingface/transformers"),
        os.path.expanduser("~/.cache/huggingface/datasets"),
        os.path.expanduser("~/.cache/torch"),
    ]
    
    for cache_dir in cache_dirs:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"Cache directory ready: {cache_dir}")
    
    return cache_dirs[0]  # transformers cache

def warm_transformers_cache():
    """Pre-download and cache transformer models."""
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        import torch
        
        # Models to cache for E2E tests
        models_to_cache = [
            "facebook/nllb-200-distilled-600M",  # Primary NLLB model
            # Note: CohereForAI/aya-expanse-8b is a gated model requiring authentication
            # For testing without authentication, you can use CohereForAI/aya-101 instead
        ]
        
        # Check if we should try to cache Aya model
        if os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN"):
            models_to_cache.append("CohereForAI/aya-expanse-8b")
            logger.info("HuggingFace token found - will attempt to cache Aya Expanse 8B")
        else:
            logger.warning("No HuggingFace token found - skipping Aya Expanse 8B (gated model)")
            logger.info("To cache Aya model, set HF_TOKEN environment variable")
        
        for model_name in models_to_cache:
            logger.info(f"Downloading and caching model: {model_name}")
            
            try:
                # Download tokenizer
                logger.info(f"  Downloading tokenizer...")
                tokenizer = AutoTokenizer.from_pretrained(model_name)
                logger.info(f"  ✓ Tokenizer cached")
                
                # Download model files only (don't load into memory)
                logger.info(f"  Downloading model files...")
                try:
                    # Just download the files without loading the model
                    from transformers import AutoConfig
                    config = AutoConfig.from_pretrained(model_name)
                    logger.info(f"  ✓ Model configuration downloaded")
                    
                    # Download model files using snapshot_download
                    from huggingface_hub import snapshot_download
                    cache_path = snapshot_download(
                        repo_id=model_name,
                        cache_dir=os.environ.get('TRANSFORMERS_CACHE'),
                        resume_download=True
                    )
                    logger.info(f"  ✓ Model files cached at: {cache_path}")
                    
                except Exception as download_error:
                    logger.warning(f"  Alternative download method failed: {download_error}")
                    # Fallback: try loading model normally but don't test
                    model = AutoModelForSeq2SeqLM.from_pretrained(
                        model_name,
                        torch_dtype=torch.float32,
                        low_cpu_mem_usage=True
                    )
                    logger.info(f"  ✓ Model downloaded via fallback method")
                    del model
                
                logger.info(f"✓ Model {model_name} successfully cached")
                
                # Clean up tokenizer
                del tokenizer
                
            except Exception as e:
                logger.error(f"Failed to cache model {model_name}: {e}")
                raise
        
        logger.info("All models successfully cached!")
        
    except ImportError as e:
        logger.error(f"Required packages not available: {e}")
        logger.error("Make sure transformers and torch are installed")
        sys.exit(1)

def check_cache_status():
    """Check what models are already cached."""
    cache_dir = os.path.expanduser("~/.cache/huggingface/transformers")
    
    if not os.path.exists(cache_dir):
        logger.info("No cache directory found - will create on first download")
        return
    
    cached_items = list(Path(cache_dir).iterdir())
    logger.info(f"Found {len(cached_items)} items in transformers cache")
    
    # Look for NLLB models specifically
    nllb_items = [item for item in cached_items if 'nllb' in item.name.lower()]
    if nllb_items:
        logger.info(f"Found {len(nllb_items)} NLLB-related cache items:")
        for item in nllb_items:
            size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file()) / (1024**3)
            logger.info(f"  {item.name}: {size:.2f}GB")
    else:
        logger.info("No NLLB models found in cache")

def main():
    """Main cache warming function."""
    logger.info("Starting model cache warming for E2E tests...")
    
    # Set up environment variables for consistent caching
    os.environ['HF_HOME'] = os.path.expanduser("~/.cache/huggingface")
    os.environ['TRANSFORMERS_CACHE'] = os.path.expanduser("~/.cache/huggingface/transformers")
    os.environ['HF_DATASETS_CACHE'] = os.path.expanduser("~/.cache/huggingface/datasets")
    os.environ['TORCH_HOME'] = os.path.expanduser("~/.cache/torch")
    
    # Check current cache status
    check_cache_status()
    
    # Set up cache directories
    cache_dir = setup_cache_directories()
    
    # Warm the cache
    warm_transformers_cache()
    
    # Final status check
    logger.info("\nCache warming complete!")
    check_cache_status()
    
    logger.info(f"\nCache location: {cache_dir}")
    logger.info("You can now run E2E tests with cached models for faster startup.")

if __name__ == "__main__":
    main()