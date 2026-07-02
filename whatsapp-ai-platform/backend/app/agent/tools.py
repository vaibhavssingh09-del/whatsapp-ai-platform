"""
Tool registry for the LangGraph agent.

Design decision: tools are plain async functions registered in a dict
(`TOOL_REGISTRY`), each described by a small JSON-schema-like dict for the
planner prompt, rather than using LangChain's `@tool` decorator + bound
tool-calling model. This keeps the tool layer decoupled from any specific
LLM provider's function-calling format — the planner node below asks the
model to emit a JSON plan matching these schemas, which is provider-agnostic
and easy to unit test without hitting the OpenAI API at all.

Two tools are implemented as genuinely useful, safe defaults for a WhatsApp
business bot. Real deployments plug in tenant-specific tools (order lookup,
CRM search, calendar booking) by adding entries to this same registry —
that's the intended extension point, called out in README "Adding a Tool".
"""
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

ToolFn = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


async def get_current_datetime(args: dict[str, Any]) -> dict[str, Any]:
    """Returns the current UTC date/time. Useful for 'are you open now' style questions."""
    now = datetime.now(timezone.utc)
    return {"utc_datetime": now.isoformat(), "weekday": now.strftime("%A")}


async def search_faq(args: dict[str, Any]) -> dict[str, Any]:
    """
    A tiny in-memory FAQ lookup, standing in for a real knowledge base /
    vector search in production (README notes swapping this for a pgvector
    or Atlas Vector Search-backed retriever as a drop-in replacement — the
    node calling this tool doesn't care how the answer was retrieved).
    """
    query = args.get("query", "").lower()
    faqs = {
        "hours": "We're open Monday-Saturday, 9am-6pm.",
        "returns": "Items can be returned within 14 days with a receipt.",
        "shipping": "Standard shipping takes 3-5 business days.",
        "pricing": "Pricing varies by product; ask about a specific item and we'll check.",
    }
    for key, answer in faqs.items():
        if key in query:
            return {"found": True, "answer": answer}
    return {"found": False, "answer": None}


TOOL_REGISTRY: dict[str, ToolFn] = {
    "get_current_datetime": get_current_datetime,
    "search_faq": search_faq,
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "get_current_datetime",
        "description": "Get the current UTC date and time, e.g. to answer 'are you open right now'.",
        "parameters": {},
    },
    {
        "name": "search_faq",
        "description": "Search the business FAQ knowledge base for an answer (hours, returns, shipping, pricing).",
        "parameters": {"query": "string - the customer's question, in their own words"},
    },
]


async def execute_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name not in TOOL_REGISTRY:
        return {"error": f"Unknown tool '{name}'"}
    try:
        return await TOOL_REGISTRY[name](args)
    except Exception as exc:  # noqa: BLE001 - tool failures are data, not crashes
        return {"error": str(exc)}
