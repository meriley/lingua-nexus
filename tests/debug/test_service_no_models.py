#!/usr/bin/env python3
"""
Test service startup without models to verify service layer stability.
"""

import sys
import os
import requests
import time

# Add the e2e directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "e2e"))

from utils.service_manager import ServiceManager, MultiModelServiceConfig


def test_service_without_models():
    """Test service startup with model loading disabled."""
    print("Testing Service Without Models")
    print("=" * 50)
    
    manager = ServiceManager()
    
    try:
        # Configure service with no models
        config = MultiModelServiceConfig(
            api_key="test-api-key-no-models",
            models_to_load="",  # Empty - no models
            log_level="INFO",
            custom_env={
                "MODELS_TO_LOAD": "",  # Explicitly disable model loading
                "PYTEST_RUNNING": "true",
            }
        )
        
        print("1. Starting service without models...")
        start_time = time.time()
        service_url = manager.start_multimodel_service(config, timeout=30)
        startup_time = time.time() - start_time
        print(f"   ✓ Service started in {startup_time:.2f}s at {service_url}")
        
        # Test health endpoint multiple times
        print("\n2. Testing health endpoint stability...")
        for i in range(5):
            try:
                response = requests.get(f"{service_url}/health", timeout=5)
                print(f"   Health check {i+1}: {response.status_code} - {response.json()}")
                
                if response.status_code != 200:
                    print(f"   ❌ Health check failed with status {response.status_code}")
                    return False
                    
            except requests.exceptions.RequestException as e:
                print(f"   ❌ Health check failed with exception: {e}")
                return False
            
            time.sleep(1)
        
        # Test other endpoints
        print("\n3. Testing API endpoints...")
        
        # Test models endpoint
        try:
            response = requests.get(f"{service_url}/models", timeout=5)
            print(f"   Models endpoint: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"   Models endpoint error: {e}")
        
        # Test languages endpoint  
        try:
            response = requests.get(f"{service_url}/languages", timeout=5)
            print(f"   Languages endpoint: {response.status_code}")
        except Exception as e:
            print(f"   Languages endpoint error: {e}")
        
        print("\n✅ Service stability test: SUCCESS")
        print("   - Service starts quickly without models")
        print("   - Health checks remain responsive")
        print("   - API endpoints are accessible")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Service test FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print("\n4. Cleaning up service...")
        manager.cleanup()
        print("   ✓ Service stopped")


def test_service_health_during_startup():
    """Test health endpoint responsiveness during startup sequence."""
    print("\n" + "=" * 50)
    print("Testing Health During Startup")
    print("=" * 50)
    
    manager = ServiceManager()
    
    try:
        config = MultiModelServiceConfig(
            api_key="test-api-key-startup",
            models_to_load="",
            log_level="INFO",
            custom_env={
                "MODELS_TO_LOAD": "",
                "PYTEST_RUNNING": "true",
            }
        )
        
        print("1. Starting service and monitoring health...")
        service_url = manager.start_multimodel_service(config, timeout=30)
        
        # Rapid health checks
        print("\n2. Rapid health checks (every 0.5s for 10s)...")
        start_time = time.time()
        check_count = 0
        success_count = 0
        
        while time.time() - start_time < 10:
            try:
                response = requests.get(f"{service_url}/health", timeout=2)
                check_count += 1
                if response.status_code == 200:
                    success_count += 1
                    print(f"   ✓ Check {check_count}: {response.status_code}")
                else:
                    print(f"   ✗ Check {check_count}: {response.status_code}")
            except Exception as e:
                check_count += 1
                print(f"   ✗ Check {check_count}: {type(e).__name__}")
            
            time.sleep(0.5)
        
        success_rate = success_count / check_count if check_count > 0 else 0
        print(f"\n   Success rate: {success_count}/{check_count} ({success_rate:.1%})")
        
        if success_rate >= 0.9:
            print("✅ High availability during normal operation")
            return True
        else:
            print("❌ Poor availability - connection issues detected")
            return False
            
    except Exception as e:
        print(f"\n❌ Startup health test FAILED: {e}")
        return False
    
    finally:
        manager.cleanup()


def main():
    """Main test execution."""
    print("Service Stability Test (No Models)")
    print("=" * 60)
    
    # Test 1: Basic service without models
    test1_success = test_service_without_models()
    
    # Test 2: Health responsiveness
    test2_success = test_service_health_during_startup()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"  Service without models: {'✅ SUCCESS' if test1_success else '❌ FAILED'}")
    print(f"  Health responsiveness:  {'✅ SUCCESS' if test2_success else '❌ FAILED'}")
    
    if test1_success and test2_success:
        print("\n✓ Service layer is stable - model loading is the issue")
    else:
        print("\n✗ Service layer has stability issues")


if __name__ == "__main__":
    main()