from pydantic import BaseModel
from typing import List, Optional

class Trip(BaseModel):
    destination: str
    start_date: str
    end_date: str
    activities: Optional[List[str]] = []
    weather_info: Optional[dict] = {}
    packing_list: Optional[List[str]] = []

