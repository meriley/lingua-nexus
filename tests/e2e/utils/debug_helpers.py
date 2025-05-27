"""Debug utilities for E2E tests."""

import json
import time
import sys
import traceback
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
import logging
from contextlib import contextmanager
import psutil
import requests


class E2EDebugger:
    """Debugging utilities for E2E test development and troubleshooting."""
    
    def __init__(self, debug_dir: str = "/tmp/e2e_debug"):
        self.debug_dir = Path(debug_dir)
        self.debug_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.debug_session_id = int(time.time())
        
    def capture_test_state(
        self,
        test_name: str,
        service_manager=None,
        client=None,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """Capture comprehensive test state for debugging."""
        timestamp = time.time()
        state_data = {
            "test_name": test_name,
            "timestamp": timestamp,
            "session_id": self.debug_session_id,
            "system_info": self._get_system_info(),
            "additional_info": additional_info or {}
        }
        
        # Capture service state if available
        if service_manager:
            state_data["service_state"] = self._capture_service_state(service_manager)
        
        # Capture client state if available
        if client:
            state_data["client_state"] = self._capture_client_state(client)
        
        # Save to file
        filename = f"debug_state_{test_name}_{int(timestamp)}.json"
        filepath = self.debug_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(state_data, f, indent=2, default=str)
        
        self.logger.info(f"Debug state captured: {filepath}")
        return str(filepath)
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get current system information."""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            return {
                "cpu_percent": cpu_percent,
                "memory_total": memory.total,
                "memory_available": memory.available,
                "memory_percent": memory.percent,
                "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None,
                "disk_usage": {
                    "/tmp": dict(psutil.disk_usage("/tmp")._asdict())
                },
                "network_connections": len(psutil.net_connections()),
                "process_count": len(psutil.pids())
            }
        except Exception as e:
            return {"error": f"Failed to get system info: {e}"}
    
    def _capture_service_state(self, service_manager) -> Dict[str, Any]:
        """Capture service manager state."""
        try:
            state = {
                "is_running": service_manager.is_running(),
                "current_port": service_manager.current_port,
                "service_url": service_manager.service_url,
                "process_id": service_manager.process.pid if service_manager.process else None,
                "logs": service_manager.get_service_logs(max_lines=20)
            }
            
            # Get process info if available
            if service_manager.process and service_manager.is_running():
                try:
                    process = psutil.Process(service_manager.process.pid)
                    state["process_info"] = {
                        "cpu_percent": process.cpu_percent(),
                        "memory_info": dict(process.memory_info()._asdict()),
                        "status": process.status(),
                        "create_time": process.create_time(),
                        "num_threads": process.num_threads()
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    state["process_info"] = "Process not accessible"
            
            return state
        except Exception as e:
            return {"error": f"Failed to capture service state: {e}"}
    
    def _capture_client_state(self, client) -> Dict[str, Any]:
        """Capture HTTP client state."""
        try:
            return {
                "base_url": client.base_url,
                "session_headers": dict(client.session.headers),
                "session_cookies": dict(client.session.cookies),
                "last_response_url": getattr(client.session, '_last_response_url', None)
            }
        except Exception as e:
            return {"error": f"Failed to capture client state: {e}"}
    
    def debug_request_response(
        self,
        test_name: str,
        request_details: Dict[str, Any],
        response_details: Dict[str, Any],
        expected_outcome: str = None
    ) -> str:
        """Debug HTTP request/response details."""
        debug_data = {
            "test_name": test_name,
            "timestamp": time.time(),
            "request": request_details,
            "response": response_details,
            "expected_outcome": expected_outcome,
            "analysis": self._analyze_request_response(request_details, response_details)
        }
        
        filename = f"debug_request_{test_name}_{int(time.time())}.json"
        filepath = self.debug_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(debug_data, f, indent=2, default=str)
        
        return str(filepath)
    
    def _analyze_request_response(
        self,
        request: Dict[str, Any],
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze request/response for common issues."""
        analysis = {
            "issues": [],
            "suggestions": []
        }
        
        # Check response status
        status_code = response.get("status_code", 0)
        
        if status_code == 0:
            analysis["issues"].append("Network connection failed")
            analysis["suggestions"].append("Check service availability and network connectivity")
        elif status_code == 401:
            analysis["issues"].append("Authentication failed")
            analysis["suggestions"].extend([
                "Verify API key is correct",
                "Check authentication header format",
                "Ensure API key is not expired"
            ])
        elif status_code == 404:
            analysis["issues"].append("Endpoint not found")
            analysis["suggestions"].extend([
                "Verify URL is correct",
                "Check if service is fully started",
                "Validate API endpoint exists"
            ])
        elif status_code == 500:
            analysis["issues"].append("Server error")
            analysis["suggestions"].extend([
                "Check server logs for errors",
                "Verify service configuration",
                "Check for application bugs"
            ])
        elif status_code == 429:
            analysis["issues"].append("Rate limit exceeded")
            analysis["suggestions"].extend([
                "Reduce request frequency",
                "Implement request throttling",
                "Add delays between requests"
            ])
        
        # Check response time
        response_time = response.get("response_time", 0)
        if response_time > 10:
            analysis["issues"].append("Slow response time")
            analysis["suggestions"].append("Investigate performance bottlenecks")
        
        # Check request format
        if "json_data" in request and not request["json_data"]:
            analysis["issues"].append("Empty request body")
            analysis["suggestions"].append("Ensure request body contains required fields")
        
        return analysis
    
    def trace_test_execution(self, test_function: Callable) -> Callable:
        """Decorator to trace test execution with detailed logging."""
        def wrapper(*args, **kwargs):
            test_name = test_function.__name__
            start_time = time.time()
            
            self.logger.info(f"Starting test execution: {test_name}")
            
            try:
                # Capture initial state
                initial_state_file = self.capture_test_state(f"{test_name}_start")
                
                # Execute test
                result = test_function(*args, **kwargs)
                
                # Capture final state
                final_state_file = self.capture_test_state(f"{test_name}_end")
                
                duration = time.time() - start_time
                self.logger.info(f"Test completed successfully: {test_name} ({duration:.2f}s)")
                
                return result
                
            except Exception as e:
                # Capture failure state
                failure_state_file = self.capture_test_state(f"{test_name}_failure")
                
                # Log detailed error information
                error_details = {
                    "test_name": test_name,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                    "failure_state_file": failure_state_file
                }
                
                self.save_error_details(test_name, error_details)
                
                duration = time.time() - start_time
                self.logger.error(f"Test failed: {test_name} ({duration:.2f}s) - {e}")
                
                raise
        
        return wrapper
    
    def save_error_details(self, test_name: str, error_details: Dict[str, Any]) -> str:
        """Save detailed error information for debugging."""
        filename = f"error_details_{test_name}_{int(time.time())}.json"
        filepath = self.debug_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(error_details, f, indent=2, default=str)
        
        return str(filepath)
    
    def compare_test_states(self, state_file1: str, state_file2: str) -> Dict[str, Any]:
        """Compare two test state files to identify differences."""
        try:
            with open(state_file1, 'r') as f:
                state1 = json.load(f)
            
            with open(state_file2, 'r') as f:
                state2 = json.load(f)
            
            comparison = {
                "timestamp_diff": state2.get("timestamp", 0) - state1.get("timestamp", 0),
                "system_changes": self._compare_system_states(
                    state1.get("system_info", {}),
                    state2.get("system_info", {})
                ),
                "service_changes": self._compare_service_states(
                    state1.get("service_state", {}),
                    state2.get("service_state", {})
                )
            }
            
            return comparison
            
        except Exception as e:
            return {"error": f"Failed to compare states: {e}"}
    
    def _compare_system_states(self, state1: Dict, state2: Dict) -> Dict[str, Any]:
        """Compare system states."""
        changes = {}
        
        for key in ["cpu_percent", "memory_percent"]:
            if key in state1 and key in state2:
                diff = state2[key] - state1[key]
                if abs(diff) > 5:  # Significant change
                    changes[key] = {
                        "before": state1[key],
                        "after": state2[key],
                        "change": diff
                    }
        
        return changes
    
    def _compare_service_states(self, state1: Dict, state2: Dict) -> Dict[str, Any]:
        """Compare service states."""
        changes = {}
        
        # Check running status
        if state1.get("is_running") != state2.get("is_running"):
            changes["running_status"] = {
                "before": state1.get("is_running"),
                "after": state2.get("is_running")
            }
        
        # Check port changes
        if state1.get("current_port") != state2.get("current_port"):
            changes["port"] = {
                "before": state1.get("current_port"),
                "after": state2.get("current_port")
            }
        
        return changes
    
    @contextmanager
    def debug_context(self, test_name: str):
        """Context manager for debugging test execution."""
        self.logger.info(f"Entering debug context: {test_name}")
        start_time = time.time()
        
        try:
            initial_state = self.capture_test_state(f"{test_name}_start")
            yield self
        except Exception as e:
            error_state = self.capture_test_state(f"{test_name}_error")
            self.logger.error(f"Exception in debug context: {e}")
            raise
        finally:
            final_state = self.capture_test_state(f"{test_name}_end")
            duration = time.time() - start_time
            self.logger.info(f"Exiting debug context: {test_name} ({duration:.2f}s)")
    
    def interactive_debug_session(self, service_manager=None, client=None):
        """Start an interactive debugging session."""
        print("\n" + "="*60)
        print("E2E TEST INTERACTIVE DEBUG SESSION")
        print("="*60)
        print("Available commands:")
        print("  state - Show current test state")
        print("  service - Show service information")
        print("  client - Show client information")
        print("  request <url> - Make a test request")
        print("  logs - Show recent service logs")
        print("  system - Show system information")
        print("  quit - Exit debug session")
        print("="*60)
        
        while True:
            try:
                command = input("\ndebug> ").strip().lower()
                
                if command == "quit":
                    break
                elif command == "state":
                    state_file = self.capture_test_state("interactive_debug", service_manager, client)
                    print(f"State captured to: {state_file}")
                elif command == "service" and service_manager:
                    service_info = self._capture_service_state(service_manager)
                    print(json.dumps(service_info, indent=2, default=str))
                elif command == "client" and client:
                    client_info = self._capture_client_state(client)
                    print(json.dumps(client_info, indent=2, default=str))
                elif command.startswith("request") and client:
                    parts = command.split()
                    if len(parts) > 1:
                        endpoint = parts[1]
                        try:
                            response = client.get(endpoint)
                            print(f"Status: {response.status_code}")
                            print(f"Response time: {response.response_time:.3f}s")
                            if response.json_data:
                                print(f"JSON: {json.dumps(response.json_data, indent=2)}")
                        except Exception as e:
                            print(f"Request failed: {e}")
                elif command == "logs" and service_manager:
                    logs = service_manager.get_service_logs(max_lines=10)
                    for log_line in logs:
                        print(f"  {log_line}")
                elif command == "system":
                    system_info = self._get_system_info()
                    print(json.dumps(system_info, indent=2, default=str))
                else:
                    print("Unknown command or missing required objects")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
        
        print("\nDebug session ended.")
    
    def generate_debug_report(self) -> str:
        """Generate a comprehensive debug report."""
        debug_files = list(self.debug_dir.glob("*.json"))
        
        report_data = {
            "session_id": self.debug_session_id,
            "generated_at": time.time(),
            "debug_files_count": len(debug_files),
            "debug_directory": str(self.debug_dir),
            "recent_files": [
                {
                    "filename": f.name,
                    "size": f.stat().st_size,
                    "modified": f.stat().st_mtime
                }
                for f in sorted(debug_files, key=lambda x: x.stat().st_mtime, reverse=True)[:10]
            ]
        }
        
        report_filename = f"debug_report_{self.debug_session_id}.json"
        report_filepath = self.debug_dir / report_filename
        
        with open(report_filepath, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        return str(report_filepath)


# Global debugger instance
_global_debugger: Optional[E2EDebugger] = None


def get_debugger() -> E2EDebugger:
    """Get or create the global debugger instance."""
    global _global_debugger
    if _global_debugger is None:
        _global_debugger = E2EDebugger()
    return _global_debugger


def debug_test(test_function: Callable) -> Callable:
    """Convenience decorator for debugging tests."""
    debugger = get_debugger()
    return debugger.trace_test_execution(test_function)


@contextmanager
def debug_context(test_name: str):
    """Convenience context manager for debugging."""
    debugger = get_debugger()
    with debugger.debug_context(test_name):
        yield debugger