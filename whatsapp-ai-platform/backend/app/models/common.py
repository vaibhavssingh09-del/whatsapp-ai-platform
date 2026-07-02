"""
Shared model primitives.

Design decision: we store Mongo `_id` as a plain string (str(ObjectId)) on
the way out of the repository layer, rather than exposing bson.ObjectId to
the rest of the app. Pydantic v2 + FastAPI serialize ObjectId poorly by
default, and leaking a Mongo-specific type into services/API layers couples
them to the database driver. Repositories are the only place that ever
touches bson.ObjectId directly.
"""
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MongoBaseModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }


class TimestampedModel(MongoBaseModel):
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
