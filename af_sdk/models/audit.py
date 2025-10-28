from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import uuid4


class AuditEvent(BaseModel):
    """Canonical audit event schema.

    Designed to avoid storing sensitive values; callers should pre-redact.
    """

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: str
    actor_id: Optional[str] = None
    actor_scopes: Optional[list[str]] = None
    source_service: str  # af-gateway | af-registry | other
    action: str          # e.g., agent.create, tool.delete, auth.login
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    route: Optional[str] = None
    method: Optional[str] = None
    status: str = "success"  # success | failure | denied
    request_id: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    mtls_san: Optional[str] = None
    pop_thumbprint: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


def build_audit_subject(source_service: str, action: str, tenant_id: str) -> str:
    """Generate audit subject aligned with AUDIT stream subjects.

    Format: audit.<service>.<action>.<tenant>
    """
    service = source_service.replace("_", "-")
    action_norm = action.replace("/", ".")
    return f"audit.{service}.{action_norm}.{tenant_id}"


