from typing import Union, Optional, List, Tuple, Type, Mapping

from pydantic import BaseModel
from pymongo.client_session import ClientSession
from pymongo.results import UpdateResult

from beanie.exceptions import DocumentNotFound
from beanie.odm.enums import SortDirection
from beanie.odm.interfaces.aggregate import AggregateMethods
from beanie.odm.interfaces.session import SessionMethods
from beanie.odm.interfaces.update import (
    UpdateMethods,
)
from beanie.odm.operators.find.logical import And
from beanie.odm.queries.aggregation import AggregationQuery
from beanie.odm.queries.cursor import BaseCursorQuery
from beanie.odm.queries.delete import (
    DeleteQuery,
    DeleteMany,
    DeleteOne,
)
from beanie.odm.queries.update import (
    UpdateQuery,
    UpdateMany,
    UpdateOne,
)
from beanie.odm.utils.projection import get_projection


class FindQuery(UpdateMethods, SessionMethods):
    """
    Find Query base class
    """

    UpdateQueryType = UpdateQuery
    DeleteQueryType = DeleteQuery

    def __init__(self, document_model):
        self.document_model = document_model
        self.find_expressions: List[Union[dict, Mapping]] = []
        self.projection_model = document_model
        self.session = None

    def get_filter_query(self):
        if self.find_expressions:
            return And(*self.find_expressions)
        else:
            return {}

    def update(
        self,
        *args: Union[dict, Mapping],
        session: Optional[ClientSession] = None
    ):
        """
        Create Update with modifications query
        and provide search criteria there

        :param args: *Union[dict, Mapping] - the modifications to apply.
        :param session: Optional[ClientSession]
        :return: UpdateMany query
        """
        self.set_session(session=session)
        return (
            self.UpdateQueryType(
                document_model=self.document_model,
                find_query=self.get_filter_query(),
            )
            .update(*args)
            .set_session(session=self.session)
        )

    def delete(self, session: Optional[ClientSession] = None):
        """
        Provide search criteria to the Delete query

        :param session: Optional[ClientSession]
        :return: UpdateMany query
        """
        self.set_session(session=session)
        return self.DeleteQueryType(
            document_model=self.document_model,
            find_query=self.get_filter_query(),
        ).set_session(session=session)

    def project(self, projection_model: Optional[Type[BaseModel]]):
        """
        Apply projection parameter

        :param projection_model: Optional[Type[BaseModel]] - projection model
        :return: self
        """
        if projection_model is not None:
            self.projection_model = projection_model
        return self


class FindMany(BaseCursorQuery, FindQuery, AggregateMethods):
    """
    Find Many query class

    Inherited from:

    - [FindQuery](/api/queries/#findquery)
    - [BaseCursorQuery](/api/queries/#basecursorquery)
    - [AggregateMethods](/api/interfaces/#aggregatemethods)

    """

    UpdateQueryType = UpdateMany
    DeleteQueryType = DeleteMany

    def __init__(self, document_model):
        super(FindMany, self).__init__(document_model=document_model)
        self.sort_expressions: List[Tuple[str, SortDirection]] = []
        self.skip_number: int = 0
        self.limit_number: int = 0

    def find_many(
        self,
        *args,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        sort: Union[None, str, List[Tuple[str, SortDirection]]] = None,
        projection_model: Optional[Type[BaseModel]] = None,
        session: Optional[ClientSession] = None
    ):
        """
        Find many documents by criteria

        :param args: *Union[dict, Mapping] - search criteria
        :param skip: Optional[int] - The number of documents to omit.
        :param limit: Optional[int] - The maximum number of results to return.
        :param sort: Union[None, str, List[Tuple[str, SortDirection]]] - A key
        or a list of (key, direction) pairs specifying the sort order
        for this query.
        :param projection_model: Optional[Type[BaseModel]] - projection model
        :param session: Optional[ClientSession] - pymongo session
        :return: FindMany - query instance
        """
        self.find_expressions += args
        self.skip(skip)
        self.limit(limit)
        self.sort(sort)
        self.project(projection_model)
        self.set_session(session=session)
        return self

    def find(
        self,
        *args,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        sort: Union[None, str, List[Tuple[str, SortDirection]]] = None,
        projection_model: Optional[Type[BaseModel]] = None,
        session: Optional[ClientSession] = None
    ):
        """
        The same as `find_many(...)`
        """
        return self.find_many(
            *args,
            skip=skip,
            limit=limit,
            sort=sort,
            projection_model=projection_model,
            session=session
        )

    def sort(self, *args):
        """
        Add sort parameters
        :param args: A key or a list of (key, direction) pairs specifying
        the sort order for this query.
        :return: self
        """
        for arg in args:
            if arg is None:
                pass
            elif isinstance(arg, list):
                self.sort(*arg)
            elif isinstance(arg, tuple):
                self.sort_expressions.append(arg)
            elif isinstance(arg, str):
                if arg.startswith("+"):
                    self.sort_expressions.append(
                        (arg[1:], SortDirection.ASCENDING)
                    )
                elif arg.startswith("-"):
                    self.sort_expressions.append(
                        (arg[1:], SortDirection.DESCENDING)
                    )
                else:
                    self.sort_expressions.append(
                        (arg, SortDirection.ASCENDING)
                    )
            else:
                raise TypeError("Wrong argument type")
        return self

    def skip(self, n: Optional[int]):
        """
        Set skip parameter
        :param n: int
        :return: self
        """
        if n is not None:
            self.skip_number = n
        return self

    def limit(self, n: Optional[int]):
        """
        Set limit parameter
        :param n: int
        :return:
        """
        if n is not None:
            self.limit_number = n
        return self

    def update_many(
        self,
        *args: Union[dict, Mapping],
        session: Optional[ClientSession] = None
    ) -> UpdateMany:
        """
        Provide search criteria to the update query

        :param args: *Union[dict, Mapping] - the modifications to apply.
        :param session: Optional[ClientSession]
        :return: UpdateMany query
        """
        return self.update(*args, session=session)

    def delete_many(
        self, session: Optional[ClientSession] = None
    ) -> DeleteMany:
        """
        Provide search criteria to the DeleteMany query

        :param session:
        :return: DeleteMany query
        """
        return self.delete(session=session)

    async def count(self) -> int:
        """
        Number of found documents
        :return: int
        """
        return (
            await self.document_model.get_motor_collection().count_documents(
                self.get_filter_query()
            )
        )

    def aggregate(
        self,
        aggregation_pipeline: list,
        projection_model: Type[BaseModel] = None,
        session: Optional[ClientSession] = None,
    ) -> AggregationQuery:
        """
        Provide search criteria to the AggregateQuery
        :param aggregation_pipeline: list - aggregation pipeline. MongoDB doc:
        <https://docs.mongodb.com/manual/core/aggregation-pipeline/>
        :param projection_model: Type[BaseModel] - Projection Model
        :param session: Optional[ClientSession] - PyMongo session
        :return:AggregationQuery
        """
        self.set_session(session=session)
        return AggregationQuery(
            aggregation_pipeline=aggregation_pipeline,
            document_model=self.document_model,
            projection_model=projection_model,
            find_query=self.get_filter_query(),
        ).set_session(session=self.session)

    @property
    def motor_cursor(self):
        return self.document_model.get_motor_collection().find(
            filter=self.get_filter_query(),
            sort=self.sort_expressions,
            projection=get_projection(self.projection_model),
            skip=self.skip_number,
            limit=self.limit_number,
            session=self.session,
        )


class FindOne(FindQuery):
    """
    Find One query class

    Inherited from:

    - [FindQuery](/api/queries/#findquery)
    """

    UpdateQueryType = UpdateOne
    DeleteQueryType = DeleteOne

    def find_one(
        self,
        *args,
        projection_model: Optional[Type[BaseModel]] = None,
        session: Optional[ClientSession] = None
    ):
        """
        Find one document by criteria

        :param args: *Union[dict, Mapping] - search criteria
        :param projection_model: Optional[Type[BaseModel]] - projection model
        :param session: Optional[ClientSession] - pymongo session
        :return: FindOne - query instance
        """
        self.find_expressions += args
        self.project(projection_model)
        self.set_session(session=session)
        return self

    def update_one(
        self, *args, session: Optional[ClientSession] = None
    ) -> UpdateOne:
        """
        Create UpdateOne query using modifications and
        provide search criteria there
        :param args: *Union[dict, Mapping] - the modifications to apply
        :param session: Optional[ClientSession] - PyMongo sessions
        :return: UpdateOne query
        """
        return self.update(*args, session=session)

    def delete_one(self, session: Optional[ClientSession] = None) -> DeleteOne:
        """
        Provide search criteria to the DeleteOne query
        :param session: Optional[ClientSession] - PyMongo sessions
        :return: DeleteOne query
        """
        return self.delete(session=session)

    async def replace_one(
        self, document, session: Optional[ClientSession] = None
    ) -> UpdateResult:
        """
        Replace found document by provided
        :param document: Document - document, which will replace the found one
        :param session: Optional[ClientSession] - PyMongo session
        :return: UpdateResult
        """
        self.set_session(session=session)
        result = await self.document_model.get_motor_collection().replace_one(
            self.get_filter_query(),
            document.dict(by_alias=True, exclude={"id"}),
            session=self.session,
        )

        if not result.raw_result["updatedExisting"]:
            raise DocumentNotFound
        return result

    def __await__(self):
        """
        Run the query
        :return: Document
        """
        projection = (
            get_projection(self.projection_model)
            if self.projection_model
            else None
        )
        document = (
            yield from self.document_model.get_motor_collection().find_one(
                filter=self.get_filter_query(),
                projection=projection,
                session=self.session,
            )
        )
        if document is None:
            return None
        return self.document_model.parse_obj(document)
