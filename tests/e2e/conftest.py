"""E2E test configuration and fixtures."""

import pytest
import logging
from typing import Generator, Dict, Any
from pathlib import Path

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    DOCKER_AVAILABLE = False

from .utils.service_manager import E2EServiceManager, ServiceConfig
from .utils.http_client import E2EHttpClient


class E2ETestConfig:
    """Test configuration for E2E tests."""
    
    # Valid configurations for testing
    VALID_CONFIGS = {
        "default": ServiceConfig(
            api_key="test-api-key-12345",
            model_name="facebook/nllb-200-distilled-600M",
            cache_dir="/tmp/test_cache",
            log_level="INFO"
        ),
        "debug": ServiceConfig(
            api_key="debug-api-key-67890",
            model_name="facebook/nllb-200-distilled-600M",
            cache_dir="/tmp/debug_cache",
            log_level="DEBUG"
        ),
        "custom_model": ServiceConfig(
            api_key="custom-api-key-11111",
            model_name="facebook/nllb-200-distilled-600M",  # Keep same for testing
            cache_dir="/tmp/custom_cache",
            log_level="INFO"
        )
    }
    
    # Invalid configurations for error testing
    INVALID_CONFIGS = {
        "empty_api_key": ServiceConfig(
            api_key="",
            model_name="facebook/nllb-200-distilled-600M",
            cache_dir="/tmp/invalid_cache",
            log_level="INFO"
        ),
        "invalid_model": ServiceConfig(
            api_key="invalid-test-key",
            model_name="non/existent-model",
            cache_dir="/tmp/invalid_model_cache",
            log_level="INFO"
        ),
        "invalid_log_level": ServiceConfig(
            api_key="invalid-log-test-key",
            model_name="facebook/nllb-200-distilled-600M",
            cache_dir="/tmp/invalid_log_cache",
            log_level="INVALID_LEVEL"
        )
    }
    
    # Test data for translations
    TRANSLATION_TEST_DATA = [
        {
            "text": "Hello, world!",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn",
            "expected_keywords": ["bonjour", "monde", "salut"]  # May contain these
        },
        {
            "text": "How are you?",
            "source_lang": "eng_Latn", 
            "target_lang": "spa_Latn",
            "expected_keywords": ["cómo", "está", "como"]  # May contain these
        },
        {
            "text": "Good morning",
            "source_lang": "eng_Latn",
            "target_lang": "deu_Latn", 
            "expected_keywords": ["guten", "morgen", "tag"]  # May contain these
        },
        {
            "text": "Thank you very much",
            "source_lang": "eng_Latn",
            "target_lang": "ita_Latn",
            "expected_keywords": ["grazie", "molto", "prego"]  # May contain these
        }
    ]
    
    # Unicode and special character test data
    UNICODE_TEST_DATA = [
        {
            "text": "Hello 👋 World 🌍",
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn"
        },
        {
            "text": "Café, naïve, résumé",
            "source_lang": "eng_Latn",
            "target_lang": "spa_Latn"
        },
        {
            "text": "测试文本",
            "source_lang": "zho_Hans",
            "target_lang": "eng_Latn"
        }
    ]
    
    # Performance test configuration
    PERFORMANCE_CONFIG = {
        "concurrent_connections": 10,
        "requests_per_connection": 5,
        "max_response_time": 2.0,  # seconds
        "health_check_max_time": 0.1,  # seconds
        "startup_timeout": 30,  # seconds
    }


@pytest.fixture(scope="session")
def e2e_service_manager() -> Generator[E2EServiceManager, None, None]:
    """Session-scoped service manager for E2E tests."""
    manager = E2EServiceManager()
    try:
        yield manager
    finally:
        # Ensure cleanup even if tests fail
        if manager.is_running():
            manager.stop_service()


@pytest.fixture(scope="function")
def running_service(e2e_service_manager: E2EServiceManager) -> Generator[str, None, None]:
    """Function-scoped fixture that provides a running service instance."""
    config = E2ETestConfig.VALID_CONFIGS["default"]
    
    try:
        service_url = e2e_service_manager.start_service(config)
        yield service_url
    finally:
        # Cleanup after each test
        e2e_service_manager.stop_service()


@pytest.fixture(scope="function")
def e2e_client(running_service: str) -> Generator[E2EHttpClient, None, None]:
    """HTTP client configured for E2E testing with authentication."""
    config = E2ETestConfig.VALID_CONFIGS["default"]
    
    headers = {
        "X-API-Key": config.api_key,
        "Content-Type": "application/json"
    }
    
    with E2EHttpClient(running_service, default_headers=headers) as client:
        yield client


@pytest.fixture(scope="session")
def docker_manager():
    """Session-scoped Docker manager for container tests."""
    if not DOCKER_AVAILABLE:
        pytest.skip("Docker not available - install docker package")
    
    try:
        client = docker.from_env()
        # Test Docker connectivity
        client.ping()
        yield client
    except Exception as e:
        pytest.skip(f"Docker not available: {e}")
    finally:
        if 'client' in locals():
            client.close()


@pytest.fixture
def test_config() -> E2ETestConfig:
    """Provide test configuration object."""
    return E2ETestConfig()


@pytest.fixture
def valid_service_configs() -> Dict[str, ServiceConfig]:
    """Provide valid service configurations for testing."""
    return E2ETestConfig.VALID_CONFIGS


@pytest.fixture
def invalid_service_configs() -> Dict[str, ServiceConfig]:
    """Provide invalid service configurations for error testing."""
    return E2ETestConfig.INVALID_CONFIGS


@pytest.fixture
def translation_test_data() -> list[Dict[str, Any]]:
    """Provide translation test data."""
    return E2ETestConfig.TRANSLATION_TEST_DATA


@pytest.fixture
def unicode_test_data() -> list[Dict[str, Any]]:
    """Provide Unicode and special character test data."""
    return E2ETestConfig.UNICODE_TEST_DATA


@pytest.fixture
def performance_config() -> Dict[str, Any]:
    """Provide performance test configuration."""
    return E2ETestConfig.PERFORMANCE_CONFIG


# Pytest configuration for E2E tests
def pytest_configure(config):
    """Configure pytest for E2E tests."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "e2e_foundation: mark test as foundation E2E test"
    )
    config.addinivalue_line(
        "markers", "e2e_performance: mark test as performance E2E test"
    )
    config.addinivalue_line(
        "markers", "e2e_docker: mark test as Docker deployment E2E test"
    )
    config.addinivalue_line(
        "markers", "e2e_slow: mark test as slow E2E test"
    )
    
    # Configure logging for E2E tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/tmp/e2e_tests.log')
        ]
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Auto-mark E2E tests
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            
        # Auto-mark slow tests based on name patterns
        if any(keyword in item.name.lower() for keyword in ["performance", "load", "stress", "docker"]):
            item.add_marker(pytest.mark.e2e_slow)


@pytest.fixture(autouse=True)
def e2e_test_logging(request):
    """Auto-logging fixture for E2E tests."""
    logger = logging.getLogger("e2e_test")
    logger.info(f"Starting E2E test: {request.node.name}")
    
    def log_test_result():
        if hasattr(request.node, 'rep_call'):
            if request.node.rep_call.passed:
                logger.info(f"E2E test PASSED: {request.node.name}")
            elif request.node.rep_call.failed:
                logger.error(f"E2E test FAILED: {request.node.name}")
                logger.error(f"Failure reason: {request.node.rep_call.longrepr}")
    
    request.addfinalizer(log_test_result)


@pytest.fixture(autouse=True)
def e2e_timeout_config(request):
    """
    Auto-configure timeouts based on test markers.
    
    This fixture automatically sets appropriate timeout values based on 
    the markers present on the test (e.g., @pytest.mark.quick, @pytest.mark.slow).
    """
    try:
        from .utils.timeout_config import configure_timeouts_for_test, E2ETimeoutConfig
        
        # Get test markers
        test_markers = [marker.name for marker in request.node.iter_markers()]
        
        # Configure timeouts based on markers
        timeout_profile = configure_timeouts_for_test(test_markers)
        
        # Store timeout configuration for the test to use
        request.node.timeout_profile = timeout_profile
        
        # Set environment variables for the test
        import os
        os.environ['E2E_SERVICE_STARTUP_TIMEOUT'] = str(timeout_profile.service_startup)
        os.environ['E2E_MODEL_LOADING_TIMEOUT'] = str(timeout_profile.model_loading)
        os.environ['E2E_HEALTH_CHECK_TIMEOUT'] = str(timeout_profile.health_check)
        os.environ['E2E_TRANSLATION_TIMEOUT'] = str(timeout_profile.translation)
        os.environ['E2E_CLEANUP_TIMEOUT'] = str(timeout_profile.cleanup)
        
        logger = logging.getLogger("e2e_test")
        logger.debug(f"Test {request.node.name} configured with timeouts: "
                    f"startup={timeout_profile.service_startup}s, "
                    f"model={timeout_profile.model_loading}s, "
                    f"total={timeout_profile.test_execution}s")
        
    except ImportError:
        # Fallback if timeout_config module not available
        pass


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Store test results for logging."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)