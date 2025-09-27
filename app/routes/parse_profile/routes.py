from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from utils.jwt_utils import get_user_from_cookie
from routes.users.users_response_schemas import UserResponse
from models.profile import ProfileCreate
from agents.profile_reader_agent import  profile_reader

router = APIRouter(prefix="/ai", tags=["AI Profile Reader"])

class ParseProfileRequest(BaseModel):
    raw_profile_text: str

@router.post("/parse-profile", response_model=ProfileCreate)
def parse_profile(
    request: ParseProfileRequest,
    current_user: UserResponse = Depends(get_user_from_cookie)
):
    """
    Parse raw ad text into structured roommate profile categories.
    Does NOT save to MongoDB.
    """
    try:
        parsed = profile_reader.parse_profile(request.raw_profile_text)
        return ProfileCreate(**parsed)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
