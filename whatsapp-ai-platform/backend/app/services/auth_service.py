from typing import Optional

from app.core.security import create_access_token, verify_password
from app.models.tenant import User
from app.repositories.user_repository import UserRepository


class AuthError(Exception):
    pass


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo

    async def authenticate(self, email: str, password: str) -> tuple[User, str, str]:
        """
        Returns (user, access_token, refresh_token). Raises AuthError on any
        failure. We deliberately raise the same generic error for "no such
        user" and "wrong password" so the API response can't be used to
        enumerate registered email addresses.
        """
        user = await self._user_repo.get_by_email_any_tenant(email)
        if not user or not user.is_active:
            raise AuthError("Invalid email or password")
        if not verify_password(password, user.hashed_password):
            raise AuthError("Invalid email or password")

        access_token = create_access_token(subject=user.id, tenant_id=user.tenant_id, role=user.role.value, token_type="access")
        refresh_token = create_access_token(subject=user.id, tenant_id=user.tenant_id, role=user.role.value, token_type="refresh")
        return user, access_token, refresh_token
