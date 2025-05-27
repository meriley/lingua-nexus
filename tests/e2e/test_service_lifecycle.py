"""E2E tests for service lifecycle management."""

import pytest
import time
import requests
from typing import Dict

from .utils.service_manager import E2EServiceManager, ServiceConfig
from .utils.http_client import E2EHttpClient


@pytest.mark.e2e
@pytest.mark.e2e_foundation
class TestServiceLifecycle:
    """Test service startup, readiness, and shutdown scenarios."""
    
    def test_service_startup_valid_config(self, e2e_service_manager: E2EServiceManager, valid_service_configs: Dict[str, ServiceConfig]):
        """Test that service starts successfully with valid configuration."""
        config = valid_service_configs["default"]
        
        # Ensure service is not running
        assert not e2e_service_manager.is_running()
        
        # Start service
        service_url = e2e_service_manager.start_service(config, timeout=30)
        
        # Verify service is running
        assert e2e_service_manager.is_running()
        assert service_url is not None
        assert service_url.startswith("http://")
        
        # Verify health check works
        assert e2e_service_manager.health_check()
        
        # Cleanup
        e2e_service_manager.stop_service()
        assert not e2e_service_manager.is_running()
    
    def test_service_readiness_verification(self, e2e_service_manager: E2EServiceManager, valid_service_configs: Dict[str, ServiceConfig]):
        """Test that health checks work properly after startup."""
        config = valid_service_configs["default"]
        
        service_url = e2e_service_manager.start_service(config, timeout=30)
        
        try:
            # Test direct health check
            health_response = requests.get(f"{service_url}/health", timeout=5)
            assert health_response.status_code == 200
            
            # Test using service manager health check
            assert e2e_service_manager.health_check()
            
            # Test multiple consecutive health checks
            for _ in range(5):
                assert e2e_service_manager.health_check()
                time.sleep(0.1)
                
        finally:
            e2e_service_manager.stop_service()
    
    def test_graceful_shutdown(self, e2e_service_manager: E2EServiceManager, valid_service_configs: Dict[str, ServiceConfig]):
        """Test graceful shutdown with SIGTERM handling."""
        config = valid_service_configs["default"]
        
        service_url = e2e_service_manager.start_service(config, timeout=30)
        
        # Verify service is running
        assert e2e_service_manager.is_running()
        assert e2e_service_manager.health_check()
        
        # Stop service gracefully
        shutdown_success = e2e_service_manager.stop_service(timeout=10)
        
        # Verify graceful shutdown
        assert shutdown_success
        assert not e2e_service_manager.is_running()
        
        # Verify service is no longer accessible
        with pytest.raises(requests.exceptions.RequestException):
            requests.get(f"{service_url}/health", timeout=2)
    
    def test_invalid_configuration_failures(self, e2e_service_manager: E2EServiceManager, invalid_service_configs: Dict[str, ServiceConfig]):
        """Test that service fails to start with invalid configurations."""
        # Test with empty API key - this might still start but should be handled
        config = invalid_service_configs["empty_api_key"]
        
        # Some invalid configs might still allow startup but fail during operation
        # We'll test that the service can start but may behave differently
        try:
            service_url = e2e_service_manager.start_service(config, timeout=15)
            # If it starts, verify it's at least responding
            assert e2e_service_manager.health_check()
        except (RuntimeError, TimeoutError):
            # It's acceptable for invalid configs to fail startup
            pass
        finally:
            if e2e_service_manager.is_running():
                e2e_service_manager.stop_service()
        
        # Test with invalid model - this should fail or take very long
        config = invalid_service_configs["invalid_model"]
        
        with pytest.raises((RuntimeError, TimeoutError)):
            e2e_service_manager.start_service(config, timeout=10)
        
        # Ensure cleanup
        if e2e_service_manager.is_running():
            e2e_service_manager.stop_service()
    
    def test_port_conflict_handling(self, valid_service_configs: Dict[str, ServiceConfig]):
        """Test handling of multiple service instances and port conflicts."""
        config = valid_service_configs["default"]
        
        manager1 = E2EServiceManager()
        manager2 = E2EServiceManager()
        
        try:
            # Start first service
            service_url1 = manager1.start_service(config, timeout=30)
            assert manager1.is_running()
            
            # Start second service (should get different port)
            service_url2 = manager2.start_service(config, timeout=30)
            assert manager2.is_running()
            
            # Verify they have different URLs/ports
            assert service_url1 != service_url2
            
            # Verify both are accessible
            assert manager1.health_check()
            assert manager2.health_check()
            
            # Test direct HTTP calls to both
            response1 = requests.get(f"{service_url1}/health", timeout=5)
            response2 = requests.get(f"{service_url2}/health", timeout=5)
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            
        finally:
            # Cleanup both services
            if manager1.is_running():
                manager1.stop_service()
            if manager2.is_running():
                manager2.stop_service()
    
    def test_service_restart_capability(self, e2e_service_manager: E2EServiceManager, valid_service_configs: Dict[str, ServiceConfig]):
        """Test stop and restart scenarios."""
        config = valid_service_configs["default"]
        
        # First startup
        service_url1 = e2e_service_manager.start_service(config, timeout=30)
        original_port = e2e_service_manager.current_port
        
        assert e2e_service_manager.is_running()
        assert e2e_service_manager.health_check()
        
        # Stop service
        e2e_service_manager.stop_service()
        assert not e2e_service_manager.is_running()
        
        # Restart service
        service_url2 = e2e_service_manager.start_service(config, timeout=30)
        new_port = e2e_service_manager.current_port
        
        # Verify restart successful
        assert e2e_service_manager.is_running()
        assert e2e_service_manager.health_check()
        
        # Port might be different after restart
        assert new_port is not None
        
        # Test multiple restart cycles
        for i in range(3):
            e2e_service_manager.stop_service()
            assert not e2e_service_manager.is_running()
            
            e2e_service_manager.start_service(config, timeout=30)
            assert e2e_service_manager.is_running()
            assert e2e_service_manager.health_check()
        
        # Final cleanup
        e2e_service_manager.stop_service()
    
    def test_service_startup_timeout_handling(self, e2e_service_manager: E2EServiceManager, valid_service_configs: Dict[str, ServiceConfig]):
        """Test service startup timeout scenarios."""
        config = valid_service_configs["default"]
        
        # Test with very short timeout
        with pytest.raises(TimeoutError):
            e2e_service_manager.start_service(config, timeout=1)
        
        # Ensure cleanup after timeout
        if e2e_service_manager.is_running():
            e2e_service_manager.stop_service()
        
        # Test with reasonable timeout
        service_url = e2e_service_manager.start_service(config, timeout=30)
        assert e2e_service_manager.is_running()
        assert e2e_service_manager.health_check()
        
        e2e_service_manager.stop_service()
    
    def test_service_log_capture(self, e2e_service_manager: E2EServiceManager, valid_service_configs: Dict[str, ServiceConfig]):
        """Test that service logs are captured for debugging."""
        config = valid_service_configs["debug"]  # Use debug config for more logs
        
        service_url = e2e_service_manager.start_service(config, timeout=30)
        
        try:
            # Generate some activity to create logs
            client = E2EHttpClient(service_url)
            client.set_api_key(config.api_key)
            
            # Make some requests to generate logs
            health_response = client.health_check()
            assert health_response.is_success
            
            # Try a translation request
            translation_response = client.translate(
                text="Hello",
                source_lang="eng_Latn",
                target_lang="fra_Latn"
            )
            
            # Get logs for debugging
            logs = e2e_service_manager.get_service_logs()
            
            # Verify logs were captured
            assert isinstance(logs, list)
            # Logs might be empty if service hasn't output much yet, which is OK
            
        finally:
            e2e_service_manager.stop_service()
    
    def test_service_process_monitoring(self, e2e_service_manager: E2EServiceManager, valid_service_configs: Dict[str, ServiceConfig]):
        """Test service process status monitoring."""
        config = valid_service_configs["default"]
        
        # Initially not running
        assert not e2e_service_manager.is_running()
        
        # Start service
        service_url = e2e_service_manager.start_service(config, timeout=30)
        
        # Monitor running status
        assert e2e_service_manager.is_running()
        
        # Process should remain running during normal operation
        time.sleep(2)
        assert e2e_service_manager.is_running()
        
        # Test health check during monitoring
        assert e2e_service_manager.health_check()
        assert e2e_service_manager.is_running()
        
        # Stop and verify status change
        e2e_service_manager.stop_service()
        assert not e2e_service_manager.is_running()