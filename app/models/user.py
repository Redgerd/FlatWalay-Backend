from pydantic import BaseModel, Field
from typing import Optional, List

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

class UserLikes(BaseModel):
    user_id: str             
    liked_profile_ids: List[str] = []  

class UserCreate(BaseModel):
    username: str
    password: str
    profile_id: Optional[str] = None
    listing_id: Optional[str] = None
    email:str
    is_verified: Optional[bool] = False