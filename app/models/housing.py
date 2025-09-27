from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class Amenity(str, Enum):
    SECURITY_GUARD = "Security guard"
    PARKING = "Parking"
    FURNISHED = "Furnished"
    MESS_FACILITY = "Mess facility"
    SEPARATE_WASHROOM = "Separate washroom"
    ATTACHED_BATHROOM = "Attached bathroom"
    LAUNDRY_SERVICE = "Laundry service"
    ELECTRICITY_BACKUP = "Electricity backup"
    WATER_SUPPLY = "Water supply"
    AC_ROOM = "AC room"
    SHARED_KITCHEN = "Shared kitchen"
    NEARBY_BUS_STOP = "Nearby bus stop"


class HousingBase(BaseModel):
    city: str
    area: str
    monthly_rent_PKR: int = Field(..., description="Monthly rent in Pakistani Rupees")
    rooms_available: int = Field(..., description="Number of rooms available")
    availability: str = Field("Available", description="Available / Not Available")
    amenities: Optional[List[Amenity]] = Field(default_factory=list, description="List of amenities provided")
    latitude: Optional[float] = Field(None, description="Latitude coordinate for maps")
    longitude: Optional[float] = Field(None, description="Longitude coordinate for maps")


class HousingCreate(HousingBase):
    """Schema for creating a new housing listing"""
    pass


class HousingUpdate(BaseModel):
    """Schema for updating an existing housing listing (all fields optional)"""
    city: Optional[str] = None
    area: Optional[str] = None
    monthly_rent_PKR: Optional[int] = None
    rooms_available: Optional[int] = None
    availability: Optional[str] = None
    amenities: Optional[List[Amenity]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class Housing(HousingBase):
    """Schema returned in responses, including MongoDB _id"""
    id: Optional[str] = Field(alias="_id")

    class Config:
        populate_by_name = True
        orm_mode = True