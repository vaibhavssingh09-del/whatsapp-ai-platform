"""
Seeds a fresh MongoDB database with a demo tenant, an owner user, a few
media assets, and a handful of dummy conversations/messages so the
dashboard has something to show immediately after `docker compose up`.

Run with:  python -m scripts.seed  (from the backend/ directory, venv active)

Design decision: this is a standalone script (not a FastAPI startup hook)
so it's never accidentally re-run against a populated production database
just because the app restarted. It's explicitly opt-in.
"""
import asyncio
import random
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import get_settings
from app.core.security import hash_password

DEMO_CUSTOMERS = [
    ("919812345678", "Ananya Rao"),
    ("919823456789", "Vikram Shah"),
    ("14155550101", "Emma Clarke"),
    ("447700900123", "Oliver Bennett"),
]

DUMMY_EXCHANGES = [
    ("Hi, what are your store hours?", "We're open Monday-Saturday, 9am-6pm. Anything else I can help with?"),
    ("Do you accept returns?", "Yes, items can be returned within 14 days with a receipt."),
    ("How long does shipping take?", "Standard shipping takes 3-5 business days."),
    ("I want to speak to a real person about a refund", "Thanks for your patience — I'm looping in a member of our team who can help with this."),
]


async def seed() -> None:
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    existing = await db.tenants.find_one({"slug": "demo-store"})
    if existing:
        print("Seed data already present (tenant 'demo-store' exists). Skipping.")
        return

    now = datetime.now(timezone.utc)

    tenant_result = await db.tenants.insert_one({
        "name": "Demo Store",
        "slug": "demo-store",
        "is_active": True,
        "whatsapp_phone_number_id": "1126003877272002",
        "whatsapp_business_account_id": "1007689475457299",
        "whatsapp_access_token": "EAAXsW3uop7MBRz8suxsFKahhJWetyufZC3Ox7eqjmZBgLWYNMqmwomFpaoVufIZCIBbmu4WQ4NTTin7JipZB1c1WsoGo5tsxfbmlQYld8ihVB5N8iycfR4xPi8FiZCTU36Hu53Qjv1kAvsE1XY5VDcbthJc7LqmBZCYXRBQbqZB4YzqhtWNrYOHzFF1XAEm3AbABIg9S2NZBuU9aXvnHbkkOw1NeCtKniWZCKBvKm8Ob3bznN6yyXHgYucHA74NyLyylHrQQf4q8bs7xNoW1KBrhY1Gfd",
        "timezone": "Asia/Kolkata",
        "created_at": now,
        "updated_at": now,
    })
    tenant_id = str(tenant_result.inserted_id)
    print(f"Created tenant 'Demo Store' ({tenant_id})")

    await db.users.insert_one({
        "tenant_id": tenant_id,
        "email": "owner@example.com",
        "hashed_password": hash_password("ChangeMe123!"),
        "full_name": "Demo Owner",
        "role": "owner",
        "is_active": True,
        "additional_tenant_ids": [],
        "created_at": now,
        "updated_at": now,
    })
    await db.users.insert_one({
        "tenant_id": tenant_id,
        "email": "agent@example.com",
        "hashed_password": hash_password("ChangeMe123!"),
        "full_name": "Demo Agent",
        "role": "agent",
        "is_active": True,
        "additional_tenant_ids": [],
        "created_at": now,
        "updated_at": now,
    })
    print("Created users: owner@demo-store.test / agent@demo-store.test (password: ChangeMe123!)")

    for wa_id, name in DEMO_CUSTOMERS:
        convo_result = await db.conversations.insert_one({
            "tenant_id": tenant_id,
            "wa_contact_id": wa_id,
            "contact_name": name,
            "status": random.choice(["bot_active", "bot_active", "human_handoff", "resolved"]),
            "assigned_agent_id": None,
            "last_message_at": now.isoformat(),
            "last_message_preview": "",
            "unread_count": random.randint(0, 3),
            "tags": [],
            "created_at": now - timedelta(days=random.randint(0, 5)),
            "updated_at": now,
        })
        conversation_id = str(convo_result.inserted_id)

        message_time = now - timedelta(hours=random.randint(1, 48))
        for user_text, bot_text in random.sample(DUMMY_EXCHANGES, k=2):
            await db.messages.insert_one({
                "tenant_id": tenant_id,
                "conversation_id": conversation_id,
                "wa_message_id": f"seed-{random.randint(100000, 999999)}",
                "direction": "inbound",
                "message_type": "text",
                "text": user_text,
                "status": "read",
                "created_at": message_time,
                "updated_at": message_time,
            })
            message_time += timedelta(seconds=45)
            await db.messages.insert_one({
                "tenant_id": tenant_id,
                "conversation_id": conversation_id,
                "wa_message_id": f"seed-{random.randint(100000, 999999)}",
                "direction": "outbound",
                "message_type": "text",
                "text": bot_text,
                "status": "delivered",
                "sent_by_bot": True,
                "agent_confidence": round(random.uniform(0.55, 0.98), 2),
                "created_at": message_time,
                "updated_at": message_time,
            })
            message_time += timedelta(minutes=random.randint(2, 20))

        await db.conversations.update_one(
            {"_id": convo_result.inserted_id},
            {"$set": {"last_message_at": message_time.isoformat(), "last_message_preview": bot_text[:120]}},
        )

    print(f"Seeded {len(DEMO_CUSTOMERS)} dummy conversations with messages.")

    # Media seeding note: actual binary files aren't generated here since
    # media requires real bytes on disk under MEDIA_STORAGE_DIR. Upload a
    # real image/PDF once via POST /api/v1/media after the app is running —
    # inserting a fake MediaAsset document without a matching file on disk
    # would make GET /media/{id}/file 404, which is worse than not seeding it.
    print("Skipped media seeding: upload real files via POST /api/v1/media once the API is running.")

    client.close()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
