from pydantic import BaseModel
from typing import Optional

class UserResponse(BaseModel):
    id: Optional[str]
    username: str
    listing_id: Optional[str] = None
    profile_id: Optional[str] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    id: str
    username: str
    token: str
    listing_id: Optional[str] = None
    profile_id: Optional[str] = None


class RegisterRequest(BaseModel):
    username: str
    password: str
    listing_id: Optional[str] = None
    profile_id: Optional[str] = None
