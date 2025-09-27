# routes/ai/room_hunter_route.py
from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any
from agents.room_hunter_agent import room_hunter_agent, HousingMatch
from db.mongo import get_profiles_collection, get_users_collection
from bson import ObjectId
router = APIRouter(prefix="/ai", tags=["Housing"])

@router.post("/top_housing_matches", response_model=List[HousingMatch])
def top_housing_matches_route(
    profile_id_1: str = Body(..., embed=True),
    profile_id_2: str = Body(..., embed=True),
    top_n: int = 2
):
    """
    Return top N housing listings for two given student profiles with reasons.
    """
    profiles_collection = get_profiles_collection()

    try:
        # Fetch both profiles from DB
        db_profile_1 = profiles_collection.find_one({"_id": ObjectId(profile_id_1)})
        db_profile_2 = profiles_collection.find_one({"_id": ObjectId(profile_id_2)})

        if not db_profile_1 or not db_profile_2:
            raise HTTPException(status_code=404, detail="One or both profiles not found")

        # Convert Mongo docs into dicts usable by the agent
        profiles = [
            {
                "id": str(db_profile_1["_id"]),
                "city": db_profile_1.get("city"),
                "area": db_profile_1.get("area"),
                "budget_PKR": db_profile_1.get("budget_PKR"),
                "sleep_schedule": db_profile_1.get("sleep_schedule"),
                "cleanliness": db_profile_1.get("cleanliness"),
                "noise_tolerance": db_profile_1.get("noise_tolerance"),
                "study_habits": db_profile_1.get("study_habits"),
                "food_pref": db_profile_1.get("food_pref"),
            },
            {
                "id": str(db_profile_2["_id"]),
                "city": db_profile_2.get("city"),
                "area": db_profile_2.get("area"),
                "budget_PKR": db_profile_2.get("budget_PKR"),
                "sleep_schedule": db_profile_2.get("sleep_schedule"),
                "cleanliness": db_profile_2.get("cleanliness"),
                "noise_tolerance": db_profile_2.get("noise_tolerance"),
                "study_habits": db_profile_2.get("study_habits"),
                "food_pref": db_profile_2.get("food_pref"),
            }
        ]

        # Get top housing matches
        matches = room_hunter_agent.get_top_housing_matches(profiles, top_n=top_n)
        return matches or []

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing housing matches: {e}")