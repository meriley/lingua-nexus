"""
Model Loading Time Baseline Tests

This module establishes and verifies performance baselines for model loading times.
These baselines are used for regression detection and performance monitoring.
"""

import pytest
import sys
import os
import time
import json
from typing import Dict, Any

# Add the e2e directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.robust_service_manager import RobustServiceManager
from utils.service_manager import MultiModelServiceConfig
from utils.comprehensive_client import ComprehensiveTestClient


class TestModelLoadingBaselines:
    """Test suite for establishing model loading performance baselines."""
    
    @pytest.mark.parametrize("model_config", [
        {
            "model_name": "nllb",
            "models_to_load": "nllb",
            "model_env": "facebook/nllb-200-distilled-600M",
            "expected_max_seconds": 300,  # 5 minutes baseline
            "size_gb": 4.6,
            "description": "NLLB 600M distilled model"
        },
        {
            "model_name": "aya", 
            "models_to_load": "aya",
            "model_env": "CohereForAI/aya-expanse-8b",
            "expected_max_seconds": 3600,  # 60 minutes baseline
            "size_gb": 15.0,
            "description": "Aya Expanse 8B model"
        }
    ])
    def test_model_loading_time_baseline(self, model_config):
        """Test and record model loading time baselines."""
        manager = RobustServiceManager()
        
        try:
            # Prepare model-specific configuration
            env_config = {
                "PYTEST_RUNNING": "true",
                "MODELS_TO_LOAD": model_config["models_to_load"],
                "MODEL_CACHE_DIR": os.path.expanduser("~/.cache/huggingface/transformers"),
                "HF_HOME": os.path.expanduser("~/.cache/huggingface"),
                "TRANSFORMERS_CACHE": os.path.expanduser("~/.cache/huggingface/transformers"),
                "MODEL_LOADING_TIMEOUT": str(model_config["expected_max_seconds"]),
                "LOG_MODEL_LOADING_PROGRESS": "true",
            }
            
            # Add model-specific environment variables
            if model_config["model_name"] == "nllb":
                env_config["NLLB_MODEL"] = model_config["model_env"]
            elif model_config["model_name"] == "aya":
                env_config["AYA_MODEL"] = model_config["model_env"]
                env_config["HF_TOKEN"] = os.environ.get("HF_TOKEN", "test-hf-token-placeholder")
                env_config["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"
            
            config = MultiModelServiceConfig(
                api_key=f"test-api-key-{model_config['model_name']}-baseline",
                models_to_load=model_config["models_to_load"],
                log_level="INFO",
                custom_env=env_config
            )
            
            print(f"\nTesting {model_config['description']} loading baseline...")
            print(f"Expected max loading time: {model_config['expected_max_seconds']} seconds")
            print(f"Model size: {model_config['size_gb']} GB")
            
            # Measure loading time
            loading_start = time.time()
            
            service_url = manager.start_with_model_wait(
                config=config,
                model_name=model_config["model_name"],
                timeout=model_config["expected_max_seconds"]
            )
            
            loading_duration = time.time() - loading_start
            
            # Verify model is ready
            client = ComprehensiveTestClient(
                service_url, 
                api_key=f"test-api-key-{model_config['model_name']}-baseline"
            )
            
            assert manager.verify_model_readiness(
                model_config["model_name"],
                api_key=f"test-api-key-{model_config['model_name']}-baseline"
            ), f"{model_config['model_name']} model not ready after loading"
            
            # Calculate performance metrics
            loading_rate_gb_per_min = (model_config["size_gb"] / loading_duration) * 60
            
            baseline_data = {
                "model_name": model_config["model_name"],
                "model_description": model_config["description"],
                "model_size_gb": model_config["size_gb"],
                "loading_time_seconds": loading_duration,
                "loading_time_minutes": loading_duration / 60,
                "loading_rate_gb_per_minute": loading_rate_gb_per_min,
                "expected_max_seconds": model_config["expected_max_seconds"],
                "within_baseline": loading_duration <= model_config["expected_max_seconds"],
                "test_timestamp": time.time(),
                "performance_category": self._categorize_performance(loading_duration, model_config["expected_max_seconds"])
            }
            
            # Save baseline data
            baseline_file = f"/tmp/{model_config['model_name']}_loading_baseline.json"
            with open(baseline_file, "w") as f:
                json.dump(baseline_data, f, indent=2)
            
            # Assertions for baseline verification
            assert loading_duration <= model_config["expected_max_seconds"], \
                f"{model_config['model_name']} loading time {loading_duration:.1f}s " + \
                f"exceeds baseline {model_config['expected_max_seconds']}s"
            
            # Log results
            print(f"✓ {model_config['description']} baseline results:")
            print(f"  Loading time: {loading_duration:.1f} seconds ({loading_duration/60:.1f} minutes)")
            print(f"  Loading rate: {loading_rate_gb_per_min:.2f} GB/minute")
            print(f"  Performance: {baseline_data['performance_category']}")
            print(f"  Within baseline: {'✓' if baseline_data['within_baseline'] else '✗'}")
            print(f"  Baseline saved to: {baseline_file}")
            
        finally:
            manager.cleanup()
    
    def _categorize_performance(self, actual_time: float, baseline_time: float) -> str:
        """Categorize loading performance relative to baseline."""
        ratio = actual_time / baseline_time
        
        if ratio <= 0.5:
            return "Excellent"
        elif ratio <= 0.7:
            return "Good"
        elif ratio <= 0.9:
            return "Acceptable"
        elif ratio <= 1.0:
            return "Baseline"
        else:
            return "Below Baseline"
    
    def test_sequential_loading_baseline(self):
        """Test baseline for loading models sequentially."""
        manager = RobustServiceManager()
        
        try:
            # Test NLLB first, then Aya
            models_sequence = [
                {
                    "model_name": "nllb",
                    "models_to_load": "nllb",
                    "env_key": "NLLB_MODEL",
                    "env_value": "facebook/nllb-200-distilled-600M",
                    "expected_time": 300
                },
                {
                    "model_name": "aya",
                    "models_to_load": "aya", 
                    "env_key": "AYA_MODEL",
                    "env_value": "CohereForAI/aya-expanse-8b",
                    "expected_time": 3600
                }
            ]
            
            sequential_results = {
                "test_type": "sequential_loading",
                "test_timestamp": time.time(),
                "models": []
            }
            
            total_start = time.time()
            
            for i, model_config in enumerate(models_sequence):
                print(f"\nSequential loading {i+1}/{len(models_sequence)}: {model_config['model_name']}")
                
                env_config = {
                    "PYTEST_RUNNING": "true",
                    "MODELS_TO_LOAD": model_config["models_to_load"],
                    model_config["env_key"]: model_config["env_value"],
                    "MODEL_CACHE_DIR": os.path.expanduser("~/.cache/huggingface/transformers"),
                    "HF_HOME": os.path.expanduser("~/.cache/huggingface"),
                    "TRANSFORMERS_CACHE": os.path.expanduser("~/.cache/huggingface/transformers"),
                    "MODEL_LOADING_TIMEOUT": str(model_config["expected_time"]),
                    "LOG_MODEL_LOADING_PROGRESS": "true",
                }
                
                if model_config["model_name"] == "aya":
                    env_config["HF_TOKEN"] = os.environ.get("HF_TOKEN", "test-hf-token-placeholder")
                    env_config["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"
                
                config = MultiModelServiceConfig(
                    api_key=f"test-api-key-sequential-{model_config['model_name']}",
                    models_to_load=model_config["models_to_load"],
                    log_level="INFO",
                    custom_env=env_config
                )
                
                # Clean up previous service if exists
                if i > 0:
                    manager.cleanup()
                    manager = RobustServiceManager()
                
                model_start = time.time()
                
                service_url = manager.start_with_model_wait(
                    config=config,
                    model_name=model_config["model_name"],
                    timeout=model_config["expected_time"]
                )
                
                model_duration = time.time() - model_start
                
                # Verify model readiness
                client = ComprehensiveTestClient(
                    service_url,
                    api_key=f"test-api-key-sequential-{model_config['model_name']}"
                )
                
                ready = manager.verify_model_readiness(
                    model_config["model_name"],
                    api_key=f"test-api-key-sequential-{model_config['model_name']}"
                )
                
                model_result = {
                    "model_name": model_config["model_name"],
                    "loading_time_seconds": model_duration,
                    "expected_time_seconds": model_config["expected_time"],
                    "within_baseline": model_duration <= model_config["expected_time"],
                    "ready": ready,
                    "sequence_position": i + 1
                }
                
                sequential_results["models"].append(model_result)
                
                print(f"  ✓ {model_config['model_name']}: {model_duration:.1f}s " +
                      f"({'within' if model_result['within_baseline'] else 'exceeds'} baseline)")
            
            total_duration = time.time() - total_start
            sequential_results["total_duration_seconds"] = total_duration
            sequential_results["total_duration_minutes"] = total_duration / 60
            
            # Save sequential results
            sequential_file = "/tmp/sequential_loading_baseline.json"
            with open(sequential_file, "w") as f:
                json.dump(sequential_results, f, indent=2)
            
            print(f"\n✓ Sequential loading baseline:")
            print(f"  Total time: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
            print(f"  Results saved to: {sequential_file}")
            
            # Verify all models loaded within their individual baselines
            for model_result in sequential_results["models"]:
                assert model_result["within_baseline"], \
                    f"Sequential loading of {model_result['model_name']} " + \
                    f"exceeded baseline: {model_result['loading_time_seconds']:.1f}s > " + \
                    f"{model_result['expected_time_seconds']}s"
                assert model_result["ready"], \
                    f"Model {model_result['model_name']} not ready after sequential loading"
            
        finally:
            manager.cleanup()
    
    def test_parallel_loading_baseline(self):
        """Test baseline for loading both models in parallel (if supported)."""
        manager = RobustServiceManager()
        
        try:
            print("\nTesting parallel model loading baseline...")
            
            # Configure service to load both models
            config = MultiModelServiceConfig(
                api_key="test-api-key-parallel-loading",
                models_to_load="nllb,aya",  # Both models
                log_level="INFO",
                custom_env={
                    "PYTEST_RUNNING": "true",
                    "MODELS_TO_LOAD": "nllb,aya",
                    "NLLB_MODEL": "facebook/nllb-200-distilled-600M",
                    "AYA_MODEL": "CohereForAI/aya-expanse-8b",
                    "MODEL_CACHE_DIR": os.path.expanduser("~/.cache/huggingface/transformers"),
                    "HF_HOME": os.path.expanduser("~/.cache/huggingface"),
                    "TRANSFORMERS_CACHE": os.path.expanduser("~/.cache/huggingface/transformers"),
                    "HF_TOKEN": os.environ.get("HF_TOKEN", "test-hf-token-placeholder"),
                    "MODEL_LOADING_TIMEOUT": "3600",  # 60 minutes for both
                    "LOG_MODEL_LOADING_PROGRESS": "true",
                    "PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:512",
                }
            )
            
            parallel_start = time.time()
            
            # Use the multi-model loading capability
            service_url = manager.start_multimodel_with_progress(
                config=config,
                models=["nllb", "aya"],
                timeout=3600  # 60 minutes total
            )
            
            parallel_duration = time.time() - parallel_start
            
            # Verify both models are ready
            client = ComprehensiveTestClient(service_url, api_key="test-api-key-parallel-loading")
            
            nllb_ready = manager.verify_model_readiness("nllb", api_key="test-api-key-parallel-loading")
            aya_ready = manager.verify_model_readiness("aya", api_key="test-api-key-parallel-loading")
            
            # Get loading report from manager
            loading_report = manager.get_model_loading_report()
            
            parallel_results = {
                "test_type": "parallel_loading",
                "test_timestamp": time.time(),
                "total_duration_seconds": parallel_duration,
                "total_duration_minutes": parallel_duration / 60,
                "nllb_ready": nllb_ready,
                "aya_ready": aya_ready,
                "both_ready": nllb_ready and aya_ready,
                "loading_report": loading_report,
                "efficiency_vs_sequential": None  # Will be calculated if sequential data exists
            }
            
            # Try to compare with sequential loading if data exists
            try:
                with open("/tmp/sequential_loading_baseline.json", "r") as f:
                    sequential_data = json.load(f)
                    sequential_total = sequential_data["total_duration_seconds"]
                    efficiency = (sequential_total - parallel_duration) / sequential_total
                    parallel_results["efficiency_vs_sequential"] = efficiency
                    parallel_results["sequential_duration_seconds"] = sequential_total
            except FileNotFoundError:
                pass
            
            # Save parallel results
            parallel_file = "/tmp/parallel_loading_baseline.json"
            with open(parallel_file, "w") as f:
                json.dump(parallel_results, f, indent=2)
            
            print(f"✓ Parallel loading baseline:")
            print(f"  Total time: {parallel_duration:.1f} seconds ({parallel_duration/60:.1f} minutes)")
            print(f"  NLLB ready: {'✓' if nllb_ready else '✗'}")
            print(f"  Aya ready: {'✓' if aya_ready else '✗'}")
            if parallel_results["efficiency_vs_sequential"] is not None:
                print(f"  Efficiency vs sequential: {parallel_results['efficiency_vs_sequential']:+.1%}")
            print(f"  Results saved to: {parallel_file}")
            
            # Assertions
            assert nllb_ready, "NLLB not ready after parallel loading"
            assert aya_ready, "Aya not ready after parallel loading"
            assert parallel_duration <= 3600, f"Parallel loading exceeded 60 minutes: {parallel_duration:.1f}s"
            
        finally:
            manager.cleanup()
    
    def test_cold_vs_warm_loading_comparison(self):
        """Compare cold loading (first time) vs warm loading (cached) performance."""
        print("\nTesting cold vs warm loading comparison...")
        
        # This test assumes models might be cached from previous runs
        # We'll test NLLB twice to compare warm loading performance
        
        manager = RobustServiceManager()
        loading_times = []
        
        for attempt in range(2):
            try:
                print(f"\nNLLB loading attempt {attempt + 1}/2 ({'cold' if attempt == 0 else 'warm'} loading)")
                
                config = MultiModelServiceConfig(
                    api_key=f"test-api-key-loading-{attempt}",
                    models_to_load="nllb",
                    log_level="INFO",
                    custom_env={
                        "PYTEST_RUNNING": "true",
                        "MODELS_TO_LOAD": "nllb",
                        "NLLB_MODEL": "facebook/nllb-200-distilled-600M",
                        "MODEL_CACHE_DIR": os.path.expanduser("~/.cache/huggingface/transformers"),
                        "HF_HOME": os.path.expanduser("~/.cache/huggingface"),
                        "TRANSFORMERS_CACHE": os.path.expanduser("~/.cache/huggingface/transformers"),
                        "MODEL_LOADING_TIMEOUT": "300",
                        "LOG_MODEL_LOADING_PROGRESS": "true",
                    }
                )
                
                load_start = time.time()
                
                service_url = manager.start_with_model_wait(
                    config=config,
                    model_name="nllb",
                    timeout=300
                )
                
                load_duration = time.time() - load_start
                loading_times.append(load_duration)
                
                # Verify model readiness
                ready = manager.verify_model_readiness("nllb", api_key=f"test-api-key-loading-{attempt}")
                assert ready, f"NLLB not ready on attempt {attempt + 1}"
                
                print(f"  ✓ Loading time: {load_duration:.1f} seconds")
                
                # Cleanup between attempts
                manager.cleanup()
                
                # Brief pause between attempts
                if attempt == 0:
                    time.sleep(5)
                
            except Exception as e:
                print(f"  ✗ Loading attempt {attempt + 1} failed: {e}")
                loading_times.append(None)
            finally:
                if attempt < 1:  # Don't cleanup after last attempt in finally
                    manager.cleanup()
                    manager = RobustServiceManager()
        
        try:
            # Analyze cold vs warm performance
            comparison_results = {
                "test_type": "cold_vs_warm_loading",
                "test_timestamp": time.time(),
                "cold_loading_seconds": loading_times[0] if loading_times[0] else None,
                "warm_loading_seconds": loading_times[1] if len(loading_times) > 1 and loading_times[1] else None,
                "improvement": None,
                "improvement_percentage": None
            }
            
            if loading_times[0] and len(loading_times) > 1 and loading_times[1]:
                cold_time = loading_times[0]
                warm_time = loading_times[1]
                improvement = cold_time - warm_time
                improvement_pct = (improvement / cold_time) * 100
                
                comparison_results["improvement"] = improvement
                comparison_results["improvement_percentage"] = improvement_pct
                
                print(f"\n✓ Cold vs Warm loading comparison:")
                print(f"  Cold loading: {cold_time:.1f} seconds")
                print(f"  Warm loading: {warm_time:.1f} seconds")
                print(f"  Improvement: {improvement:.1f} seconds ({improvement_pct:+.1f}%)")
            else:
                print(f"\n⚠ Cold vs Warm comparison incomplete - some loading attempts failed")
            
            # Save comparison results
            comparison_file = "/tmp/cold_warm_loading_comparison.json"
            with open(comparison_file, "w") as f:
                json.dump(comparison_results, f, indent=2)
            print(f"  Results saved to: {comparison_file}")
            
        finally:
            manager.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])