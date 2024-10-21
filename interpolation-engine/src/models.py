"""
Here are all the pydantic models used in this application used for input validation and automated generation of API documentation
"""

from datetime import datetime

from pydantic import BaseModel, field_validator, Field
from typing_extensions import Annotated
from typing import List, Optional, Tuple
from shapely import Polygon


class PolygonGeometry(BaseModel):
    type : str = "Polygon"
    coordinates: Annotated[
        List[Annotated[
            List[Tuple[
                Annotated[float, Field(ge=5, lt=16, title="longitude", description="longitude")],
                Annotated[float, Field(ge=46, lt=55, title="latitude", description="latitude")]
            ]],
            Field(min_length=4, title="vertices", description="vertices as counter-clockwise closed loop")
        ]],
        Field(min_length=1, max_length=1, title="loops", description="loop list with only 1 member (we dont allow holes)" )
    ]


    @field_validator('coordinates')
    @classmethod
    def validate_coords(cls, coordinates: List[List[Tuple[float, float]]]) -> List[List[Tuple[float, float]]]:
        if coordinates[0][0] != coordinates[0][-1]:
            raise ValueError('Loop must be closed (first vertex == last vertex)')

        polygon = Polygon(coordinates[0])
        if not polygon.exterior.is_ccw:
            raise ValueError('Vertices must be ordered counter-clockwise')

        return coordinates

class CellProperties(BaseModel):
    cell : str = Field(..., title="s2 cell id", description="s2 cell id to be supplied to data endpoint")

class SensorData(BaseModel):
    time: datetime
    bucket : float
    ws: float = Field(..., gt=0.0, lt=160.0, title="wind speed", description="wind speed in m/s") #166 is significantly higher than the highest windspeed ever recorded
    wd : float = Field(..., gt=0.0, lt=360.0, title="wind direction", description="wind direction in degrees")

class SensorDataProperties(BaseModel):
    sensor_data : Optional[SensorData] = None

class InputPolygonFeature(BaseModel):
    type : str = "Feature"
    geometry: PolygonGeometry
    properties: Optional[SensorDataProperties] = None

class OutputPolygonFeature(BaseModel):
    type : str = "Feature"
    geometry: PolygonGeometry
    properties : CellProperties


class Covering(BaseModel):
    type : str = "FeatureCollection"
    properties : SensorDataProperties
    features: List[OutputPolygonFeature]