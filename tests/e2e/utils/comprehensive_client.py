"""
Comprehensive test client with full API coverage and model synchronization.
Extends ModelTestClient with missing methods for complete E2E testing.
"""

import time
import logging
from typing import Dict, Any, Optional, List
from .multimodel_http_client import ModelTestClient, RequestResult, RequestConfig
from .model_loading_monitor import ModelLoadingMonitor
from .retry_mechanism import retry_http_request, RetryManager, RetryConfig


class ComprehensiveTestClient(ModelTestClient):
    """Enhanced test client with complete API coverage and synchronization capabilities."""
    
    def __init__(self, base_url: str, api_key: str):
        """
        Initialize comprehensive test client.
        
        Args:
            base_url: Base URL for the API
            api_key: API key for authentication
        """
        super().__init__(base_url, api_key)
        self.monitor = ModelLoadingMonitor(self.logger)
        
        # Initialize retry manager for HTTP requests
        self.retry_manager = RetryManager(RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=10.0,
            retryable_exceptions=[ConnectionError, TimeoutError, OSError]
        ))
    
    def detect_language(self, text: str, model: Optional[str] = None) -> RequestResult:
        """
        Detect language of input text.
        
        Args:
            text: Text to analyze for language detection
            model: Optional model name to use for detection
            
        Returns:
            RequestResult with detected language information
        """
        data = {"text": text}
        if model:
            data["model"] = model
        
        return self.retry_manager.execute_with_retry(
            self.post, "/detect", json_data=data
        )
    
    def get_model_info(self, model_name: str) -> RequestResult:
        """
        Get detailed information about a specific model.
        
        Args:
            model_name: Name of the model to query
            
        Returns:
            RequestResult with model status and details
        """
        # First try the specific model info endpoint
        result = self.get(f"/models/{model_name}/info")
        
        # If that doesn't exist, try to extract from general models endpoint
        if result.status_code == 404:
            models_result = self.get("/models")
            if models_result.status_code == 200 and models_result.response_data:
                models_data = models_result.response_data
                
                # Extract model info if available
                if isinstance(models_data, dict) and model_name in models_data:
                    # Create a synthetic result with the model info
                    return RequestResult(
                        status_code=200,
                        response_data=models_data[model_name],
                        duration_ms=models_result.duration_ms
                    )
                elif isinstance(models_data, list) and model_name in models_data:
                    # Simple list format - create basic info
                    return RequestResult(
                        status_code=200,
                        response_data={"name": model_name, "status": "ready"},
                        duration_ms=models_result.duration_ms
                    )
        
        return result
    
    def wait_for_model(self, model_name: str, timeout: int = 1800) -> bool:
        """
        Wait for specific model to be ready using ModelLoadingMonitor.
        
        Args:
            model_name: Name of the model to wait for
            timeout: Maximum time to wait in seconds (default: 30 minutes)
            
        Returns:
            True if model is ready, False otherwise
            
        Raises:
            TimeoutError: If model is not ready within timeout
        """
        try:
            return self.monitor.wait_for_model_ready(self, model_name, timeout)
        except TimeoutError:
            self.logger.error(f"Model '{model_name}' failed to load within {timeout} seconds")
            raise
    
    def get_model_status(self, model_name: str) -> Dict[str, Any]:
        """
        Get comprehensive status for a model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Dictionary with model status information
        """
        status = {
            "model_name": model_name,
            "available": False,
            "loaded": False,
            "ready": False,
            "info": None,
            "error": None
        }
        
        try:
            # Check if model is in available models list
            models_result = self.list_models()
            if models_result.status_code == 200 and models_result.response_data:
                models_data = models_result.response_data
                
                if isinstance(models_data, dict):
                    status["available"] = model_name in models_data
                    if status["available"]:
                        status["loaded"] = True
                        model_info = models_data[model_name]
                        status["ready"] = model_info.get("status") == "ready"
                        status["info"] = model_info
                elif isinstance(models_data, list):
                    # Handle list format from multi-model API
                    for model_data in models_data:
                        if isinstance(model_data, dict) and model_data.get("name") == model_name:
                            status["available"] = True
                            status["loaded"] = True
                            status["ready"] = model_data.get("available", False)
                            status["info"] = model_data
                            break
                    # Fallback for simple list format
                    if not status["available"] and model_name in models_data:
                        status["available"] = True
                        status["loaded"] = True
                        status["ready"] = True
            
            # Try to get more detailed info
            info_result = self.get_model_info(model_name)
            if info_result.status_code == 200:
                status["info"] = info_result.response_data
                
        except Exception as e:
            status["error"] = str(e)
            self.logger.error(f"Error getting model status: {e}")
        
        return status
    
    # Retry-enabled wrapper methods for improved reliability
    
    def translate_with_retry(self, text: str, source_lang: str, target_lang: str, 
                           model: str = "nllb", model_options: Optional[Dict] = None) -> RequestResult:
        """
        Translate text with retry logic for improved reliability.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            model: Model to use for translation
            model_options: Optional model-specific parameters
            
        Returns:
            RequestResult from translation API
        """
        return self.retry_manager.execute_with_retry(
            super().translate, text, source_lang, target_lang, model, model_options
        )
    
    def get_health_with_retry(self) -> RequestResult:
        """Get health status with retry logic."""
        return self.retry_manager.execute_with_retry(
            self.get, "/health"
        )
    
    def list_models_with_retry(self) -> RequestResult:
        """List models with retry logic."""
        return self.retry_manager.execute_with_retry(
            self.list_models
        )
    
    def load_model_with_retry(self, model_name: str) -> RequestResult:
        """Load model with retry logic."""
        return self.retry_manager.execute_with_retry(
            self.load_model, model_name
        )
    
    def test_translation_with_detection(self, text: str, target_lang: str, 
                                      model: str = "nllb") -> Dict[str, Any]:
        """
        Test translation with automatic language detection.
        
        Args:
            text: Text to translate
            target_lang: Target language code
            model: Model to use for translation
            
        Returns:
            Dictionary with detection and translation results
        """
        results = {
            "detection": None,
            "translation": None,
            "success": False,
            "error": None
        }
        
        try:
            # First detect the language
            detect_result = self.detect_language(text, model)
            if detect_result.status_code == 200:
                results["detection"] = detect_result.response_data
                detected_lang = detect_result.response_data.get("detected_language")
                
                if detected_lang:
                    # Then translate
                    translate_result = self.translate(
                        text=text,
                        source_lang=detected_lang,
                        target_lang=target_lang,
                        model=model
                    )
                    
                    if translate_result.status_code == 200:
                        results["translation"] = translate_result.response_data
                        results["success"] = True
                    else:
                        results["error"] = f"Translation failed: {translate_result.status_code}"
                else:
                    results["error"] = "Language detection did not return a language"
            else:
                results["error"] = f"Language detection failed: {detect_result.status_code}"
                
        except Exception as e:
            results["error"] = str(e)
            self.logger.error(f"Error in translation with detection: {e}")
        
        return results
    
    def batch_translate_with_retry(self, requests_data: List[Dict[str, Any]], 
                                 max_retries: int = 3, 
                                 retry_delay: float = 2.0) -> RequestResult:
        """
        Batch translate with enhanced retry logic.
        
        Args:
            requests_data: List of translation requests
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            RequestResult with batch translation results
        """
        config = RequestConfig(
            timeout=60.0,  # Longer timeout for batch operations
            max_retries=max_retries,
            retry_delay=retry_delay
        )
        
        return self.post("/translate/batch", json_data=requests_data, config=config)
    
    def test_model_switching(self, text: str, models: List[str]) -> Dict[str, Any]:
        """
        Test switching between different models.
        
        Args:
            text: Text to translate with each model
            models: List of model names to test
            
        Returns:
            Dictionary with results from each model
        """
        results = {
            "models_tested": models,
            "results": {},
            "switching_times": [],
            "total_duration_ms": 0
        }
        
        start_time = time.time()
        
        for i, model in enumerate(models):
            model_start = time.time()
            
            # Ensure model is ready
            try:
                if not self.wait_for_model(model, timeout=300):
                    results["results"][model] = {"error": "Model not ready"}
                    continue
            except TimeoutError:
                results["results"][model] = {"error": "Model loading timeout"}
                continue
            
            # Test translation
            translate_result = self.translate(
                text=text,
                source_lang="en",
                target_lang="es",
                model=model
            )
            
            model_duration = (time.time() - model_start) * 1000
            
            results["results"][model] = {
                "success": translate_result.status_code == 200,
                "response": translate_result.response_data,
                "duration_ms": model_duration
            }
            
            if i > 0:
                # Calculate switching time (time between models)
                results["switching_times"].append(model_duration)
        
        results["total_duration_ms"] = (time.time() - start_time) * 1000
        
        return results
    
    def stress_test_model(self, model_name: str, duration_seconds: int = 60, 
                         requests_per_second: int = 1) -> Dict[str, Any]:
        """
        Stress test a model with sustained load.
        
        Args:
            model_name: Model to stress test
            duration_seconds: How long to run the test
            requests_per_second: Target request rate
            
        Returns:
            Dictionary with stress test results
        """
        results = {
            "model": model_name,
            "duration_seconds": duration_seconds,
            "target_rps": requests_per_second,
            "requests_sent": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "errors": []
        }
        
        start_time = time.time()
        request_interval = 1.0 / requests_per_second
        
        while time.time() - start_time < duration_seconds:
            request_start = time.time()
            
            # Send translation request
            result = self.translate(
                text=f"Stress test message at {time.time()}",
                model=model_name
            )
            
            results["requests_sent"] += 1
            
            if result.status_code == 200:
                results["successful_requests"] += 1
                results["response_times"].append(result.duration_ms)
            else:
                results["failed_requests"] += 1
                results["errors"].append({
                    "timestamp": time.time(),
                    "status_code": result.status_code,
                    "error": result.error or result.response_text
                })
            
            # Sleep to maintain request rate
            elapsed = time.time() - request_start
            if elapsed < request_interval:
                time.sleep(request_interval - elapsed)
        
        # Calculate statistics
        actual_duration = time.time() - start_time
        results["actual_duration_seconds"] = actual_duration
        results["actual_rps"] = results["requests_sent"] / actual_duration
        
        if results["response_times"]:
            results["avg_response_time_ms"] = sum(results["response_times"]) / len(results["response_times"])
            results["min_response_time_ms"] = min(results["response_times"])
            results["max_response_time_ms"] = max(results["response_times"])
        
        results["success_rate"] = (
            results["successful_requests"] / results["requests_sent"] 
            if results["requests_sent"] > 0 else 0
        )
        
        return results
    
    def verify_model_persistence(self, model_name: str, test_text: str = "Test message") -> Dict[str, Any]:
        """
        Verify that a model remains loaded and functional over time.
        
        Args:
            model_name: Model to verify
            test_text: Text to use for verification
            
        Returns:
            Dictionary with persistence verification results
        """
        results = {
            "model": model_name,
            "checks": [],
            "all_successful": True
        }
        
        # Perform checks at different intervals
        check_intervals = [0, 5, 15, 30, 60]  # seconds
        
        for interval in check_intervals:
            if interval > 0:
                self.logger.info(f"Waiting {interval} seconds before next check...")
                time.sleep(interval)
            
            check_result = {
                "interval_seconds": interval,
                "timestamp": time.time(),
                "model_ready": False,
                "translation_success": False,
                "error": None
            }
            
            try:
                # Check model status
                status = self.get_model_status(model_name)
                check_result["model_ready"] = status["ready"]
                
                if status["ready"]:
                    # Test translation
                    translate_result = self.translate(test_text, model=model_name)
                    check_result["translation_success"] = translate_result.status_code == 200
                    
                    if not check_result["translation_success"]:
                        check_result["error"] = f"Translation failed: {translate_result.status_code}"
                        results["all_successful"] = False
                else:
                    check_result["error"] = "Model not ready"
                    results["all_successful"] = False
                    
            except Exception as e:
                check_result["error"] = str(e)
                results["all_successful"] = False
            
            results["checks"].append(check_result)
        
        return results