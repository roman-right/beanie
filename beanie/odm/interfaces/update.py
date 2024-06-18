from abc import abstractmethod
from typing import Any, Awaitable, Dict, Mapping, Optional, Union, overload
from motor.motor_asyncio import AsyncIOMotorClientSession
from pymongo.results import UpdateResult
from beanie.odm.bulk import BulkWriter
from beanie.odm.fields import ExpressionField
from beanie.odm.operators.update.general import (
    CurrentDate,
    Inc,
    Set,
)


class UpdateMethods:
    """
    Update methods
    """

    @abstractmethod
    def update(
        self,
        *args: Mapping[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None,
        bulk_writer: Optional[BulkWriter] = None,
        **kwargs: Any,
    ) -> Awaitable[UpdateResult]:
        return self

    @overload
    async def set(  # type: ignore
        self,
        expression: Dict[Union[ExpressionField, str], Any],
        session: Optional[AsyncIOMotorClientSession] = None,
        bulk_writer: Optional[BulkWriter] = None,
        **kwargs: Any,
    ) -> UpdateResult: ...

    def set(
        self,
        expression: Dict[Union[ExpressionField, str], Any],
        session: Optional[AsyncIOMotorClientSession] = None,
        bulk_writer: Optional[BulkWriter] = None,
        **kwargs: Any,
    ):
        """
        Set values

        Example:

        ```python

        class Sample(Document):
            one: int

        await Document.find(Sample.one == 1).set({Sample.one: 100})

        ```

        Uses [Set operator](operators/update.md#set)

        :param expression: Dict[Union[ExpressionField, str], Any] - keys and
        values to set
        :param session: Optional[AsyncIOMotorClientSession] - pymongo session
        :param bulk_writer: Optional[BulkWriter] - bulk writer
        :return: self
        """
        return self.update(
            Set(expression), session=session, bulk_writer=bulk_writer, **kwargs
        )

    @overload
    async def current_date(  # type: ignore
        self,
        expression: Dict[Union[ExpressionField, str], Any],
        session: Optional[AsyncIOMotorClientSession] = None,
        bulk_writer: Optional[BulkWriter] = None,
        **kwargs: Any,
    ) -> UpdateResult: ...

    def current_date(
        self,
        expression: Dict[Union[ExpressionField, str], Any],
        session: Optional[AsyncIOMotorClientSession] = None,
        bulk_writer: Optional[BulkWriter] = None,
        **kwargs: Any,
    ):
        """
        Set current date

        Uses [CurrentDate operator](operators/update.md#currentdate)

        :param expression: Dict[Union[ExpressionField, str], Any]
        :param session: Optional[AsyncIOMotorClientSession] - pymongo session
        :param bulk_writer: Optional[BulkWriter] - bulk writer
        :return: self
        """
        return self.update(
            CurrentDate(expression),
            session=session,
            bulk_writer=bulk_writer,
            **kwargs,
        )

    @overload
    async def inc(  # type: ignore
        self,
        expression: Dict[Union[ExpressionField, str], Any],
        session: Optional[AsyncIOMotorClientSession] = None,
        bulk_writer: Optional[BulkWriter] = None,
        **kwargs: Any,
    ) -> UpdateResult: ...

    def inc(
        self,
        expression: Dict[Union[ExpressionField, str], Any],
        session: Optional[AsyncIOMotorClientSession] = None,
        bulk_writer: Optional[BulkWriter] = None,
        **kwargs: Any,
    ):
        """
        Increment

        Example:

        ```python

        class Sample(Document):
            one: int

        await Document.find(Sample.one == 1).inc({Sample.one: 100})

        ```

        Uses [Inc operator](operators/update.md#inc)

        :param expression: Dict[Union[ExpressionField, str], Any]
        :param session: Optional[AsyncIOMotorClientSession] - pymongo session
        :param bulk_writer: Optional[BulkWriter] - bulk writer
        :return: self
        """
        return self.update(
            Inc(expression), session=session, bulk_writer=bulk_writer, **kwargs
        )
