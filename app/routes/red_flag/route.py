from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from utils.jwt_utils import get_user_from_cookie
from routes.users.users_response_schemas import UserResponse
from agents.red_flag_agent import red_flag_agent

router = APIRouter(prefix="/ai", tags=["AI Red Flag Detector"])

@router.post("/detect-conflicts")
def detect_conflicts(
    profile_a: Dict[str, Any],
    profile_b: Dict[str, Any],
    current_user: UserResponse = Depends(get_user_from_cookie)
):
    if not red_flag_agent:
        raise HTTPException(status_code=500, detail="RedFlagAgent not initialized. Check GROQ_API_KEY.")
    
    try:
        result = red_flag_agent.detect_conflicts(profile_a, profile_b)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
