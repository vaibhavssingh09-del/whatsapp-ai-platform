"""
Media library service.

Design decision: media files are stored on local disk (MEDIA_STORAGE_DIR) in
this reference implementation, addressed by a UUID filename, with metadata in
Mongo. For a real production deployment on Render (ephemeral filesystem),
swap `_save_to_disk`/`_read_from_disk` for an S3-compatible object store —
the rest of the service (Mongo metadata, Meta upload flow) is unaffected
because storage access is isolated to these two private methods. This is
called out explicitly in the README deployment section.
"""
import os
import uuid
from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.models.media import MediaAsset, MediaKind
from app.repositories.misc_repositories import MediaRepository
from app.services.whatsapp_service import WhatsAppService


def _kind_from_content_type(content_type: str) -> MediaKind:
    if content_type.startswith("image/"):
        return MediaKind.IMAGE
    if content_type.startswith("audio/"):
        return MediaKind.AUDIO
    if content_type.startswith("video/"):
        return MediaKind.VIDEO
    return MediaKind.DOCUMENT


class MediaService:
    def __init__(self, media_repo: MediaRepository):
        self._repo = media_repo
        self._storage_dir = Path(get_settings().MEDIA_STORAGE_DIR)
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def _save_to_disk(self, file_bytes: bytes, extension: str) -> str:
        unique_name = f"{uuid.uuid4().hex}{extension}"
        path = self._storage_dir / unique_name
        path.write_bytes(file_bytes)
        return str(path)

    def _read_from_disk(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()

    async def upload_asset(
        self,
        tenant_id: str,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        caption: Optional[str] = None,
        uploaded_by_user_id: Optional[str] = None,
    ) -> MediaAsset:
        extension = Path(filename).suffix or ""
        storage_path = self._save_to_disk(file_bytes, extension)
        asset = MediaAsset(
            tenant_id=tenant_id,
            kind=_kind_from_content_type(content_type),
            filename=filename,
            content_type=content_type,
            size_bytes=len(file_bytes),
            storage_path=storage_path,
            caption=caption,
            uploaded_by_user_id=uploaded_by_user_id,
        )
        return await self._repo.create(asset)

    async def get_asset(self, tenant_id: str, asset_id: str) -> Optional[MediaAsset]:
        return await self._repo.get_by_id(tenant_id, asset_id)

    async def list_assets(self, tenant_id: str, limit: int = 50, skip: int = 0) -> list[MediaAsset]:
        return await self._repo.find_many(tenant_id, limit=limit, skip=skip, sort=[("created_at", -1)])

    def read_bytes(self, asset: MediaAsset) -> bytes:
        return self._read_from_disk(asset.storage_path)

    async def ensure_uploaded_to_whatsapp(self, tenant_id: str, asset: MediaAsset, wa_service: WhatsAppService) -> str:
        """
        Media must be uploaded to Meta's media endpoint before it can be sent
        in a WhatsApp message (Meta returns an opaque media id, distinct from
        our own asset id). We cache that id on the asset the first time so
        repeated sends of the same image don't re-upload it to Meta.
        """
        if asset.wa_media_id:
            return asset.wa_media_id
        file_bytes = self._read_from_disk(asset.storage_path)
        wa_media_id = await wa_service.upload_media(file_bytes, asset.content_type, asset.filename)
        await self._repo.update(tenant_id, asset.id, {"wa_media_id": wa_media_id})
        return wa_media_id
