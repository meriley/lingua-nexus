"""
Robust service manager with enhanced model loading synchronization and monitoring.
Extends ServiceManager with proper wait mechanisms and progress tracking.
"""

import os
import time
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
from .service_manager import ServiceManager, MultiModelServiceConfig, ServiceConfig
from .model_loading_monitor import ModelLoadingMonitor
from .comprehensive_client import ComprehensiveTestClient
from .retry_mechanism import ServiceRetryMixin, ModelLoadingRetryMixin, retry_service_start, retry_model_operation
from .parallel_test_manager import ParallelServiceManager, get_worker_config, is_parallel_execution


class RobustServiceManager(ServiceRetryMixin, ModelLoadingRetryMixin, ServiceManager):
    """Enhanced service manager with proper model loading synchronization and retry capabilities."""
    
    def __init__(self):
        """Initialize robust service manager with monitoring capabilities."""
        super().__init__()
        self.progress_monitor = ModelLoadingMonitor()
        self.performance_tracker = PerformanceTracker()
        self.model_loading_times = {}
        
        # Initialize parallel service manager for worker isolation
        self.parallel_manager = ParallelServiceManager(get_worker_config())
        self.is_parallel = is_parallel_execution()
        
    def find_available_port(self, start_port: int = 8000, max_attempts: int = 100) -> int:
        """Find an available port, using worker-specific port allocation if in parallel mode."""
        if self.is_parallel:
            # Use isolated port from parallel manager
            return self.parallel_manager.get_available_port()
        else:
            # Use parent implementation for sequential execution
            return super().find_available_port(start_port, max_attempts)
            
    def get_cache_dir(self) -> str:
        """Get cache directory, using worker-specific directory if in parallel mode."""
        if self.is_parallel:
            return self.parallel_manager.get_cache_dir()
        else:
            return "/mnt/dionysus/coding/tg-text-translate/test-data/cache"
        
    def start_with_model_wait(self, config: Union[MultiModelServiceConfig, ServiceConfig], 
                            model_name: str, timeout: Optional[int] = None) -> str:
        """
        Start service and wait for specific model to be ready.
        
        Args:
            config: Service configuration
            model_name: Name of the model to wait for
            timeout: Maximum time to wait for model loading (auto-configured based on test markers if None)
            
        Returns:
            Service URL
            
        Raises:
            TimeoutError: If model is not ready within timeout
            RuntimeError: If service fails to start
        """
        # Use environment-configured timeout if available, otherwise fallback to provided timeout or default
        if timeout is None:
            timeout = int(os.environ.get('E2E_MODEL_LOADING_TIMEOUT', '1800'))  # 30 minutes default
        
        service_startup_timeout = int(os.environ.get('E2E_SERVICE_STARTUP_TIMEOUT', '60'))  # 1 minute default
        # Use retry mechanism for service startup
        def start_service_func():
            # Update config to use isolated cache directory if in parallel mode
            if self.is_parallel and hasattr(config, 'cache_dir'):
                config.cache_dir = self.get_cache_dir()
                
            if isinstance(config, MultiModelServiceConfig):
                return self.start_multimodel_service(config, timeout=service_startup_timeout)
            else:
                return self.start_service(config, timeout=service_startup_timeout)
        
        # Start service with retry logic
        service_url = self.start_with_retry(
            start_service_func,
            cleanup_func=self.cleanup
        )
        
        # Create client for monitoring
        api_key = config.api_key if hasattr(config, 'api_key') else "test-api-key"
        client = ComprehensiveTestClient(service_url, api_key)
        
        # Track model loading start time
        loading_start = time.time()
        self.progress_monitor.track_loading_stages(model_name, "requested")
        
        try:
            # Wait for model to be fully loaded with retry logic
            def wait_for_model_func():
                self.logger.info(f"Waiting for model '{model_name}' to be ready...")
                client.wait_for_model(model_name, timeout=timeout)
                return True
            
            self.load_model_with_retry(
                wait_for_model_func,
                cleanup_func=lambda: self.logger.info("Retrying model loading wait...")
            )
            
            # Record loading time
            loading_duration = time.time() - loading_start
            self.model_loading_times[model_name] = loading_duration
            self.progress_monitor.track_loading_stages(model_name, "ready", {
                "duration_seconds": loading_duration
            })
            
            self.logger.info(
                f"Model '{model_name}' ready after {loading_duration:.1f} seconds"
            )
            
            # Record performance metric
            self.performance_tracker.record_model_loading(model_name, loading_duration)
            
            return service_url
            
        except TimeoutError as e:
            # Capture logs on timeout
            logs = self.get_service_logs(max_lines=200)
            self.logger.error("Service logs on timeout:")
            for log in logs:
                self.logger.error(f"  {log}")
            
            # Clean up and re-raise
            self.cleanup()
            raise TimeoutError(
                f"Model '{model_name}' failed to load within {timeout} seconds. "
                f"Check logs for details."
            ) from e
        except Exception as e:
            self.cleanup()
            raise RuntimeError(f"Failed to start service with model: {e}") from e
    
    def start_multimodel_with_progress(self, config: MultiModelServiceConfig, 
                                     models: list[str], timeout: int = 3600) -> str:
        """
        Start multi-model service with progress tracking for multiple models.
        
        Args:
            config: Multi-model service configuration
            models: List of model names to wait for
            timeout: Total timeout for all models (default: 60 minutes)
            
        Returns:
            Service URL
        """
        # Start the service
        service_url = self.start_multimodel_service(config, timeout=60)
        
        # Create client
        client = ComprehensiveTestClient(service_url, config.api_key)
        
        # Wait for each model with progress tracking
        total_start = time.time()
        remaining_timeout = timeout
        
        for model_name in models:
            if remaining_timeout <= 0:
                raise TimeoutError("Total timeout exceeded while loading models")
            
            model_start = time.time()
            self.logger.info(f"Loading model {model_name}...")
            
            try:
                client.wait_for_model(model_name, timeout=int(remaining_timeout))
                
                model_duration = time.time() - model_start
                self.model_loading_times[model_name] = model_duration
                self.logger.info(
                    f"Model '{model_name}' loaded in {model_duration:.1f} seconds"
                )
                
            except TimeoutError:
                elapsed = time.time() - total_start
                self.logger.error(
                    f"Failed to load all models. Got through {models.index(model_name)} "
                    f"of {len(models)} models in {elapsed:.1f} seconds"
                )
                raise
            
            # Update remaining timeout
            elapsed = time.time() - total_start
            remaining_timeout = timeout - elapsed
        
        total_duration = time.time() - total_start
        self.logger.info(
            f"All {len(models)} models loaded successfully in {total_duration:.1f} seconds"
        )
        
        return service_url
    
    def get_model_loading_report(self) -> Dict[str, Any]:
        """
        Get comprehensive report on model loading performance.
        
        Returns:
            Dictionary with loading times and statistics
        """
        report = {
            "models_loaded": list(self.model_loading_times.keys()),
            "loading_times": self.model_loading_times.copy(),
            "total_models": len(self.model_loading_times),
            "performance_metrics": self.performance_tracker.get_summary()
        }
        
        if self.model_loading_times:
            times = list(self.model_loading_times.values())
            report["statistics"] = {
                "total_loading_time": sum(times),
                "average_loading_time": sum(times) / len(times),
                "min_loading_time": min(times),
                "max_loading_time": max(times)
            }
        
        return report
    
    def verify_model_readiness(self, model_name: str, api_key: str = "test-api-key") -> bool:
        """
        Verify that a model is truly ready for use.
        
        Args:
            model_name: Name of the model to verify
            api_key: API key for authentication
            
        Returns:
            True if model is ready and functional
        """
        if not self.service_url:
            return False
        
        client = ComprehensiveTestClient(self.service_url, api_key)
        
        try:
            # Check model status
            status = client.get_model_status(model_name)
            if not status["ready"]:
                return False
            
            # Perform a test translation to verify functionality
            test_result = client.translate(
                text="Hello world",
                source_lang="en",
                target_lang="es",
                model=model_name
            )
            
            return test_result.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Error verifying model readiness: {e}")
            return False
    
    def cleanup_with_report(self) -> Dict[str, Any]:
        """
        Clean up resources and return a performance report.
        
        Returns:
            Performance report dictionary
        """
        report = self.get_model_loading_report()
        self.cleanup()
        return report


class PerformanceTracker:
    """Tracks performance metrics for model operations."""
    
    def __init__(self):
        """Initialize performance tracker."""
        self.metrics = {
            "model_loading": [],
            "translations": [],
            "errors": []
        }
        self.logger = logging.getLogger(__name__)
    
    def record_model_loading(self, model_name: str, duration_seconds: float):
        """Record model loading performance."""
        self.metrics["model_loading"].append({
            "model": model_name,
            "duration_seconds": duration_seconds,
            "timestamp": time.time()
        })
        
        # Log performance baseline
        self.logger.info(
            f"Performance baseline - Model '{model_name}' loading: {duration_seconds:.1f}s"
        )
    
    def record_translation(self, model_name: str, text_length: int, 
                          duration_ms: float, success: bool):
        """Record translation performance."""
        self.metrics["translations"].append({
            "model": model_name,
            "text_length": text_length,
            "duration_ms": duration_ms,
            "success": success,
            "timestamp": time.time()
        })
    
    def record_error(self, operation: str, error_type: str, details: str):
        """Record error occurrence."""
        self.metrics["errors"].append({
            "operation": operation,
            "error_type": error_type,
            "details": details,
            "timestamp": time.time()
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        summary = {
            "model_loading": self._summarize_model_loading(),
            "translations": self._summarize_translations(),
            "errors": self._summarize_errors()
        }
        
        return summary
    
    def _summarize_model_loading(self) -> Dict[str, Any]:
        """Summarize model loading performance."""
        if not self.metrics["model_loading"]:
            return {"count": 0}
        
        loadings = self.metrics["model_loading"]
        durations = [m["duration_seconds"] for m in loadings]
        
        return {
            "count": len(loadings),
            "models": list(set(m["model"] for m in loadings)),
            "total_time_seconds": sum(durations),
            "average_time_seconds": sum(durations) / len(durations),
            "min_time_seconds": min(durations),
            "max_time_seconds": max(durations)
        }
    
    def _summarize_translations(self) -> Dict[str, Any]:
        """Summarize translation performance."""
        if not self.metrics["translations"]:
            return {"count": 0}
        
        translations = self.metrics["translations"]
        successful = [t for t in translations if t["success"]]
        
        summary = {
            "count": len(translations),
            "successful": len(successful),
            "failed": len(translations) - len(successful),
            "success_rate": len(successful) / len(translations)
        }
        
        if successful:
            durations = [t["duration_ms"] for t in successful]
            summary.update({
                "average_duration_ms": sum(durations) / len(durations),
                "min_duration_ms": min(durations),
                "max_duration_ms": max(durations)
            })
        
        return summary
    
    def _summarize_errors(self) -> Dict[str, Any]:
        """Summarize errors."""
        if not self.metrics["errors"]:
            return {"count": 0}
        
        errors = self.metrics["errors"]
        error_types = {}
        
        for error in errors:
            error_type = error["error_type"]
            if error_type not in error_types:
                error_types[error_type] = 0
            error_types[error_type] += 1
        
        return {
            "count": len(errors),
            "by_type": error_types,
            "operations": list(set(e["operation"] for e in errors))
        }