"""
Meta WhatsApp webhook endpoints.

Design decision: this is the one router in the app that deliberately has NO
JWT auth dependency — Meta calls it directly, unauthenticated by our own
scheme. Trust is instead established via `verify_signature` (HMAC over the
raw body using the Meta app secret) on every POST, and via the `hub.verify_token`
challenge-response on the one-time GET verification Meta performs when the
webhook URL is first configured. Skipping signature verification here would
let anyone forge inbound WhatsApp messages against arbitrary tenants.
"""
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response, status

from app.agent.runner import AgentRunner
from app.api.deps import (
    get_agent_session_repository,
    get_audit_repository,
    get_conversation_repository,
    get_db,
    get_message_repository,
    get_tenant_repository,
)
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.conversation import Message, MessageDirection, MessageStatus, MessageType
from app.repositories.conversation_repository import ConversationRepository, MessageRepository
from app.repositories.misc_repositories import AgentSessionRepository, AuditLogRepository
from app.repositories.tenant_repository import TenantRepository
from app.services.audit_service import AuditService
from app.services.webhook_service import parse_webhook_payload, verify_signature
from app.services.whatsapp_service import WhatsAppService

logger = get_logger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.get("/whatsapp")
async def verify_webhook(
    settings: Annotated[Settings, Depends(get_settings)],
    hub_mode: Annotated[str, Query(alias="hub.mode")] = "",
    hub_verify_token: Annotated[str, Query(alias="hub.verify_token")] = "",
    hub_challenge: Annotated[str, Query(alias="hub.challenge")] = "",
):
    """
    One-time handshake Meta performs when you save the webhook URL in the
    App Dashboard. Must echo back `hub.challenge` as plain text if the mode
    and token match what's configured, or Meta refuses to save the webhook.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification token mismatch")


async def _process_inbound_message(
    tenant_id: str,
    wa_access_token: str,
    wa_phone_number_id: str,
    conversation_repo: ConversationRepository,
    message_repo: MessageRepository,
    session_repo: AgentSessionRepository,
    audit_repo: AuditLogRepository,
    inbound,
) -> None:
    """
    Runs in a BackgroundTask so the webhook responds to Meta within its
    ~10s timeout even while the LLM call / reply send are in flight — Meta
    will retry the webhook delivery (causing duplicate processing) if we
    don't return 200 quickly.
    """
    wa_service = WhatsAppService(phone_number_id=wa_phone_number_id, access_token=wa_access_token)

    try:
        await wa_service.mark_as_read(inbound.wa_message_id)
        await wa_service.send_typing_indicator(inbound.wa_message_id)
    except Exception:  # noqa: BLE001
        logger.warning("read_receipt_or_typing_failed", wa_message_id=inbound.wa_message_id)

    conversation = await conversation_repo.get_or_create(tenant_id, inbound.from_number, inbound.contact_name)

    inbound_text = inbound.text or f"[{inbound.message_type} message received]"
    await message_repo.create(
        Message(
            tenant_id=tenant_id,
            conversation_id=conversation.id,
            wa_message_id=inbound.wa_message_id,
            direction=MessageDirection.INBOUND,
            message_type=MessageType(inbound.message_type) if inbound.message_type in MessageType._value2member_map_ else MessageType.TEXT,
            text=inbound_text,
        )
    )
    await conversation_repo.touch_last_message(tenant_id, conversation.id, inbound_text)

    if conversation.status.value == "human_handoff":
        # A human is already handling this thread; the agent stays silent so
        # it doesn't talk over the human agent.
        return

    runner = AgentRunner(session_repo)
    result = await runner.run_turn(tenant_id, conversation.id, inbound_text)

    send_response = await wa_service.send_text_message(inbound.from_number, result.reply)
    await message_repo.create(
        Message(
            tenant_id=tenant_id,
            conversation_id=conversation.id,
            wa_message_id=send_response.get("messages", [{}])[0].get("id"),
            direction=MessageDirection.OUTBOUND,
            message_type=MessageType.TEXT,
            text=result.reply,
            status=MessageStatus.SENT,
            sent_by_bot=True,
            agent_confidence=result.confidence,
        )
    )
    await conversation_repo.touch_last_message(tenant_id, conversation.id, result.reply)

    if result.needs_human_handoff:
        await conversation_repo.update(tenant_id, conversation.id, {"status": "human_handoff"})
        await AuditService(audit_repo).record(
            tenant_id=tenant_id,
            actor_label="system:langgraph_agent",
            action="conversation.handoff",
            resource_type="conversation",
            resource_id=conversation.id,
            metadata={"reason": result.handoff_reason, "confidence": result.confidence},
        )


@router.post("/whatsapp")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    settings: Annotated[Settings, Depends(get_settings)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    conversation_repo: Annotated[ConversationRepository, Depends(get_conversation_repository)],
    message_repo: Annotated[MessageRepository, Depends(get_message_repository)],
    session_repo: Annotated[AgentSessionRepository, Depends(get_agent_session_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_repository)],
):
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if settings.META_APP_SECRET and not verify_signature(settings.META_APP_SECRET, raw_body, signature):
        logger.warning("webhook_signature_invalid")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")

    body = await request.json()
    parsed = parse_webhook_payload(body)

    # Resolve tenant per-message since a single payload could (rarely) span
    # numbers if Meta batches entries; in practice it's almost always one.
    for status_update in parsed.statuses:
        tenant = await tenant_repo.get_by_phone_number_id(status_update.phone_number_id)
        if tenant:
            await message_repo.update_status_by_wa_message_id(tenant.id, status_update.wa_message_id, status_update.status)

    for inbound in parsed.messages:
        tenant = await tenant_repo.get_by_phone_number_id(inbound.phone_number_id)
        if not tenant:
            logger.warning("webhook_unknown_phone_number_id", phone_number_id=inbound.phone_number_id)
            continue
        background_tasks.add_task(
            _process_inbound_message,
            tenant.id,
            tenant.whatsapp_access_token,
            tenant.whatsapp_phone_number_id,
            conversation_repo,
            message_repo,
            session_repo,
            audit_repo,
            inbound,
        )

    # Always 200 quickly regardless of downstream outcome, per Meta's webhook contract.
    return {"status": "received"}
