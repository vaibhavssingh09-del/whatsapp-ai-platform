"""
FastAPI dependency-injection wiring.

Design decision: repositories and services are constructed per-request via
`Depends(...)` chains rather than as global singletons. They're cheap to
construct (just wrapping a shared Motor database handle), and per-request
construction makes unit testing trivial — tests override `get_database` with
a test DB and every downstream dependency picks it up automatically, with
zero test-only branching inside the services themselves.
"""
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.security import decode_token
from app.models.tenant import User, UserRole
from app.repositories.conversation_repository import ConversationRepository, MessageRepository
from app.repositories.misc_repositories import AgentSessionRepository, AuditLogRepository, BroadcastRepository, MediaRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository


def get_db() -> AsyncIOMotorDatabase:
    return get_database()


class AuthContext:
    """Everything a request handler needs about who is calling, resolved once from the JWT."""

    def __init__(self, user_id: str, tenant_id: str, role: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role


async def get_auth_context(authorization: Annotated[str | None, Header()] = None) -> AuthContext:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or malformed Authorization header")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token used where access token required")
    return AuthContext(user_id=payload["sub"], tenant_id=payload["tenant_id"], role=payload["role"])


def require_roles(*allowed_roles: UserRole):
    """
    Returns a FastAPI dependency that enforces the caller's role is one of
    `allowed_roles`. Used to gate destructive/admin-only endpoints (e.g. only
    OWNER/ADMIN can send broadcasts) while keeping read endpoints open to AGENT.
    """

    async def _check(ctx: Annotated[AuthContext, Depends(get_auth_context)]) -> AuthContext:
        if ctx.role not in {r.value for r in allowed_roles}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return ctx

    return _check


# --- Repository providers ---

def get_tenant_repository(db: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> TenantRepository:
    return TenantRepository(db)


def get_user_repository(db: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> UserRepository:
    return UserRepository(db)


def get_conversation_repository(db: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> ConversationRepository:
    return ConversationRepository(db)


def get_message_repository(db: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> MessageRepository:
    return MessageRepository(db)


def get_media_repository(db: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> MediaRepository:
    return MediaRepository(db)


def get_broadcast_repository(db: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> BroadcastRepository:
    return BroadcastRepository(db)


def get_audit_repository(db: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> AuditLogRepository:
    return AuditLogRepository(db)


def get_agent_session_repository(db: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> AgentSessionRepository:
    return AgentSessionRepository(db)


async def get_current_user(
    ctx: Annotated[AuthContext, Depends(get_auth_context)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    user = await user_repo.get_by_id(ctx.tenant_id, ctx.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user
