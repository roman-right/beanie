from abc import abstractmethod
from typing import Dict, Union, Any

from beanie.odm.fields import CollectionField
from beanie.odm.operators.update.general import (
    Set,
    CurrentDate,
    Inc,
)


class UpdateMethods:
    @abstractmethod
    def _pass_update_expression(self, expression):
        ...

    def set(self, expression: Dict[Union[CollectionField, str], Any]):
        return self._pass_update_expression(Set(expression))

    def current_date(self, expression: Dict[Union[CollectionField, str], Any]):
        return self._pass_update_expression(CurrentDate(expression))

    def inc(self, expression: Dict[Union[CollectionField, str], Any]):
        return self._pass_update_expression(Inc(expression))