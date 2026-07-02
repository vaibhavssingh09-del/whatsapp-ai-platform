"""
Thin wrapper around Meta's WhatsApp Cloud API.

Design decision: this service takes credentials (phone_number_id, access_token)
as constructor arguments rather than reading them from global settings. Since
this is a multi-tenant platform, each tenant has its own WhatsApp Business
number and token — the caller (WebhookService / BroadcastService) is
responsible for loading the right Tenant document and constructing a
per-request WhatsAppService instance with that tenant's credentials.

httpx.AsyncClient is used with a short-lived `async with` per call rather than
a shared client, trading a small amount of connection-reuse efficiency for
simplicity and to avoid a client outliving the tenant's token being rotated
mid-process.
"""
from typing import Any, Optional

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class WhatsAppAPIError(Exception):
    def __init__(self, message: str, response_body: Optional[dict] = None):
        super().__init__(message)
        self.response_body = response_body


class WhatsAppService:
    def __init__(self, phone_number_id: str, access_token: str):
        settings = get_settings()
        self._base_url = f"{settings.WHATSAPP_GRAPH_BASE_URL}/{settings.WHATSAPP_API_VERSION}"
        self._phone_number_id = phone_number_id
        self._access_token = access_token

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._access_token}", "Content-Type": "application/json"}
    async def _post(self, path: str, payload: dict) -> dict:
        url = f"{self._base_url}/{path}"
        print("PAYLOAD:", payload)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url,
                json=payload,
                headers=self._headers,
            )

        if resp.status_code >= 400:
            print("\n========== META RESPONSE ==========")
            print("URL:", url)
            print("Status:", resp.status_code)
            print("Payload:", payload)
            print("Response:", resp.text)
            print("===================================\n")

            raise WhatsAppAPIError(
                f"WhatsApp API error {resp.status_code}",
                response_body=resp.json() if resp.text else None,
            )

        return resp.json()

    async def send_text_message(self, to: str, body: str) -> dict:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body, "preview_url": False},
        }
        return await self._post(f"{self._phone_number_id}/messages", payload)

    async def send_image_message(self, to: str, wa_media_id: str, caption: Optional[str] = None) -> dict:
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "image",
            "image": {"id": wa_media_id, **({"caption": caption} if caption else {})},
        }
        return await self._post(f"{self._phone_number_id}/messages", payload)

    async def send_document_message(self, to: str, wa_media_id: str, filename: str, caption: Optional[str] = None) -> dict:
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "document",
            "document": {"id": wa_media_id, "filename": filename, **({"caption": caption} if caption else {})},
        }
        return await self._post(f"{self._phone_number_id}/messages", payload)

    async def send_template_message(self, to: str, template_name: str, language: str, variables: dict[str, str]) -> dict:
        components = []
        if variables:
            components.append({
                "type": "body",
                "parameters": [{"type": "text", "text": v} for v in variables.values()],
            })
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {"name": template_name, "language": {"code": language}, "components": components},
        }
        return await self._post(f"{self._phone_number_id}/messages", payload)

    async def mark_as_read(self, wa_message_id: str) -> dict:
        """Sends a blue-tick read receipt back to the customer for an inbound message."""
        payload = {"messaging_product": "whatsapp", "status": "read", "message_id": wa_message_id}
        return await self._post(f"{self._phone_number_id}/messages", payload)

    async def send_typing_indicator(self, wa_message_id: str) -> dict:
        """
        Meta's Cloud API exposes the typing indicator as a status update tied
        to the inbound message being replied to (available on API v20.0+).
        """
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": wa_message_id,
            "typing_indicator": {"type": "text"},
        }
        return await self._post(f"{self._phone_number_id}/messages", payload)

    async def upload_media(self, file_bytes: bytes, content_type: str, filename: str) -> str:
        """Uploads a file to Meta's media endpoint and returns the wa_media_id used when sending it."""
        url = f"{self._base_url}/{self._phone_number_id}/media"
        files = {"file": (filename, file_bytes, content_type)}
        data = {"messaging_product": "whatsapp"}
        headers = {"Authorization": f"Bearer {self._access_token}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, data=data, files=files, headers=headers)
        if resp.status_code >= 400:
            raise WhatsAppAPIError(f"Media upload failed {resp.status_code}", response_body=resp.json() if resp.text else None)
        return resp.json()["id"]
