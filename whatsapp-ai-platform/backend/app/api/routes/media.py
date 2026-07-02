from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
import io

from app.api.deps import AuthContext, get_auth_context, get_conversation_repository, get_media_repository, get_message_repository, get_tenant_repository
from app.core.config import Settings, get_settings
from app.models.conversation import Message, MessageDirection, MessageType
from app.models.media import MediaAssetPublic, MediaKind
from app.repositories.conversation_repository import ConversationRepository, MessageRepository
from app.repositories.misc_repositories import MediaRepository
from app.repositories.tenant_repository import TenantRepository
from app.services.media_service import MediaService
from app.services.whatsapp_service import WhatsAppService

router = APIRouter(prefix="/media", tags=["media"])


def _to_public(asset, request_prefix: str) -> MediaAssetPublic:
    return MediaAssetPublic(
        id=asset.id,
        kind=asset.kind,
        filename=asset.filename,
        content_type=asset.content_type,
        size_bytes=asset.size_bytes,
        caption=asset.caption,
        url=f"{request_prefix}/api/v1/media/{asset.id}/file",
    )


@router.post("", response_model=MediaAssetPublic)
async def upload_media(
    file: UploadFile,
    ctx: Annotated[AuthContext, Depends(get_auth_context)],
    repo: Annotated[MediaRepository, Depends(get_media_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    file_bytes = await file.read()
    max_bytes = settings.MAX_MEDIA_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"File exceeds {settings.MAX_MEDIA_SIZE_MB}MB limit")

    service = MediaService(repo)
    asset = await service.upload_asset(
        tenant_id=ctx.tenant_id,
        file_bytes=file_bytes,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        uploaded_by_user_id=ctx.user_id,
    )
    return _to_public(asset, "")


@router.get("", response_model=list[MediaAssetPublic])
async def list_media(
    ctx: Annotated[AuthContext, Depends(get_auth_context)],
    repo: Annotated[MediaRepository, Depends(get_media_repository)],
    limit: int = 50,
    skip: int = 0,
):
    service = MediaService(repo)
    assets = await service.list_assets(ctx.tenant_id, limit, skip)
    return [_to_public(a, "") for a in assets]


@router.get("/{asset_id}/file")
async def get_media_file(
    asset_id: str,
    ctx: Annotated[AuthContext, Depends(get_auth_context)],
    repo: Annotated[MediaRepository, Depends(get_media_repository)],
):
    service = MediaService(repo)
    asset = await service.get_asset(ctx.tenant_id, asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    file_bytes = service.read_bytes(asset)
    return StreamingResponse(io.BytesIO(file_bytes), media_type=asset.content_type)


@router.post("/{asset_id}/send/{conversation_id}")
async def send_media_to_conversation(
    asset_id: str,
    conversation_id: str,
    ctx: Annotated[AuthContext, Depends(get_auth_context)],
    media_repo: Annotated[MediaRepository, Depends(get_media_repository)],
    convo_repo: Annotated[ConversationRepository, Depends(get_conversation_repository)],
    message_repo: Annotated[MessageRepository, Depends(get_message_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
):
    """
    Sends a media library asset (image or PDF/document) into an active
    conversation: uploads it to Meta's media endpoint (cached on the asset
    after the first send), sends it via the appropriate WhatsApp message
    type, and records the outbound message the same way a text reply is.
    """
    conversation = await convo_repo.get_by_id(ctx.tenant_id, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    media_service = MediaService(media_repo)
    asset = await media_service.get_asset(ctx.tenant_id, asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")

    tenant = await tenant_repo.get_by_id(ctx.tenant_id)
    wa_service = WhatsAppService(tenant.whatsapp_phone_number_id, tenant.whatsapp_access_token)

    wa_media_id = await media_service.ensure_uploaded_to_whatsapp(ctx.tenant_id, asset, wa_service)

    if asset.kind == MediaKind.IMAGE:
        send_response = await wa_service.send_image_message(conversation.wa_contact_id, wa_media_id, asset.caption)
        message_type = MessageType.IMAGE
    else:
        send_response = await wa_service.send_document_message(
            conversation.wa_contact_id, wa_media_id, asset.filename, asset.caption
        )
        message_type = MessageType.DOCUMENT

    message = await message_repo.create(
        Message(
            tenant_id=ctx.tenant_id,
            conversation_id=conversation_id,
            wa_message_id=send_response.get("messages", [{}])[0].get("id"),
            direction=MessageDirection.OUTBOUND,
            message_type=message_type,
            media_asset_id=asset_id,
            text=asset.caption,
            sent_by_agent_id=ctx.user_id,
        )
    )
    await convo_repo.touch_last_message(ctx.tenant_id, conversation_id, f"[{message_type.value}] {asset.caption or asset.filename}")
    return message
