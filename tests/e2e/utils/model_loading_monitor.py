"""
Model loading monitoring utilities for E2E tests.
Provides proper synchronization and progress tracking for model initialization.
"""

import time
import logging
from typing import Optional, Dict, Any


class ModelLoadingMonitor:
    """Monitors and reports model loading progress with proper synchronization."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the monitor.
        
        Args:
            logger: Optional logger instance. If not provided, creates a new one.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.loading_stages = {}
        self._last_progress_log = 0
        
    def wait_for_model_ready(self, client, model_name: str, timeout: int = 1800) -> bool:
        """
        Wait for a specific model to be fully loaded and ready.
        
        Args:
            client: Test client instance with get() method
            model_name: Name of the model to wait for (e.g., 'nllb', 'aya')
            timeout: Maximum time to wait in seconds (default: 30 minutes)
            
        Returns:
            True if model is ready, False otherwise
            
        Raises:
            TimeoutError: If model is not ready within timeout period
        """
        start_time = time.time()
        last_status = None
        last_models_loaded = -1
        
        self.logger.info(f"Waiting for model '{model_name}' to be ready (timeout: {timeout}s)...")
        
        while time.time() - start_time < timeout:
            try:
                # Check health endpoint
                health_result = client.get("/health")
                
                if health_result.status_code == 200:
                    health_data = health_result.response_data
                    current_status = health_data.get("status", "unknown")
                    models_loaded = health_data.get("models_loaded", 0)
                    
                    # Log status changes
                    if current_status != last_status or models_loaded != last_models_loaded:
                        self.logger.info(
                            f"Service status: {current_status}, "
                            f"Models loaded: {models_loaded}"
                        )
                        last_status = current_status
                        last_models_loaded = models_loaded
                    
                    # Check if service is healthy and has models loaded
                    if current_status == "healthy" and models_loaded > 0:
                        # Check models endpoint for specific model status
                        models_result = client.get("/models")
                        
                        if models_result.status_code == 200:
                            models_info = models_result.response_data
                            
                            # Check if our specific model is in the loaded models
                            if isinstance(models_info, dict):
                                if model_name in models_info:
                                    model_status = models_info[model_name].get("status", "unknown")
                                    
                                    if model_status == "ready":
                                        elapsed = time.time() - start_time
                                        self.logger.info(
                                            f"Model '{model_name}' is ready! "
                                            f"Loading took {elapsed:.1f} seconds"
                                        )
                                        return True
                                    else:
                                        self.logger.debug(
                                            f"Model '{model_name}' status: {model_status}"
                                        )
                            elif isinstance(models_info, list):
                                # List format - check if model is available in the list
                                for model_data in models_info:
                                    if isinstance(model_data, dict) and model_data.get("name") == model_name:
                                        if model_data.get("available", False):
                                            elapsed = time.time() - start_time
                                            self.logger.info(
                                                f"Model '{model_name}' is ready! "
                                                f"Loading took {elapsed:.1f} seconds"
                                            )
                                            return True
                                        else:
                                            self.logger.debug(
                                                f"Model '{model_name}' not available: {model_data}"
                                            )
                                            break
                                # Fallback: check if model_name is in the list directly
                                if model_name in models_info:
                                    elapsed = time.time() - start_time
                                    self.logger.info(
                                        f"Model '{model_name}' is loaded! "
                                        f"Loading took {elapsed:.1f} seconds"
                                    )
                                    return True
                
                # Log progress every 30 seconds
                elapsed = time.time() - start_time
                if int(elapsed) - self._last_progress_log >= 30:
                    self._last_progress_log = int(elapsed)
                    self.logger.info(
                        f"Still waiting for model '{model_name}'... "
                        f"({elapsed:.0f}s elapsed, {timeout - elapsed:.0f}s remaining)"
                    )
                    
                    # Try to get more detailed status if available
                    self._log_detailed_status(client, model_name)
                
            except Exception as e:
                self.logger.warning(f"Error checking model status: {e}")
            
            # Sleep before next check
            time.sleep(5)
        
        # Timeout reached
        elapsed = time.time() - start_time
        raise TimeoutError(
            f"Model '{model_name}' not ready after {elapsed:.1f} seconds "
            f"(timeout: {timeout}s)"
        )
    
    def _log_detailed_status(self, client, model_name: str) -> None:
        """Log detailed model loading status if available."""
        try:
            # Try to get model-specific info endpoint if it exists
            model_info_result = client.get(f"/models/{model_name}/info")
            
            if model_info_result.status_code == 200:
                info = model_info_result.response_data
                self.logger.info(f"Model '{model_name}' detailed status: {info}")
            elif model_info_result.status_code == 404:
                # Endpoint doesn't exist, try models endpoint
                models_result = client.get("/models")
                if models_result.status_code == 200:
                    models_data = models_result.response_data
                    if isinstance(models_data, dict) and model_name in models_data:
                        self.logger.info(
                            f"Model '{model_name}' info: {models_data[model_name]}"
                        )
        except Exception as e:
            self.logger.debug(f"Could not get detailed status: {e}")
    
    def track_loading_stages(self, model_name: str, stage: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Track loading stages for a model.
        
        Args:
            model_name: Name of the model
            stage: Current loading stage (e.g., 'downloading', 'loading', 'ready')
            details: Optional additional details about the stage
        """
        if model_name not in self.loading_stages:
            self.loading_stages[model_name] = []
        
        stage_info = {
            "stage": stage,
            "timestamp": time.time(),
            "details": details or {}
        }
        
        self.loading_stages[model_name].append(stage_info)
        self.logger.info(f"Model '{model_name}' entered stage: {stage}")
        
        if details:
            self.logger.debug(f"Stage details: {details}")
    
    def get_loading_duration(self, model_name: str) -> Optional[float]:
        """
        Get total loading duration for a model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Duration in seconds if model has loading stages, None otherwise
        """
        if model_name not in self.loading_stages or not self.loading_stages[model_name]:
            return None
        
        stages = self.loading_stages[model_name]
        start_time = stages[0]["timestamp"]
        end_time = stages[-1]["timestamp"]
        
        return end_time - start_time
    
    def clear_stages(self, model_name: Optional[str] = None) -> None:
        """
        Clear tracked loading stages.
        
        Args:
            model_name: Specific model to clear, or None to clear all
        """
        if model_name:
            self.loading_stages.pop(model_name, None)
        else:
            self.loading_stages.clear()