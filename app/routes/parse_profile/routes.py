from fastapi import APIRouter, HTTPException, Depends
from utils.jwt_utils import get_user_from_cookie
from routes.users.users_response_schemas import UserResponse
from models.profile import ProfileCreate
from agent.profile_reader_agent import agent_instance  # ✅ Reuse the global agent

router = APIRouter(prefix="/ai", tags=["AI Profile Reader"])

@router.post("/parse-profile", response_model=ProfileCreate)
def parse_profile(
    raw_profile_text: str,
    current_user: UserResponse = Depends(get_user_from_cookie)
):
    """
    Parse raw ad text into structured roommate profile categories.
    Does NOT save to MongoDB.
    """
    try:
        parsed = agent_instance.parse_profile(raw_profile_text)
        return ProfileCreate(**parsed)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
