from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class SleepSchedule(str, Enum):
    NIGHT_OWL = "Night owl"
    EARLY_RISER = "Early riser"
    FLEXIBLE = "Flexible"


class Cleanliness(str, Enum):
    TIDY = "Tidy"
    AVERAGE = "Average"
    MESSY = "Messy"


class NoiseTolerance(str, Enum):
    QUIET = "Quiet"
    MODERATE = "Moderate"
    LOUD_OK = "Loud ok"


class StudyHabits(str, Enum):
    ONLINE_CLASSES = "Online classes"
    LATE_NIGHT = "Late-night study"
    ROOM_STUDY = "Room study"
    LIBRARY = "Library"


class FoodPref(str, Enum):
    FLEXIBLE = "Flexible"
    NON_VEG = "Non-veg"
    VEG = "Veg"


class Profile(BaseModel):
    id: Optional[str] = Field(alias="_id")
    raw_profile_text: Optional[str] = None
    city: str
    area: str
    budget_PKR: int

    sleep_schedule: SleepSchedule
    cleanliness: Cleanliness
    noise_tolerance: NoiseTolerance
    study_habits: StudyHabits
    food_pref: FoodPref

    # For AI agents (not user-facing input)
    context_notes: Optional[str] = None

    class Config:
        populate_by_name = True
        use_enum_values = True  # store enum values directly in MongoDB


class ProfileCreate(BaseModel):
    raw_profile_text: Optional[str] = None
    city: str
    area: str
    budget_PKR: int

    sleep_schedule: SleepSchedule
    cleanliness: Cleanliness
    noise_tolerance: NoiseTolerance
    study_habits: StudyHabits
    food_pref: FoodPref