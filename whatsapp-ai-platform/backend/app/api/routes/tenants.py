from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import AuthContext, get_auth_context, get_current_user, get_tenant_repository
from app.models.tenant import User
from app.repositories.tenant_repository import TenantRepository

router = APIRouter(prefix="/tenants", tags=["tenants"])


class TenantSummary(BaseModel):
    id: str
    name: str
    slug: str


@router.get("/accessible", response_model=list[TenantSummary])
async def list_accessible_tenants(
    user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
):
    """Powers the frontend Tenant Switcher dropdown."""
    ids = {user.tenant_id, *user.additional_tenant_ids}
    tenants = []
    for tid in ids:
        tenant = await repo.get_by_id(tid)
        if tenant:
            tenants.append(TenantSummary(id=tenant.id, name=tenant.name, slug=tenant.slug))
    return tenants


@router.get("/current", response_model=TenantSummary)
async def get_current_tenant(
    ctx: Annotated[AuthContext, Depends(get_auth_context)],
    repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
):
    tenant = await repo.get_by_id(ctx.tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return TenantSummary(id=tenant.id, name=tenant.name, slug=tenant.slug)
