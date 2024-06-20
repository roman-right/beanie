from typing import List, Union

from pydantic import UUID4, BaseModel

from beanie.odm.enums import InspectionStatuses
from beanie.odm.fields import PydanticObjectId


class InspectionError(BaseModel):
    """
    Inspection error details
    """

    document_id: Union[PydanticObjectId, UUID4]
    error: str


class InspectionResult(BaseModel):
    """
    Collection inspection result
    """

    status: InspectionStatuses = InspectionStatuses.OK
    errors: List[InspectionError] = []
