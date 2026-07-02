from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import AuthContext, get_auth_context, get_conversation_repository, get_message_repository, get_tenant_repository
from app.models.conversation import Conversation, Message, MessageDirection, MessageType
from app.repositories.conversation_repository import ConversationRepository, MessageRepository
from app.repositories.tenant_repository import TenantRepository
from app.services.whatsapp_service import WhatsAppService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[Conversation])
async def list_conversations(
    ctx: Annotated[AuthContext, Depends(get_auth_context)],
    repo: Annotated[ConversationRepository, Depends(get_conversation_repository)],
    status_filter: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
):
    return await repo.list_by_status(ctx.tenant_id, status_filter, limit, skip)


@router.get("/{conversation_id}/messages", response_model=list[Message])
async def get_conversation_messages(
    conversation_id: str,
    ctx: Annotated[AuthContext, Depends(get_auth_context)],
    repo: Annotated[MessageRepository, Depends(get_message_repository)],
):
    return await repo.list_for_conversation(ctx.tenant_id, conversation_id)


class OperatorReplyRequest(BaseModel):
    text: str


@router.post("/{conversation_id}/reply")
async def send_operator_reply(
    conversation_id: str,
    payload: OperatorReplyRequest,
    ctx: Annotated[AuthContext, Depends(get_auth_context)],
    convo_repo: Annotated[ConversationRepository, Depends(get_conversation_repository)],
    message_repo: Annotated[MessageRepository, Depends(get_message_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
):
    """
    Lets a human operator (post human-handoff) send a message directly.
    Sending here is intentionally free-text (not template-restricted like
    broadcasts) because it's always inside an active customer-initiated
    session, which Meta permits.
    """
    conversation = await convo_repo.get_by_id(ctx.tenant_id, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    tenant = await tenant_repo.get_by_id(ctx.tenant_id)
    wa_service = WhatsAppService(tenant.whatsapp_phone_number_id, tenant.whatsapp_access_token)
    send_response = await wa_service.send_text_message(conversation.wa_contact_id, payload.text)
    print("META RESPONSE:", send_response)
    message = await message_repo.create(
        Message(
            tenant_id=ctx.tenant_id,
            conversation_id=conversation_id,
            wa_message_id=send_response.get("messages", [{}])[0].get("id"),
            direction=MessageDirection.OUTBOUND,
            message_type=MessageType.TEXT,
            text=payload.text,
            sent_by_agent_id=ctx.user_id,
        )
    )
    await convo_repo.touch_last_message(ctx.tenant_id, conversation_id, payload.text)
    return message


@router.post("/{conversation_id}/resolve")
async def resolve_conversation(
    conversation_id: str,
    ctx: Annotated[AuthContext, Depends(get_auth_context)],
    repo: Annotated[ConversationRepository, Depends(get_conversation_repository)],
):
    """Hands the conversation back to the bot / marks it resolved after a human agent has helped."""
    updated = await repo.update(ctx.tenant_id, conversation_id, {"status": "resolved"})
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return {"status": "resolved"}
