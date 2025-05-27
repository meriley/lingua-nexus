# Model Template System

This directory contains templates for creating new translation model implementations in the single-model architecture.

## Template Variables

When using these templates, replace the following placeholders:

- `{MODEL_NAME}`: The model identifier (e.g., "aya-expanse-8b", "nllb")
- `{MODEL_CLASS_NAME}`: The Python class name (e.g., "AyaExpanse8B", "NLLB")
- `{MODEL_ENV_PREFIX}`: Environment variable prefix (e.g., "AYA", "NLLB")
- `{DEFAULT_MODEL_PATH}`: Default model path or HuggingFace model name
- `{MEMORY_REQUIREMENTS}`: Memory requirements description
- `{MODEL_VERSION}`: Model version string
- `{MODEL_SPECIFIC_REQUIREMENTS}`: Additional pip requirements

## Usage Example

To create a new model called "my-model":

1. Create directory: `models/my-model/`
2. Copy templates and replace variables:
   ```bash
   # Copy and customize model.py
   cp models/template/model.py.template models/my-model/model.py
   sed -i 's/{MODEL_NAME}/my-model/g' models/my-model/model.py
   sed -i 's/{MODEL_CLASS_NAME}/MyModel/g' models/my-model/model.py
   
   # Repeat for other files
   ```
3. Implement the TODO sections in the generated files
4. Test with `make build:my-model`

## Template Files

- `model.py.template`: Main model implementation with TranslationModel interface
- `config.py.template`: Model configuration class with environment variable support
- `requirements.txt.template`: Python dependencies template
- `Dockerfile.template`: Multi-stage Docker build template

## Generated Structure

After using templates, your model directory should contain:
```
models/my-model/
├── __init__.py
├── model.py          # Model implementation
├── config.py         # Configuration class
├── requirements.txt  # Dependencies
└── Dockerfile       # Container build
```