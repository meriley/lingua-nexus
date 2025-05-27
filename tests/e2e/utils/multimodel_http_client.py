"""
Enhanced HTTP client for multi-model translation API testing.

This module provides a specialized HTTP client for testing the multi-model
translation API with built-in retry logic, performance monitoring, and
comprehensive error handling.
"""

import time
import requests
from typing import Dict, Any, Optional, List
import logging
from dataclasses import dataclass, field


@dataclass
class RequestConfig:
    """Configuration for HTTP requests."""
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    verify_ssl: bool = False
    follow_redirects: bool = True


@dataclass
class RequestResult:
    """Result of an HTTP request."""
    status_code: int
    response_data: Optional[Dict[str, Any]] = None
    response_text: str = ""
    duration_ms: float = 0.0
    error: Optional[str] = None
    attempt: int = 1


class MultiModelHTTPClient:
    """Enhanced HTTP client for multi-model API testing."""
    
    def __init__(self, base_url: str, default_headers: Optional[Dict[str, str]] = None):
        """
        Initialize HTTP client.
        
        Args:
            base_url: Base URL for the API
            default_headers: Default headers to include with all requests
        """
        self.base_url = base_url.rstrip('/')
        self.default_headers = default_headers or {}
        self.session = requests.Session()
        self.session.headers.update(self.default_headers)
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self.request_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_duration_ms": 0.0,
            "avg_duration_ms": 0.0
        }
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, 
            config: Optional[RequestConfig] = None, headers: Optional[Dict[str, str]] = None) -> RequestResult:
        """Perform GET request."""
        return self._make_request("GET", endpoint, params=params, config=config, headers=headers)
    
    def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None,
             config: Optional[RequestConfig] = None, headers: Optional[Dict[str, str]] = None) -> RequestResult:
        """Perform POST request."""
        return self._make_request("POST", endpoint, json=json_data, config=config, headers=headers)
    
    def delete(self, endpoint: str, config: Optional[RequestConfig] = None, 
               headers: Optional[Dict[str, str]] = None) -> RequestResult:
        """Perform DELETE request."""
        return self._make_request("DELETE", endpoint, config=config, headers=headers)
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> RequestResult:
        """Make HTTP request with retry logic and error handling."""
        config = kwargs.pop('config', None) or RequestConfig()
        headers = kwargs.pop('headers', None) or {}
        
        # Merge headers
        request_headers = {**self.default_headers, **headers}
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(1, config.max_retries + 1):
            start_time = time.time()
            
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    timeout=config.timeout,
                    verify=config.verify_ssl,
                    allow_redirects=config.follow_redirects,
                    **kwargs
                )
                
                duration_ms = (time.time() - start_time) * 1000
                
                # Update stats
                self._update_stats(duration_ms, success=response.status_code < 400)
                
                # Parse response
                response_data = None
                try:
                    if response.headers.get('content-type', '').startswith('application/json'):
                        response_data = response.json()
                except Exception:
                    pass  # Non-JSON response is okay
                
                result = RequestResult(
                    status_code=response.status_code,
                    response_data=response_data,
                    response_text=response.text,
                    duration_ms=duration_ms,
                    attempt=attempt
                )
                
                # Log successful request
                self.logger.debug(f"{method} {url} -> {response.status_code} ({duration_ms:.1f}ms)")
                
                return result
                
            except requests.exceptions.RequestException as e:
                duration_ms = (time.time() - start_time) * 1000
                error_msg = str(e)
                
                # Update stats for failed request
                self._update_stats(duration_ms, success=False)
                
                self.logger.warning(f"{method} {url} attempt {attempt} failed: {error_msg}")
                
                # If this is the last attempt, return the error
                if attempt == config.max_retries:
                    return RequestResult(
                        status_code=0,
                        error=error_msg,
                        duration_ms=duration_ms,
                        attempt=attempt
                    )
                
                # Wait before retry
                time.sleep(config.retry_delay)
        
        # Should not reach here, but just in case
        return RequestResult(
            status_code=0,
            error="Max retries exceeded",
            attempt=config.max_retries
        )
    
    def _update_stats(self, duration_ms: float, success: bool):
        """Update request statistics."""
        self.request_stats["total_requests"] += 1
        self.request_stats["total_duration_ms"] += duration_ms
        
        if success:
            self.request_stats["successful_requests"] += 1
        else:
            self.request_stats["failed_requests"] += 1
        
        # Update average
        total_requests = self.request_stats["total_requests"]
        self.request_stats["avg_duration_ms"] = self.request_stats["total_duration_ms"] / total_requests
    
    def health_check(self, timeout: float = 5.0) -> bool:
        """Perform health check on the service."""
        try:
            config = RequestConfig(timeout=timeout, max_retries=1)
            result = self.get("/health", config=config)
            if result.status_code != 200:
                self.logger.debug(f"Health check failed with status {result.status_code}: {result.response_text}")
            return result.status_code == 200
        except Exception as e:
            self.logger.debug(f"Health check exception: {e}")
            return False
    
    def wait_for_service(self, timeout: float = 60.0, check_interval: float = 1.0) -> bool:
        """Wait for service to become available."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.health_check(timeout=check_interval):
                return True
            time.sleep(check_interval)
        
        return False
    
    def translate(self, text: str, source_lang: str = "en", target_lang: str = "ru", 
                  model: str = "nllb", model_options: Optional[Dict[str, Any]] = None) -> RequestResult:
        """Convenient method for translation requests."""
        data = {
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "model": model
        }
        
        if model_options:
            data["model_options"] = model_options
        
        return self.post("/translate", json_data=data)
    
    def batch_translate(self, requests_data: List[Dict[str, Any]]) -> RequestResult:
        """Convenient method for batch translation requests."""
        return self.post("/translate/batch", json_data=requests_data)
    
    def list_models(self) -> RequestResult:
        """Get list of available models."""
        return self.get("/models")
    
    def load_model(self, model_name: str) -> RequestResult:
        """Load a specific model."""
        return self.post(f"/models/{model_name}/load")
    
    def unload_model(self, model_name: str) -> RequestResult:
        """Unload a specific model."""
        return self.delete(f"/models/{model_name}")
    
    def get_languages(self, model_name: Optional[str] = None) -> RequestResult:
        """Get supported languages."""
        if model_name:
            return self.get(f"/languages/{model_name}")
        else:
            return self.get("/languages")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        stats = self.request_stats.copy()
        
        # Add success rate
        total = stats["total_requests"]
        if total > 0:
            stats["success_rate"] = stats["successful_requests"] / total
            stats["failure_rate"] = stats["failed_requests"] / total
        else:
            stats["success_rate"] = 0.0
            stats["failure_rate"] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset request statistics."""
        self.request_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_duration_ms": 0.0,
            "avg_duration_ms": 0.0
        }
    
    def close(self):
        """Close the HTTP session."""
        if self.session:
            self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class ModelTestClient(MultiModelHTTPClient):
    """Specialized client for model testing with additional convenience methods."""
    
    def __init__(self, base_url: str, api_key: str):
        """Initialize with API key authentication."""
        super().__init__(base_url, {"X-API-Key": api_key})
        self.api_key = api_key
    
    def test_model_loading_workflow(self, model_name: str) -> Dict[str, Any]:
        """Test complete model loading workflow."""
        results = {}
        
        # 1. Check initial state
        models_result = self.list_models()
        results["initial_models"] = models_result.response_data
        
        # 2. Load model
        load_result = self.load_model(model_name)
        results["load_result"] = {
            "success": load_result.status_code == 200,
            "response": load_result.response_data,
            "duration_ms": load_result.duration_ms
        }
        
        # 3. Verify model is loaded
        models_after_load = self.list_models()
        results["models_after_load"] = models_after_load.response_data
        
        # 4. Test translation
        if load_result.status_code == 200:
            translate_result = self.translate("Hello, world!", model=model_name)
            results["translation_test"] = {
                "success": translate_result.status_code == 200,
                "response": translate_result.response_data,
                "duration_ms": translate_result.duration_ms
            }
        
        return results
    
    def test_language_support(self, model_name: str) -> Dict[str, Any]:
        """Test language support for a model."""
        results = {}
        
        # Get general language support
        general_langs = self.get_languages()
        results["general_languages"] = {
            "success": general_langs.status_code == 200,
            "count": len(general_langs.response_data) if general_langs.response_data else 0
        }
        
        # Get model-specific language support
        model_langs = self.get_languages(model_name)
        results["model_languages"] = {
            "success": model_langs.status_code == 200,
            "response": model_langs.response_data
        }
        
        return results
    
    def performance_test(self, model_name: str, num_requests: int = 10) -> Dict[str, Any]:
        """Run performance test with multiple translation requests."""
        results = {
            "num_requests": num_requests,
            "durations": [],
            "success_count": 0,
            "error_count": 0,
            "errors": []
        }
        
        test_texts = [
            f"Performance test message {i} for model {model_name}"
            for i in range(num_requests)
        ]
        
        start_time = time.time()
        
        for i, text in enumerate(test_texts):
            result = self.translate(text, model=model_name)
            results["durations"].append(result.duration_ms)
            
            if result.status_code == 200:
                results["success_count"] += 1
            else:
                results["error_count"] += 1
                results["errors"].append({
                    "request_index": i,
                    "error": result.error,
                    "status_code": result.status_code
                })
        
        total_time = (time.time() - start_time) * 1000
        results["total_time_ms"] = total_time
        results["avg_duration_ms"] = sum(results["durations"]) / len(results["durations"])
        results["min_duration_ms"] = min(results["durations"])
        results["max_duration_ms"] = max(results["durations"])
        results["success_rate"] = results["success_count"] / num_requests
        
        return results