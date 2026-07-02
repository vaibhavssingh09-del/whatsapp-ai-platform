"""
Thin OpenAI client wrapper used by every agent node.

Design decision: a single `complete_json` helper that asks the model to
return strict JSON and parses it, used by both the planner and responder
nodes. Centralizing this means json-parsing/retry-on-malformed-output logic
exists in exactly one place instead of being duplicated (and drifting) across
nodes.
"""
import json
from typing import Any, Optional

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=get_settings().OPENAI_API_KEY)
    return _client


async def complete_json(system_prompt: str, user_content: str, temperature: float = 0.2) -> dict[str, Any]:
    """
    Calls the model with response_format=json_object and parses the result.
    If the model somehow returns invalid JSON (rare with json_object mode,
    but not impossible), we return a well-formed error dict rather than
    raising, so the calling graph node can route to the retry/error path
    instead of crashing the whole request.
    """
    settings = get_settings()
    client = get_openai_client()
    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("llm_json_parse_error", error=str(exc), raw=raw)
        return {"error": "malformed_json_response"}
    except Exception as exc:  # noqa: BLE001
        logger.error("llm_call_failed", error=str(exc))
        return {"error": str(exc)}


async def complete_text(system_prompt: str, messages: list[dict[str, str]], temperature: float = 0.4) -> str:
    settings = get_settings()
    client = get_openai_client()
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=temperature,
        messages=[{"role": "system", "content": system_prompt}, *messages],
    )
    return response.choices[0].message.content or ""
