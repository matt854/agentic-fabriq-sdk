"""
Client-side DPoP (Proof of Possession) helper for AF SDK.

This provides a simple HMAC-signed JWT for development that matches the
Gateway's mock PoP verifier semantics. In production, replace with a
DPoP JWT signed using a private key corresponding to the client cert
thumbprint per RFC 9449.
"""

from __future__ import annotations

import time
from typing import Dict, Optional

import jwt


def create_dpop_proof(*, method: str, url: str, thumbprint: str = "dev-thumbprint", lifetime_s: int = 60, secret: Optional[str] = None) -> str:
    """Create a development DPoP-like JWT for AF mock endpoints.

    Args:
        method: HTTP method, e.g., "POST".
        url: Full request URL.
        thumbprint: x5t#S256 thumbprint string (dev default).
        lifetime_s: Token lifetime in seconds.
        secret: HMAC secret for signing (dev only). If not provided, uses a default.

    Returns:
        A compact JWT string to send in the DPoP header.
    """
    now = int(time.time())
    payload: Dict = {
        "htm": method.upper(),
        "htu": url,
        "iat": now,
        "exp": now + lifetime_s,
        "cnf": {"x5t#S256": thumbprint},
        "typ": "pop",
    }
    key = secret or "af-dev-pop-secret"
    return jwt.encode(payload, key, algorithm="HS256")


