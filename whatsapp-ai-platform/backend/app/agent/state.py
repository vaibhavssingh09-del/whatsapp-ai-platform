"""
LangGraph state schema.

Design decision: this is a TypedDict, not a Pydantic model, because
LangGraph's StateGraph applies reducers (e.g. `operator.add` for message
lists) to plain dict-like state on every node transition, and its built-in
reducer support is written against TypedDict/dataclass state. Wrapping it in
Pydantic would require a manual __init__ hook to translate between the two
on every node call for no real benefit here — the AgentSessionState Pydantic
model (in repositories/misc_repositories.py) is the persisted, validated
representation; this TypedDict is the transient, in-graph working copy.
"""
import operator
from typing import Annotated, Any, Optional, TypedDict


class AgentState(TypedDict, total=False):
    tenant_id: str
    conversation_id: str

    # Rolling chat history, each item like {"role": "user"|"assistant"|"tool", "content": str}
    messages: Annotated[list[dict[str, Any]], operator.add]

    # Long-term compressed memory carried across turns (set by the memory node)
    memory_summary: str

    # Output of the planner node: which tool (if any) the agent decided to call
    plan: Optional[dict[str, Any]]

    # Result of the most recent tool execution
    tool_result: Optional[dict[str, Any]]

    # Final natural-language reply to send back to the customer
    final_reply: Optional[str]

    # Planner/responder's self-reported confidence in `final_reply`, 0.0-1.0
    confidence: float

    # How many times we've retried the current turn after a tool failure
    retry_count: int

    # Set True when the graph decides a human must take over
    needs_human_handoff: bool
    handoff_reason: Optional[str]

    # Set if a node raised an exception, so the retry/error node can react
    error: Optional[str]
