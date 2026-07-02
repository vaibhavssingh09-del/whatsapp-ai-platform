"""
Bridges the stateless compiled LangGraph graph with per-conversation
persistence in MongoDB.

Design decision: LangGraph's own checkpointer interface (e.g. a Mongo/SQLite
checkpointer) would work here too, but we roll a small explicit
load-state / invoke / save-state wrapper instead. Reason: our persisted
"session" (AgentSessionState) is also read directly by the dashboard's
Conversation Monitor (to show memory_summary, confidence, retry_count) and
by human handoff logic — coupling it to LangGraph's internal checkpoint
serialization format would leak agent-library internals into the API/UI
layer. This wrapper is the single seam that keeps them independent.
"""
from dataclasses import dataclass

from app.agent.graph import AGENT_GRAPH
from app.agent.state import AgentState
from app.repositories.misc_repositories import AgentSessionRepository, AgentSessionState
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AgentTurnResult:
    reply: str
    confidence: float
    needs_human_handoff: bool
    handoff_reason: str | None


class AgentRunner:
    def __init__(self, session_repo: AgentSessionRepository):
        self._session_repo = session_repo

    async def run_turn(self, tenant_id: str, conversation_id: str, user_message: str) -> AgentTurnResult:
        persisted = await self._session_repo.get_by_conversation(tenant_id, conversation_id)
        if persisted is None:
            persisted = AgentSessionState(tenant_id=tenant_id, conversation_id=conversation_id)

        initial_state: AgentState = {
            "tenant_id": tenant_id,
            "conversation_id": conversation_id,
            "messages": [*persisted.messages, {"role": "user", "content": user_message}],
            "memory_summary": persisted.memory_summary,
            "plan": None,
            "tool_result": None,
            "final_reply": None,
            "confidence": 0.0,
            "retry_count": 0,  # retry count resets each customer turn; it counts in-turn re-plans, not across turns
            "needs_human_handoff": persisted.handed_off,
            "handoff_reason": None,
            "error": None,
        }

        final_state = await AGENT_GRAPH.ainvoke(initial_state)

        persisted.messages = final_state.get("messages", [])[-20:]  # cap history to last 20 turns kept in the session doc
        persisted.memory_summary = final_state.get("memory_summary", persisted.memory_summary)
        persisted.last_confidence = final_state.get("confidence")
        persisted.handed_off = final_state.get("needs_human_handoff", False)
        await self._session_repo.upsert(persisted)

        return AgentTurnResult(
            reply=final_state.get("final_reply") or "Sorry, something went wrong on our end.",
            confidence=final_state.get("confidence", 0.0),
            needs_human_handoff=final_state.get("needs_human_handoff", False),
            handoff_reason=final_state.get("handoff_reason"),
        )
