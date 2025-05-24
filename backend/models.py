from pydantic import BaseModel
from typing import List, Optional

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