"""
Parallel test execution manager for E2E tests.
Handles test isolation, resource allocation, and coordination between parallel workers.
"""

import os
import time
import socket
import logging
import threading
import multiprocessing
from typing import Dict, Set, Optional, List, Any
from pathlib import Path
import json
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class TestWorkerConfig:
    """Configuration for individual test worker."""
    worker_id: str
    base_port: int
    cache_dir: str
    temp_dir: str
    log_level: str = "INFO"
    timeout: int = 300


class PortManager:
    """Manages port allocation for parallel test workers with atomic allocation."""
    
    def __init__(self, base_port: int = 8000, port_range: int = 100):
        """
        Initialize port manager.
        
        Args:
            base_port: Starting port number
            port_range: Number of ports to manage
        """
        self.base_port = base_port
        self.port_range = port_range
        self.allocated_ports: Set[int] = set()
        self.port_lock = threading.Lock()
        self.worker_ports: Dict[str, List[int]] = {}
        self._port_pool = list(range(base_port, base_port + port_range))
        self._next_port_index = 0
        
    def allocate_ports(self, worker_id: str, count: int = 3) -> List[int]:
        """
        Allocate ports for a test worker using atomic allocation.
        
        Args:
            worker_id: Unique identifier for the worker
            count: Number of ports to allocate
            
        Returns:
            List of allocated port numbers
        """
        with self.port_lock:
            # Return existing allocation if worker already registered
            if worker_id in self.worker_ports:
                return self.worker_ports[worker_id]
                
            allocated = []
            attempts = 0
            max_attempts = self.port_range * 2  # Give plenty of chances
            
            while len(allocated) < count and attempts < max_attempts:
                attempts += 1
                
                # Use round-robin allocation from pool to avoid conflicts
                port = self._get_next_available_port()
                if port is None:
                    break
                    
                # Double-check port availability (defense in depth)
                if self._is_port_available(port):
                    allocated.append(port)
                    self.allocated_ports.add(port)
                    
            if len(allocated) < count:
                # Clean up partial allocation
                for port in allocated:
                    self.allocated_ports.discard(port)
                raise RuntimeError(f"Unable to allocate {count} ports for worker {worker_id}. "
                                 f"Only {len(allocated)} ports available after {attempts} attempts.")
                
            self.worker_ports[worker_id] = allocated
            return allocated
            
    def _get_next_available_port(self) -> Optional[int]:
        """Get the next available port from the pool using round-robin."""
        start_index = self._next_port_index
        
        # Try all ports starting from current index
        for _ in range(len(self._port_pool)):
            port = self._port_pool[self._next_port_index]
            self._next_port_index = (self._next_port_index + 1) % len(self._port_pool)
            
            if port not in self.allocated_ports:
                return port
                
        # No available ports found
        return None
            
    def release_ports(self, worker_id: str):
        """Release ports allocated to a worker."""
        with self.port_lock:
            if worker_id in self.worker_ports:
                for port in self.worker_ports[worker_id]:
                    self.allocated_ports.discard(port)
                del self.worker_ports[worker_id]
                
    def _is_port_available(self, port: int) -> bool:
        """
        Check if a port is available by attempting to bind to it.
        This is more reliable than connect_ex for testing availability.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.settimeout(0.5)
                sock.bind(('localhost', port))
                return True
        except (socket.error, OSError):
            return False


class ResourceIsolation:
    """Manages resource isolation between test workers."""
    
    def __init__(self):
        """Initialize resource isolation manager."""
        self.worker_resources: Dict[str, Dict[str, Any]] = {}
        self.resource_lock = threading.Lock()
        self.base_temp_dir = tempfile.gettempdir()
        
    def setup_worker_environment(self, config: TestWorkerConfig) -> Dict[str, str]:
        """
        Set up isolated environment for a test worker.
        
        Args:
            config: Worker configuration
            
        Returns:
            Environment variables for the worker
        """
        with self.resource_lock:
            # Create isolated directories from base paths (not from config to avoid nesting)
            worker_temp = Path(self.base_temp_dir) / f"e2e_test_worker_{config.worker_id}"
            worker_cache = Path(config.cache_dir) / f"worker_{config.worker_id}"  
            worker_logs = worker_temp / "logs"
            
            # Ensure directories exist
            for directory in [worker_temp, worker_cache, worker_logs]:
                directory.mkdir(parents=True, exist_ok=True)
                
            # Store resource allocation
            self.worker_resources[config.worker_id] = {
                "temp_dir": str(worker_temp),
                "cache_dir": str(worker_cache),
                "log_dir": str(worker_logs),
                "base_port": config.base_port,
                "created_at": time.time()
            }
            
            # Environment variables for isolation
            env_vars = {
                "E2E_WORKER_ID": config.worker_id,
                "E2E_TEMP_DIR": str(worker_temp),
                "E2E_CACHE_DIR": str(worker_cache),
                "E2E_LOG_DIR": str(worker_logs),
                "E2E_BASE_PORT": str(config.base_port),
                "E2E_LOG_LEVEL": config.log_level,
                "E2E_TIMEOUT": str(config.timeout),
                "CUDA_VISIBLE_DEVICES": self._allocate_gpu(config.worker_id),
                "TOKENIZERS_PARALLELISM": "false"  # Avoid warnings in parallel execution
            }
            
            return env_vars
            
    def cleanup_worker_environment(self, worker_id: str):
        """Clean up worker environment."""
        with self.resource_lock:
            if worker_id in self.worker_resources:
                resources = self.worker_resources[worker_id]
                
                # Clean up temporary directories
                temp_dir = Path(resources["temp_dir"])
                if temp_dir.exists():
                    import shutil
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception as e:
                        logging.warning(f"Failed to clean up temp dir for worker {worker_id}: {e}")
                
                del self.worker_resources[worker_id]
                
    def _allocate_gpu(self, worker_id: str) -> str:
        """
        Allocate GPU resources to worker.
        
        For now, returns empty string (CPU only) to avoid GPU conflicts.
        In production, this could implement GPU scheduling.
        """
        return ""  # CPU only for parallel execution


class TestCoordinator:
    """Coordinates parallel test execution."""
    
    def __init__(self):
        """Initialize test coordinator."""
        self.port_manager = PortManager()
        self.resource_isolation = ResourceIsolation()
        self.active_workers: Dict[str, TestWorkerConfig] = {}
        self.coordinator_lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
    def register_worker(self, worker_id: Optional[str] = None) -> TestWorkerConfig:
        """
        Register a new test worker.
        
        Args:
            worker_id: Optional worker ID (will be generated if not provided)
            
        Returns:
            Configuration for the worker
        """
        if worker_id is None:
            worker_id = f"worker_{int(time.time() * 1000)}_{os.getpid()}"
            
        with self.coordinator_lock:
            if worker_id in self.active_workers:
                return self.active_workers[worker_id]
                
            # Allocate ports
            ports = self.port_manager.allocate_ports(worker_id)
            base_port = ports[0]
            
            # Create worker configuration with base directories
            base_cache_dir = os.environ.get("E2E_CACHE_DIR", "/tmp/e2e_cache")
            base_temp_dir = os.environ.get("E2E_TEMP_DIR", "/tmp")
            
            config = TestWorkerConfig(
                worker_id=worker_id,
                base_port=base_port,
                cache_dir=base_cache_dir,  # Use base cache dir, isolation happens in setup_worker_environment
                temp_dir=base_temp_dir,    # Use base temp dir, isolation happens in setup_worker_environment
                log_level=os.environ.get("E2E_LOG_LEVEL", "INFO"),
                timeout=int(os.environ.get("E2E_TIMEOUT", "300"))
            )
            
            # Set up environment
            env_vars = self.resource_isolation.setup_worker_environment(config)
            
            # Update config with isolated directories from environment setup
            config.cache_dir = env_vars["E2E_CACHE_DIR"]
            config.temp_dir = env_vars["E2E_TEMP_DIR"]
            
            # Update environment
            os.environ.update(env_vars)
            
            self.active_workers[worker_id] = config
            
            self.logger.info(f"Registered test worker {worker_id} with port {base_port}")
            
            return config
            
    def unregister_worker(self, worker_id: str):
        """Unregister and cleanup a test worker."""
        with self.coordinator_lock:
            if worker_id in self.active_workers:
                # Release ports
                self.port_manager.release_ports(worker_id)
                
                # Clean up environment
                self.resource_isolation.cleanup_worker_environment(worker_id)
                
                del self.active_workers[worker_id]
                
                self.logger.info(f"Unregistered test worker {worker_id}")
                
    def get_worker_config(self, worker_id: str) -> Optional[TestWorkerConfig]:
        """Get configuration for a specific worker."""
        return self.active_workers.get(worker_id)
        
    def list_active_workers(self) -> List[str]:
        """List all active worker IDs."""
        return list(self.active_workers.keys())


# Global coordinator instance
_test_coordinator = None
_coordinator_lock = threading.Lock()


def get_test_coordinator() -> TestCoordinator:
    """Get or create the global test coordinator."""
    global _test_coordinator
    
    with _coordinator_lock:
        if _test_coordinator is None:
            _test_coordinator = TestCoordinator()
        return _test_coordinator


@contextmanager
def parallel_test_worker(worker_id: Optional[str] = None):
    """
    Context manager for parallel test worker.
    
    Usage:
        with parallel_test_worker() as config:
            # Test code here
            # Ports and resources are automatically allocated
    """
    coordinator = get_test_coordinator()
    config = coordinator.register_worker(worker_id)
    
    try:
        yield config
    finally:
        coordinator.unregister_worker(config.worker_id)


class ParallelServiceManager:
    """Service manager that works with parallel test execution."""
    
    def __init__(self, worker_config: Optional[TestWorkerConfig] = None):
        """
        Initialize parallel service manager.
        
        Args:
            worker_config: Configuration for the current worker
        """
        if worker_config is None:
            # Try to get from environment or create new
            worker_id = os.environ.get("E2E_WORKER_ID")
            if worker_id:
                coordinator = get_test_coordinator()
                worker_config = coordinator.get_worker_config(worker_id)
                
        self.worker_config = worker_config
        self.logger = logging.getLogger(__name__)
        
    def get_available_port(self) -> int:
        """Get an available port for this worker."""
        if self.worker_config:
            return self.worker_config.base_port
        else:
            # Fallback to finding any available port
            return self._find_free_port()
            
    def get_cache_dir(self) -> str:
        """Get the cache directory for this worker."""
        if self.worker_config:
            return self.worker_config.cache_dir
        else:
            return os.environ.get("E2E_CACHE_DIR", "/tmp/e2e_cache")
            
    def get_temp_dir(self) -> str:
        """Get the temp directory for this worker."""
        if self.worker_config:
            return self.worker_config.temp_dir
        else:
            return os.environ.get("E2E_TEMP_DIR", "/tmp")
            
    def _find_free_port(self, start_port: int = 8000) -> int:
        """Find a free port starting from start_port."""
        for port in range(start_port, start_port + 100):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                if result != 0:  # Port is available
                    return port
        raise RuntimeError("No available ports found")


def pytest_configure(config):
    """Configure pytest for parallel execution."""
    # Set up parallel test environment if running with xdist
    if hasattr(config, 'workerinput'):
        # Running in xdist worker
        worker_id = config.workerinput['workerid']
        
        # Register worker with coordinator
        coordinator = get_test_coordinator()
        worker_config = coordinator.register_worker(worker_id)
        
        # Store config in pytest namespace for access in tests
        config._parallel_worker_config = worker_config


def pytest_unconfigure(config):
    """Clean up after pytest execution."""
    if hasattr(config, '_parallel_worker_config'):
        # Unregister worker
        coordinator = get_test_coordinator()
        coordinator.unregister_worker(config._parallel_worker_config.worker_id)


# Utility functions for tests

def get_worker_config() -> Optional[TestWorkerConfig]:
    """Get the current worker configuration."""
    worker_id = os.environ.get("E2E_WORKER_ID")
    if worker_id:
        coordinator = get_test_coordinator()
        return coordinator.get_worker_config(worker_id)
    return None


def is_parallel_execution() -> bool:
    """Check if we're running in parallel execution mode."""
    return "E2E_WORKER_ID" in os.environ


def get_isolated_port() -> int:
    """Get an isolated port for the current worker."""
    manager = ParallelServiceManager()
    return manager.get_available_port()


def get_isolated_cache_dir() -> str:
    """Get an isolated cache directory for the current worker."""
    manager = ParallelServiceManager()
    return manager.get_cache_dir()


if __name__ == "__main__":
    # Test the parallel system
    print("Testing parallel test manager...")
    
    with parallel_test_worker("test_worker") as config:
        print(f"Worker ID: {config.worker_id}")
        print(f"Base Port: {config.base_port}")
        print(f"Cache Dir: {config.cache_dir}")
        print(f"Temp Dir: {config.temp_dir}")
        
    print("Test completed successfully!")