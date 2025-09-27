from pydantic import BaseModel, Field
from typing import List, Optional


class HousingBase(BaseModel):
    city: str
    area: str
    monthly_rent: int = Field(..., description="Monthly rent in PKR")
    rooms_available: int = Field(..., description="Number of rooms available")
    amenities: Optional[List[str]] = []
    availability: str = Field("Available", description="Available / Not Available")
    latitude: Optional[float] = Field(None, description="Latitude coordinate for maps")
    longitude: Optional[float] = Field(None, description="Longitude coordinate for maps")


class HousingCreate(HousingBase):
    pass


class HousingUpdate(BaseModel):
    city: Optional[str] = None
    area: Optional[str] = None
    monthly_rent: Optional[int] = None
    rooms_available: Optional[int] = None
    amenities: Optional[List[str]] = None
    availability: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class Housing(HousingBase):
    id: Optional[str] = Field(alias="_id")

    class Config:
        populate_by_name = True
        orm_mode = True