from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.api.deps import (
    AuthContext,
    get_audit_repository,
    get_broadcast_repository,
    get_tenant_repository,
    require_roles,
)
from app.models.broadcast import Broadcast, BroadcastCreate
from app.models.tenant import UserRole
from app.repositories.misc_repositories import AuditLogRepository, BroadcastRepository
from app.repositories.tenant_repository import TenantRepository
from app.services.audit_service import AuditService
from app.services.broadcast_service import BroadcastService
from app.services.whatsapp_service import WhatsAppService

router = APIRouter(prefix="/broadcasts", tags=["broadcasts"])

# Only owners/admins can trigger bulk sends — an AGENT (human-handoff operator)
# should not be able to mass-message the tenant's entire customer list.
_can_manage_broadcasts = require_roles(UserRole.OWNER, UserRole.ADMIN)


@router.get("", response_model=list[Broadcast])
async def list_broadcasts(
    ctx: Annotated[AuthContext, Depends(_can_manage_broadcasts)],
    repo: Annotated[BroadcastRepository, Depends(get_broadcast_repository)],
):
    service = BroadcastService(repo)
    return await service.list_broadcasts(ctx.tenant_id)


@router.post("", response_model=Broadcast)
async def create_and_send_broadcast(
    payload: BroadcastCreate,
    background_tasks: BackgroundTasks,
    ctx: Annotated[AuthContext, Depends(_can_manage_broadcasts)],
    broadcast_repo: Annotated[BroadcastRepository, Depends(get_broadcast_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_repository)],
):
    tenant = await tenant_repo.get_by_id(ctx.tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    broadcast_service = BroadcastService(broadcast_repo)
    broadcast = await broadcast_service.create_broadcast(
        Broadcast(tenant_id=ctx.tenant_id, created_by_user_id=ctx.user_id, **payload.model_dump())
    )

    wa_service = WhatsAppService(tenant.whatsapp_phone_number_id, tenant.whatsapp_access_token)
    background_tasks.add_task(broadcast_service.execute_broadcast, ctx.tenant_id, broadcast, wa_service)

    await AuditService(audit_repo).record(
        tenant_id=ctx.tenant_id,
        actor_label=f"user:{ctx.user_id}",
        actor_user_id=ctx.user_id,
        action="broadcast.created",
        resource_type="broadcast",
        resource_id=broadcast.id,
        metadata={"recipient_count": len(broadcast.recipient_wa_contact_ids), "template": broadcast.template_name},
    )
    return broadcast


@router.get("/{broadcast_id}", response_model=Broadcast)
async def get_broadcast(
    broadcast_id: str,
    ctx: Annotated[AuthContext, Depends(_can_manage_broadcasts)],
    repo: Annotated[BroadcastRepository, Depends(get_broadcast_repository)],
):
    broadcast = await BroadcastService(repo).get_broadcast(ctx.tenant_id, broadcast_id)
    if not broadcast:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Broadcast not found")
    return broadcast
