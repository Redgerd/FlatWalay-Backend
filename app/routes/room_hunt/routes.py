# routes/ai/room_hunter_route.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from bson import ObjectId

from db.mongo import get_profiles_collection
from utils.jwt_utils import get_user_from_cookie
from routes.users.users_response_schemas import UserResponse
from agents.room_hunter_agent import room_hunter_agent, HousingMatch

router = APIRouter(prefix="/ai", tags=["Housing"])


@router.post("/top_housing_matches", response_model=List[HousingMatch])
def top_housing_matches_route(
    profile_a: Dict[str, Any],
    profile_b: Dict[str, Any],
    current_user: UserResponse = Depends(get_user_from_cookie),
    top_n: int = 10
):
    """
    Return top N housing listings for two given student profiles with reasons.
    """
    if not room_hunter_agent:
        raise HTTPException(status_code=500, detail="RoomHunterAgent not initialized.")

    try:
        # If profile_a and profile_b are just IDs, fetch from DB
        profiles_collection = get_profiles_collection()
        for profile in [profile_a, profile_b]:
            if "id" in profile and not all(k in profile for k in ["city", "area", "budget_PKR"]):
                db_profile = profiles_collection.find_one({"_id": ObjectId(profile["id"])})
                if not db_profile:
                    raise HTTPException(status_code=404, detail=f"Profile {profile['id']} not found")
                profile.update({
                    "city": db_profile.get("city"),
                    "area": db_profile.get("area"),
                    "budget_PKR": db_profile.get("budget_PKR"),
                    "sleep_schedule": db_profile.get("sleep_schedule"),
                    "cleanliness": db_profile.get("cleanliness"),
                    "noise_tolerance": db_profile.get("noise_tolerance"),
                    "study_habits": db_profile.get("study_habits"),
                    "food_pref": db_profile.get("food_pref"),
                })

        # Get top housing matches
        matches = room_hunter_agent.get_top_housing_matches([profile_a, profile_b], top_n=top_n)
        return matches or []

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing housing matches: {e}")