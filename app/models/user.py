from pydantic import BaseModel, Field
from typing import Optional

class User(BaseModel):
    id: Optional[str] = Field(alias="_id")
    username: str
    password: str
    token: Optional[str] = None
    role: str
    department: Optional[str] = None  

    class Config:
        validate_by_name = True
        arbitrary_types_allowed = True