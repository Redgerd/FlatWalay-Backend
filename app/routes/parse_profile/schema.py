from pydantic import BaseModel

class ParseProfileRequest(BaseModel):
    raw_profile_text: str