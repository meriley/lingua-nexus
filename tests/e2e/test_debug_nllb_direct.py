"""
Debug test to run NLLB directly without robust infrastructure
to isolate connection reset issues.
"""

import os
import sys
import time
import requests
import subprocess
import signal
from pathlib import Path

# Add the e2e directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.service_manager import ServiceManager, MultiModelServiceConfig


def test_debug_nllb_direct():
    """Debug test to run NLLB service directly and check for issues."""
    manager = ServiceManager()
    
    try:
        # Simple configuration
        config = MultiModelServiceConfig(
            api_key="development-key",  # Use the default API key
            models_to_load="nllb",
            log_level="DEBUG",  # More verbose logging
            custom_env={
                "API_KEY": "development-key",  # Set the API key in server environment
                "MODELS_TO_LOAD": "nllb",
                "NLLB_MODEL": "facebook/nllb-200-distilled-600M",
                "MODEL_CACHE_DIR": os.path.expanduser("~/.cache/huggingface/transformers"),
                "HF_HOME": os.path.expanduser("~/.cache/huggingface"),
                "TRANSFORMERS_CACHE": os.path.expanduser("~/.cache/huggingface/transformers"),
                "MODEL_LOADING_TIMEOUT": "300",  # 5 minutes only
                "LOG_MODEL_LOADING_PROGRESS": "true",
                "CUDA_VISIBLE_DEVICES": "0",  # Ensure using GPU 0
                "PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:512",  # Prevent memory fragmentation
            }
        )
        
        print("🚀 Starting NLLB service...")
        start_time = time.time()
        
        # Start service
        service_url = manager.start_multimodel_service(config, timeout=60)
        print(f"✅ Service started at {service_url}")
        
        # Monitor health for 10 minutes
        print("🔍 Monitoring service health...")
        check_interval = 10  # Check every 10 seconds
        max_checks = 60  # 10 minutes worth of checks
        successful_checks = 0
        
        for check_num in range(max_checks):
            elapsed = time.time() - start_time
            print(f"\n--- Health Check {check_num + 1} (at {elapsed:.1f}s) ---")
            
            try:
                response = requests.get(f"{service_url}/health", timeout=10)
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"Health data: {data}")
                    successful_checks += 1
                    
                    # If we have models loaded, try to get models info
                    if data.get("models_loaded", 0) > 0:
                        try:
                            models_response = requests.get(
                                f"{service_url}/models", 
                                timeout=10,
                                headers={"X-API-Key": "development-key"}
                            )
                            if models_response.status_code == 200:
                                models_data = models_response.json()
                                print(f"Models data: {models_data}")
                                
                                # Check if NLLB is ready
                                if "nllb" in models_data:
                                    model_status = models_data["nllb"].get("status", "unknown")
                                    print(f"NLLB status: {model_status}")
                                    
                                    if model_status == "ready":
                                        print("🎉 NLLB model is ready!")
                                        
                                        # Try a test translation
                                        try:
                                            translate_data = {
                                                "text": "Hello world",
                                                "source_lang": "eng_Latn",
                                                "target_lang": "spa_Latn",
                                                "model": "nllb"
                                            }
                                            
                                            translate_response = requests.post(
                                                f"{service_url}/translate",
                                                json=translate_data,
                                                timeout=30,
                                                headers={"X-API-Key": "development-key"}
                                            )
                                            
                                            print(f"Translation test: {translate_response.status_code}")
                                            if translate_response.status_code == 200:
                                                result = translate_response.json()
                                                print(f"Translation result: {result}")
                                                print("✅ Translation test successful!")
                                                return  # Success!
                                            else:
                                                print(f"Translation failed: {translate_response.text}")
                                                
                                        except Exception as e:
                                            print(f"Translation test error: {e}")
                        except Exception as e:
                            print(f"Models endpoint error: {e}")
                else:
                    print(f"Health check failed: {response.text}")
                    
            except requests.exceptions.ConnectionError as e:
                print(f"❌ Connection error: {e}")
                
                # Check if process is still running
                if manager.process:
                    poll_result = manager.process.poll()
                    if poll_result is not None:
                        print(f"⚠️  Process died with exit code: {poll_result}")
                        
                        # Get any remaining output
                        if manager.process.stdout:
                            remaining_output = manager.process.stdout.read()
                            if remaining_output:
                                print(f"Process output: {remaining_output}")
                        break
                    else:
                        print("Process is still running...")
                else:
                    print("No process found!")
                    break
                    
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
            
            # Wait before next check
            if check_num < max_checks - 1:
                print(f"Waiting {check_interval} seconds...")
                time.sleep(check_interval)
        
        print(f"\n📊 Final Stats:")
        print(f"Total runtime: {time.time() - start_time:.1f} seconds")
        print(f"Successful health checks: {successful_checks}/{max_checks}")
        
        # Get service logs
        logs = manager.get_service_logs(max_lines=50)
        print("\n📝 Recent service logs:")
        for log in logs[-20:]:  # Last 20 lines
            print(f"  {log}")
            
    finally:
        print("\n🧹 Cleaning up...")
        manager.cleanup()


if __name__ == "__main__":
    test_debug_nllb_direct()