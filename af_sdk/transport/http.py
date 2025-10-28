"""
HTTP transport layer for Agentic Fabric SDK.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import httpx
from opentelemetry import trace
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

from ..exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    UpstreamError,
    ValidationError,
    create_exception_from_response,
)


class HTTPClient:
    """HTTP client with retries, tracing, and error handling."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        retries: int = 3,
        backoff_factor: float = 0.5,
        logger: Optional[logging.Logger] = None,
        auth_token: Optional[str] = None,
        user_agent: str = "agentic-fabriq-sdk/1.0.0",
        trace_enabled: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.backoff_factor = backoff_factor
        self.logger = logger or logging.getLogger(__name__)
        self.auth_token = auth_token
        self.user_agent = user_agent
        self.trace_enabled = trace_enabled

        # Configure HTTP client
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "User-Agent": user_agent,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

        # Enable OpenTelemetry tracing
        if trace_enabled:
            HTTPXClientInstrumentor().instrument_client(self.client)

        self.tracer = trace.get_tracer(__name__)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    def _build_url(self, path: str) -> str:
        """Build full URL from base URL and path."""
        return urljoin(self.base_url + "/", path.lstrip("/"))

    def _prepare_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Prepare headers for request."""
        request_headers = headers.copy() if headers else {}
        
        if self.auth_token:
            request_headers.setdefault("Authorization", f"Bearer {self.auth_token}")
        
        return request_headers

    async def _make_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        files: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> httpx.Response:
        """Make HTTP request with retries and error handling."""
        url = self._build_url(path)
        request_headers = self._prepare_headers(headers)
        
        # Generate request ID for tracing
        request_id = f"req_{int(time.time() * 1000)}"
        request_headers["X-Request-ID"] = request_id

        with self.tracer.start_as_current_span(
            f"http_{method.lower()}",
            attributes={
                "http.method": method,
                "http.url": url,
                "http.request_id": request_id,
            },
        ) as span:
            last_exception = None
            
            for attempt in range(self.retries + 1):
                try:
                    self.logger.debug(
                        f"Making {method} request to {url} (attempt {attempt + 1})",
                        extra={
                            "request_id": request_id,
                            "method": method,
                            "url": url,
                            "attempt": attempt + 1,
                        },
                    )

                    response = await self.client.request(
                        method=method,
                        url=url,
                        headers=request_headers,
                        params=params,
                        json=json,
                        data=data,
                        files=files,
                        **kwargs,
                    )

                    # Add response attributes to span
                    span.set_attributes({
                        "http.status_code": response.status_code,
                        "http.response_size": len(response.content),
                    })

                    self.logger.debug(
                        f"Response: {response.status_code}",
                        extra={
                            "request_id": request_id,
                            "status_code": response.status_code,
                            "response_time": response.elapsed.total_seconds(),
                        },
                    )

                    # Handle different status codes
                    if response.status_code < 400:
                        return response
                    elif response.status_code in [429, 502, 503, 504]:
                        # Retry on rate limit and server errors
                        if attempt < self.retries:
                            await self._handle_retry_response(response, attempt)
                            continue
                    
                    # Handle client and server errors
                    await self._handle_error_response(response, request_id)

                except httpx.TimeoutException as e:
                    last_exception = e
                    self.logger.warning(
                        f"Request timeout (attempt {attempt + 1})",
                        extra={"request_id": request_id, "error": str(e)},
                    )
                    if attempt < self.retries:
                        await asyncio.sleep(self.backoff_factor * (2 ** attempt))
                        continue
                    
                except httpx.NetworkError as e:
                    last_exception = e
                    self.logger.warning(
                        f"Network error (attempt {attempt + 1})",
                        extra={"request_id": request_id, "error": str(e)},
                    )
                    if attempt < self.retries:
                        await asyncio.sleep(self.backoff_factor * (2 ** attempt))
                        continue

                except Exception as e:
                    last_exception = e
                    self.logger.error(
                        f"Unexpected error (attempt {attempt + 1})",
                        extra={"request_id": request_id, "error": str(e)},
                    )
                    if attempt < self.retries:
                        await asyncio.sleep(self.backoff_factor * (2 ** attempt))
                        continue

            # All retries exhausted
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            if last_exception:
                raise ServiceUnavailableError(
                    f"Request failed after {self.retries + 1} attempts: {last_exception}",
                    request_id=request_id,
                )
            else:
                raise ServiceUnavailableError(
                    f"Request failed after {self.retries + 1} attempts",
                    request_id=request_id,
                )

    async def _handle_retry_response(self, response: httpx.Response, attempt: int):
        """Handle response that should be retried."""
        if response.status_code == 429:
            # Rate limited - check for Retry-After header
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    delay = float(retry_after)
                    self.logger.info(f"Rate limited, retrying after {delay}s")
                    await asyncio.sleep(delay)
                    return
                except ValueError:
                    pass
        
        # Default exponential backoff
        delay = self.backoff_factor * (2 ** attempt)
        self.logger.info(f"Retrying after {delay}s")
        await asyncio.sleep(delay)

    async def _handle_error_response(self, response: httpx.Response, request_id: str):
        """Handle error responses by raising appropriate exceptions."""
        try:
            error_data = response.json()
        except Exception:
            error_data = {
                "error": "SERVER_ERROR",
                "message": f"HTTP {response.status_code}",
                "request_id": request_id,
            }

        # Map HTTP status codes to exceptions
        status_code = response.status_code
        if status_code == 401:
            raise AuthenticationError(
                error_data.get("message", "Authentication failed"),
                request_id=request_id,
                details=error_data.get("details", {}),
            )
        elif status_code == 403:
            raise AuthorizationError(
                error_data.get("message", "Access denied"),
                request_id=request_id,
                details=error_data.get("details", {}),
            )
        elif status_code == 404:
            raise NotFoundError(
                error_data.get("message", "Resource not found"),
                request_id=request_id,
                details=error_data.get("details", {}),
            )
        elif status_code == 400:
            raise ValidationError(
                error_data.get("message", "Validation failed"),
                request_id=request_id,
                details=error_data.get("details", {}),
            )
        elif status_code == 429:
            raise RateLimitError(
                error_data.get("message", "Rate limit exceeded"),
                request_id=request_id,
                details=error_data.get("details", {}),
            )
        elif status_code >= 500:
            raise UpstreamError(
                error_data.get("message", "Server error"),
                request_id=request_id,
                details=error_data.get("details", {}),
            )
        else:
            # Use error response data if available
            if "error" in error_data:
                raise create_exception_from_response(error_data)
            else:
                raise UpstreamError(
                    f"HTTP {status_code}: {response.text}",
                    request_id=request_id,
                )

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> httpx.Response:
        """Make GET request."""
        return await self._make_request("GET", path, params=params, headers=headers, **kwargs)

    async def post(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> httpx.Response:
        """Make POST request."""
        return await self._make_request("POST", path, json=json, data=data, headers=headers, **kwargs)

    async def put(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> httpx.Response:
        """Make PUT request."""
        return await self._make_request("PUT", path, json=json, data=data, headers=headers, **kwargs)

    async def patch(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> httpx.Response:
        """Make PATCH request."""
        return await self._make_request("PATCH", path, json=json, data=data, headers=headers, **kwargs)

    async def delete(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> httpx.Response:
        """Make DELETE request."""
        return await self._make_request("DELETE", path, headers=headers, **kwargs)

    def set_auth_token(self, token: str):
        """Set authentication token."""
        self.auth_token = token

    def clear_auth_token(self):
        """Clear authentication token."""
        self.auth_token = None 

    async def stream(
        self,
        method: str,
        path: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ):
        """Stream a response using httpx's streaming interface.

        Returns an async context manager yielding the httpx.Response stream.
        """
        url = self._build_url(path)
        request_headers = self._prepare_headers(headers)
        # Add request id for traceability
        request_headers.setdefault("X-Request-ID", f"req_{int(time.time() * 1000)}")
        return self.client.stream(method, url, headers=request_headers, params=params, json=json)