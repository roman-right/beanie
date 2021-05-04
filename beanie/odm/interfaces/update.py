from abc import abstractmethod
from typing import Dict, Union, Any, Optional

from pymongo.client_session import ClientSession

from beanie.odm.fields import ExpressionField
from beanie.odm.operators.update.general import (
    Set,
    CurrentDate,
    Inc,
)


class UpdateMethods:
    """
    Update methods
    """

    @abstractmethod
    def update(self, *args, session: Optional[ClientSession] = None):
        ...

    def set(
        self,
        expression: Dict[Union[ExpressionField, str], Any],
        session: Optional[ClientSession] = None,
    ):
        """
        Set values

        MongoDB doc:
        https://docs.mongodb.com/manual/reference/operator/update/set/
        :param expression: Dict[Union[ExpressionField, str], Any] - keys and
        values to set
        :param session: Optional[ClientSession] - pymongo session
        :return: self
        """
        return self.update(Set(expression), session=session)

    def current_date(
        self,
        expression: Dict[Union[ExpressionField, str], Any],
        session: Optional[ClientSession] = None,
    ):
        """
        Set current date

        MongoDB doc:
        https://docs.mongodb.com/manual/reference/operator/update/currentDate/
        :param expression: Dict[Union[ExpressionField, str], Any]
        :param session: Optional[ClientSession] - pymongo session
        :return: self
        """
        return self.update(CurrentDate(expression), session=session)

    def inc(
        self,
        expression: Dict[Union[ExpressionField, str], Any],
        session: Optional[ClientSession] = None,
    ):
        """
        Increment

        MongoDB doc:
        https://docs.mongodb.com/manual/reference/operator/update/inc/
        :param expression: Dict[Union[ExpressionField, str], Any]
        :param session: Optional[ClientSession] - pymongo session
        :return: self
        """
        return self.update(Inc(expression), session=session)
