from pydantic import BaseModel
from typing import Optional
from pydantic import BaseModel, EmailStr

class UserResponse(BaseModel):
    id: Optional[str]
    username: Optional[str]
    listing_id: Optional[str] = None
    profile_id: Optional[str] = None
    email: Optional[str] = None
    is_verified: Optional[bool] = False

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    id: str
    username: str
    email: str
    token: str
    listing_id: Optional[str] = None
    profile_id: Optional[str] = None
    is_verified: Optional[bool] = False


class RegisterRequest(BaseModel):
    username: str
    password: str
    listing_id: Optional[str] = None
    profile_id: Optional[str] = None


class EmailRequest(BaseModel):
    email: EmailStr
    token: str

class GoogleAuthSchema(BaseModel):
    """Schema for Google OAuth ID token exchange"""
    id_token: str