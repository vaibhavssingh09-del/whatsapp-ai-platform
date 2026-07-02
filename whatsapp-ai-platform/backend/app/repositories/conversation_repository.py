from typing import Optional

from app.models.common import utcnow
from app.models.conversation import Conversation, Message
from app.repositories.base import BaseRepository, serialize_doc, to_object_id


class ConversationRepository(BaseRepository[Conversation]):
    collection_name = "conversations"
    model = Conversation

    async def get_by_wa_contact(self, tenant_id: str, wa_contact_id: str) -> Optional[Conversation]:
        doc = await self.collection.find_one({"tenant_id": tenant_id, "wa_contact_id": wa_contact_id})
        return Conversation(**serialize_doc(doc)) if doc else None

    async def get_or_create(self, tenant_id: str, wa_contact_id: str, contact_name: Optional[str] = None) -> Conversation:
        existing = await self.get_by_wa_contact(tenant_id, wa_contact_id)
        if existing:
            return existing
        new_convo = Conversation(tenant_id=tenant_id, wa_contact_id=wa_contact_id, contact_name=contact_name)
        return await self.create(new_convo)

    async def touch_last_message(self, tenant_id: str, conversation_id: str, preview: str) -> None:
        await self.collection.update_one(
            {"_id": to_object_id(conversation_id), "tenant_id": tenant_id},
            {
                "$set": {
                    "last_message_at": utcnow().isoformat(),
                    "last_message_preview": preview[:120],
                    "updated_at": utcnow(),
                },
                "$inc": {"unread_count": 1},
            },
        )

    async def list_by_status(self, tenant_id: str, status: Optional[str], limit: int, skip: int) -> list[Conversation]:
        query = {"status": status} if status else {}
        return await self.find_many(tenant_id, query, limit=limit, skip=skip, sort=[("last_message_at", -1)])


class MessageRepository(BaseRepository[Message]):
    collection_name = "messages"
    model = Message

    async def list_for_conversation(self, tenant_id: str, conversation_id: str, limit: int = 100) -> list[Message]:
        return await self.find_many(
            tenant_id,
            {"conversation_id": conversation_id},
            limit=limit,
            sort=[("created_at", 1)],
        )

    async def update_status_by_wa_message_id(self, tenant_id: str, wa_message_id: str, status: str) -> bool:
        """Used to apply Meta's delivery/read-receipt webhooks to our stored messages."""
        result = await self.collection.update_one(
            {"tenant_id": tenant_id, "wa_message_id": wa_message_id},
            {"$set": {"status": status, "updated_at": utcnow()}},
        )
        return result.modified_count > 0
