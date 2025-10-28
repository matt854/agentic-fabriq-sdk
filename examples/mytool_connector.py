"""
Example ToolConnector using SDK auth decorators.
"""

from typing import Any, Dict, Optional

import httpx

from af_sdk.connectors.base import ToolConnector
from af_sdk.auth.oauth import oauth_required


class MyToolConnector(ToolConnector):
    TOOL_ID = "mytool"

    @oauth_required(scopes=["mytool.read"])
    async def list_items(self, *, limit: int = 10, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        # Make an authenticated request; headers contain the Bearer token
        async with httpx.AsyncClient() as client:
            r = await client.get("https://api.mytool.example/items", headers=headers, params={"limit": limit})
            r.raise_for_status()
            return r.json()

    async def invoke(self, method: str, **kwargs):
        return await getattr(self, method)(**kwargs)


