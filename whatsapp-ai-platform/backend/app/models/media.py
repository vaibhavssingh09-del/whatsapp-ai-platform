from enum import Enum
from typing import Optional

from pydantic import BaseModel

from app.models.common import TimestampedModel


class MediaKind(str, Enum):
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"


class MediaAsset(TimestampedModel):
    tenant_id: str
    kind: MediaKind
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    wa_media_id: Optional[str] = None  # set once uploaded to Meta's media endpoint
    caption: Optional[str] = None
    uploaded_by_user_id: Optional[str] = None


class MediaAssetPublic(BaseModel):
    id: str
    kind: MediaKind
    filename: str
    content_type: str
    size_bytes: int
    caption: Optional[str] = None
    url: str
