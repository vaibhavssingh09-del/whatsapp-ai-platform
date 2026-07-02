"""
Handles Meta webhook signature verification and payload normalization.

Design decision: signature verification (`verify_signature`) is a pure
function taking the raw request body bytes + the tenant-independent app
secret, kept separate from payload parsing. Meta signs the whole raw body
with the *app* secret (not a per-tenant secret), so verification happens
once, before we even know which tenant the message is for. This ordering
matters: we must verify BEFORE trusting anything in the payload (including
which phone_number_id it claims), otherwise we'd be doing tenant lookups
against a payload that might be forged.
"""
import hashlib
import hmac
from typing import Any, Optional

from pydantic import BaseModel

from app.core.logging import get_logger

logger = get_logger(__name__)


def verify_signature(app_secret: str, raw_body: bytes, signature_header: Optional[str]) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)


class InboundMessage(BaseModel):
    wa_message_id: str
    from_number: str
    contact_name: Optional[str] = None
    message_type: str  # text | image | document | audio
    text: Optional[str] = None
    media_id: Optional[str] = None
    media_mime_type: Optional[str] = None
    phone_number_id: str  # identifies which tenant this belongs to


class StatusUpdate(BaseModel):
    wa_message_id: str
    status: str  # sent | delivered | read | failed
    phone_number_id: str


class ParsedWebhookPayload(BaseModel):
    messages: list[InboundMessage] = []
    statuses: list[StatusUpdate] = []


def parse_webhook_payload(body: dict[str, Any]) -> ParsedWebhookPayload:
    """
    Meta's webhook payload is deeply nested and can contain zero-or-more
    changes per entry, each with zero-or-more messages AND/OR statuses. We
    flatten all of it into simple lists so the rest of the app never has to
    know about the entry/changes/value nesting.
    """
    result = ParsedWebhookPayload()
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = value.get("metadata", {}).get("phone_number_id", "")
            contacts = {c["wa_id"]: c.get("profile", {}).get("name") for c in value.get("contacts", [])}

            for msg in value.get("messages", []):
                msg_type = msg.get("type")
                inbound = InboundMessage(
                    wa_message_id=msg["id"],
                    from_number=msg["from"],
                    contact_name=contacts.get(msg["from"]),
                    message_type=msg_type,
                    phone_number_id=phone_number_id,
                )
                if msg_type == "text":
                    inbound.text = msg.get("text", {}).get("body")
                elif msg_type in ("image", "document", "audio"):
                    media_obj = msg.get(msg_type, {})
                    inbound.media_id = media_obj.get("id")
                    inbound.media_mime_type = media_obj.get("mime_type")
                    inbound.text = media_obj.get("caption")
                result.messages.append(inbound)

            for status in value.get("statuses", []):
                result.statuses.append(
                    StatusUpdate(
                        wa_message_id=status["id"],
                        status=status["status"],
                        phone_number_id=phone_number_id,
                    )
                )

    return result
