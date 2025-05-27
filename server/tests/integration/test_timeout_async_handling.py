"""
Timeout and Async Handling Tests
Tests timeout scenarios, async operation edge cases, and resource management
"""

import pytest
import asyncio
import time
from unittest.mock import patch, AsyncMock, MagicMock
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import threading
from typing import Dict, List, Any, Optional
import signal
import sys

from fastapi.testclient import TestClient
from app.main import app


class AsyncTimeoutTestHelper:
    """Helper class for async timeout testing"""
    
    def __init__(self):
        self.test_results = {
            'timeout_tests': [],
            'async_edge_cases': [],
            'resource_management': [],
            'cancellation_tests': []
        }
        self.active_tasks = []
    
    async def simulate_slow_translation(self, delay_seconds: float = 5.0) -> str:
        """Simulate a slow translation that might timeout"""
        await asyncio.sleep(delay_seconds)
        return "Translated: Slow translation result"
    
    async def simulate_hanging_operation(self) -> str:
        """Simulate an operation that hangs indefinitely"""
        while True:
            await asyncio.sleep(1)
    
    def create_timeout_scenario(self, timeout_duration: float, operation_duration: float) -> Dict[str, Any]:
        """Create a timeout test scenario"""
        return {
            'timeout_duration': timeout_duration,
            'operation_duration': operation_duration,
            'should_timeout': operation_duration > timeout_duration,
            'test_name': f"timeout_{timeout_duration}s_operation_{operation_duration}s"
        }
    
    async def test_async_cancellation(self, operation_func, timeout_seconds: float) -> Dict[str, Any]:
        """Test async operation cancellation"""
        start_time = time.time()
        result = None
        error = None
        cancelled = False
        
        try:
            # Create task and set timeout
            task = asyncio.create_task(operation_func())
            self.active_tasks.append(task)
            
            # Wait with timeout
            result = await asyncio.wait_for(task, timeout=timeout_seconds)
            
        except asyncio.TimeoutError:
            # Handle timeout - task should be cancelled
            if task and not task.done():
                task.cancel()
                cancelled = True
            error = "TimeoutError"
            
        except asyncio.CancelledError:
            cancelled = True
            error = "CancelledError"
            
        except Exception as e:
            error = str(e)
        
        finally:
            # Clean up active tasks
            if task in self.active_tasks:
                self.active_tasks.remove(task)
        
        execution_time = time.time() - start_time
        
        return {
            'result': result,
            'error': error,
            'cancelled': cancelled,
            'execution_time': execution_time,
            'timeout_respected': execution_time <= (timeout_seconds + 0.5)  # Allow small buffer
        }


class AsyncResourceManager:
    """Manages async resources during testing"""
    
    def __init__(self):
        self.active_connections = []
        self.resource_usage = {
            'memory': [],
            'cpu': [],
            'file_descriptors': [],
            'network_connections': []
        }
    
    async def simulate_resource_intensive_operation(self, duration: float = 2.0) -> Dict[str, Any]:
        """Simulate resource-intensive async operation"""
        start_time = time.time()
        
        # Simulate memory allocation
        large_data = [f"data_chunk_{i}" * 1000 for i in range(100)]
        
        # Simulate CPU intensive task
        total = 0
        for _ in range(10000):
            total += sum(range(100))
        
        # Simulate async I/O
        await asyncio.sleep(duration)
        
        execution_time = time.time() - start_time
        
        # Clean up
        del large_data
        
        return {
            'execution_time': execution_time,
            'cpu_operations': total,
            'memory_allocated': True,
            'async_io_completed': True
        }
    
    def track_resource_usage(self) -> Dict[str, Any]:
        """Track current resource usage"""
        import psutil
        import gc
        
        # Get process info
        process = psutil.Process()
        
        usage = {
            'memory_mb': process.memory_info().rss / 1024 / 1024,
            'cpu_percent': process.cpu_percent(),
            'num_threads': process.num_threads(),
            'num_fds': process.num_fds() if hasattr(process, 'num_fds') else 0,
            'gc_count': len(gc.get_objects())
        }
        
        return usage


class TestTimeoutAsyncHandling:
    """Timeout and Async Handling Test Suite"""
    
    @pytest.fixture(autouse=True)
    def setup(self, enhanced_mock_objects):
        """Setup for timeout and async tests"""
        self.timeout_helper = AsyncTimeoutTestHelper()
        self.resource_manager = AsyncResourceManager()
        self.enhanced_mock_objects = enhanced_mock_objects
    
    def test_request_timeout_handling(self, test_client, enhanced_mock_objects):
        """Test request timeout handling with slow responses"""
        # Patch the translation function to be slow
        with patch('app.main.translate_text') as mock_translate:
            # Configure mock to simulate slow response
            def slow_translation(*args, **kwargs):
                time.sleep(3)  # Simulate 3-second delay
                return "Translated: Slow response"
            
            mock_translate.side_effect = slow_translation
            
            # Test with normal timeout expectation
            start_time = time.time()
            response = test_client.post(
                "/translate",
                json={
                    "text": "Test slow translation",
                    "source_lang": "eng_Latn",
                    "target_lang": "fra_Latn"
                },
                headers={"X-API-Key": "test_api_key"},
                timeout=5.0  # 5-second timeout
            )
            execution_time = time.time() - start_time
            
            # Should complete successfully within timeout
            assert response.status_code == 200
            assert execution_time < 5.0
            assert "translated_text" in response.json()
    
    def test_connection_timeout_scenarios(self, test_client, enhanced_mock_objects):
        """Test various connection timeout scenarios"""
        timeout_scenarios = [
            {'timeout': 1.0, 'expected_behavior': 'fast_response'},
            {'timeout': 0.1, 'expected_behavior': 'potential_timeout'},
            {'timeout': 10.0, 'expected_behavior': 'guaranteed_success'}
        ]
        
        for scenario in timeout_scenarios:
            start_time = time.time()
            
            try:
                response = test_client.post(
                    "/translate",
                    json={
                        "text": f"Timeout test {scenario['timeout']}s",
                        "source_lang": "eng_Latn",
                        "target_lang": "spa_Latn"
                    },
                    headers={"X-API-Key": "test_api_key"},
                    timeout=scenario['timeout']
                )
                
                execution_time = time.time() - start_time
                
                if scenario['expected_behavior'] == 'guaranteed_success':
                    assert response.status_code == 200
                    assert execution_time <= scenario['timeout'] + 0.5
                
                elif scenario['expected_behavior'] == 'fast_response':
                    assert execution_time <= scenario['timeout']
                    if response.status_code == 200:
                        assert "translated_text" in response.json()
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                if scenario['expected_behavior'] == 'potential_timeout':
                    # Timeout is acceptable for very short timeouts
                    assert execution_time <= scenario['timeout'] + 0.1
                else:
                    # Unexpected timeout
                    pytest.fail(f"Unexpected timeout in scenario {scenario}: {e}")
    
    @pytest.mark.asyncio
    async def test_async_operation_cancellation(self):
        """Test proper cancellation of async operations"""
        # Test scenarios with different timeout durations
        scenarios = [
            self.timeout_helper.create_timeout_scenario(1.0, 2.0),  # Should timeout
            self.timeout_helper.create_timeout_scenario(3.0, 1.0),  # Should complete
            self.timeout_helper.create_timeout_scenario(0.5, 5.0),  # Should timeout quickly
        ]
        
        for scenario in scenarios:
            if scenario['should_timeout']:
                # Test timeout scenario
                result = await self.timeout_helper.test_async_cancellation(
                    lambda: self.timeout_helper.simulate_slow_translation(scenario['operation_duration']),
                    scenario['timeout_duration']
                )
                
                assert result['error'] == "TimeoutError"
                assert result['timeout_respected']
                assert result['execution_time'] <= scenario['timeout_duration'] + 0.5
                
            else:
                # Test successful completion
                result = await self.timeout_helper.test_async_cancellation(
                    lambda: self.timeout_helper.simulate_slow_translation(scenario['operation_duration']),
                    scenario['timeout_duration']
                )
                
                assert result['error'] is None
                assert result['result'] is not None
                assert "Translated:" in result['result']
    
    @pytest.mark.asyncio
    async def test_hanging_operation_handling(self):
        """Test handling of operations that hang indefinitely"""
        # Test that hanging operations are properly cancelled
        result = await self.timeout_helper.test_async_cancellation(
            self.timeout_helper.simulate_hanging_operation,
            2.0  # 2-second timeout
        )
        
        assert result['error'] == "TimeoutError"
        assert result['cancelled'] or result['timeout_respected']
        assert result['execution_time'] <= 2.5  # Should be close to timeout
    
    @pytest.mark.asyncio
    async def test_concurrent_async_operations_with_timeouts(self):
        """Test multiple concurrent async operations with different timeouts"""
        # Create multiple concurrent operations with different characteristics
        operations = [
            {'delay': 1.0, 'timeout': 2.0, 'should_succeed': True},
            {'delay': 3.0, 'timeout': 2.0, 'should_succeed': False},
            {'delay': 0.5, 'timeout': 1.0, 'should_succeed': True},
            {'delay': 4.0, 'timeout': 1.0, 'should_succeed': False},
        ]
        
        # Start all operations concurrently
        tasks = []
        for i, op in enumerate(operations):
            task = asyncio.create_task(
                self.timeout_helper.test_async_cancellation(
                    lambda delay=op['delay']: self.timeout_helper.simulate_slow_translation(delay),
                    op['timeout']
                )
            )
            tasks.append((task, op))
        
        # Wait for all to complete
        results = await asyncio.gather(*[task for task, _ in tasks], return_exceptions=True)
        
        # Validate results
        for i, (result, operation) in enumerate(zip(results, operations)):
            if operation['should_succeed']:
                assert not isinstance(result, Exception)
                assert result['error'] is None or result['result'] is not None
            else:
                assert not isinstance(result, Exception)
                assert result['error'] == "TimeoutError"
                assert result['timeout_respected']
    
    @pytest.mark.asyncio
    async def test_resource_cleanup_after_timeout(self):
        """Test that resources are properly cleaned up after timeouts"""
        initial_usage = self.resource_manager.track_resource_usage()
        
        # Perform resource-intensive operations that timeout
        timeout_operations = []
        for i in range(5):
            try:
                result = await asyncio.wait_for(
                    self.resource_manager.simulate_resource_intensive_operation(5.0),  # 5-second operation
                    timeout=1.0  # 1-second timeout
                )
                timeout_operations.append(result)
            except asyncio.TimeoutError:
                timeout_operations.append({'timeout': True})
        
        # Allow some time for cleanup
        await asyncio.sleep(1.0)
        
        # Check resource usage after cleanup
        final_usage = self.resource_manager.track_resource_usage()
        
        # Memory usage should not have grown significantly
        memory_growth = final_usage['memory_mb'] - initial_usage['memory_mb']
        assert memory_growth < 100, f"Memory leak detected: {memory_growth:.2f} MB growth"
        
        # GC count should be reasonable (not indicating massive object leaks)
        gc_growth = final_usage['gc_count'] - initial_usage['gc_count']
        assert gc_growth < 10000, f"Object leak detected: {gc_growth} new objects"
    
    def test_client_timeout_behavior(self, test_client, enhanced_mock_objects):
        """Test client-side timeout behavior"""
        with patch('app.main.translate_text') as mock_translate:
            # Mock function that varies response time
            response_times = [0.1, 0.5, 1.0, 2.0, 0.3]
            
            def variable_speed_translation(*args, **kwargs):
                delay = response_times[len(mock_translate.call_args_list) % len(response_times)]
                time.sleep(delay)
                return f"Translated: Response after {delay}s"
            
            mock_translate.side_effect = variable_speed_translation
            
            # Test multiple requests with different client timeouts
            timeout_tests = [
                {'client_timeout': 3.0, 'expected_successes': 5},
                {'client_timeout': 1.5, 'expected_successes': 4},
                {'client_timeout': 0.8, 'expected_successes': 3},
            ]
            
            for test_config in timeout_tests:
                success_count = 0
                
                # Reset mock call count
                mock_translate.reset_mock()
                
                for i in range(5):
                    try:
                        start_time = time.time()
                        response = test_client.post(
                            "/translate",
                            json={
                                "text": f"Client timeout test {i}",
                                "source_lang": "eng_Latn",
                                "target_lang": "fra_Latn"
                            },
                            headers={"X-API-Key": "test_api_key"},
                            timeout=test_config['client_timeout']
                        )
                        execution_time = time.time() - start_time
                        
                        if response.status_code == 200:
                            success_count += 1
                            assert execution_time <= test_config['client_timeout'] + 0.1
                        
                    except Exception:
                        # Timeout occurred - this is expected for some tests
                        pass
                
                # Validate expected behavior
                assert success_count >= test_config['expected_successes'] - 1, \
                    f"Too few successes with {test_config['client_timeout']}s timeout: {success_count}"
    
    @pytest.mark.asyncio
    async def test_async_context_manager_cleanup(self):
        """Test proper cleanup of async context managers"""
        class TestAsyncContext:
            def __init__(self):
                self.entered = False
                self.exited = False
                self.cleanup_called = False
            
            async def __aenter__(self):
                self.entered = True
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                self.exited = True
                self.cleanup_called = True
                return False
            
            async def do_work(self, duration: float):
                await asyncio.sleep(duration)
                return "work_completed"
        
        # Test successful context manager usage
        async_context = TestAsyncContext()
        
        async with async_context:
            result = await async_context.do_work(0.1)
            assert result == "work_completed"
        
        assert async_context.entered
        assert async_context.exited
        assert async_context.cleanup_called
        
        # Test context manager cleanup on timeout
        timeout_context = TestAsyncContext()
        
        try:
            async with timeout_context:
                await asyncio.wait_for(timeout_context.do_work(5.0), timeout=1.0)
        except asyncio.TimeoutError:
            pass  # Expected timeout
        
        # Context manager should still have cleaned up
        assert timeout_context.entered
        assert timeout_context.exited
        assert timeout_context.cleanup_called
    
    def test_signal_handling_during_async_operations(self, test_client, enhanced_mock_objects):
        """Test signal handling during async operations"""
        # This test simulates signal interruption scenarios
        signal_test_results = []
        
        def signal_handler(signum, frame):
            signal_test_results.append(f"Signal {signum} received")
        
        # Set up signal handler
        original_handler = signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Test normal operation
            response = test_client.post(
                "/translate",
                json={
                    "text": "Signal handling test",
                    "source_lang": "eng_Latn",
                    "target_lang": "fra_Latn"
                },
                headers={"X-API-Key": "test_api_key"}
            )
            
            assert response.status_code == 200
            assert "translated_text" in response.json()
            
            # Verify no unexpected signals were handled
            assert len(signal_test_results) == 0
            
        finally:
            # Restore original signal handler
            signal.signal(signal.SIGTERM, original_handler)