"""
Configuration for unit tests in the single-model architecture.

This module provides pytest fixtures and configuration for testing
individual model implementations.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add the models directory to Python path for imports
models_path = os.path.join(os.path.dirname(__file__), '../../../..')
if models_path not in sys.path:
    sys.path.insert(0, models_path)


@pytest.fixture
def mock_torch():
    """Mock torch for testing without requiring actual PyTorch installation."""
    with patch('torch.cuda.is_available', return_value=False):
        with patch('torch.tensor') as mock_tensor:
            mock_tensor.return_value = Mock()
            yield mock_tensor


@pytest.fixture
def mock_transformers():
    """Mock transformers library components."""
    mocks = {}
    
    with patch('transformers.AutoModelForSeq2SeqLM') as mock_model:
        with patch('transformers.AutoTokenizer') as mock_tokenizer:
            with patch('transformers.pipeline') as mock_pipeline:
                mocks['model'] = mock_model
                mocks['tokenizer'] = mock_tokenizer
                mocks['pipeline'] = mock_pipeline
                yield mocks


@pytest.fixture
def mock_llama_cpp():
    """Mock llama-cpp-python components."""
    with patch('llama_cpp.Llama') as mock_llama:
        mock_instance = Mock()
        mock_instance.create_chat_completion.return_value = {
            'choices': [{'message': {'content': 'Test response'}}]
        }
        mock_llama.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def basic_model_config():
    """Basic model configuration for testing."""
    return {
        'device': 'cpu',
        'max_length': 512,
        'temperature': 0.1,
        'batch_size': 1
    }


@pytest.fixture
def aya_model_config():
    """Configuration specific to Aya Expanse 8B model."""
    return {
        'model_path': 'bartowski/aya-expanse-8b-GGUF',
        'gguf_filename': 'aya-expanse-8b-Q4_K_M.gguf',
        'device': 'cpu',
        'max_length': 3072,
        'temperature': 0.1,
        'gpu_layers': 20,
        'use_gguf': True,
        'fallback_to_transformers': True
    }


@pytest.fixture
def nllb_model_config():
    """Configuration specific to NLLB model."""
    return {
        'model_path': 'facebook/nllb-200-distilled-600M',
        'device': 'cpu',
        'max_length': 512,
        'num_beams': 4,
        'use_pipeline': True,
        'batch_size': 1
    }


@pytest.fixture
def sample_translation_request():
    """Sample translation request for testing."""
    return {
        'text': 'Hello, world!',
        'source_lang': 'en',
        'target_lang': 'ru',
        'model_options': {}
    }


@pytest.fixture
def sample_translation_response():
    """Sample translation response for testing."""
    return {
        'translated_text': 'Привет, мир!',
        'source_language': 'en',
        'target_language': 'ru',
        'model_used': 'test-model',
        'processing_time_ms': 100,
        'metadata': {
            'device': 'cpu',
            'backend': 'test'
        }
    }


@pytest.fixture(autouse=True)
def cleanup_imports():
    """Cleanup any module imports after each test to avoid interference."""
    yield
    # Remove any dynamically imported model modules
    modules_to_remove = []
    for module_name in sys.modules:
        if module_name.startswith('models.') and module_name != 'models.base':
            modules_to_remove.append(module_name)
    
    for module_name in modules_to_remove:
        if module_name in sys.modules:
            del sys.modules[module_name]


# Pytest configuration for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()