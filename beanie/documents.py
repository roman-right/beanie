from enum import Enum
from typing import List, Optional, Tuple, Type, Union

import pymongo
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pydantic import Field, validator
from pydantic.main import BaseModel, PrivateAttr
from pymongo.results import DeleteResult, InsertOneResult, UpdateResult

from beanie.collection import collection_factory
from beanie.cursor import Cursor
from beanie.deprecated import get_collection_class_from_document_meta_class
from beanie.exceptions import (
    CollectionWasNotInitialized,
    DocumentAlreadyCreated,
    DocumentNotFound,
    DocumentWasNotSaved,
)
from beanie.fields import PydanticObjectId


class SortDirection(int, Enum):
    ASCENDING = pymongo.ASCENDING
    DESCENDING = pymongo.DESCENDING


class FindOperationKWARGS(BaseModel):
    skip: Optional[int] = None
    limit: Optional[int] = None
    sort: Union[None, str, List[Tuple[str, SortDirection]]] = None

    @validator("sort")
    def name_must_contain_space(cls, v):
        if isinstance(v, str):
            return [(v, pymongo.ASCENDING)]
        return v


class Document(BaseModel):
    id: Optional[PydanticObjectId] = Field(None, alias="_id")
    _is_created: bool = PrivateAttr(default=False)

    def __init__(self, *args, **kwargs):
        """
        Initialization

        :param args:
        :param kwargs:
        """
        super(Document, self).__init__(*args, **kwargs)
        self.get_motor_collection()

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
        exclude = None if document.id else {"id"}
        return await cls.get_motor_collection().insert_one(
            document.dict(by_alias=True, exclude=exclude)
        )

    @classmethod
    async def insert_many(cls, documents: List["Document"]):
        """
        Insert many documents to the collection
        :return: Document
        """
        return await cls.get_motor_collection().insert_many(
            [
                document.dict(
                    by_alias=True,
                    exclude=None if document.id else {"id"},
                )
                for document in documents
            ]
        )

    async def create(self) -> "Document":
        """
        Create the document in the database
        :return: Document
        """
        if self._is_created:
            raise DocumentAlreadyCreated
        exclude = None if self.id else {"id"}
        result = await self.get_motor_collection().insert_one(
            self.dict(by_alias=True, exclude=exclude)
        )

        if isinstance(result.inserted_id, ObjectId):
            self.id = PydanticObjectId(result.inserted_id)
        else:
            self.id = result.inserted_id

        self._is_created = True
        return self

    @classmethod
    async def find_one(cls, filter_query: dict) -> Union["Document", None]:
        """
        Find one document by criteria

        :param filter_query: The selection criteria
        :return: Document
        """
        document = await cls.get_motor_collection().find_one(filter_query)
        if document is None:
            return None
        return cls.parse_obj(document)

    @classmethod
    def find_many(
        cls,
        filter_query: dict,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        sort: Union[None, str, List[Tuple[str, SortDirection]]] = None,
    ) -> Cursor:
        """
        Find many documents by criteria

        :param filter_query: The selection criteria.
        :param skip: The number of documents to omit.
        :param limit: The maximum number of results to return.
        :param sort: A key or a list of (key, direction) pairs
                     specifying the sort order for this query.
        :return: AsyncGenerator of the documents
        """
        kwargs = FindOperationKWARGS(skip=skip, limit=limit, sort=sort).dict(
            exclude_none=True
        )
        cursor = cls.get_motor_collection().find(filter_query, **kwargs)
        return Cursor(motor_cursor=cursor, model=cls)

    @classmethod
    def find_all(
        cls,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        sort: Union[None, str, List[Tuple[str, SortDirection]]] = None,
    ) -> Cursor:
        """
        Get all the documents

        :param skip: The number of documents to omit.
        :param limit: The maximum number of results to return.
        :param sort: A key or a list of (key, direction) pairs
                     specifying the sort order for this query.
        :return: AsyncGenerator of the documents
        """
        return cls.find_many(
            filter_query={}, skip=skip, limit=limit, sort=sort
        )

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
        exclude = None if document.id else {"id"}
        result = await cls.get_motor_collection().replace_one(
            filter_query, document.dict(by_alias=True, exclude=exclude)
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
        return await cls.get_motor_collection().update_one(
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
        return await cls.get_motor_collection().update_many(
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
        return await cls.get_motor_collection().delete_one(filter_query)

    @classmethod
    async def delete_many(cls, filter_query: dict) -> DeleteResult:
        """
        Delete many documents

        :param filter_query: The selection criteria
        :return: DeleteResult instance
        """
        return await cls.get_motor_collection().delete_many(filter_query)

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
        cursor = cls.get_motor_collection().aggregate(aggregation_query)
        return Cursor(motor_cursor=cursor, model=item_model)

    # Collections

    @classmethod
    async def init_collection(cls, database: AsyncIOMotorDatabase) -> None:
        """
        Internal CollectionMeta class creator

        :param database: AsyncIOMotorDatabase
        :return: None
        """
        # TODO remove deprecated function
        collection_class = get_collection_class_from_document_meta_class(
            cls
        ) or getattr(cls, "Collection", None)
        collection_meta = await collection_factory(
            database=database,
            document_class=cls,
            collection_class=collection_class,
        )
        setattr(cls, "CollectionMeta", collection_meta)

    @classmethod
    def _get_collection_meta(cls) -> Type:
        """
        Get internal CollectionMeta class, which was created on
        the collection initialization step

        :return: CollectionMeta class
        """
        collection_meta = getattr(cls, "CollectionMeta", None)
        if collection_meta is None:
            raise CollectionWasNotInitialized
        return collection_meta

    @classmethod
    def get_motor_collection(cls) -> AsyncIOMotorCollection:
        """
        Get Motor Collection to access low level control

        :return: AsyncIOMotorCollection
        """
        collection_meta = cls._get_collection_meta()
        return collection_meta.motor_collection

    class Config:
        json_encoders = {
            ObjectId: lambda v: str(v),
        }
        allow_population_by_field_name = True
