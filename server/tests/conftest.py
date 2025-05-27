import os
import sys
import time
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

# Set testing environment variable to disable rate limiting
os.environ["TESTING"] = "true"

# Add the app directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from transformers import pipeline

# Enhanced Mock objects
class EnhancedMockConfig:
    """Enhanced NLLB model config mock with all required attributes."""
    def __init__(self):
        self.forced_bos_token_id = None
        self.max_length = 128
        self.architectures = ["M2M100ForConditionalGeneration"]
        self._commit_hash = "abcdef123456"
        self._name_or_path = "facebook/nllb-200-distilled-600M"
        self.id2label = {}
        self.label2id = {}
        self.decoder_start_token_id = 2
        self.eos_token_id = 2
        self.pad_token_id = 1
        self.tokenizer_class = "NllbTokenizer"
        self.vocab_size = 256206
        self.d_model = 1024
        self.encoder_layers = 12
        self.decoder_layers = 12
        self.encoder_attention_heads = 16
        self.decoder_attention_heads = 16
        self.encoder_ffn_dim = 4096
        self.decoder_ffn_dim = 4096
        # Add missing task_specific_params attribute
        self.task_specific_params = {
            "translation": {
                "do_sample": False,
                "max_length": 200,
                "num_beams": 5
            }
        }
        # Additional HuggingFace model attributes
        self.model_type = "m2m_100"
        self.tie_word_embeddings = False
        self.use_cache = True
        # Required by HuggingFace pipeline
        self.prefix = ""
        self.task = "translation"
        self.is_encoder_decoder = True
        self.framework = "pt"  # PyTorch
        self.min_length = 1  # Required attribute
    
    def update(self, *args, **kwargs):
        """Mock config update method."""
        pass
    
    def to_dict(self):
        """Mock config to_dict method."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
class EnhancedMockModel:
    """Enhanced NLLB model mock with better interface support."""
    def __init__(self):
        self.config = EnhancedMockConfig()
        self.test_id = f"mock_model_{time.time()}"
        self.device = "cpu"
        self.call_count = 0
        self.dtype = None
        self.can_generate = lambda: True
        # Make it appear as M2M100ForConditionalGeneration
        self.__class__.__name__ = "M2M100ForConditionalGeneration"
        # CRITICAL: Add framework attribute for transformers detection
        self.framework = "pt"  # PyTorch framework
        # Add generation config mock
        class MockGenerationConfig:
            def __init__(self):
                self.max_length = 512
                self.num_beams = 5  
                self.do_sample = False
                self.pad_token_id = 1
                self.eos_token_id = 2
                
            def update(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        self.generation_config = MockGenerationConfig()
        
    def to(self, device):
        """Mock device movement."""
        self.device = device
        return self
    
    def __call__(self, *args, **kwargs):
        """Mock model call for direct usage."""
        self.call_count += 1
        return [{"translation_text": f"Translated: {kwargs.get('text', 'test')}"}]
    
    def generate(self, input_ids, max_length=128, **kwargs):
        """Mock tensor generation matching real model behavior."""
        import torch
        self.call_count += 1
        # Return a tensor with realistic shape
        batch_size = input_ids.shape[0] if hasattr(input_ids, 'shape') else 1
        return torch.randint(0, 256206, (batch_size, max_length), dtype=torch.long)
    
    def eval(self):
        """Mock eval mode."""
        return self
    
    def train(self, mode=True):
        """Mock train mode."""
        return self

class EnhancedMockTokenizer:
    """Enhanced tokenizer mock with proper language handling."""
    def __init__(self):
        self.src_lang = None
        self.tgt_lang = None
        self.model_max_length = 1024
        self.vocab_size = 256206
        self.eos_token_id = 2
        self.pad_token_id = 1
        self.unk_token_id = 3
        self.call_count = 0
        
    def __call__(self, text, return_tensors="pt", padding=True, truncation=True, max_length=512, **kwargs):
        """Mock tokenization."""
        import torch
        self.call_count += 1
        
        # Handle different input types
        if isinstance(text, list):
            batch_size = len(text)
        else:
            batch_size = 1
            
        # Return realistic tokenized output
        seq_len = min(len(str(text)) // 4 + 2, max_length)  # Better length estimation
        
        result = {
            "input_ids": torch.randint(4, 256206, (batch_size, seq_len), dtype=torch.long),
            "attention_mask": torch.ones(batch_size, seq_len, dtype=torch.long)
        }
        
        return result
    
    def batch_decode(self, sequences, skip_special_tokens=True, **kwargs):
        """Mock batch decoding."""
        self.call_count += 1
        if hasattr(sequences, 'shape'):
            batch_size = sequences.shape[0]
        else:
            batch_size = len(sequences) if isinstance(sequences, list) else 1
            
        return [f"Translated: mock_text_{i}" for i in range(batch_size)]
    
    def decode(self, token_ids, skip_special_tokens=True, **kwargs):
        """Mock single sequence decoding."""
        self.call_count += 1
        return "Translated: mock_text"
    
    def set_src_lang_special_tokens(self, lang):
        """Mock source language setting."""
        self.src_lang = lang
        
    def set_tgt_lang_special_tokens(self, lang):
        """Mock target language setting."""
        self.tgt_lang = lang
    
    @property 
    def lang_code_to_id(self):
        """Mock language code mapping."""
        return {
            "eng_Latn": 256001,
            "rus_Cyrl": 256003,
        }
    
    def convert_tokens_to_ids(self, tokens):
        """Mock token conversion."""
        if isinstance(tokens, str):
            return 100  # Mock single token ID
        return [100 + i for i in range(len(tokens))]  # Mock multiple token IDs

# Enhanced Mock pipeline and translator
class EnhancedMockTranslator:
    """Enhanced translator mock with better error simulation."""
    def __init__(self, simulate_error=False, error_type=None):
        self.call_count = 0
        self.simulate_error = simulate_error
        self.error_type = error_type
        
    def __call__(self, text, src_lang=None, tgt_lang=None, max_length=512, **kwargs):
        """Mock translation with configurable error simulation."""
        self.call_count += 1
        
        # Simulate different error types for testing
        if self.simulate_error:
            if self.error_type == "translation":
                raise RuntimeError("Simulated translation error")
            elif self.error_type == "memory":
                raise RuntimeError("CUDA out of memory")
            elif self.error_type == "language":
                raise ValueError("Unsupported language pair")
        
        # Normal translation behavior
        return [{"translation_text": f"Translated: {text}"}]

# Mock pipeline creation with enhanced error support
def enhanced_mock_pipeline(task, model, tokenizer, device=-1, **kwargs):
    """Enhanced pipeline mock with error simulation support."""
    # Add framework to the model if it doesn't have one
    if hasattr(model, '__class__') and not hasattr(model, 'framework'):
        model.framework = "pt"
    # Don't actually create a pipeline, just return our translator
    if task == "translation":
        return EnhancedMockTranslator()
    else:
        return EnhancedMockTranslator()

def error_mock_pipeline(task, model, tokenizer, device=-1, **kwargs):
    """Pipeline mock that simulates translation errors."""
    return EnhancedMockTranslator(simulate_error=True, error_type="translation")

# Fixtures
@pytest.fixture
def test_client():
    """Create a test client for the API."""
    return TestClient(app)

@pytest.fixture
def enhanced_mock_objects(monkeypatch):
    """Enhanced fixture to mock translation model and tokenizer with better coverage."""
    from app.utils import model_loader
    import app.main
    
    # Create enhanced mock objects
    mock_model = EnhancedMockModel()
    mock_tokenizer = EnhancedMockTokenizer()
    
    # Mock the pipeline creation - patch in multiple places to ensure it's caught
    monkeypatch.setattr("transformers.pipeline", enhanced_mock_pipeline)
    monkeypatch.setattr("app.utils.model_loader.pipeline", enhanced_mock_pipeline)
    
    # Patch the model loading function
    monkeypatch.setattr(model_loader, "load_nllb_model", lambda: (mock_model, mock_tokenizer))
    
    # Enhanced translation function mock with proper "Translated: " prefix
    def enhanced_mock_translate_text(text, model, tokenizer, source_lang, target_lang):
        """Enhanced mock translation with language validation."""
        # Simulate language validation - include common test languages
        valid_langs = ["eng_Latn", "rus_Cyrl", "fra_Latn", "spa_Latn", "deu_Latn", "auto"]
        if source_lang not in valid_langs or target_lang not in valid_langs:
            raise ValueError(f"Unsupported language: {source_lang} -> {target_lang}")
        
        # Always ensure "Translated: " prefix for consistency
        if not text.startswith("Translated: "):
            return f"Translated: {text}"
        return text
    
    monkeypatch.setattr(model_loader, "translate_text", enhanced_mock_translate_text)
    
    # Directly set the enhanced objects in the main app
    app.main.model = mock_model
    app.main.tokenizer = mock_tokenizer
    
    return mock_model, mock_tokenizer

@pytest.fixture
def mock_translation_objects(enhanced_mock_objects):
    """Backward compatibility fixture."""
    return enhanced_mock_objects

@pytest.fixture
def api_key_header(monkeypatch):
    """Fixture for API key header with mock API key authentication."""
    from app.main import API_KEY
    
    # Set a known API key for testing
    test_api_key = "test_api_key"
    monkeypatch.setattr("app.main.API_KEY", test_api_key)
    
    # Return the header with the test API key
    return {"X-API-Key": test_api_key}

@pytest.fixture
def error_simulation_fixture(monkeypatch):
    """Fixture for simulating various error conditions."""
    from app.utils import model_loader
    
    def simulate_translation_error(text, model, tokenizer, source_lang, target_lang):
        raise RuntimeError("Simulated translation error")
    
    def simulate_language_detection_error(text):
        raise RuntimeError("Language detection failed")
    
    # Return functions that can be used to patch specific errors
    return {
        "translation_error": lambda: monkeypatch.setattr(
            model_loader, "translate_text", simulate_translation_error
        ),
        "language_detection_error": lambda: monkeypatch.setattr(
            "app.utils.language_detection.detect_language", simulate_language_detection_error
        ),
        "pipeline_error": lambda: monkeypatch.setattr(
            "transformers.pipeline", error_mock_pipeline
        )
    }