"""
Model Loading Time Baselines - TASK-010

This module provides comprehensive baseline measurements for model loading times
across different models, hardware configurations, and loading strategies.

These tests establish performance baselines for:
- Cold start loading times from disk
- Warm start loading times from cache
- Memory usage during model loading
- GPU memory allocation patterns
- Loading time variability and consistency
- Hardware-specific performance characteristics

The baselines help identify performance regressions and optimize model loading strategies.
"""

import asyncio
import json
import os
import time
import psutil
import pytest
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from unittest.mock import patch

from tests.e2e.utils.model_loading_monitor import ModelLoadingMonitor
from tests.e2e.utils.robust_service_manager import RobustServiceManager
from tests.e2e.utils.service_manager import MultiModelServiceConfig
from tests.e2e.utils.comprehensive_client import ComprehensiveTestClient


class ModelLoadingBaselineCollector:
    """Collects and analyzes model loading performance baselines."""
    
    def __init__(self):
        self.baselines: Dict[str, List[Dict]] = {}
        self.system_info = self._collect_system_info()
        
    def _collect_system_info(self) -> Dict:
        """Collect system information for baseline context."""
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            cuda_device_count = torch.cuda.device_count() if cuda_available else 0
            cuda_memory = torch.cuda.get_device_properties(0).total_memory if cuda_available else 0
        except ImportError:
            cuda_available = False
            cuda_device_count = 0
            cuda_memory = 0
            
        return {
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": psutil.virtual_memory().total / (1024**3),
            "cuda_available": cuda_available,
            "cuda_device_count": cuda_device_count,
            "cuda_memory_gb": cuda_memory / (1024**3) if cuda_memory else 0,
            "platform": os.uname().sysname if hasattr(os, 'uname') else 'unknown'
        }
    
    def record_baseline(self, model_name: str, loading_type: str, 
                       duration_seconds: float, memory_peak_mb: float,
                       gpu_memory_mb: float = 0, metadata: Optional[Dict] = None):
        """Record a model loading baseline measurement."""
        baseline_key = f"{model_name}_{loading_type}"
        
        if baseline_key not in self.baselines:
            self.baselines[baseline_key] = []
            
        record = {
            "model_name": model_name,
            "loading_type": loading_type,
            "duration_seconds": duration_seconds,
            "memory_peak_mb": memory_peak_mb,
            "gpu_memory_mb": gpu_memory_mb,
            "timestamp": time.time(),
            "system_info": self.system_info,
            "metadata": metadata or {}
        }
        
        self.baselines[baseline_key].append(record)
    
    def get_statistics(self, model_name: str, loading_type: str) -> Dict:
        """Calculate statistics for a specific baseline."""
        baseline_key = f"{model_name}_{loading_type}"
        records = self.baselines.get(baseline_key, [])
        
        if not records:
            return {}
            
        durations = [r["duration_seconds"] for r in records]
        memory_peaks = [r["memory_peak_mb"] for r in records]
        
        return {
            "count": len(records),
            "duration_mean": sum(durations) / len(durations),
            "duration_min": min(durations),
            "duration_max": max(durations),
            "duration_std": self._calculate_std(durations),
            "memory_mean": sum(memory_peaks) / len(memory_peaks),
            "memory_min": min(memory_peaks),
            "memory_max": max(memory_peaks)
        }
    
    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
    
    def save_baselines(self, filepath: str):
        """Save baselines to JSON file."""
        output = {
            "system_info": self.system_info,
            "baselines": self.baselines,
            "statistics": {key: self.get_statistics(*key.split("_", 1)) 
                          for key in self.baselines.keys()}
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)


@pytest.fixture
def baseline_collector():
    """Provide a baseline collector instance."""
    return ModelLoadingBaselineCollector()


@pytest.fixture
def monitor():
    """Provide a model loading monitor."""
    return ModelLoadingMonitor()


class TestModelLoadingBaselines:
    """Test suite for establishing model loading performance baselines."""
    
    @pytest.mark.full
    @pytest.mark.slow  
    @pytest.mark.baseline
    def test_nllb_cold_start_baseline(self, baseline_collector):
        """Establish baseline for NLLB cold start loading time."""
        # Clear any cached models
        self._clear_model_cache()
        
        config = MultiModelServiceConfig(
            api_key="test-api-key-nllb-cold",
            models_to_load="nllb",
            log_level="INFO",
            custom_env={
                "PYTEST_RUNNING": "true",
                "MODELS_TO_LOAD": "nllb",
                "MODEL_LOADING_TIMEOUT": "1800",  # 30 minutes
                "CLEAR_MODEL_CACHE": "true"
            }
        )
        
        start_memory = psutil.virtual_memory().used / (1024**2)
        start_time = time.time()
        
        try:
            service_manager = RobustServiceManager()
            
            # Start service and wait for model to load
            service_url = service_manager.start_with_model_wait(
                config=config,
                model_name="nllb",
                timeout=1800
            )
            
            loading_duration = time.time() - start_time
            end_memory = psutil.virtual_memory().used / (1024**2)
            memory_used = end_memory - start_memory
            
            # Get GPU memory if available
            gpu_memory = self._get_gpu_memory_usage()
            
            baseline_collector.record_baseline(
                model_name="nllb",
                loading_type="cold_start",
                duration_seconds=loading_duration,
                memory_peak_mb=memory_used,
                gpu_memory_mb=gpu_memory,
                metadata={"model_size": "1.2B", "quantization": "8bit"}
            )
            
            # Verify basic functionality by checking model is loaded
            client = ComprehensiveTestClient(service_url, config.api_key)
            models_response = client.list_models()
            assert models_response.status_code == 200
            assert "nllb" in str(models_response.response_data)
            
            # Clean up
            service_manager.stop_service()
                
        except Exception as e:
            pytest.fail(f"NLLB cold start baseline failed: {e}")
        
        # Assert reasonable baseline (should be under 2 minutes for CI)
        assert loading_duration < 120, f"NLLB cold start took {loading_duration:.1f}s, expected <120s"
    
    @pytest.mark.quick
    @pytest.mark.cached
    @pytest.mark.fast
    @pytest.mark.baseline
    def test_nllb_warm_start_baseline(self, baseline_collector):
        """Establish baseline for NLLB warm start loading time."""
        # Pre-warm the model cache by running a quick cold start first
        self._prewarm_nllb_cache()
        
        config = MultiModelServiceConfig(
            api_key="test-api-key-nllb-warm",
            models_to_load="nllb",
            log_level="INFO",
            custom_env={
                "PYTEST_RUNNING": "true",
                "MODELS_TO_LOAD": "nllb",
                "MODEL_LOADING_TIMEOUT": "600",  # 10 minutes should be enough for warm start
            }
        )
        
        start_memory = psutil.virtual_memory().used / (1024**2)
        start_time = time.time()
        
        try:
            service_manager = RobustServiceManager()
            
            service_url = service_manager.start_with_model_wait(
                config=config,
                model_name="nllb",
                timeout=600
            )
            
            loading_duration = time.time() - start_time
            end_memory = psutil.virtual_memory().used / (1024**2)
            memory_used = end_memory - start_memory
            
            gpu_memory = self._get_gpu_memory_usage()
            
            baseline_collector.record_baseline(
                model_name="nllb",
                loading_type="warm_start",
                duration_seconds=loading_duration,
                memory_peak_mb=memory_used,
                gpu_memory_mb=gpu_memory,
                metadata={"model_size": "1.2B", "quantization": "8bit", "cached": True}
            )
            
            # Verify functionality by checking model is loaded
            client = ComprehensiveTestClient(service_url, config.api_key)
            models_response = client.list_models()
            assert models_response.status_code == 200
            assert "nllb" in str(models_response.response_data)
            
            service_manager.stop_service()
                
        except Exception as e:
            pytest.fail(f"NLLB warm start baseline failed: {e}")
        
        # Warm start should be significantly faster than cold start
        assert loading_duration < 60, f"NLLB warm start took {loading_duration:.1f}s, expected <60s"
    
    def test_aya_cold_start_baseline(self, baseline_collector):
        """Establish baseline for Aya cold start loading time."""
        # Check if HF token is available
        if not os.environ.get("HF_TOKEN"):
            pytest.skip("HF_TOKEN not available for Aya model testing")
        
        # Clear any cached models
        self._clear_model_cache()
        
        config = MultiModelServiceConfig(
            api_key="test-api-key-aya-cold",
            models_to_load="aya",
            log_level="INFO",
            custom_env={
                "PYTEST_RUNNING": "true",
                "MODELS_TO_LOAD": "aya",
                "AYA_MODEL": "CohereForAI/aya-expanse-8b",
                "MODEL_LOADING_TIMEOUT": "3600",  # 60 minutes for 8B model
                "HF_TOKEN": os.environ.get("HF_TOKEN"),
                "PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:512",
                "CLEAR_MODEL_CACHE": "true"
            }
        )
        
        start_memory = psutil.virtual_memory().used / (1024**2)
        start_time = time.time()
        
        try:
            service_manager = RobustServiceManager()
            
            service_url = service_manager.start_with_model_wait(
                config=config,
                model_name="aya",
                timeout=3600
            )
            
            loading_duration = time.time() - start_time
            end_memory = psutil.virtual_memory().used / (1024**2)
            memory_used = end_memory - start_memory
            
            gpu_memory = self._get_gpu_memory_usage()
            
            baseline_collector.record_baseline(
                model_name="aya",
                loading_type="cold_start",
                duration_seconds=loading_duration,
                memory_peak_mb=memory_used,
                gpu_memory_mb=gpu_memory,
                metadata={"model_size": "8B", "quantization": "4bit", "model_path": "CohereForAI/aya-expanse-8b"}
            )
            
            # Verify basic functionality by checking model is loaded
            client = ComprehensiveTestClient(service_url, config.api_key)
            models_response = client.list_models()
            assert models_response.status_code == 200
            assert "aya" in str(models_response.response_data)
            
            service_manager.stop_service()
                
        except Exception as e:
            pytest.fail(f"Aya cold start baseline failed: {e}")
        
        # Aya 8B model should load within reasonable time (allowing more time for large model)
        assert loading_duration < 1800, f"Aya cold start took {loading_duration:.1f}s, expected <1800s"
    
    def test_loading_consistency_baseline(self, baseline_collector):
        """Test consistency of loading times across multiple runs."""
        loading_times = []
        
        # Run NLLB loading 3 times to measure consistency
        for run_number in range(3):
            self._clear_model_cache()
            
            config = MultiModelServiceConfig(
                api_key=f"test-api-key-consistency-{run_number}",
                models_to_load="nllb",
                log_level="INFO",
                custom_env={
                    "PYTEST_RUNNING": "true",
                    "MODELS_TO_LOAD": "nllb",
                    "MODEL_LOADING_TIMEOUT": "1800",
                    "CLEAR_MODEL_CACHE": "true"
                }
            )
            
            start_time = time.time()
            
            try:
                service_manager = RobustServiceManager()
                
                service_url = service_manager.start_with_model_wait(
                    config=config,
                    model_name="nllb",
                    timeout=1800
                )
                
                loading_duration = time.time() - start_time
                loading_times.append(loading_duration)
                
                baseline_collector.record_baseline(
                    model_name="nllb",
                    loading_type="consistency_test",
                    duration_seconds=loading_duration,
                    memory_peak_mb=0,  # Not measuring memory for consistency test
                    metadata={"run_number": run_number, "total_runs": 3}
                )
                
                service_manager.stop_service()
                    
            except Exception as e:
                pytest.fail(f"NLLB consistency test run {run_number} failed: {e}")
        
        # Calculate consistency metrics
        mean_time = sum(loading_times) / len(loading_times)
        max_deviation = max(abs(t - mean_time) for t in loading_times)
        coefficient_of_variation = (max_deviation / mean_time) * 100
        
        # Loading times should be reasonably consistent (within 50% variation)
        assert coefficient_of_variation < 50, f"Loading time variation too high: {coefficient_of_variation:.1f}%"
    
    @pytest.mark.slow
    def test_save_baseline_report(self, baseline_collector):
        """Save comprehensive baseline report."""
        # This test should run last to collect all baseline data
        report_path = "/mnt/dionysus/coding/tg-text-translate/test_reports/model_loading_baselines.json"
        baseline_collector.save_baselines(report_path)
        
        # Verify report was created
        assert Path(report_path).exists(), "Baseline report not created"
        
        # Verify report content
        with open(report_path, 'r') as f:
            report_data = json.load(f)
        
        assert "system_info" in report_data
        assert "baselines" in report_data
        assert "statistics" in report_data
        
        # Report should contain at least some baseline data
        assert len(report_data["baselines"]) > 0, "No baseline data collected"
    
    # Helper methods
    
    def _clear_model_cache(self):
        """Clear HuggingFace model cache to ensure cold start."""
        cache_dirs = [
            os.path.expanduser("~/.cache/huggingface"),
            "/tmp/huggingface_cache",
            "/app/.cache/huggingface"
        ]
        
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                try:
                    import shutil
                    shutil.rmtree(cache_dir, ignore_errors=True)
                except Exception:
                    pass  # Ignore cleanup errors
    
    def _prewarm_nllb_cache(self):
        """Pre-warm NLLB model cache by running a quick load."""
        config = MultiModelServiceConfig(
            api_key="test-api-key-prewarm",
            models_to_load="nllb",
            log_level="ERROR",  # Minimize output
            custom_env={
                "PYTEST_RUNNING": "true",
                "MODELS_TO_LOAD": "nllb",
                "MODEL_LOADING_TIMEOUT": "600"
            }
        )
        
        try:
            service_manager = RobustServiceManager()
            service_url = service_manager.start_with_model_wait(
                config=config,
                model_name="nllb",
                timeout=600
            )
            # Just load and stop to warm cache
            service_manager.stop_service()
        except Exception:
            pass  # Ignore prewarm failures
    
    def _get_gpu_memory_usage(self) -> float:
        """Get current GPU memory usage in MB."""
        try:
            import torch
            if torch.cuda.is_available():
                return torch.cuda.memory_allocated() / (1024**2)
        except ImportError:
            pass
        return 0.0


if __name__ == "__main__":
    # Can be run standalone for baseline collection
    pytest.main([__file__, "-v", "--tb=short"])