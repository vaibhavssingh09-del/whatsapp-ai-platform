"""
MongoDB connection lifecycle + index bootstrap.

Design decision: a single module-level AsyncIOMotorClient, created once at
app startup and reused for the process lifetime. Motor's client is already
connection-pooled and safe to share across requests/coroutines, so creating
a new client per-request would only add latency and exhaust connections.

Indexes are declared here, in code, rather than only in a Mongo Atlas UI.
That means a fresh environment (e.g. a new hire's laptop, or a CI test DB)
gets correct indexes automatically the first time the app boots.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def get_database() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongo() at startup.")
    return _db


async def connect_to_mongo() -> None:
    global _client, _db
    settings = get_settings()
    _client = AsyncIOMotorClient(settings.MONGO_URI, uuidRepresentation="standard")
    _db = _client[settings.MONGO_DB_NAME]
    await _ensure_indexes(_db)
    logger.info("mongo_connected", db=settings.MONGO_DB_NAME)


async def close_mongo_connection() -> None:
    global _client
    if _client is not None:
        _client.close()
        logger.info("mongo_connection_closed")


async def _ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    """
    All indexes are compound on tenant_id first. Every collection in this
    system is tenant-scoped, and Mongo uses the leftmost prefix of a compound
    index, so putting tenant_id first lets every tenant-scoped query use the
    index regardless of which other fields it filters on.
    """
    await db.tenants.create_index("slug", unique=True)

    await db.users.create_index([("tenant_id", 1), ("email", 1)], unique=True)

    await db.conversations.create_index([("tenant_id", 1), ("wa_contact_id", 1)])
    await db.conversations.create_index([("tenant_id", 1), ("status", 1), ("last_message_at", -1)])

    await db.messages.create_index([("tenant_id", 1), ("conversation_id", 1), ("created_at", 1)])
    await db.messages.create_index([("tenant_id", 1), ("wa_message_id", 1)], unique=True, sparse=True)

    await db.media_assets.create_index([("tenant_id", 1), ("created_at", -1)])

    await db.broadcasts.create_index([("tenant_id", 1), ("status", 1), ("scheduled_at", 1)])

    await db.audit_logs.create_index([("tenant_id", 1), ("created_at", -1)])

    await db.agent_sessions.create_index([("tenant_id", 1), ("conversation_id", 1)], unique=True)
    await db.agent_sessions.create_index("updated_at", expireAfterSeconds=60 * 60 * 24 * 30)

    logger.info("mongo_indexes_ensured")
