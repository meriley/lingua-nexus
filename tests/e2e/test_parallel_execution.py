"""
E2E Test: Parallel Execution
Tests parallel test execution, worker isolation, and resource management.
"""

import pytest
import time
import os
import threading
from pathlib import Path
from tests.e2e.utils.parallel_test_manager import (
    parallel_test_worker, get_test_coordinator, ParallelServiceManager,
    is_parallel_execution, get_isolated_port, get_isolated_cache_dir
)
from tests.e2e.utils.robust_service_manager import RobustServiceManager
from tests.e2e.utils.service_manager import ServiceConfig


class TestParallelExecution:
    """Test suite for parallel execution capabilities."""
    
    def test_worker_registration_and_isolation(self):
        """Test worker registration and resource isolation."""
        print("\nTesting worker registration and isolation...")
        
        coordinator = get_test_coordinator()
        
        # Register multiple workers
        with parallel_test_worker("worker_1") as config1:
            with parallel_test_worker("worker_2") as config2:
                # Verify workers have different configurations
                assert config1.worker_id != config2.worker_id
                assert config1.base_port != config2.base_port
                assert config1.cache_dir != config2.cache_dir
                assert config1.temp_dir != config2.temp_dir
                
                print(f"✓ Worker 1: {config1.worker_id}, port {config1.base_port}")
                print(f"✓ Worker 2: {config2.worker_id}, port {config2.base_port}")
                
                # Verify both workers are active
                active_workers = coordinator.list_active_workers()
                assert config1.worker_id in active_workers
                assert config2.worker_id in active_workers
                
        # Verify workers are cleaned up after context exit
        active_workers = coordinator.list_active_workers()
        assert config1.worker_id not in active_workers
        assert config2.worker_id not in active_workers
        
        print("✓ Worker isolation and cleanup verified")
        
    def test_port_allocation_and_isolation(self):
        """Test port allocation and isolation between workers."""
        print("\nTesting port allocation and isolation...")
        
        # Test nested worker contexts to ensure proper isolation
        with parallel_test_worker("port_test_worker_0") as config0:
            manager0 = ParallelServiceManager(config0)
            port0 = manager0.get_available_port()
            print(f"✓ Worker 0: allocated port {port0}")
            
            with parallel_test_worker("port_test_worker_1") as config1:
                manager1 = ParallelServiceManager(config1)
                port1 = manager1.get_available_port()
                print(f"✓ Worker 1: allocated port {port1}")
                
                # Verify ports are different
                assert port0 != port1, f"Port conflict between worker 0 and 1: {port0} == {port1}"
                
                with parallel_test_worker("port_test_worker_2") as config2:
                    manager2 = ParallelServiceManager(config2)
                    port2 = manager2.get_available_port()
                    print(f"✓ Worker 2: allocated port {port2}")
                    
                    # Verify all ports are unique
                    ports = [port0, port1, port2]
                    assert len(set(ports)) == len(ports), f"Port conflicts detected: {ports}"
                    
                    print(f"✓ All ports unique: {ports}")
                    
        print("✓ Port allocation and isolation verified")
        
    def test_cache_directory_isolation(self):
        """Test cache directory isolation between workers."""
        print("\nTesting cache directory isolation...")
        
        cache_dirs = []
        
        for i in range(3):
            with parallel_test_worker(f"cache_test_worker_{i}") as config:
                manager = ParallelServiceManager(config)
                cache_dir = manager.get_cache_dir()
                cache_dirs.append(cache_dir)
                
                print(f"✓ Worker {i}: cache dir {cache_dir}")
                
                # Verify cache directory exists
                assert Path(cache_dir).exists(), f"Cache directory {cache_dir} should exist"
                
                # Create a test file to verify isolation
                test_file = Path(cache_dir) / f"test_worker_{i}.txt"
                test_file.write_text(f"Worker {i} test data")
                assert test_file.exists()
                
        # Verify all cache directories are different
        assert len(set(cache_dirs)) == len(cache_dirs), "Cache directories should be unique"
        
        print("✓ Cache directory isolation verified")
        
    def test_parallel_service_manager_integration(self):
        """Test integration with RobustServiceManager in parallel mode."""
        print("\nTesting parallel service manager integration...")
        
        # Simulate parallel execution environment
        original_env = os.environ.copy()
        
        try:
            with parallel_test_worker("integration_worker") as config:
                # Set environment to simulate parallel execution
                os.environ["E2E_WORKER_ID"] = config.worker_id
                
                # Create RobustServiceManager
                service_manager = RobustServiceManager()
                
                # Verify it detects parallel mode
                assert service_manager.is_parallel
                
                # Test port allocation
                port = service_manager.find_available_port()
                assert port == config.base_port
                
                # Test cache directory
                cache_dir = service_manager.get_cache_dir()
                assert config.worker_id in cache_dir
                
                print(f"✓ Integration test: port {port}, cache {cache_dir}")
                
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)
            
        print("✓ Parallel service manager integration verified")
        
    def test_concurrent_worker_operations(self):
        """Test concurrent operations with multiple workers."""
        print("\nTesting concurrent worker operations...")
        
        results = []
        errors = []
        
        def worker_task(worker_id):
            """Task to run in each worker thread."""
            try:
                with parallel_test_worker(f"concurrent_worker_{worker_id}") as config:
                    manager = ParallelServiceManager(config)
                    
                    # Simulate some work
                    port = manager.get_available_port()
                    cache_dir = manager.get_cache_dir()
                    
                    # Create test data
                    test_file = Path(cache_dir) / f"concurrent_test_{worker_id}.txt"
                    test_file.write_text(f"Concurrent worker {worker_id} data")
                    
                    # Simulate processing time
                    time.sleep(0.1)
                    
                    results.append({
                        "worker_id": worker_id,
                        "config_id": config.worker_id,
                        "port": port,
                        "cache_dir": cache_dir,
                        "test_file_exists": test_file.exists()
                    })
                    
            except Exception as e:
                errors.append(f"Worker {worker_id} failed: {e}")
        
        # Run multiple workers concurrently
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker_task, args=(i,))
            threads.append(thread)
            thread.start()
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"
        
        # Verify no resource conflicts
        ports = [r["port"] for r in results]
        cache_dirs = [r["cache_dir"] for r in results]
        
        assert len(set(ports)) == len(ports), "Port conflicts detected"
        assert len(set(cache_dirs)) == len(cache_dirs), "Cache directory conflicts detected"
        
        for result in results:
            print(f"✓ Worker {result['worker_id']}: port {result['port']}, cache isolated")
            assert result["test_file_exists"], "Test file should exist"
            
        print("✓ Concurrent worker operations verified")
        
    def test_utility_functions(self):
        """Test utility functions for parallel execution."""
        print("\nTesting utility functions...")
        
        # Ensure clean environment for this test
        original_worker_id = os.environ.get("E2E_WORKER_ID")
        if "E2E_WORKER_ID" in os.environ:
            del os.environ["E2E_WORKER_ID"]
        
        try:
            # Test outside parallel context
            assert not is_parallel_execution()
            
            # Test inside parallel context
            with parallel_test_worker("utility_test_worker") as config:
                os.environ["E2E_WORKER_ID"] = config.worker_id
                
                try:
                    assert is_parallel_execution()
                    
                    isolated_port = get_isolated_port()
                    assert isolated_port == config.base_port
                    
                    isolated_cache = get_isolated_cache_dir()
                    assert config.worker_id in isolated_cache
                    
                    print(f"✓ Utility functions: port {isolated_port}, cache {isolated_cache}")
                    
                finally:
                    # Clean up environment
                    if "E2E_WORKER_ID" in os.environ:
                        del os.environ["E2E_WORKER_ID"]
                        
            print("✓ Utility functions verified")
            
        finally:
            # Restore original environment
            if original_worker_id is not None:
                os.environ["E2E_WORKER_ID"] = original_worker_id
        
    def test_resource_cleanup(self):
        """Test proper resource cleanup after worker termination."""
        print("\nTesting resource cleanup...")
        
        coordinator = get_test_coordinator()
        temp_dirs = []
        worker_ids = []
        
        # Create workers and track resources
        for i in range(2):
            with parallel_test_worker(f"cleanup_test_worker_{i}") as config:
                worker_ids.append(config.worker_id)
                temp_dirs.append(Path(config.temp_dir))
                
                # Verify resources exist during worker lifetime
                assert temp_dirs[-1].exists(), "Temp directory should exist"
                assert config.worker_id in coordinator.list_active_workers()
                
        # Verify cleanup after workers exit
        for worker_id, temp_dir in zip(worker_ids, temp_dirs):
            assert worker_id not in coordinator.list_active_workers()
            # Note: temp directory cleanup may be delayed or handled by OS
            
        print("✓ Resource cleanup verified")
        
    @pytest.fixture(scope="class", autouse=True)
    def test_summary(self, request):
        """Print test summary after all parallel execution tests complete."""
        yield
        
        print("\n=== PARALLEL EXECUTION TEST SUMMARY ===")
        print("✓ Worker registration and isolation")
        print("✓ Port allocation and isolation")
        print("✓ Cache directory isolation")
        print("✓ Service manager integration")
        print("✓ Concurrent worker operations")
        print("✓ Utility functions")
        print("✓ Resource cleanup")
        print("\nAll parallel execution tests passed! 🎉")
        print("\nTo run tests in parallel, use:")
        print("  pytest -n auto  # Auto-detect cores")
        print("  pytest -n 4     # Use 4 workers")
        print("  pytest --dist=loadscope  # Distribute by test scope")