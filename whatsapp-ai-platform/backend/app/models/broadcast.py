from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.models.common import TimestampedModel


class BroadcastStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecipientResult(BaseModel):
    wa_contact_id: str
    status: str  # "sent" | "failed"
    error: Optional[str] = None
    wa_message_id: Optional[str] = None


class Broadcast(TimestampedModel):
    tenant_id: str
    name: str
    template_name: str = Field(description="Meta-approved WhatsApp template name")
    template_language: str = "en_US"
    template_variables: dict[str, str] = Field(default_factory=dict)
    recipient_wa_contact_ids: list[str]
    status: BroadcastStatus = BroadcastStatus.DRAFT
    scheduled_at: Optional[str] = None
    created_by_user_id: str
    results: list[RecipientResult] = Field(default_factory=list)
    sent_count: int = 0
    failed_count: int = 0


class BroadcastCreate(BaseModel):
    name: str
    template_name: str
    template_language: str = "en_US"
    template_variables: dict[str, str] = Field(default_factory=dict)
    recipient_wa_contact_ids: list[str]
    scheduled_at: Optional[str] = None
