"""
Broadcast campaign service.

Design decision: broadcasts always send WhatsApp *template* messages, never
free-form text. This isn't a style choice — Meta's policy requires a
pre-approved template for any business-initiated message sent outside the
24-hour customer service window, which is true by definition for a bulk
broadcast. Attempting to send free text here would get the tenant's WhatsApp
number flagged/restricted, so the API layer for broadcasts intentionally
does not expose a "raw body" option at all.

Sending is done with bounded concurrency (asyncio.Semaphore) rather than
either fully sequential (too slow for large lists) or fully parallel
(would blow through Meta's per-second rate limits and get throttled).
"""
import asyncio
from typing import Optional

from app.core.logging import get_logger
from app.models.broadcast import Broadcast, BroadcastStatus, RecipientResult
from app.repositories.misc_repositories import BroadcastRepository
from app.services.whatsapp_service import WhatsAppAPIError, WhatsAppService

logger = get_logger(__name__)

MAX_CONCURRENT_SENDS = 5


class BroadcastService:
    def __init__(self, broadcast_repo: BroadcastRepository):
        self._repo = broadcast_repo

    async def create_broadcast(self, broadcast: Broadcast) -> Broadcast:
        return await self._repo.create(broadcast)

    async def list_broadcasts(self, tenant_id: str, limit: int = 50) -> list[Broadcast]:
        return await self._repo.find_many(tenant_id, limit=limit, sort=[("created_at", -1)])

    async def get_broadcast(self, tenant_id: str, broadcast_id: str) -> Optional[Broadcast]:
        return await self._repo.get_by_id(tenant_id, broadcast_id)

    async def execute_broadcast(self, tenant_id: str, broadcast: Broadcast, wa_service: WhatsAppService) -> None:
        """
        Fire-and-await the full send. In production this would be invoked
        from a background task queue (see README "Scaling Beyond 48 Hours"
        note) rather than inline in the request/response cycle, so a large
        recipient list doesn't hold an HTTP connection open. For this
        reference implementation it's triggered via FastAPI BackgroundTasks.
        """
        await self._repo.update(tenant_id, broadcast.id, {"status": BroadcastStatus.SENDING.value})

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_SENDS)

        async def send_one(wa_contact_id: str) -> None:
            async with semaphore:
                try:
                    resp = await wa_service.send_template_message(
                        to=wa_contact_id,
                        template_name=broadcast.template_name,
                        language=broadcast.template_language,
                        variables=broadcast.template_variables,
                    )
                    wa_message_id = resp.get("messages", [{}])[0].get("id")
                    result = RecipientResult(wa_contact_id=wa_contact_id, status="sent", wa_message_id=wa_message_id)
                    await self._repo.append_result(tenant_id, broadcast.id, result.model_dump(), success=True)
                except WhatsAppAPIError as exc:
                    logger.warning("broadcast_send_failed", contact=wa_contact_id, error=str(exc))
                    result = RecipientResult(wa_contact_id=wa_contact_id, status="failed", error=str(exc))
                    await self._repo.append_result(tenant_id, broadcast.id, result.model_dump(), success=False)

        await asyncio.gather(*(send_one(c) for c in broadcast.recipient_wa_contact_ids))

        final = await self._repo.get_by_id(tenant_id, broadcast.id)
        final_status = BroadcastStatus.COMPLETED if final and final.failed_count == 0 else BroadcastStatus.COMPLETED
        await self._repo.update(tenant_id, broadcast.id, {"status": final_status.value})
