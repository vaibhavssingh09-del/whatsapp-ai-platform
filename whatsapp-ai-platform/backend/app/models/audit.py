from typing import Any, Optional

from app.models.common import TimestampedModel


class AuditLog(TimestampedModel):
    """
    Append-only record of security/business-relevant actions.

    Design decision: audit logs are written by a dedicated service method
    (AuditService.record) called explicitly at each meaningful action site,
    rather than via a generic ORM "on save" hook. Explicit calls make it
    obvious, at the call site, exactly what is being audited and why —
    generic hooks tend to either over-log (every field touch) or silently
    miss actions that don't go through the hooked path (e.g. bulk updates).
    """

    tenant_id: str
    actor_user_id: Optional[str] = None
    actor_label: str  # e.g. "user:jane@acme.com" or "system:langgraph_agent"
    action: str       # e.g. "broadcast.sent", "conversation.handoff", "auth.login"
    resource_type: str
    resource_id: Optional[str] = None
    metadata: dict[str, Any] = {}
    ip_address: Optional[str] = None
