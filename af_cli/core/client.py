"""
HTTP client for communicating with the Agentic Fabric Gateway.
"""

import json
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import httpx
import typer

from af_cli.core.config import get_config
from af_cli.core.output import debug, error


class AFClient:
    """HTTP client for Agentic Fabric Gateway API."""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or get_config()
        self.client = httpx.Client(
            base_url=self.config.gateway_url,
            timeout=30.0,
            follow_redirects=True,
        )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for requests."""
        return self.config.get_headers()
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle HTTP response."""
        debug(f"Response: {response.status_code} {response.url}")
        
        if response.status_code == 401:
            error("Authentication failed. Please run 'afctl auth login'")
            raise typer.Exit(1)
        
        if response.status_code == 403:
            error("Access denied. Check your permissions.")
            raise typer.Exit(1)
        
        if response.status_code >= 400:
            try:
                error_data = response.json()
                # Try different error message fields (FastAPI uses "detail")
                error_message = error_data.get("detail") or error_data.get("message") or "Unknown error"
                error(f"API Error: {error_message}")
                # Always show full response for debugging
                debug(f"Response status: {response.status_code}")
                debug(f"Request URL: {response.url}")
                debug(f"Full response: {json.dumps(error_data, indent=2)}")
            except:
                error(f"HTTP Error: {response.status_code}")
                debug(f"Response text: {response.text}")
            raise typer.Exit(1)
        
        try:
            return response.json()
        except:
            return {"message": "Success"}
    
    def get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request."""
        url = urljoin(self.config.gateway_url, path)
        if params:
            # Show params in debug output
            param_str = "&".join(f"{k}={v}" for k, v in params.items())
            debug(f"GET {url}?{param_str}")
        else:
            debug(f"GET {url}")
        
        response = self.client.get(
            path,
            params=params,
            headers=self._get_headers(),
        )
        
        return self._handle_response(response)
    
    def post(self, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make POST request."""
        url = urljoin(self.config.gateway_url, path)
        debug(f"POST {url}")
        
        response = self.client.post(
            path,
            json=data,
            headers=self._get_headers(),
        )
        
        return self._handle_response(response)
    
    def try_post(self, path: str, data: Optional[Dict] = None) -> tuple[bool, int, Optional[Dict[str, Any]]]:
        """Make POST request without exiting on error. Returns (success, status_code, response_data)."""
        url = urljoin(self.config.gateway_url, path)
        debug(f"POST {url}")
        
        try:
            response = self.client.post(
                path,
                json=data,
                headers=self._get_headers(),
            )
            
            debug(f"Response: {response.status_code} {response.url}")
            
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    return False, response.status_code, error_data
                except:
                    return False, response.status_code, {"detail": response.text}
            
            try:
                return True, response.status_code, response.json()
            except:
                return True, response.status_code, {"message": "Success"}
                
        except Exception as e:
            return False, 0, {"detail": str(e)}
    
    def put(self, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make PUT request."""
        url = urljoin(self.config.gateway_url, path)
        debug(f"PUT {url}")
        
        response = self.client.put(
            path,
            json=data,
            headers=self._get_headers(),
        )
        
        return self._handle_response(response)
    
    def delete(self, path: str) -> Dict[str, Any]:
        """Make DELETE request."""
        url = urljoin(self.config.gateway_url, path)
        debug(f"DELETE {url}")
        
        response = self.client.delete(
            path,
            headers=self._get_headers(),
        )
        
        return self._handle_response(response)
    
    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_client() -> AFClient:
    """Get HTTP client instance."""
    return AFClient() 