from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.api.deps import AuthContext, get_audit_repository, get_auth_context, get_current_user, get_user_repository
from app.core.security import create_access_token
from app.models.tenant import User, UserPublic
from app.repositories.misc_repositories import AuditLogRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService
from app.services.auth_service import AuthError, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_repository)],
):
    auth_service = AuthService(user_repo)
    try:
        user, access_token, refresh_token = await auth_service.authenticate(payload.email, payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    await AuditService(audit_repo).record(
        tenant_id=user.tenant_id,
        actor_label=f"user:{user.email}",
        actor_user_id=user.id,
        action="auth.login",
        resource_type="user",
        resource_id=user.id,
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserPublic(**user.model_dump()),
    )


@router.get("/me", response_model=UserPublic)
async def read_current_user(user: Annotated[User, Depends(get_current_user)]):
    return UserPublic(**user.model_dump())


class SwitchTenantRequest(BaseModel):
    tenant_id: str


class SwitchTenantResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/switch-tenant", response_model=SwitchTenantResponse)
async def switch_tenant(
    payload: SwitchTenantRequest,
    ctx: Annotated[AuthContext, Depends(get_auth_context)],
    user: Annotated[User, Depends(get_current_user)],
):
    """
    Re-issues an access token scoped to a different tenant the user has
    access to. This, not a client-side dropdown alone, is what makes the
    Tenant Switcher secure: every subsequent API call is authorized against
    the *new* tenant_id embedded in the freshly signed token, so a user can
    never simply claim a different tenant_id without the backend having
    verified `additional_tenant_ids` first.
    """
    allowed_tenant_ids = {user.tenant_id, *user.additional_tenant_ids}
    if payload.tenant_id not in allowed_tenant_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to that tenant")

    new_token = create_access_token(subject=user.id, tenant_id=payload.tenant_id, role=user.role.value, token_type="access")
    return SwitchTenantResponse(access_token=new_token)
