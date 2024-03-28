from abc import abstractmethod
from typing import Any, Dict, Mapping, Optional, Union
from datetime import datetime
from pymongo.client_session import ClientSession

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
        session: Optional[ClientSession] = None,
        bulk_writer: Optional[BulkWriter] = None,
        **kwargs,
    ):
        return self

    def set(
        self,
        expression: Dict[Union[ExpressionField, Any], Any],
        session: Optional[ClientSession] = None,
        bulk_writer: Optional[BulkWriter] = None,
        **kwargs,
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
        :param expression: Dict[Union[ExpressionField, Any], Any] - keys and
        values to set
        :param session: Optional[ClientSession] - pymongo session
        :param bulk_writer: Optional[BulkWriter] - bulk writer
        :return: self
        """
        return self.update(
            Set(expression), session=session, bulk_writer=bulk_writer, **kwargs
        )

    def current_date(
        self,
        expression: Dict[Union[ExpressionField, datetime, str], Any],
        session: Optional[ClientSession] = None,
        bulk_writer: Optional[BulkWriter] = None,
        **kwargs,
    ):
        """
        Set current date
        Uses [CurrentDate operator](operators/update.md#currentdate)
        :param expression: Dict[Union[ExpressionField, datetime, str], Any]
        :param session: Optional[ClientSession] - pymongo session
        :param bulk_writer: Optional[BulkWriter] - bulk writer
        :return: self
        """
        return self.update(
            CurrentDate(expression),
            session=session,
            bulk_writer=bulk_writer,
            **kwargs,
        )

    def inc(
        self,
        expression: Dict[Union[ExpressionField, float, int, str], Any],
        session: Optional[ClientSession] = None,
        bulk_writer: Optional[BulkWriter] = None,
        **kwargs,
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
        :param expression: Dict[Union[ExpressionField, float, int, str], Any]
        :param session: Optional[ClientSession] - pymongo session
        :param bulk_writer: Optional[BulkWriter] - bulk writer
        :return: self
        """
        return self.update(
            Inc(expression), session=session, bulk_writer=bulk_writer, **kwargs
        )
