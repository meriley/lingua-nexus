# Aya Model Authentication for E2E Tests

## Overview

The Aya Expanse 8B model (`CohereForAI/aya-expanse-8b`) is a gated model on HuggingFace that requires authentication to access.

## Setup Authentication

To enable Aya model testing:

1. **Get a HuggingFace Token**:
   - Go to https://huggingface.co/settings/tokens
   - Create a new token with "Read" permissions
   - Accept the model conditions at https://huggingface.co/CohereForAI/aya-expanse-8b

2. **Set the Token**:
   ```bash
   export HF_TOKEN="your-token-here"
   # or
   export HUGGING_FACE_HUB_TOKEN="your-token-here"
   ```

3. **Run Cache Warming**:
   ```bash
   python tests/e2e/warm_model_cache.py
   ```

## Alternative: Use Open Aya-101

If you don't have access to Aya Expanse 8B, you can use the open-access Aya-101 model instead:

1. Update the model references in test files from:
   ```python
   "CohereForAI/aya-expanse-8b"
   ```
   to:
   ```python
   "CohereForAI/aya-101"
   ```

2. Update the server configuration to use aya-101:
   ```python
   AYA_MODEL="CohereForAI/aya-101"
   ```

## Running Tests Without Aya

The E2E tests are designed to work with just the NLLB model if Aya is not available:

```bash
# Run only NLLB tests
pytest tests/e2e/test_nllb_model_e2e.py -v

# Run single model tests (will skip Aya if not available)
pytest tests/e2e/test_single_model_e2e.py -v -k "nllb"
```

## Troubleshooting

1. **401 Unauthorized Error**: You need to accept the model conditions on HuggingFace
2. **Token Not Working**: Ensure your token has read permissions
3. **Out of Memory**: Aya Expanse 8B requires significant memory (~16GB+)