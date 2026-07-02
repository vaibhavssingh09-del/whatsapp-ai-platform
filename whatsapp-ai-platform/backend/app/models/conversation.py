from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.models.common import TimestampedModel, utcnow


class ConversationStatus(str, Enum):
    BOT_ACTIVE = "bot_active"          # LangGraph agent is handling it
    HUMAN_HANDOFF = "human_handoff"    # escalated to a human agent
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class Conversation(TimestampedModel):
    tenant_id: str
    wa_contact_id: str = Field(description="The customer's WhatsApp phone number (E.164, no '+')")
    contact_name: Optional[str] = None
    status: ConversationStatus = ConversationStatus.BOT_ACTIVE
    assigned_agent_id: Optional[str] = None
    last_message_at: Optional[str] = None
    last_message_preview: Optional[str] = None
    unread_count: int = 0
    tags: list[str] = Field(default_factory=list)


class MessageDirection(str, Enum):
    INBOUND = "inbound"    # customer -> platform
    OUTBOUND = "outbound"  # platform -> customer


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    TEMPLATE = "template"
    SYSTEM = "system"


class MessageStatus(str, Enum):
    """WhatsApp delivery lifecycle, mirrors Meta's status webhook values."""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class Message(TimestampedModel):
    tenant_id: str
    conversation_id: str
    wa_message_id: Optional[str] = None
    direction: MessageDirection
    message_type: MessageType = MessageType.TEXT
    text: Optional[str] = None
    media_asset_id: Optional[str] = None
    status: Optional[MessageStatus] = None
    sent_by_agent_id: Optional[str] = None   # set if a human sent it
    sent_by_bot: bool = False
    agent_confidence: Optional[float] = None  # LangGraph confidence score, if bot-generated


class MessageCreate(BaseModel):
    conversation_id: str
    text: Optional[str] = None
    message_type: MessageType = MessageType.TEXT
    media_asset_id: Optional[str] = None
