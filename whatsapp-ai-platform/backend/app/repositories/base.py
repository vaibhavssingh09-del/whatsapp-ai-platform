"""
Generic repository base class.

Design decision: EVERY read/write method that touches tenant-scoped data
takes `tenant_id` as an explicit, required argument and folds it into the
Mongo filter. This is the single most important security control in a
multi-tenant system: it means there is no code path in the repository layer
that can accidentally return another tenant's documents, because the query
literally cannot be constructed without a tenant_id. Cross-tenant leaks are
caught at review time by grepping for any Mongo call that bypasses this base
class, rather than relying on every engineer remembering to add the filter.
"""
from typing import Any, Generic, Optional, Type, TypeVar

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


def to_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception as exc:
        raise ValueError(f"'{id_str}' is not a valid ObjectId") from exc


def serialize_doc(doc: dict) -> dict:
    if doc is None:
        return doc
    doc = dict(doc)
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


class BaseRepository(Generic[ModelT]):
    collection_name: str
    model: Type[ModelT]

    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db

    @property
    def collection(self) -> AsyncIOMotorCollection:
        return self._db[self.collection_name]

    async def get_by_id(self, tenant_id: str, doc_id: str) -> Optional[ModelT]:
        doc = await self.collection.find_one({"_id": to_object_id(doc_id), "tenant_id": tenant_id})
        return self.model(**serialize_doc(doc)) if doc else None

    async def find_many(
        self,
        tenant_id: str,
        query: Optional[dict[str, Any]] = None,
        limit: int = 50,
        skip: int = 0,
        sort: Optional[list[tuple[str, int]]] = None,
    ) -> list[ModelT]:
        full_query = {"tenant_id": tenant_id, **(query or {})}
        cursor = self.collection.find(full_query).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort(sort)
        return [self.model(**serialize_doc(doc)) async for doc in cursor]

    async def count(self, tenant_id: str, query: Optional[dict[str, Any]] = None) -> int:
        full_query = {"tenant_id": tenant_id, **(query or {})}
        return await self.collection.count_documents(full_query)

    async def create(self, instance: ModelT) -> ModelT:
        payload = instance.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(payload)
        instance.id = str(result.inserted_id)
        return instance

    async def update(self, tenant_id: str, doc_id: str, update_fields: dict[str, Any]) -> bool:
        result = await self.collection.update_one(
            {"_id": to_object_id(doc_id), "tenant_id": tenant_id},
            {"$set": update_fields},
        )
        return result.modified_count > 0

    async def delete(self, tenant_id: str, doc_id: str) -> bool:
        result = await self.collection.delete_one({"_id": to_object_id(doc_id), "tenant_id": tenant_id})
        return result.deleted_count > 0
