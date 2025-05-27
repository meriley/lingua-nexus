"""E2E HTTP Client for enhanced response handling and timing measurements."""

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union
import requests
import logging


@dataclass
class E2EResponse:
    """Enhanced response wrapper with timing and parsing utilities."""
    status_code: int
    json_data: Optional[Dict[str, Any]]
    headers: Dict[str, str]
    response_time: float  # in seconds
    text: str
    url: str
    method: str
    
    @property
    def is_success(self) -> bool:
        """Check if response indicates success (2xx status code)."""
        return 200 <= self.status_code < 300
    
    @property
    def is_client_error(self) -> bool:
        """Check if response indicates client error (4xx status code)."""
        return 400 <= self.status_code < 500
    
    @property
    def is_server_error(self) -> bool:
        """Check if response indicates server error (5xx status code)."""
        return 500 <= self.status_code < 600
    
    def json(self) -> Dict[str, Any]:
        """Compatibility method to match requests.Response.json()."""
        if self.json_data is None:
            raise ValueError("No JSON data available")
        return self.json_data


class E2EHttpClient:
    """Enhanced HTTP client for E2E testing with timing and response utilities."""
    
    def __init__(self, base_url: str, default_headers: Optional[Dict[str, str]] = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        
        if default_headers:
            self.session.headers.update(default_headers)
    
    def request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
        **kwargs
    ) -> E2EResponse:
        """Make HTTP request with timing and enhanced response handling."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Merge headers
        request_headers = {}
        if headers:
            request_headers.update(headers)
        
        # Measure request time
        start_time = time.time()
        
        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                json=json_data,
                headers=request_headers,
                params=params,
                timeout=timeout,
                **kwargs
            )
            
            response_time = time.time() - start_time
            
            # Parse JSON if possible
            parsed_json = None
            try:
                if response.headers.get('content-type', '').startswith('application/json'):
                    parsed_json = response.json()
            except Exception as e:
                self.logger.debug(f"Failed to parse JSON response: {e}")
            
            return E2EResponse(
                status_code=response.status_code,
                json_data=parsed_json,
                headers=dict(response.headers),
                response_time=response_time,
                text=response.text,
                url=url,
                method=method.upper()
            )
            
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            self.logger.error(f"Request failed: {method} {url} - {e}")
            
            # Return error response
            return E2EResponse(
                status_code=0,  # Indicates network/connection error
                json_data=None,
                headers={},
                response_time=response_time,
                text=str(e),
                url=url,
                method=method.upper()
            )
    
    def get(self, endpoint: str, **kwargs) -> E2EResponse:
        """Make GET request."""
        return self.request("GET", endpoint, **kwargs)
    
    def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, **kwargs) -> E2EResponse:
        """Make POST request."""
        return self.request("POST", endpoint, json_data=json_data, **kwargs)
    
    def put(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, **kwargs) -> E2EResponse:
        """Make PUT request."""
        return self.request("PUT", endpoint, json_data=json_data, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> E2EResponse:
        """Make DELETE request."""
        return self.request("DELETE", endpoint, **kwargs)
    
    def health_check(self, timeout: int = 10) -> E2EResponse:
        """Convenience method for health check endpoint."""
        return self.get("/health", timeout=timeout)
    
    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        timeout: int = 30,
        **kwargs
    ) -> E2EResponse:
        """Convenience method for translation requests."""
        payload = {
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang
        }
        
        return self.post("/translate", json_data=payload, timeout=timeout, **kwargs)
    
    def get_supported_languages(self, timeout: int = 10) -> E2EResponse:
        """Convenience method for getting supported languages."""
        return self.get("/languages", timeout=timeout)
    
    def set_default_header(self, key: str, value: str):
        """Set a default header for all requests."""
        self.session.headers[key] = value
    
    def remove_default_header(self, key: str):
        """Remove a default header."""
        if key in self.session.headers:
            del self.session.headers[key]
    
    def set_api_key(self, api_key: str):
        """Set the API key header."""
        self.set_default_header("X-API-Key", api_key)
    
    def close(self):
        """Close the session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with session cleanup."""
        self.close()


class E2EHttpClientPool:
    """Pool of HTTP clients for concurrent testing."""
    
    def __init__(self, base_url: str, pool_size: int = 10):
        self.base_url = base_url
        self.pool_size = pool_size
        self.clients: list[E2EHttpClient] = []
        self._create_pool()
    
    def _create_pool(self):
        """Create the client pool."""
        for _ in range(self.pool_size):
            client = E2EHttpClient(self.base_url)
            self.clients.append(client)
    
    def get_client(self, index: int = 0) -> E2EHttpClient:
        """Get a client from the pool."""
        if 0 <= index < len(self.clients):
            return self.clients[index]
        raise IndexError(f"Client index {index} out of range")
    
    def get_all_clients(self) -> list[E2EHttpClient]:
        """Get all clients for concurrent testing."""
        return self.clients.copy()
    
    def set_api_key_for_all(self, api_key: str):
        """Set API key for all clients in the pool."""
        for client in self.clients:
            client.set_api_key(api_key)
    
    def close_all(self):
        """Close all clients in the pool."""
        for client in self.clients:
            client.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close_all()