from pydantic import BaseModel, Field, RootModel
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

class Location(BaseModel):
    address: str
    postcode: str
    latitude: float
    longitude: float

class SearchRequest(BaseModel):
    search_term: str
    limit: Optional[int] = 10

class SearchResponse(BaseModel):
    results: List[Location]

# Fiware Sensor Data Models
class GeoJsonPoint(BaseModel):
    type: str
    coordinates: List[float]

class TimeInstant(BaseModel):
    type: str
    value: datetime

class SensorMetadata(BaseModel):
    TimeInstant: TimeInstant

class SensorLocation(BaseModel):
    type: str
    value: GeoJsonPoint
    metadata: SensorMetadata

class SensorAttribute(BaseModel):
    type: str
    value: Union[float, str, int]
    metadata: SensorMetadata

# Replace the old FiwareSensorData definition with RootModel for Pydantic v2+
class FiwareSensorData(RootModel[Dict[str, Any]]):
    pass

class FiwareWebhookData(BaseModel):
    subscriptionId: str
    data: List[FiwareSensorData] 

class SensorStatisticsResponse(BaseModel):
    total_sensors: Optional[int]
    sensor_types: Optional[int]
    earliest_reading: Optional[str]
    latest_reading: Optional[str] 