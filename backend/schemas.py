from pydantic import BaseModel
from typing import Dict, Any

class DemographicsState(BaseModel):
    enabled: bool
    sample_count: int
    gender_distribution: Dict[str, float]
    age_distribution: Dict[str, float]

class MetricsPayload(BaseModel):
    timestamp: float
    frame_id: int
    count_in: int
    count_out: int
    occupancy: int
    queue_count: int
    queue_alert: bool
    fps: float
    tracked_count: int
    demographics: DemographicsState
