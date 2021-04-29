from abc import abstractmethod
from enum import Enum
from typing import List, Optional

from beanie.odm.operators.find import BaseFindOperator


class BaseFindGeospatialOperator(BaseFindOperator):
    @property
    @abstractmethod
    def query(self):
        ...


class GeoIntersects(BaseFindGeospatialOperator):
    def __init__(self, field, geo_type: str, coordinates: List[List[float]]):
        self.field = field
        self.geo_type = geo_type
        self.coordinates = coordinates

    @property
    def query(self):
        return {
            self.field: {
                "$geoIntersects": {
                    "$geometry": {
                        "type": self.geo_type,
                        "coordinates": self.coordinates,
                    }
                }
            }
        }


class GeoWithinTypes(str, Enum):
    Polygon = "Polygon"
    MultiPolygon = "MultiPolygon"


class GeoWithin(BaseFindGeospatialOperator):
    def __init__(
        self, field, geo_type: GeoWithinTypes, coordinates: List[List[float]]
    ):
        self.field = field
        self.geo_type = geo_type
        self.coordinates = coordinates

    @property
    def query(self):
        return {
            self.field: {
                "$geoWithin": {
                    "$geometry": {
                        "type": self.geo_type,
                        "coordinates": self.coordinates,
                    }
                }
            }
        }


class Near(BaseFindGeospatialOperator):
    operator = "$near"

    def __init__(
        self,
        field,
        longitude: float,
        latitude: float,
        max_distance: Optional[float] = None,
        min_distance: Optional[float] = None,
    ):
        self.field = field
        self.longitude = longitude
        self.latitude = latitude
        self.max_distance = max_distance
        self.min_distance = min_distance

    @property
    def query(self):
        expression = {
            self.field: {
                self.operator: {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [self.longitude, self.latitude],
                    },
                }
            }
        }
        if self.max_distance:
            expression[self.field][self.operator][
                "$maxDistance"
            ] = self.max_distance
        if self.min_distance:
            expression[self.field][self.operator][
                "$minDistance"
            ] = self.min_distance
        return expression


class NearSphere(Near):
    operator = "$nearSphere"