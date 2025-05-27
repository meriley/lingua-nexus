import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import torch
import asyncio
from conftest import EnhancedMockModel, EnhancedMockTokenizer

def test_health_endpoint(test_client):
    """Test the health check endpoint."""
    response = test_client.get("/health")
    
    assert response.status_code == 200
    assert "status" in response.json()
    assert "model_loaded" in response.json()
    assert "device" in response.json()
    assert "memory_usage" in response.json()

def test_health_endpoint_with_cuda(test_client, monkeypatch):
    """Test the health check endpoint with CUDA available."""
    # Mock torch.cuda.is_available to return True
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    # Mock torch.cuda.memory_allocated to return a value
    monkeypatch.setattr(torch.cuda, "memory_allocated", lambda: 1024*1024*1024)
    
    response = test_client.get("/health")
    
    assert response.status_code == 200
    assert response.json()["device"] == "cuda"
    assert "GB" in response.json()["memory_usage"]

def test_startup_event(enhanced_mock_objects):
    """Test the application startup event with enhanced mocks."""
    from app.main import app
    import app.main
    
    # Get the enhanced mock objects from the fixture
    mock_model, mock_tokenizer = enhanced_mock_objects
    
    # The fixture already sets the model and tokenizer to mocked versions
    # Let's verify that they are properly loaded and functioning
    assert app.main.model is not None
    assert app.main.tokenizer is not None
    
    # Verify these are our enhanced mock objects
    assert hasattr(app.main.model, 'test_id')
    assert hasattr(app.main.tokenizer, 'call_count')
    assert app.main.model.test_id.startswith("mock_model_")
    
    # Test that the model and tokenizer have the expected enhanced interface
    assert hasattr(app.main.model, 'device')
    assert hasattr(app.main.model, 'config')
    assert hasattr(app.main.model.config, 'task_specific_params')
    assert hasattr(app.main.tokenizer, 'vocab_size')
    assert app.main.tokenizer.vocab_size == 256206

def test_translate_endpoint_en_to_ru(test_client, mock_translation_objects, api_key_header):
    """Test the translation endpoint with English to Russian translation."""
    request_data = {
        "text": "Hello world",
        "source_lang": "eng_Latn",
        "target_lang": "rus_Cyrl"
    }
    
    response = test_client.post(
        "/translate",
        json=request_data,
        headers=api_key_header
    )
    
    assert response.status_code == 200
    assert "translated_text" in response.json()
    assert "detected_source" in response.json()
    assert "time_ms" in response.json()
    assert response.json()["detected_source"] == "eng_Latn"
    assert response.json()["translated_text"] == "Translated: Hello world"

def test_translate_endpoint_auto_detect(test_client, mock_translation_objects, api_key_header):
    """Test the translation endpoint with automatic language detection."""
    request_data = {
        "text": "Привет мир",
        "source_lang": "auto",
        "target_lang": "eng_Latn"
    }
    
    response = test_client.post(
        "/translate",
        json=request_data,
        headers=api_key_header
    )
    
    assert response.status_code == 200
    assert "translated_text" in response.json()
    assert "detected_source" in response.json()
    assert "time_ms" in response.json()
    assert response.json()["detected_source"] == "rus_Cyrl"
    assert response.json()["translated_text"] == "Translated: Привет мир"

def test_translate_endpoint_empty_text(test_client, mock_translation_objects, api_key_header):
    """Test the translation endpoint with empty text."""
    request_data = {
        "text": "",
        "source_lang": "eng_Latn",
        "target_lang": "rus_Cyrl"
    }
    
    response = test_client.post(
        "/translate",
        json=request_data,
        headers=api_key_header
    )
    
    assert response.status_code == 422  # FastAPI validation error
    assert "detail" in response.json()
    # Check that it's a validation error for min_length
    assert any("min_length" in str(error) for error in response.json()["detail"])

def test_translate_endpoint_whitespace_only_text(test_client, mock_translation_objects, api_key_header):
    """Test the translation endpoint with text containing only whitespace."""
    request_data = {
        "text": "   \t\n",
        "source_lang": "eng_Latn",
        "target_lang": "rus_Cyrl"
    }
    
    response = test_client.post(
        "/translate",
        json=request_data,
        headers=api_key_header
    )
    
    # Whitespace gets past Pydantic validation but is caught by app logic
    assert response.status_code == 400
    assert "detail" in response.json()
    assert "Empty text" in response.json()["detail"]

def test_translate_endpoint_auth_failure(test_client, mock_translation_objects):
    """Test the translation endpoint with invalid API key."""
    request_data = {
        "text": "Hello world",
        "source_lang": "eng_Latn",
        "target_lang": "rus_Cyrl"
    }
    
    response = test_client.post(
        "/translate",
        json=request_data,
        headers={"X-API-Key": "invalid_key"}
    )
    
    assert response.status_code == 403
    assert "detail" in response.json()
    assert "Invalid API Key" in response.json()["detail"]

def test_translate_endpoint_auth_failure_empty_key(test_client, mock_translation_objects):
    """Test the translation endpoint with empty API key."""
    request_data = {
        "text": "Hello world",
        "source_lang": "eng_Latn",
        "target_lang": "rus_Cyrl"
    }
    
    response = test_client.post(
        "/translate",
        json=request_data,
        headers={"X-API-Key": ""}
    )
    
    assert response.status_code == 403
    assert "detail" in response.json()
    assert "Invalid API Key" in response.json()["detail"]

def test_translate_endpoint_no_api_key(test_client, mock_translation_objects):
    """Test the translation endpoint with no API key."""
    request_data = {
        "text": "Hello world",
        "source_lang": "eng_Latn",
        "target_lang": "rus_Cyrl"
    }
    
    response = test_client.post(
        "/translate",
        json=request_data
    )
    
    assert response.status_code == 403
    assert "detail" in response.json()
    assert "Invalid API Key" in response.json()["detail"]

def test_translate_endpoint_invalid_language(test_client, mock_translation_objects, api_key_header):
    """Test the translation endpoint with invalid language code."""
    request_data = {
        "text": "Hello world",
        "source_lang": "eng_Latn",
        "target_lang": "invalid_lang"  # Invalid language code
    }
    
    response = test_client.post(
        "/translate",
        json=request_data,
        headers=api_key_header
    )
    
    assert response.status_code == 400  # App-level validation error
    assert "detail" in response.json()
    assert "Unsupported target language" in response.json()["detail"]

def test_translate_endpoint_text_too_long(test_client, mock_translation_objects, api_key_header):
    """Test the translation endpoint with text that exceeds maximum length."""
    request_data = {
        "text": "Hello world" * 1000,  # Create a very long text
        "source_lang": "eng_Latn",
        "target_lang": "rus_Cyrl"
    }
    
    response = test_client.post(
        "/translate",
        json=request_data,
        headers=api_key_header
    )
    
    assert response.status_code == 422  # Validation error
    assert "detail" in response.json()

def test_translate_endpoint_translation_error(test_client, api_key_header, error_simulation_fixture):
    """Test the translation endpoint when a translation error occurs."""
    # Use the error simulation fixture to simulate a translation error
    error_simulation_fixture["translation_error"]()
    
    request_data = {
        "text": "Hello world",
        "source_lang": "eng_Latn",
        "target_lang": "rus_Cyrl"
    }
    
    response = test_client.post(
        "/translate",
        json=request_data,
        headers=api_key_header
    )
    
    assert response.status_code == 500
    assert "detail" in response.json()
    assert "Translation error" in response.json()["detail"]
    # The actual error message may vary, just check it contains "Translation error"

def test_translate_endpoint_language_detection_error(test_client, api_key_header, mock_translation_objects, monkeypatch):
    """Test the translation endpoint when language detection fails."""
    from app.utils import language_detection
    
    # Mock the language detection function to raise an exception
    def mock_detect_error(text):
        raise Exception("Language detection failed")
    
    monkeypatch.setattr(language_detection, "detect_language", mock_detect_error)
    
    request_data = {
        "text": "Hello world",
        "source_lang": "auto",  # This will trigger language detection
        "target_lang": "rus_Cyrl"
    }
    
    response = test_client.post(
        "/translate",
        json=request_data,
        headers=api_key_header
    )
    
    assert response.status_code == 500
    assert "detail" in response.json()
    assert "Translation error" in response.json()["detail"]
    assert "Language detection failed" in response.json()["detail"]

def test_translate_endpoint_model_not_loaded(test_client, api_key_header, monkeypatch):
    """Test the translation endpoint when the model is not loaded."""
    # Mock the model and tokenizer as None
    import app.main
    monkeypatch.setattr(app.main, "model", None)
    monkeypatch.setattr(app.main, "tokenizer", None)
    
    request_data = {
        "text": "Hello world",
        "source_lang": "eng_Latn",
        "target_lang": "rus_Cyrl"
    }
    
    response = test_client.post(
        "/translate",
        json=request_data,
        headers=api_key_header
    )
    
    assert response.status_code == 503
    assert "detail" in response.json()
    assert "Model not loaded" in response.json()["detail"]

def test_translate_endpoint_rate_limiting(test_client, mock_translation_objects, api_key_header):
    """Test rate limiting on the translation endpoint."""
    # Skip this test because rate limiting is disabled in test environment
    # Rate limiting is tested separately in test_rate_limiting.py
    pytest.skip("Rate limiting is disabled in test environment")

def test_translation_endpoint_full_coverage(test_client, mock_translation_objects, api_key_header):
    """Test the translation endpoint with various source and target languages."""
    languages = ["eng_Latn", "rus_Cyrl"]
    
    for source_lang in languages:
        for target_lang in languages:
            if source_lang != target_lang:
                request_data = {
                    "text": f"Test text from {source_lang} to {target_lang}",
                    "source_lang": source_lang,
                    "target_lang": target_lang
                }
                
                response = test_client.post(
                    "/translate",
                    json=request_data,
                    headers=api_key_header
                )
                
                assert response.status_code == 200
                assert "translated_text" in response.json()
                assert "detected_source" in response.json()
                assert "time_ms" in response.json()
                assert response.json()["detected_source"] == source_lang
                assert response.json()["translated_text"].startswith("Translated: ")