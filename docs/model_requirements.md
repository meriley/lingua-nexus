# Meta AI NLLB Model Requirements

This document outlines the requirements and configuration for the NLLB (No Language Left Behind) translation model used in the Telegram Translation System.

## Overview

NLLB is Meta's multilingual translation model capable of translating across 200 languages. It provides high-quality translations directly between any pair of supported languages, including low-resource languages. Our system uses NLLB to provide translation capabilities in Telegram.

## Model Variants

NLLB is available in several variants with different sizes and capabilities:

1. **NLLB-200-3.3B**: The full model with 3.3 billion parameters, offering maximum translation quality.
2. **NLLB-200-1.3B**: Medium-sized model with 1.3 billion parameters.
3. **NLLB-200-distilled-600M**: Distilled model with 600 million parameters, providing a good balance of performance and efficiency.

For our server implementation, we recommend the distilled model (`facebook/nllb-200-distilled-600M`) as it provides a good balance between translation quality and resource usage.

## Hardware Requirements

The hardware requirements depend on the model size:

| Model | CPU Memory | GPU Memory | Storage |
|-------|------------|------------|---------|
| NLLB-200-3.3B | 16GB+ | 12GB+ | 15GB |
| NLLB-200-1.3B | 8GB+ | 6GB+ | 6GB |
| NLLB-200-distilled-600M | 4GB+ | 2GB+ | 3GB |

For optimal performance:
- Use a CUDA-capable GPU with at least 4GB of VRAM
- Have at least 8GB of RAM
- SSD storage is recommended for faster model loading

## Software Requirements

- Python 3.8 or later
- PyTorch 1.10 or later
- Transformers 4.18.0 or later
- FastAPI (for the server component)
- CUDA 11.3+ and cuDNN (for GPU acceleration)

## Installation

The model can be installed using Hugging Face's Transformers library:

```bash
pip install torch transformers sentencepiece
```

For our server implementation, additional dependencies are required:

```bash
pip install fastapi uvicorn slowapi
```

## Loading the Model

The model should be loaded at server startup:

```python
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

# Load model and tokenizer
model = AutoModelForSeq2SeqLM.from_pretrained("facebook/nllb-200-distilled-600M")
tokenizer = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M")

# Move to GPU if available
device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device)
```

## Translation Process

When translating text:

1. Tokenize the input text
2. Generate the translation with forced BOS token for the target language
3. Decode the generated tokens

```python
def translate_text(text, model, tokenizer, source_lang="eng_Latn", target_lang="rus_Cyrl"):
    # Tokenize input text
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    
    # Generate translation with target language BOS token
    translated_tokens = model.generate(
        **inputs,
        forced_bos_token_id=tokenizer.lang_code_to_id[target_lang],
        max_length=256
    )
    
    # Decode the generated tokens
    translation = tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]
    return translation
```

## Language Codes

NLLB uses BCP-47-style language codes with language and script components:

- English: `eng_Latn`
- Russian: `rus_Cyrl`
- Chinese (Simplified): `zho_Hans`
- Arabic: `ara_Arab`

Ensure that both source and target language codes are valid for the model.

## Memory Management

To optimize memory usage:

1. Use the smaller distilled model when possible
2. Consider implementing model unloading if server is idle for extended periods
3. For CPU-only servers, adjust batch sizes to prevent OOM errors
4. If running multiple instances, implement proper resource allocation

## Error Handling

Common errors to handle:

1. Model loading failure (file not found, corrupt files)
2. Out of memory errors during translation
3. Invalid language codes
4. Text length exceeding model capacity
5. Translation timeouts for long texts

Implement proper error handling and status checks to ensure the system remains stable.

## Performance Optimization

To optimize translation performance:

1. Use batch translation when possible (for multiple texts)
2. Keep the model loaded in memory between requests
3. Implement proper caching for frequently translated texts
4. Use GPU acceleration when available
5. Consider quantization for reduced memory footprint

## Testing

Test the model with:

1. Various language pairs (common and uncommon)
2. Different text lengths and complexities
3. Special characters and symbols
4. Edge cases (empty text, very long text)
5. Load testing for concurrent translation requests

## Licensing

NLLB models from Meta have specific licensing requirements:

- The original models are released under CC-BY-NC-4.0 license
- This is a non-commercial license and restricts commercial use
- For commercial applications, alternative models or licensing must be arranged

## Additional Resources

- [NLLB GitHub Repository](https://github.com/facebookresearch/fairseq/tree/nllb)
- [Hugging Face Model Hub](https://huggingface.co/facebook/nllb-200-distilled-600M)
- [Model Paper](https://arxiv.org/abs/2207.04672)
- [Meta AI NLLB Blog Post](https://ai.meta.com/blog/nllb-200-high-quality-machine-translation/)