from typing import Optional, List, Type, Union

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import Field
from pydantic.main import BaseModel
from pymongo.results import DeleteResult, UpdateResult, InsertOneResult

from beanie.collection import collection_factory
from beanie.cursor import Cursor
from beanie.exceptions import (
    DocumentWasNotSaved,
    DocumentNotFound,
    DocumentAlreadyCreated,
)
from beanie.fields import PydanticObjectId


class Document(BaseModel):
    id: Optional[PydanticObjectId] = Field(None, alias="_id")
    _collection_storage = {}  # TODO think about better solution for this

    def __init__(self, *args, **kwargs):
        """
        Initialization

        :param args:
        :param kwargs:
        """
        super(Document, self).__init__(*args, **kwargs)
        if getattr(self, "Collection", None) is None:
            raise AttributeError(
                "No collection is associated with this document model"
            )

    @classmethod
    async def _init_collection(cls, database: AsyncIOMotorDatabase):
        """
        Internal Collection class creator

        :param database:
        :return:
        """
        collection_class = getattr(cls, "Collection", None)
        collection = await collection_factory(
            database=database,
            document_class=cls,
            collection_class=collection_class,
        )
        setattr(cls, "Collection", collection)

    async def _sync(self) -> None:
        """
        Update local document from the database
        :return: None
        """
        new_instance = await self.get(self.id)
        for key, value in dict(new_instance).items():
            setattr(self, key, value)

    @classmethod
    async def insert_one(cls, document: "Document") -> InsertOneResult:
        """
        Insert one document to the collection
        :return: Document
        """
        return await cls.Collection.motor_collection.insert_one(
            document.dict(by_alias=True, exclude={"id"})
        )

    @classmethod
    async def insert_many(cls, documents: List["Document"]):
        """
        Insert many documents to the collection
        :return: Document
        """
        return await cls.Collection.motor_collection.insert_many(
            [
                document.dict(by_alias=True, exclude={"id"})
                for document in documents
            ]
        )

    async def create(self) -> "Document":
        """
        Create the document in the database
        :return: Document
        """
        if self.id is not None:
            raise DocumentAlreadyCreated
        result = await self.Collection.motor_collection.insert_one(
            self.dict(by_alias=True, exclude={"id"})
        )
        self.id = PydanticObjectId(result.inserted_id)
        return self

    @classmethod
    async def find_one(cls, filter_query: dict) -> Union["Document", None]:
        """
        Find one document by criteria

        :param filter_query: The selection criteria
        :return: Document
        """
        document = await cls.Collection.motor_collection.find_one(filter_query)
        if document is None:
            return None
        return cls.parse_obj(document)

    @classmethod
    def find_many(cls, filter_query: dict) -> Cursor:
        """
        Find many documents by criteria

        :param filter_query: The selection criteria.
        :return: AsyncGenerator of the documents
        """
        cursor = cls.Collection.motor_collection.find(filter_query)
        return Cursor(motor_cursor=cursor, model=cls)

    @classmethod
    def find_all(cls) -> Cursor:
        """
        Get all the documents

        :return: AsyncGenerator of the documents
        """
        return cls.find_many(filter_query={})

    @classmethod
    async def get(
        cls, document_id: PydanticObjectId
    ) -> Union["Document", None]:
        """
        Get document by id

        :return:
        """
        return await cls.find_one({"_id": document_id})

    @classmethod
    async def replace_one(cls, filter_query: dict, document: "Document"):
        """
        Fully update one document in the database
        :return: None
        """
        result = await cls.Collection.motor_collection.replace_one(
            filter_query, document.dict(by_alias=True, exclude={"id"})
        )
        if not result.raw_result["updatedExisting"]:
            raise DocumentNotFound
        return result

    async def replace(self) -> "Document":
        """
        Fully update the document in the database
        :return: None
        """
        if self.id is None:
            raise DocumentWasNotSaved

        await self.replace_one({"_id": self.id}, self)
        return self

    @classmethod
    async def update_one(
        cls,
        filter_query: dict,
        update_query: dict,
    ) -> UpdateResult:
        """
        Partially update already created document

        :param update_query: The modifications to apply.
        :param filter_query: The selection criteria for the update. Optional.
        :return: UpdateResult instance
        """
        return await cls.Collection.motor_collection.update_one(
            filter_query, update_query
        )

    @classmethod
    async def update_many(
        cls, filter_query: dict, update_query: dict
    ) -> UpdateResult:
        """
        Partially update many documents

        :param filter_query: The selection criteria for the update.
        :param update_query: The modifications to apply.
        :return: UpdateResult instance
        """
        return await cls.Collection.motor_collection.update_many(
            filter_query, update_query
        )

    @classmethod
    async def update_all(cls, update_query: dict) -> UpdateResult:
        """
        Partially update all the documents

        :param update_query: The modifications to apply.
        :return: UpdateResult instance
        """
        return await cls.update_many({}, update_query)

    async def update(self, update_query: dict) -> None:
        """
        Partially update the document in the database

        :param update_query: The modifications to apply.
        :return: None
        """
        await self.update_one({"_id": self.id}, update_query=update_query)
        await self._sync()

    @classmethod
    async def delete_one(cls, filter_query: dict) -> DeleteResult:
        """
        Delete one document

        :param filter_query: The selection criteria
        :return: DeleteResult instance
        """
        return await cls.Collection.motor_collection.delete_one(filter_query)

    @classmethod
    async def delete_many(cls, filter_query: dict) -> DeleteResult:
        """
        Delete many documents

        :param filter_query: The selection criteria
        :return: DeleteResult instance
        """
        return await cls.Collection.motor_collection.delete_many(filter_query)

    @classmethod
    async def delete_all(cls) -> DeleteResult:
        """
        Delete all the documents

        :return: DeleteResult instance
        """
        return await cls.delete_many({})

    async def delete(self) -> DeleteResult:
        """
        Delete the document

        :return:
        """
        return await self.delete_one({"_id": self.id})

    @classmethod
    def aggregate(
        cls, aggregation_query: List[dict], item_model: Type[BaseModel] = None
    ) -> Cursor:
        """
        Aggregate

        :param aggregation_query: Query with aggregation commands
        :param item_model: Model of item to return in the list of aggregations
        :return: AsyncGenerator of aggregated items
        """
        cursor = cls.Collection.motor_collection.aggregate(aggregation_query)
        return Cursor(motor_cursor=cursor, model=item_model)

    class Config:
        json_encoders = {
            ObjectId: lambda v: str(v),
        }
        allow_population_by_field_name = True
