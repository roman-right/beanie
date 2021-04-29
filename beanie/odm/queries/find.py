from typing import Union, Optional, List, Tuple, Type, Mapping

from pydantic import BaseModel

from beanie.exceptions import DocumentNotFound
from beanie.odm.interfaces.aggregate import AggregateMethods
from beanie.odm.interfaces.update import (
    UpdateMethods,
)
from beanie.odm.models import SortDirection
from beanie.odm.operators.find.logical import And
from beanie.odm.projections import get_projection
from beanie.odm.queries.aggregation import AggregationPipeline
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


class FindQuery(UpdateMethods):
    UpdateQueryType = UpdateQuery
    DeleteQueryType = DeleteQuery

    def __init__(self, document_model):
        self.document_model = document_model
        self.find_expressions: List[Union[dict, Mapping]] = []
        self.projection_model = document_model

    def get_filter_query(self):
        if self.find_expressions:
            return And(*self.find_expressions)
        else:
            return {}

    def _pass_update_expression(self, expression):
        return self.UpdateQueryType(
            document_model=self.document_model,
            find_query=self.get_filter_query(),
        ).update(expression)

    def update(self, *args):
        return self.UpdateQueryType(
            document_model=self.document_model,
            find_query=self.get_filter_query(),
        ).update(*args)

    def delete(self):
        return self.DeleteQueryType(
            document_model=self.document_model,
            find_query=self.get_filter_query(),
        )

    def project(self, projection_model: Optional[Type[BaseModel]]):
        if projection_model is None:
            self.projection_model = projection_model


class FindMany(BaseCursorQuery, FindQuery, AggregateMethods):
    UpdateQueryType = UpdateMany
    DeleteQueryType = DeleteMany

    def __init__(self, document_model):
        super(FindMany, self).__init__(document_model=document_model)
        self.sort_expressions: List[Tuple[str, SortDirection]] = []
        self.skip_number: int = 0
        self.limit_number: int = 0
        self.init_cursor(return_model=document_model)

    @property
    def motor_cursor(self):
        projection = (
            get_projection(self.projection_model)
            if self.projection_model
            else None
        )
        return self.document_model.get_motor_collection().find(
            filter=self.get_filter_query(),
            sort=self.sort_expressions,
            projection=projection,
            skip=self.skip_number,
            limit=self.limit_number,
        )

    def find_many(
        self,
        *args,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        sort: Union[None, str, List[Tuple[str, SortDirection]]] = None,
        projection_model: Optional[Type[BaseModel]] = None
    ):
        self.find_expressions += args
        self.skip(skip)
        self.limit(limit)
        self.sort(sort)
        self.project(projection_model)
        return self

    def find(
        self,
        *args,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        sort: Union[None, str, List[Tuple[str, SortDirection]]] = None,
        projection_model: Optional[Type[BaseModel]] = None
    ):
        return self.find_many(
            *args,
            skip=skip,
            limit=limit,
            sort=sort,
            projection_model=projection_model
        )

    def sort(self, *args):
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
                raise Exception  # TODO come up with exception
        return self

    def skip(self, n: Optional[int]):
        if n is not None:
            self.skip_number = n
        return self

    def limit(self, n: Optional[int]):
        if n is not None:
            self.limit_number = n
        return self

    def update_many(self, *args):
        return self.update(*args)

    def delete_many(self):
        return self.delete()

    async def count(self):
        return (
            await self.document_model.get_motor_collection().count_documents(
                self.get_filter_query()
            )
        )

    def aggregate(
        self,
        aggregation_pipeline,
        aggregation_model: Type[BaseModel] = None,
    ) -> AggregationPipeline:
        return AggregationPipeline(
            aggregation_pipeline=aggregation_pipeline,
            document_model=self.document_model,
            projection_model=aggregation_model,
            find_query=self.get_filter_query(),
        )


class FindOne(FindQuery):
    UpdateQueryType = UpdateOne
    DeleteQueryType = DeleteOne

    def find_one(
        self, *args, projection_model: Optional[Type[BaseModel]] = None
    ):
        self.find_expressions += args
        self.project(projection_model)
        return self

    def update_one(self, *args):
        return self.update(*args)

    def delete_one(self):
        return self.delete()

    async def replace_one(self, document):
        result = await self.document_model.get_motor_collection().replace_one(
            self.get_filter_query(),
            document.dict(by_alias=True, exclude={"id"}),
        )

        if not result.raw_result["updatedExisting"]:
            raise DocumentNotFound
        return result

    def __await__(self):
        projection = (
            get_projection(self.projection_model)
            if self.projection_model
            else None
        )
        document = yield from self.document_model.get_motor_collection().find_one(
            filter=self.get_filter_query(),
            projection=projection,
            # session=session,
        )  # noqa
        if document is None:
            return None
        return self.document_model.parse_obj(document)