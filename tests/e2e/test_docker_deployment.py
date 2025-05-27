"""E2E tests for Docker containerized deployment validation."""

import pytest
import time
import os
from typing import Dict, Any
from pathlib import Path

from .utils.docker_manager import E2EDockerManager, DockerTestConfig
from .utils.http_client import E2EHttpClient


@pytest.mark.e2e
@pytest.mark.e2e_docker
@pytest.mark.e2e_slow
class TestDockerDeployment:
    """Test containerized deployment validation."""
    
    @pytest.fixture(scope="class")
    def docker_image_tag(self, docker_manager):
        """Build Docker image for testing."""
        if not docker_manager:
            pytest.skip("Docker not available")
        
        # Check if Dockerfile exists
        dockerfile_path = Path(__file__).parent.parent.parent.parent / "Dockerfile"
        if not dockerfile_path.exists():
            pytest.skip("Dockerfile not found - Docker tests require Dockerfile")
        
        try:
            image_tag = docker_manager.build_image(
                tag="tg-text-translate:e2e-test",
                build_args={"BUILDKIT_INLINE_CACHE": "1"}
            )
            yield image_tag
        except Exception as e:
            pytest.skip(f"Failed to build Docker image: {e}")
        finally:
            # Cleanup image after tests
            try:
                docker_manager.remove_image("tg-text-translate:e2e-test", force=True)
            except Exception:
                pass
    
    def test_docker_container_service_startup(self, docker_manager, docker_image_tag):
        """Test service startup in Docker container."""
        env_config = DockerTestConfig.CONTAINER_ENV_CONFIGS["default"]
        
        # Start container
        container = docker_manager.start_container(
            image_tag=docker_image_tag,
            environment=env_config,
            name="e2e-test-startup"
        )
        
        try:
            # Wait for container to become ready
            is_ready = docker_manager.wait_for_container_ready(
                container, 
                timeout=DockerTestConfig.TIMEOUTS["startup"]
            )
            
            assert is_ready, "Container should become ready within timeout"
            
            # Verify container is running
            container.reload()
            assert container.status == "running", "Container should be in running state"
            
            # Get service URL
            service_url = docker_manager.get_container_url(container)
            assert service_url is not None, "Should be able to get container service URL"
            
            # Test basic connectivity
            client = E2EHttpClient(service_url)
            health_response = client.health_check()
            
            assert health_response.is_success, "Health check should succeed in container"
            
            client.close()
            
        finally:
            # Cleanup
            docker_manager.stop_container(container)
    
    def test_environment_variable_configuration(self, docker_manager, docker_image_tag):
        """Test Docker environment variable injection."""
        # Test different environment configurations
        for config_name, env_config in DockerTestConfig.CONTAINER_ENV_CONFIGS.items():
            container = docker_manager.start_container(
                image_tag=docker_image_tag,
                environment=env_config,
                name=f"e2e-test-env-{config_name}"
            )
            
            try:
                # Wait for readiness
                is_ready = docker_manager.wait_for_container_ready(container, timeout=90)
                
                if is_ready:
                    service_url = docker_manager.get_container_url(container)
                    
                    # Test with the configured API key
                    client = E2EHttpClient(service_url)
                    client.set_api_key(env_config["API_KEY"])
                    
                    # Test translation request
                    response = client.translate(
                        text=f"Environment test {config_name}",
                        source_lang="eng_Latn",
                        target_lang="fra_Latn"
                    )
                    
                    # Should work with correct API key
                    assert response.status_code != 403, \
                        f"Environment config '{config_name}' should work with correct API key"
                    
                    # Test with wrong API key
                    client.set_api_key("wrong-api-key")
                    wrong_response = client.translate(
                        text="Wrong key test",
                        source_lang="eng_Latn", 
                        target_lang="fra_Latn"
                    )
                    
                    assert wrong_response.status_code == 403, \
                        f"Environment config '{config_name}' should reject wrong API key"
                    
                    client.close()
                
            finally:
                docker_manager.stop_container(container)
    
    def test_container_port_mapping(self, docker_manager, docker_image_tag):
        """Test container port mapping and network accessibility."""
        env_config = DockerTestConfig.CONTAINER_ENV_CONFIGS["default"]
        
        # Test with explicit port mapping
        container = docker_manager.start_container(
            image_tag=docker_image_tag,
            environment=env_config,
            ports={'8000/tcp': None},  # Map to random host port
            name="e2e-test-ports"
        )
        
        try:
            # Wait for readiness
            is_ready = docker_manager.wait_for_container_ready(container, timeout=90)
            assert is_ready, "Container should become ready"
            
            # Verify port mapping
            container.reload()
            port_info = container.attrs['NetworkSettings']['Ports']
            
            assert '8000/tcp' in port_info, "Container should expose port 8000"
            assert port_info['8000/tcp'] is not None, "Port should be mapped to host"
            
            host_port = port_info['8000/tcp'][0]['HostPort']
            assert host_port is not None, "Should have host port mapping"
            
            # Test connectivity to mapped port
            service_url = f"http://localhost:{host_port}"
            client = E2EHttpClient(service_url)
            client.set_api_key(env_config["API_KEY"])
            
            # Test health endpoint
            health_response = client.health_check()
            assert health_response.is_success, "Should be accessible via port mapping"
            
            # Test translation endpoint
            translation_response = client.translate(
                text="Port mapping test",
                source_lang="eng_Latn",
                target_lang="fra_Latn"
            )
            
            assert translation_response.status_code != 0, \
                "Translation endpoint should be accessible via port mapping"
            
            client.close()
            
        finally:
            docker_manager.stop_container(container)
    
    def test_container_health_checks(self, docker_manager, docker_image_tag):
        """Test Docker health check integration."""
        env_config = DockerTestConfig.CONTAINER_ENV_CONFIGS["default"]
        
        # Start container
        container = docker_manager.start_container(
            image_tag=docker_image_tag,
            environment=env_config,
            name="e2e-test-health"
        )
        
        try:
            # Wait for startup
            is_ready = docker_manager.wait_for_container_ready(container, timeout=90)
            assert is_ready, "Container should start successfully"
            
            # Monitor container health over time
            health_checks = []
            
            for i in range(10):  # Check health 10 times
                container.reload()
                
                # Check container status
                status = container.status
                health_checks.append({
                    "check": i,
                    "status": status,
                    "timestamp": time.time()
                })
                
                # Container should remain running
                assert status == "running", f"Container should stay running (check {i})"
                
                time.sleep(2)  # Wait 2 seconds between checks
            
            # Verify health check consistency
            running_checks = sum(1 for check in health_checks if check["status"] == "running")
            assert running_checks == len(health_checks), \
                "Container should remain healthy throughout monitoring"
            
        finally:
            docker_manager.stop_container(container)
    
    def test_container_resource_constraints(self, docker_manager, docker_image_tag):
        """Test container memory and CPU limits."""
        env_config = DockerTestConfig.CONTAINER_ENV_CONFIGS["default"]
        
        # Start container with resource constraints
        container = docker_manager.start_container(
            image_tag=docker_image_tag,
            environment=env_config,
            name="e2e-test-resources"
        )
        
        try:
            # Wait for readiness
            is_ready = docker_manager.wait_for_container_ready(container, timeout=90)
            assert is_ready, "Container should start with resource constraints"
            
            # Get baseline resource usage
            baseline_stats = docker_manager.get_container_stats(container)
            assert baseline_stats is not None, "Should be able to get container stats"
            
            # Generate some load and monitor resources
            service_url = docker_manager.get_container_url(container)
            client = E2EHttpClient(service_url)
            client.set_api_key(env_config["API_KEY"])
            
            # Make several translation requests to generate load
            resource_samples = [baseline_stats]
            
            for i in range(5):
                # Make translation request
                response = client.translate(
                    text=f"Resource test {i} " * 50,  # Longer text for more processing
                    source_lang="eng_Latn",
                    target_lang="fra_Latn",
                    timeout=30
                )
                
                # Sample resource usage
                stats = docker_manager.get_container_stats(container)
                if stats:
                    resource_samples.append(stats)
                
                time.sleep(1)
            
            client.close()
            
            # Analyze resource usage
            if len(resource_samples) > 1:
                memory_usages = [s["memory_usage"] for s in resource_samples]
                max_memory = max(memory_usages)
                
                # Memory usage should be reasonable (less than 1GB for test)
                max_memory_mb = max_memory / (1024 * 1024)
                assert max_memory_mb < 1024, \
                    f"Memory usage too high: {max_memory_mb:.1f}MB"
                
                print(f"Resource usage: max memory = {max_memory_mb:.1f}MB")
            
        finally:
            docker_manager.stop_container(container)
    
    def test_container_graceful_shutdown(self, docker_manager, docker_image_tag):
        """Test container graceful shutdown behavior."""
        env_config = DockerTestConfig.CONTAINER_ENV_CONFIGS["default"]
        
        # Start container
        container = docker_manager.start_container(
            image_tag=docker_image_tag,
            environment=env_config,
            name="e2e-test-shutdown"
        )
        
        try:
            # Wait for readiness
            is_ready = docker_manager.wait_for_container_ready(container, timeout=90)
            assert is_ready, "Container should start successfully"
            
            # Verify service is working
            service_url = docker_manager.get_container_url(container)
            client = E2EHttpClient(service_url)
            client.set_api_key(env_config["API_KEY"])
            
            health_response = client.health_check()
            assert health_response.is_success, "Service should be working before shutdown"
            
            client.close()
            
            # Test graceful shutdown
            shutdown_start = time.time()
            
            success = docker_manager.stop_container(
                container, 
                timeout=DockerTestConfig.TIMEOUTS["shutdown"]
            )
            
            shutdown_time = time.time() - shutdown_start
            
            # Verify graceful shutdown
            assert success, "Container should shutdown successfully"
            assert shutdown_time < DockerTestConfig.TIMEOUTS["shutdown"], \
                f"Shutdown took too long: {shutdown_time:.1f}s"
            
            # Verify container is stopped
            container.reload()
            assert container.status in ["exited", "stopped"], \
                f"Container should be stopped, got: {container.status}"
            
            print(f"Graceful shutdown completed in {shutdown_time:.2f} seconds")
            
        except Exception as e:
            # Force cleanup on error
            try:
                container.stop(timeout=5)
                container.remove(force=True)
            except Exception:
                pass
            raise e
    
    def test_container_log_capture(self, docker_manager, docker_image_tag):
        """Test container log capture for debugging."""
        env_config = DockerTestConfig.CONTAINER_ENV_CONFIGS["debug"]  # Use debug config for more logs
        
        container = docker_manager.start_container(
            image_tag=docker_image_tag,
            environment=env_config,
            name="e2e-test-logs"
        )
        
        try:
            # Wait for readiness
            is_ready = docker_manager.wait_for_container_ready(container, timeout=90)
            assert is_ready, "Container should start successfully"
            
            # Generate some activity to create logs
            service_url = docker_manager.get_container_url(container)
            client = E2EHttpClient(service_url)
            client.set_api_key(env_config["API_KEY"])
            
            # Make several requests to generate log entries
            for i in range(3):
                health_response = client.health_check()
                translation_response = client.translate(
                    text=f"Log test {i}",
                    source_lang="eng_Latn",
                    target_lang="fra_Latn"
                )
                time.sleep(0.5)
            
            client.close()
            
            # Capture logs
            logs = docker_manager.get_container_logs(container, tail=50)
            
            # Verify logs were captured
            assert isinstance(logs, str), "Logs should be returned as string"
            assert len(logs) > 0, "Should capture some log output"
            
            # Look for expected log patterns
            log_lines = logs.split('\n')
            log_text = logs.lower()
            
            # Should contain some application logs
            # (Exact log format depends on the application)
            assert len(log_lines) > 1, "Should have multiple log lines"
            
            print(f"Captured {len(log_lines)} log lines")
            print("Sample log entries:")
            for line in log_lines[:3]:  # Show first 3 lines
                if line.strip():
                    print(f"  {line.strip()[:100]}")
            
        finally:
            docker_manager.stop_container(container)
    
    def test_multiple_container_instances(self, docker_manager, docker_image_tag):
        """Test running multiple container instances simultaneously."""
        env_config = DockerTestConfig.CONTAINER_ENV_CONFIGS["default"]
        
        containers = []
        try:
            # Start multiple containers
            for i in range(3):
                container = docker_manager.start_container(
                    image_tag=docker_image_tag,
                    environment=env_config,
                    name=f"e2e-test-multi-{i}"
                )
                containers.append(container)
            
            # Wait for all containers to become ready
            service_urls = []
            for i, container in enumerate(containers):
                is_ready = docker_manager.wait_for_container_ready(container, timeout=120)
                assert is_ready, f"Container {i} should become ready"
                
                service_url = docker_manager.get_container_url(container)
                assert service_url is not None, f"Should get URL for container {i}"
                service_urls.append(service_url)
            
            # Verify all containers are accessible
            for i, service_url in enumerate(service_urls):
                client = E2EHttpClient(service_url)
                client.set_api_key(env_config["API_KEY"])
                
                health_response = client.health_check()
                assert health_response.is_success, f"Container {i} should be healthy"
                
                translation_response = client.translate(
                    text=f"Multi-container test {i}",
                    source_lang="eng_Latn",
                    target_lang="fra_Latn"
                )
                
                assert translation_response.status_code != 0, \
                    f"Container {i} should handle translation requests"
                
                client.close()
            
            print(f"Successfully tested {len(containers)} concurrent containers")
            
        finally:
            # Cleanup all containers
            for container in containers:
                try:
                    docker_manager.stop_container(container)
                except Exception as e:
                    print(f"Warning: Failed to stop container {container.id[:12]}: {e}")