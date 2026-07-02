"""
Aggregate metrics for the dashboard's Metrics view.

Design decision: metrics are computed with Mongo aggregation pipelines run
on demand, not pre-computed/cached in a separate collection. At the scale
this reference implementation targets (a single small-to-mid business's
conversation volume), an on-demand count/aggregate over indexed fields
(tenant_id + created_at, see database.py) is well under 100ms. The README
"Scaling Beyond 48 Hours" section notes the point at which this should move
to a scheduled rollup job instead (roughly: once conversation volume makes
a single tenant's daily message count exceed ~100k).
"""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import AuthContext, get_auth_context, get_audit_repository, get_db
from app.models.audit import AuditLog
from app.repositories.misc_repositories import AuditLogRepository
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class DashboardMetrics(BaseModel):
    total_conversations: int
    active_bot_conversations: int
    human_handoff_conversations: int
    resolved_conversations: int
    messages_last_24h: int
    avg_agent_confidence: float
    handoff_rate_pct: float


@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    ctx: Annotated[AuthContext, Depends(get_auth_context)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
):
    tenant_filter = {"tenant_id": ctx.tenant_id}

    total = await db.conversations.count_documents(tenant_filter)
    active = await db.conversations.count_documents({**tenant_filter, "status": "bot_active"})
    handoff = await db.conversations.count_documents({**tenant_filter, "status": "human_handoff"})
    resolved = await db.conversations.count_documents({**tenant_filter, "status": "resolved"})

    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    messages_24h = await db.messages.count_documents({**tenant_filter, "created_at": {"$gte": datetime.fromisoformat(since)}})

    confidence_pipeline = [
        {"$match": {**tenant_filter, "agent_confidence": {"$ne": None}}},
        {"$group": {"_id": None, "avg_confidence": {"$avg": "$agent_confidence"}}},
    ]
    confidence_result = await db.messages.aggregate(confidence_pipeline).to_list(length=1)
    avg_confidence = confidence_result[0]["avg_confidence"] if confidence_result else 0.0

    handoff_rate = (handoff / total * 100) if total else 0.0

    return DashboardMetrics(
        total_conversations=total,
        active_bot_conversations=active,
        human_handoff_conversations=handoff,
        resolved_conversations=resolved,
        messages_last_24h=messages_24h,
        avg_agent_confidence=round(avg_confidence, 2),
        handoff_rate_pct=round(handoff_rate, 1),
    )


@router.get("/audit-logs", response_model=list[AuditLog])
async def get_audit_logs(
    ctx: Annotated[AuthContext, Depends(get_auth_context)],
    repo: Annotated[AuditLogRepository, Depends(get_audit_repository)],
    limit: int = 100,
):
    return await repo.list_recent(ctx.tenant_id, limit=limit)
