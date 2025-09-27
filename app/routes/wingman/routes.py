from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Dict, Any, List
from utils.jwt_utils import get_user_from_cookie
from routes.users.users_response_schemas import UserResponse
from agents.wingman_agent import match_explainer_agent

router = APIRouter(prefix="/ai", tags=["AI Match Explainer"])

@router.post("/generate-explanation")
def generate_explanation(
    request: Dict[str, Any] = Body(...),
    current_user: UserResponse = Depends(get_user_from_cookie)
):
    if not match_explainer_agent:
        raise HTTPException(status_code=500, detail="MatchExplainerAgent not initialized. Check GROQ_API_KEY.")
    
    try:
        match_score = request.get("match_score")
        match_reasons = request.get("match_reasons", [])
        red_flags = request.get("red_flags", [])

        result = match_explainer_agent.generate_explanation(
            match_score=match_score,
            match_reasons=match_reasons,
            red_flags=red_flags
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
