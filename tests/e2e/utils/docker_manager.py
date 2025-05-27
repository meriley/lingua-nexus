"""Docker container management utilities for E2E testing."""

import time
from typing import Dict, Optional, List
import logging
from pathlib import Path

try:
    import docker
    from docker.models.containers import Container
    from docker.errors import DockerException, APIError
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    Container = None
    DockerException = Exception
    APIError = Exception
    DOCKER_AVAILABLE = False


class E2EDockerManager:
    """Manages Docker containers for E2E testing."""
    
    def __init__(self):
        self.client = None
        self.containers: List = []
        self.logger = logging.getLogger(__name__)
        
        if not DOCKER_AVAILABLE:
            self.logger.error("Docker not available: docker package not installed")
            raise RuntimeError("Docker not available: docker package not installed")
        
        try:
            self.client = docker.from_env()
            self.client.ping()  # Test connectivity
        except Exception as e:
            self.logger.error(f"Docker not available: {e}")
            raise RuntimeError(f"Docker not available: {e}")
    
    def build_image(
        self, 
        dockerfile_path: str = None, 
        build_context: str = None,
        tag: str = "tg-text-translate:e2e-test",
        build_args: Optional[Dict[str, str]] = None
    ) -> str:
        """Build Docker image for testing."""
        if not self.client:
            raise RuntimeError("Docker client not available")
        
        # Default to project root for build context
        if build_context is None:
            build_context = str(Path(__file__).parent.parent.parent.parent)
        
        # Default to Dockerfile in project root
        if dockerfile_path is None:
            dockerfile_path = "Dockerfile"
        
        self.logger.info(f"Building Docker image: {tag}")
        self.logger.info(f"Build context: {build_context}")
        self.logger.info(f"Dockerfile: {dockerfile_path}")
        
        try:
            # Build image
            image, build_logs = self.client.images.build(
                path=build_context,
                dockerfile=dockerfile_path,
                tag=tag,
                rm=True,  # Remove intermediate containers
                forcerm=True,  # Force remove intermediate containers
                buildargs=build_args or {}
            )
            
            # Log build output
            for log in build_logs:
                if 'stream' in log:
                    self.logger.debug(log['stream'].strip())
            
            self.logger.info(f"Successfully built image: {tag}")
            return tag
            
        except Exception as e:
            self.logger.error(f"Failed to build Docker image: {e}")
            raise RuntimeError(f"Docker build failed: {e}")
    
    def start_container(
        self,
        image_tag: str,
        environment: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[str, int]] = None,
        name: Optional[str] = None,
        detach: bool = True,
        remove: bool = True
    ) -> Container:
        """Start a Docker container."""
        if not self.client:
            raise RuntimeError("Docker client not available")
        
        try:
            # Default port mapping
            if ports is None:
                ports = {'8000/tcp': None}  # Map container port 8000 to random host port
            
            self.logger.info(f"Starting container from image: {image_tag}")
            
            container = self.client.containers.run(
                image=image_tag,
                environment=environment,
                ports=ports,
                detach=detach,
                remove=remove,
                name=name
            )
            
            if detach:
                self.containers.append(container)
                self.logger.info(f"Container started: {container.id[:12]}")
                return container
            else:
                return container
                
        except Exception as e:
            self.logger.error(f"Failed to start container: {e}")
            raise RuntimeError(f"Container start failed: {e}")
    
    def wait_for_container_ready(
        self, 
        container: Container, 
        timeout: int = 60,
        check_interval: float = 1.0
    ) -> bool:
        """Wait for container to become ready."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Reload container info
                container.reload()
                
                # Check if container is running
                if container.status != 'running':
                    self.logger.warning(f"Container not running: {container.status}")
                    return False
                
                # Get container port mapping
                port_info = container.attrs['NetworkSettings']['Ports']
                if '8000/tcp' in port_info and port_info['8000/tcp']:
                    host_port = port_info['8000/tcp'][0]['HostPort']
                    
                    # Try to connect to the service
                    import requests
                    try:
                        health_url = f"http://localhost:{host_port}/health"
                        response = requests.get(health_url, timeout=5)
                        if response.status_code == 200:
                            self.logger.info(f"Container ready at port {host_port}")
                            return True
                    except requests.exceptions.RequestException:
                        pass  # Service not ready yet
                
            except Exception as e:
                self.logger.debug(f"Container readiness check error: {e}")
            
            time.sleep(check_interval)
        
        self.logger.error(f"Container failed to become ready within {timeout} seconds")
        return False
    
    def get_container_url(self, container: Container) -> Optional[str]:
        """Get the HTTP URL for the container service."""
        try:
            container.reload()
            port_info = container.attrs['NetworkSettings']['Ports']
            
            if '8000/tcp' in port_info and port_info['8000/tcp']:
                host_port = port_info['8000/tcp'][0]['HostPort']
                return f"http://localhost:{host_port}"
            
        except Exception as e:
            self.logger.error(f"Failed to get container URL: {e}")
        
        return None
    
    def stop_container(self, container: Container, timeout: int = 10) -> bool:
        """Stop a container gracefully."""
        try:
            self.logger.info(f"Stopping container: {container.id[:12]}")
            container.stop(timeout=timeout)
            
            # Remove from tracked containers
            if container in self.containers:
                self.containers.remove(container)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop container: {e}")
            return False
    
    def get_container_logs(self, container: Container, tail: int = 100) -> str:
        """Get container logs for debugging."""
        try:
            logs = container.logs(tail=tail, timestamps=True)
            return logs.decode('utf-8') if isinstance(logs, bytes) else str(logs)
        except Exception as e:
            self.logger.error(f"Failed to get container logs: {e}")
            return f"Failed to get logs: {e}"
    
    def cleanup_containers(self):
        """Clean up all tracked containers."""
        for container in self.containers[:]:  # Copy list to avoid modification during iteration
            try:
                container.stop(timeout=5)
                container.remove(force=True)
            except Exception as e:
                self.logger.warning(f"Failed to cleanup container {container.id[:12]}: {e}")
        
        self.containers.clear()
    
    def remove_image(self, image_tag: str, force: bool = False):
        """Remove a Docker image."""
        if not self.client:
            return
        
        try:
            self.client.images.remove(image_tag, force=force)
            self.logger.info(f"Removed image: {image_tag}")
        except Exception as e:
            self.logger.warning(f"Failed to remove image {image_tag}: {e}")
    
    def list_containers(self) -> List[Dict]:
        """List all containers (running and stopped)."""
        if not self.client:
            return []
        
        try:
            containers = self.client.containers.list(all=True)
            return [
                {
                    "id": container.id[:12],
                    "name": container.name,
                    "status": container.status,
                    "image": container.image.tags[0] if container.image.tags else "unknown"
                }
                for container in containers
            ]
        except Exception as e:
            self.logger.error(f"Failed to list containers: {e}")
            return []
    
    def get_container_stats(self, container: Container) -> Optional[Dict]:
        """Get container resource usage statistics."""
        try:
            stats = container.stats(stream=False)
            
            # Extract useful metrics
            cpu_stats = stats.get('cpu_stats', {})
            memory_stats = stats.get('memory_stats', {})
            
            return {
                "memory_usage": memory_stats.get('usage', 0),
                "memory_limit": memory_stats.get('limit', 0),
                "cpu_usage": cpu_stats.get('cpu_usage', {}).get('total_usage', 0),
                "timestamp": time.time()
            }
        except Exception as e:
            self.logger.error(f"Failed to get container stats: {e}")
            return None
    
    def close(self):
        """Close Docker client and cleanup."""
        self.cleanup_containers()
        if self.client:
            self.client.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close()


class DockerTestConfig:
    """Configuration for Docker-based E2E tests."""
    
    # Environment variables for container testing
    CONTAINER_ENV_CONFIGS = {
        "default": {
            "API_KEY": "test-docker-api-key",
            "MODEL_NAME": "facebook/nllb-200-distilled-600M",
            "CACHE_DIR": "/app/cache",
            "LOG_LEVEL": "INFO"
        },
        "debug": {
            "API_KEY": "debug-docker-api-key",
            "MODEL_NAME": "facebook/nllb-200-distilled-600M",
            "CACHE_DIR": "/app/debug_cache",
            "LOG_LEVEL": "DEBUG"
        },
        "production": {
            "API_KEY": "prod-docker-api-key",
            "MODEL_NAME": "facebook/nllb-200-distilled-600M",
            "CACHE_DIR": "/app/prod_cache",
            "LOG_LEVEL": "WARNING"
        }
    }
    
    # Resource constraints for testing
    RESOURCE_CONSTRAINTS = {
        "memory_limit": "2g",
        "cpu_limit": "1.0",
        "disk_limit": "10g"
    }
    
    # Test timeouts
    TIMEOUTS = {
        "build": 300,  # 5 minutes
        "startup": 120,  # 2 minutes
        "readiness": 60,  # 1 minute
        "shutdown": 30   # 30 seconds
    }