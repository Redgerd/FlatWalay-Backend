from pydantic import BaseModel
from typing import Optional

class ProfileResponse(BaseModel):
    id: str
    raw_profile_text: str
    city: str
    area: str
    budget_PKR: int
    sleep_schedule: Optional[str]
    cleanliness: Optional[str]
    noise_tolerance: Optional[str]
    study_habits: Optional[str]
    food_pref: Optional[str]