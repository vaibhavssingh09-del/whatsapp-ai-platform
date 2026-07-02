from typing import Optional

from app.models.tenant import User
from app.repositories.base import BaseRepository, serialize_doc


class UserRepository(BaseRepository[User]):
    collection_name = "users"
    model = User

    async def get_by_email(self, tenant_id: str, email: str) -> Optional[User]:
        doc = await self.collection.find_one({"tenant_id": tenant_id, "email": email})
        return User(**serialize_doc(doc)) if doc else None

    async def get_by_email_any_tenant(self, email: str) -> Optional[User]:
        """
        Used only at login time, before we know which tenant the user belongs
        to. The client sends email + password (not tenant slug), so we must
        look the user up globally first, then use their stored tenant_id for
        every subsequent request via the JWT claim.
        """
        doc = await self.collection.find_one({"email": email})
        return User(**serialize_doc(doc)) if doc else None
