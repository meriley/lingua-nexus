"""
Timeout configuration for E2E tests based on execution categories.

This module provides appropriate timeout values for different types of E2E tests,
ensuring tests have sufficient time for real operations while preventing excessive waits.
"""

import os
from typing import Dict, Union
from dataclasses import dataclass
from enum import Enum


class TestCategory(Enum):
    """Test execution categories with associated timeout profiles."""
    QUICK = "quick"           # Tests with cached models (< 2 minutes)
    FAST = "fast"            # Fast tests (< 30 seconds)  
    MEDIUM = "medium"        # Medium tests (30 seconds - 5 minutes)
    SLOW = "slow"            # Slow tests (5+ minutes)
    FULL = "full"            # Tests with fresh model downloads (30+ minutes)
    CACHED = "cached"        # Tests using pre-cached models
    WARMUP = "warmup"        # Tests requiring model cache pre-warming


@dataclass
class TimeoutProfile:
    """Timeout configuration profile for a test category."""
    service_startup: int      # Time for service to start (seconds)
    model_loading: int        # Time for model loading (seconds)  
    health_check: int         # Time for health check requests (seconds)
    translation: int          # Time for translation requests (seconds)
    test_execution: int       # Total test execution timeout (seconds)
    cleanup: int             # Time for cleanup operations (seconds)


class E2ETimeoutConfig:
    """Centralized timeout configuration for E2E tests."""
    
    # Timeout profiles for different test categories
    PROFILES: Dict[TestCategory, TimeoutProfile] = {
        TestCategory.QUICK: TimeoutProfile(
            service_startup=30,      # Quick service startup
            model_loading=60,        # Cached models load quickly
            health_check=10,         # Fast health checks
            translation=30,          # Quick translations
            test_execution=120,      # 2 minutes total
            cleanup=15              # Quick cleanup
        ),
        
        TestCategory.FAST: TimeoutProfile(
            service_startup=20,      # Very fast startup
            model_loading=30,        # Minimal model loading
            health_check=5,          # Very fast health checks
            translation=15,          # Fast translations
            test_execution=60,       # 1 minute total
            cleanup=10              # Quick cleanup
        ),
        
        TestCategory.MEDIUM: TimeoutProfile(
            service_startup=60,      # Standard startup time
            model_loading=180,       # 3 minutes for model loading
            health_check=15,         # Standard health checks
            translation=60,          # Standard translations
            test_execution=300,      # 5 minutes total
            cleanup=30              # Standard cleanup
        ),
        
        TestCategory.SLOW: TimeoutProfile(
            service_startup=120,     # Slower startup allowed
            model_loading=600,       # 10 minutes for model loading
            health_check=30,         # Longer health checks
            translation=120,         # Longer translations
            test_execution=900,      # 15 minutes total
            cleanup=60              # Longer cleanup
        ),
        
        TestCategory.FULL: TimeoutProfile(
            service_startup=300,     # 5 minutes for full startup
            model_loading=1800,      # 30 minutes for fresh downloads
            health_check=60,         # Longer health checks
            translation=300,         # Longer translations for large models
            test_execution=2700,     # 45 minutes total
            cleanup=120             # Thorough cleanup
        ),
        
        TestCategory.CACHED: TimeoutProfile(
            service_startup=45,      # Quick startup with cached models
            model_loading=90,        # Fast loading from cache
            health_check=10,         # Fast health checks
            translation=45,          # Quick translations
            test_execution=180,      # 3 minutes total
            cleanup=20              # Quick cleanup
        ),
        
        TestCategory.WARMUP: TimeoutProfile(
            service_startup=60,      # Standard startup
            model_loading=300,       # 5 minutes for warmup
            health_check=20,         # Standard health checks
            translation=60,          # Standard translations
            test_execution=600,      # 10 minutes total
            cleanup=30              # Standard cleanup
        )
    }
    
    @classmethod
    def get_timeout(cls, category: Union[TestCategory, str], operation: str) -> int:
        """
        Get timeout value for a specific operation in a test category.
        
        Args:
            category: Test category (enum or string)
            operation: Operation name (service_startup, model_loading, etc.)
            
        Returns:
            Timeout value in seconds
            
        Raises:
            ValueError: If category or operation is invalid
        """
        if isinstance(category, str):
            try:
                category = TestCategory(category)
            except ValueError:
                raise ValueError(f"Invalid test category: {category}")
        
        if category not in cls.PROFILES:
            raise ValueError(f"No timeout profile for category: {category}")
            
        profile = cls.PROFILES[category]
        
        if not hasattr(profile, operation):
            raise ValueError(f"Invalid operation: {operation}")
            
        return getattr(profile, operation)
    
    @classmethod
    def get_profile(cls, category: Union[TestCategory, str]) -> TimeoutProfile:
        """
        Get complete timeout profile for a test category.
        
        Args:
            category: Test category (enum or string)
            
        Returns:
            TimeoutProfile instance
        """
        if isinstance(category, str):
            category = TestCategory(category)
            
        return cls.PROFILES[category]
    
    @classmethod
    def apply_environment_overrides(cls) -> None:
        """
        Apply timeout overrides from environment variables.
        
        Environment variables format: E2E_TIMEOUT_{CATEGORY}_{OPERATION}
        Example: E2E_TIMEOUT_QUICK_MODEL_LOADING=120
        """
        for category in TestCategory:
            profile = cls.PROFILES[category]
            category_name = category.value.upper()
            
            for operation in ['service_startup', 'model_loading', 'health_check', 
                            'translation', 'test_execution', 'cleanup']:
                env_var = f"E2E_TIMEOUT_{category_name}_{operation.upper()}"
                env_value = os.environ.get(env_var)
                
                if env_value:
                    try:
                        timeout_value = int(env_value)
                        setattr(profile, operation, timeout_value)
                    except ValueError:
                        pass  # Ignore invalid values
    
    @classmethod
    def get_pytest_timeout(cls, category: Union[TestCategory, str]) -> int:
        """
        Get pytest timeout value for a test category.
        
        This is used for the @pytest.mark.timeout decorator.
        
        Args:
            category: Test category
            
        Returns:
            Timeout value in seconds for pytest
        """
        profile = cls.get_profile(category)
        # Add 20% buffer for pytest timeout to allow for cleanup
        return int(profile.test_execution * 1.2)


def configure_timeouts_for_test(test_markers: list) -> TimeoutProfile:
    """
    Configure timeouts based on pytest markers present on a test.
    
    Args:
        test_markers: List of pytest marker names
        
    Returns:
        TimeoutProfile for the test
    """
    # Priority order for determining test category
    category_priority = [
        TestCategory.FAST,
        TestCategory.QUICK,
        TestCategory.CACHED,
        TestCategory.MEDIUM,
        TestCategory.WARMUP,
        TestCategory.SLOW,
        TestCategory.FULL
    ]
    
    # Find the highest priority category that matches the test markers
    for category in category_priority:
        if category.value in test_markers:
            return E2ETimeoutConfig.get_profile(category)
    
    # Default to medium timeouts if no specific category found
    return E2ETimeoutConfig.get_profile(TestCategory.MEDIUM)


# Apply environment overrides when module is imported
E2ETimeoutConfig.apply_environment_overrides()


# Export commonly used functions
__all__ = [
    'E2ETimeoutConfig',
    'TestCategory',
    'TimeoutProfile',
    'configure_timeouts_for_test'
]