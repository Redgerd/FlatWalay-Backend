from pydantic import BaseModel, Field
from typing import List, Optional

# --- Base schema for common housing fields ---
class HousingBase(BaseModel):
    city: str
    area: str
    monthly_rent_PKR: int = Field(..., description="Monthly rent in Pakistani Rupees")
    rooms_available: int = Field(..., description="Number of rooms available")
    availability: str = Field("Available", description="Available / Not Available")
    amenities: Optional[List[str]] = Field(default_factory=list, description="List of amenities provided")
    latitude: Optional[float] = Field(None, description="Latitude coordinate for maps")
    longitude: Optional[float] = Field(None, description="Longitude coordinate for maps")


# --- Schema for creating a new housing listing ---
class HousingCreate(HousingBase):
    """Schema for creating a new housing listing"""
    pass


# --- Schema for updating an existing housing listing ---
class HousingUpdate(BaseModel):
    """Schema for updating an existing housing listing (all fields optional)"""
    city: Optional[str] = None
    area: Optional[str] = None
    monthly_rent_PKR: Optional[int] = None
    rooms_available: Optional[int] = None
    availability: Optional[str] = None
    amenities: Optional[List[str]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


# --- Schema returned in responses (including RoomHunter short_reason) ---
class Housing(HousingBase):
    id: Optional[str] = Field(alias="_id", description="MongoDB ObjectId as string")
    short_reason: Optional[str] = Field(None, description="Concise explanation why this listing matches the profile")

    class Config:
        populate_by_name = True
        orm_mode = True
