"""
FabriqClient: High-level async helper for Agentic Fabric Gateway.

This client wraps common Gateway API flows so agent developers can:
- List and invoke tools
- Invoke agents (via proxy)
- Manage per-user secrets via the Gateway-backed Vault API

Usage:
    from af_sdk.fabriq_client import FabriqClient

    async with FabriqClient(base_url="http://localhost:8000", auth_token=JWT) as af:
        tools = await af.list_tools()
        result = await af.invoke_tool(tool_id, method="list_items", parameters={"limit": 10})
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .transport.http import HTTPClient


class FabriqClient:
    """Async helper around the Gateway REST API.

    Args:
        base_url: Gateway base URL (e.g., "http://localhost:8000").
        auth_token: Bearer JWT with required scopes.
        api_prefix: API root prefix. Defaults to "/api/v1".
        timeout: Request timeout in seconds.
        retries: Number of retry attempts for transient errors.
        backoff_factor: Exponential backoff base delay in seconds.
        trace_enabled: Enable OpenTelemetry HTTPX instrumentation.
    """

    def __init__(
        self,
        *,
        base_url: str,
        auth_token: Optional[str] = None,
        api_prefix: str = "/api/v1",
        timeout: float = 30.0,
        retries: int = 3,
        backoff_factor: float = 0.5,
        trace_enabled: bool = True,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self._root = base_url.rstrip("/")
        self._api = api_prefix if api_prefix.startswith("/") else f"/{api_prefix}"
        self._extra_headers = extra_headers or {}
        self._http = HTTPClient(
            base_url=f"{self._root}{self._api}",
            timeout=timeout,
            retries=retries,
            backoff_factor=backoff_factor,
            auth_token=auth_token,
            trace_enabled=trace_enabled,
        )

    async def __aenter__(self) -> "FabriqClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        await self._http.close()

    # -----------------
    # Tools
    # -----------------
    async def list_tools(self, *, page: int = 1, page_size: int = 20, search: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"page": page, "page_size": page_size}
        if search:
            params["search"] = search
        r = await self._http.get("/tools", params=params, headers=self._extra_headers)
        return r.json()

    async def invoke_connection(
        self,
        connection_id: str,
        *,
        method: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Invoke a tool using its connection ID (preferred method).
        
        This directly uses the connection_id (like 'slacker', 'gurt') to invoke
        the tool without needing to look up UUIDs. This is the most efficient
        and reliable way to invoke tools.
        
        Args:
            connection_id: Connection identifier (e.g., 'slacker', 'gurt')
            method: Method name to invoke
            parameters: Method parameters
            
        Returns:
            Tool invocation result
            
        Examples:
            result = await client.invoke_connection("slacker", method="get_channels")
            result = await client.invoke_connection("slacker", method="post_message",
                                                   parameters={"channel": "test", "text": "Hello!"})
            result = await client.invoke_connection("gurt", method="list_files")
        """
        # Use the direct connection-based invoke endpoint
        # This matches what the CLI uses and is more efficient
        body = {
            "method": method,
            "parameters": parameters or {},
        }
        
        # Call the connection-based invoke endpoint
        r = await self._http.post(
            f"/tools/connections/{connection_id}/invoke",
            json=body,
            headers=self._extra_headers
        )
        return r.json()

    # -----------------
    # Secrets (Gateway-backed Vault)
    # -----------------
    async def get_secret(self, *, path: str, version: Optional[int] = None) -> Dict[str, Any]:
        params = {"version": version} if version is not None else None
        r = await self._http.get(f"/secrets/{path}", params=params, headers=self._extra_headers)
        return r.json()

    async def create_secret(
        self,
        *,
        path: str,
        value: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"value": value}
        if description is not None:
            body["description"] = description
        if metadata is not None:
            body["metadata"] = metadata
        if ttl is not None:
            body["ttl"] = ttl
        r = await self._http.post(f"/secrets/{path}", json=body, headers=self._extra_headers)
        return r.json()

    async def update_secret(
        self,
        *,
        path: str,
        value: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {}
        if value is not None:
            body["value"] = value
        if description is not None:
            body["description"] = description
        if metadata is not None:
            body["metadata"] = metadata
        if ttl is not None:
            body["ttl"] = ttl
        r = await self._http.put(f"/secrets/{path}", json=body, headers=self._extra_headers)
        return r.json()

    async def delete_secret(self, *, path: str) -> Dict[str, Any]:
        r = await self._http.delete(f"/secrets/{path}", headers=self._extra_headers)
        return r.json() if r.content else {"status": "deleted"}


