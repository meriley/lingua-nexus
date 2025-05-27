"""
Retry mechanisms for E2E tests with exponential backoff and proper cleanup.
Handles transient failures gracefully for improved test reliability.
"""

import time
import logging
import functools
from typing import Callable, Any, Optional, Union, List, Type
import asyncio
from contextlib import contextmanager


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[Type[Exception]]] = None
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff calculation
            jitter: Whether to add random jitter to delays
            retryable_exceptions: List of exceptions that should trigger retries
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [
            ConnectionError,
            TimeoutError,
            OSError,
            # Common network and service exceptions
            Exception  # Catch-all for testing (more specific in production)
        ]


class RetryManager:
    """Manages retry logic with exponential backoff and cleanup."""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """Initialize retry manager with configuration."""
        self.config = config or RetryConfig()
        self.logger = logging.getLogger(__name__)
        
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number."""
        delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            import random
            # Add up to 20% jitter
            jitter_amount = delay * 0.2 * random.random()
            delay += jitter_amount
            
        return delay
        
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if an exception should trigger a retry."""
        if attempt >= self.config.max_attempts:
            return False
            
        for exc_type in self.config.retryable_exceptions:
            if isinstance(exception, exc_type):
                return True
                
        return False
        
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        cleanup_func: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args: Arguments to pass to function
            cleanup_func: Optional cleanup function to call between retries
            **kwargs: Keyword arguments to pass to function
            
        Returns:
            Result of successful function execution
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                self.logger.debug(f"Executing {func.__name__}, attempt {attempt}/{self.config.max_attempts}")
                result = func(*args, **kwargs)
                
                if attempt > 1:
                    self.logger.info(f"{func.__name__} succeeded after {attempt} attempts")
                    
                return result
                
            except Exception as e:
                last_exception = e
                
                if not self.should_retry(e, attempt):
                    self.logger.error(f"{func.__name__} failed after {attempt} attempts: {e}")
                    raise e
                    
                if attempt < self.config.max_attempts:
                    delay = self.calculate_delay(attempt)
                    self.logger.warning(
                        f"{func.__name__} failed (attempt {attempt}): {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    # Run cleanup function if provided
                    if cleanup_func:
                        try:
                            cleanup_func()
                        except Exception as cleanup_error:
                            self.logger.warning(f"Cleanup failed: {cleanup_error}")
                    
                    time.sleep(delay)
                else:
                    self.logger.error(f"{func.__name__} failed after {attempt} attempts: {e}")
                    
        if last_exception:
            raise last_exception


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
    cleanup_func: Optional[Callable] = None
):
    """
    Decorator for adding retry logic to functions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        retryable_exceptions: List of exceptions that should trigger retries
        cleanup_func: Optional cleanup function to call between retries
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                retryable_exceptions=retryable_exceptions
            )
            retry_manager = RetryManager(config)
            
            return retry_manager.execute_with_retry(
                func, *args, cleanup_func=cleanup_func, **kwargs
            )
            
        return wrapper
    return decorator


@contextmanager
def retry_context(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: Optional[List[Type[Exception]]] = None
):
    """
    Context manager for retry logic.
    
    Usage:
        with retry_context(max_attempts=3) as retry:
            for attempt in retry:
                # Your code here
                if success:
                    break
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        retryable_exceptions=retryable_exceptions
    )
    retry_manager = RetryManager(config)
    
    class RetryIterator:
        def __init__(self, manager: RetryManager):
            self.manager = manager
            self.attempt = 0
            self.last_exception = None
            
        def __iter__(self):
            return self
            
        def __next__(self):
            self.attempt += 1
            
            if self.attempt > self.manager.config.max_attempts:
                if self.last_exception:
                    raise self.last_exception
                raise StopIteration
                
            return self.attempt
            
        def failed(self, exception: Exception):
            """Mark current attempt as failed."""
            self.last_exception = exception
            
            if self.attempt < self.manager.config.max_attempts:
                if self.manager.should_retry(exception, self.attempt):
                    delay = self.manager.calculate_delay(self.attempt)
                    self.manager.logger.warning(
                        f"Attempt {self.attempt} failed: {exception}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)
                else:
                    raise exception
            else:
                raise exception
    
    yield RetryIterator(retry_manager)


class ServiceRetryMixin:
    """Mixin class to add retry capabilities to service managers."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.retry_manager = RetryManager(RetryConfig(
            max_attempts=3,
            base_delay=2.0,
            max_delay=30.0,
            retryable_exceptions=[
                ConnectionError,
                TimeoutError,
                OSError,
                RuntimeError  # For service startup failures
            ]
        ))
        
    def start_with_retry(self, start_func: Callable, cleanup_func: Optional[Callable] = None, *args, **kwargs):
        """Start service with retry logic."""
        return self.retry_manager.execute_with_retry(
            start_func, *args, cleanup_func=cleanup_func, **kwargs
        )
        
    def request_with_retry(self, request_func: Callable, *args, **kwargs):
        """Make request with retry logic."""
        config = RetryConfig(
            max_attempts=5,  # More attempts for requests
            base_delay=0.5,  # Shorter delays for requests
            max_delay=10.0,
            retryable_exceptions=[
                ConnectionError,
                TimeoutError,
                OSError
            ]
        )
        retry_manager = RetryManager(config)
        
        return retry_manager.execute_with_retry(request_func, *args, **kwargs)


class ModelLoadingRetryMixin:
    """Specialized retry logic for model loading operations."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_retry_manager = RetryManager(RetryConfig(
            max_attempts=2,  # Model loading is expensive, limit retries
            base_delay=10.0,  # Longer delays for model loading
            max_delay=60.0,
            retryable_exceptions=[
                ConnectionError,
                TimeoutError,
                RuntimeError,
                OSError
            ]
        ))
        
    def load_model_with_retry(
        self, 
        load_func: Callable, 
        cleanup_func: Optional[Callable] = None,
        *args, 
        **kwargs
    ):
        """Load model with specialized retry logic."""
        return self.model_retry_manager.execute_with_retry(
            load_func, *args, cleanup_func=cleanup_func, **kwargs
        )


# Convenience functions for common retry patterns

def retry_service_start(max_attempts: int = 3, base_delay: float = 2.0):
    """Decorator specifically for service startup operations."""
    return retry_with_backoff(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=30.0,
        retryable_exceptions=[ConnectionError, TimeoutError, OSError, RuntimeError]
    )


def retry_http_request(max_attempts: int = 5, base_delay: float = 0.5):
    """Decorator specifically for HTTP requests."""
    return retry_with_backoff(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=10.0,
        retryable_exceptions=[ConnectionError, TimeoutError, OSError]
    )


def retry_model_operation(max_attempts: int = 2, base_delay: float = 10.0):
    """Decorator specifically for model operations (loading, inference)."""
    return retry_with_backoff(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=60.0,
        retryable_exceptions=[ConnectionError, TimeoutError, RuntimeError, OSError]
    )


# Example usage functions for testing

def test_retry_functionality():
    """Test function to verify retry mechanisms work correctly."""
    attempt_count = 0
    
    @retry_with_backoff(max_attempts=3, base_delay=0.1)
    def flaky_function():
        nonlocal attempt_count
        attempt_count += 1
        
        if attempt_count < 3:
            raise ConnectionError(f"Simulated failure on attempt {attempt_count}")
        
        return f"Success on attempt {attempt_count}"
    
    try:
        result = flaky_function()
        print(f"Retry test passed: {result}")
        return True
    except Exception as e:
        print(f"Retry test failed: {e}")
        return False


if __name__ == "__main__":
    # Run basic test when module is executed directly
    test_retry_functionality()