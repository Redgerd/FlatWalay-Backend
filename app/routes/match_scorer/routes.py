from fastapi import APIRouter, Depends, HTTPException
from utils.jwt_utils import get_user_from_cookie
from db.mongo import get_profiles_collection, get_users_collection
from bson import ObjectId
from agents.match_scorer_agent import match_scorer_agent, MatchResult
from routes.profiles.profiles_response_schemas import ProfileResponse
from routes.users.users_response_schemas import UserResponse
from typing import List

router = APIRouter(prefix="/ai", tags=["Match"])

@router.get("/best_matches", response_model=List[MatchResult])
def best_matches_route(
    current_user: UserResponse = Depends(get_user_from_cookie),
    top_n: int = 5
):
    """
    Get top N best matching roommate profiles for the logged-in user.
    """
    if not match_scorer_agent:
        raise HTTPException(status_code=503, detail="Match scorer agent not initialized")

    users_collection = get_users_collection()
    profiles_collection = get_profiles_collection()

    # Fetch user document
    try:
        user_doc = users_collection.find_one({"_id": ObjectId(current_user.id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    profile_id = user_doc.get("profile_id")
    if not profile_id:
        raise HTTPException(status_code=404, detail="No profile assigned to this user")

    # Fetch user's profile
    try:
        profile_doc = profiles_collection.find_one({"_id": ObjectId(profile_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid profile ID in user document")

    if not profile_doc:
        raise HTTPException(status_code=404, detail="User profile not found")

    user_profile = ProfileResponse(
        id=str(profile_doc["_id"]),
        raw_profile_text=profile_doc["raw_profile_text"],
        city=profile_doc["city"],
        area=profile_doc["area"],
        budget_PKR=profile_doc["budget_PKR"],
        sleep_schedule=profile_doc.get("sleep_schedule"),
        cleanliness=profile_doc.get("cleanliness"),
        noise_tolerance=profile_doc.get("noise_tolerance"),
        study_habits=profile_doc.get("study_habits"),
        food_pref=profile_doc.get("food_pref"),
    )

    # Get best matches using the agent
    best_matches = match_scorer_agent.get_best_matches(user_profile, top_n=top_n)
    return best_matches