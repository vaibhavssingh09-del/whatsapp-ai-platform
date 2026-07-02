"""
TenantRepository is intentionally NOT tenant-scoped (it doesn't inherit the
tenant-filtering behavior of BaseRepository) because it manages the tenants
table itself — a tenant document has no parent tenant_id to filter by.
Every other repository in this project is tenant-scoped; this is the one
deliberate exception, called out here so it doesn't look like an oversight.
"""
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.tenant import Tenant
from app.repositories.base import serialize_doc, to_object_id


class TenantRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db
        self.collection = db.tenants

    async def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        doc = await self.collection.find_one({"_id": to_object_id(tenant_id)})
        return Tenant(**serialize_doc(doc)) if doc else None

    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        doc = await self.collection.find_one({"slug": slug})
        return Tenant(**serialize_doc(doc)) if doc else None

    async def get_by_phone_number_id(self, phone_number_id: str) -> Optional[Tenant]:
        """Used by the WhatsApp webhook to resolve which tenant a message belongs to."""
        doc = await self.collection.find_one({"whatsapp_phone_number_id": phone_number_id})
        return Tenant(**serialize_doc(doc)) if doc else None

    async def list_all(self, active_only: bool = True) -> list[Tenant]:
        query = {"is_active": True} if active_only else {}
        cursor = self.collection.find(query)
        return [Tenant(**serialize_doc(doc)) async for doc in cursor]

    async def create(self, tenant: Tenant) -> Tenant:
        payload = tenant.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(payload)
        tenant.id = str(result.inserted_id)
        return tenant
