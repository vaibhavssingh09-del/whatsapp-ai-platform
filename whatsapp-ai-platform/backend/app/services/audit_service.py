from typing import Any, Optional

from app.models.audit import AuditLog
from app.repositories.misc_repositories import AuditLogRepository


class AuditService:
    def __init__(self, repo: AuditLogRepository):
        self._repo = repo

    async def record(
        self,
        tenant_id: str,
        actor_label: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        actor_user_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        entry = AuditLog(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            actor_label=actor_label,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata or {},
            ip_address=ip_address,
        )
        return await self._repo.create(entry)

    async def list_recent(self, tenant_id: str, limit: int = 100) -> list[AuditLog]:
        return await self._repo.list_recent(tenant_id, limit=limit)
