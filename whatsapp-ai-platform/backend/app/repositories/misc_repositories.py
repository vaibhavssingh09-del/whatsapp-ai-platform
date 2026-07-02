"""
Smaller repositories grouped in one file since each is a thin wrapper over
BaseRepository with only one or two bespoke query methods. Splitting these
into five separate one-liner files would add navigation overhead without
adding clarity; if any of these grow bespoke query logic, split them out.
"""
from typing import Any, Optional

from pydantic import BaseModel

from app.models.audit import AuditLog
from app.models.broadcast import Broadcast
from app.models.media import MediaAsset
from app.repositories.base import BaseRepository, serialize_doc


class MediaRepository(BaseRepository[MediaAsset]):
    collection_name = "media_assets"
    model = MediaAsset


class BroadcastRepository(BaseRepository[Broadcast]):
    collection_name = "broadcasts"
    model = Broadcast

    async def append_result(self, tenant_id: str, broadcast_id: str, result: dict, success: bool) -> None:
        from app.repositories.base import to_object_id

        inc_field = "sent_count" if success else "failed_count"
        await self.collection.update_one(
            {"_id": to_object_id(broadcast_id), "tenant_id": tenant_id},
            {"$push": {"results": result}, "$inc": {inc_field: 1}},
        )


class AuditLogRepository(BaseRepository[AuditLog]):
    collection_name = "audit_logs"
    model = AuditLog

    async def list_recent(self, tenant_id: str, limit: int = 100) -> list[AuditLog]:
        return await self.find_many(tenant_id, limit=limit, sort=[("created_at", -1)])


class AgentSessionState(BaseModel):
    """
    Persisted LangGraph state for one conversation. This is what makes the
    agent's memory survive process restarts / multiple backend replicas —
    the graph is re-hydrated from this document at the start of every turn
    rather than kept in an in-memory dict (which would break the moment you
    run more than one uvicorn worker).
    """
    id: Optional[str] = None
    tenant_id: str
    conversation_id: str
    messages: list[dict[str, Any]] = []          # rolling chat history (role/content)
    memory_summary: str = ""                      # long-term compressed memory
    last_confidence: Optional[float] = None
    retry_count: int = 0
    handed_off: bool = False


class AgentSessionRepository(BaseRepository[AgentSessionState]):
    collection_name = "agent_sessions"
    model = AgentSessionState

    async def get_by_conversation(self, tenant_id: str, conversation_id: str) -> Optional[AgentSessionState]:
        doc = await self.collection.find_one({"tenant_id": tenant_id, "conversation_id": conversation_id})
        return AgentSessionState(**serialize_doc(doc)) if doc else None

    async def upsert(self, state: AgentSessionState) -> AgentSessionState:
        from app.models.common import utcnow

        payload = state.model_dump(exclude={"id"})
        payload["updated_at"] = utcnow()
        result = await self.collection.update_one(
            {"tenant_id": state.tenant_id, "conversation_id": state.conversation_id},
            {"$set": payload, "$setOnInsert": {"created_at": utcnow()}},
            upsert=True,
        )
        if result.upserted_id:
            state.id = str(result.upserted_id)
        return state
