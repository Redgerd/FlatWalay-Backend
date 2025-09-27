# routes/ai/room_hunter_route.py
from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any
from agents.room_hunter_agent import room_hunter_agent, HousingMatch

router = APIRouter(prefix="/ai", tags=["Housing"])

@router.post("/top_housing_matches", response_model=List[HousingMatch])
def top_housing_matches_route(
    profiles: List[Dict[str, Any]] = Body(...),
    top_n: int = 2
):
    """
    Return top N housing listings for given student profiles with reasons.
    """
    if not profiles or len(profiles) == 0:
        raise HTTPException(status_code=400, detail="No profiles provided")

    try:
        matches = room_hunter_agent.get_top_housing_matches(profiles, top_n=top_n)
        if not matches:
            return []
        return matches
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing housing matches: {e}")
