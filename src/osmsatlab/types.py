from dataclasses import dataclass
from typing import TypedDict, Optional

@dataclass
class BoundingBox:
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float

class Location(TypedDict):
    lat: float
    lon: float
    name: Optional[str]
