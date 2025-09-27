from pydantic import BaseModel, Field
from typing import Optional


class User(BaseModel):
    id: Optional[str] = Field(alias="_id")
    username: str
    password: str
    token: Optional[str] = None
    is_verified: bool = False   # ✅ Boolean instead of string
    profile_id: str
    listing_id: str

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class UserCreate(BaseModel):
    username: str
    password: str
    profile_id: str
    listing_id: str
    email:str

