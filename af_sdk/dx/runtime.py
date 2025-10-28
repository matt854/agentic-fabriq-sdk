from __future__ import annotations

from typing import Any, Dict, List, Optional
import os
import httpx


def _base_headers(token: str, tenant_id: Optional[str]) -> Dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if tenant_id:
        headers["X-Tenant-Id"] = tenant_id
    # Dev helper: allow overriding scopes from env for local testing
    debug_scopes = os.getenv("FABRIQ_DEBUG_SCOPES")
    if debug_scopes is not None:
        headers["X-Debug-Scopes"] = debug_scopes
    return headers


class ToolFabric:
    """Thin facade over Fabriq provider proxy endpoints (e.g., Slack).

    This class lets developers think in terms of a "fabric" of tools provided
    by a vendor, while under the hood we call the Gateway proxy endpoints.
    """

    def __init__(self, *, provider: str, base_url: str, access_token: str, tenant_id: Optional[str] = None):
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.token = access_token
        self.tenant_id = tenant_id

    def get_tools(self, names: List[str]) -> List[str]:
        # Placeholder: simply returns opaque method identifiers as strings the Agent understands
        return [f"{self.provider}:{name}" for name in names]

    def invoke(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/proxy/{self.provider}/{action}"
        with httpx.Client(timeout=30.0) as c:
            r = c.post(url, json=params, headers=_base_headers(self.token, self.tenant_id))
            r.raise_for_status()
            return r.json()

