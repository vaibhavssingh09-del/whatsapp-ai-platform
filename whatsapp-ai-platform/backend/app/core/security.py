"""
Security primitives: password hashing and JWT issuance/verification.

Design decision: JWTs carry `tenant_id` and `role` as claims, not just `sub`
(user id). Multi-tenancy is enforced at the data layer (every Mongo query is
scoped by tenant_id extracted from the verified token), not just at the UI
layer. This means a stolen/forged token cannot be used to read another
tenant's data without also forging a valid signature.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    tenant_id: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
    token_type: str = "access",
) -> str:
    settings = get_settings()
    expire_minutes = (
        settings.ACCESS_TOKEN_EXPIRE_MINUTES
        if token_type == "access"
        else settings.REFRESH_TOKEN_EXPIRE_MINUTES
    )
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=expire_minutes))
    payload: dict[str, Any] = {
        "sub": subject,
        "tenant_id": tenant_id,
        "role": role,
        "type": token_type,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
