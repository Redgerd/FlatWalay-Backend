from fastapi import APIRouter, HTTPException, Path, Depends
from models.profile import ProfileCreate
from routes.profiles.profiles_response_schemas import ProfileResponse
from db.mongo import get_profiles_collection, get_users_collection
from bson import ObjectId
from typing import List
from utils.jwt_utils import get_user_from_cookie
from routes.users.users_response_schemas import UserResponse

router = APIRouter(prefix="/profiles", tags=["Profiles"])


# --- Create Profile ---
@router.post("/", response_model=ProfileResponse)
def create_profile(
    request: ProfileCreate,
    current_user: UserResponse = Depends(get_user_from_cookie)
):
    profiles_collection = get_profiles_collection()
    users_collection = get_users_collection()

    # Check if user already has a profile
    user_doc = users_collection.find_one({"_id": ObjectId(current_user.id)})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    if user_doc.get("profile_id"):
        raise HTTPException(status_code=400, detail="User already has a profile")

    # Insert the new profile
    result = profiles_collection.insert_one(request.dict())
    db_profile = profiles_collection.find_one({"_id": result.inserted_id})

    # Update the user's profile_id in the users collection
    update_result = users_collection.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": {"profile_id": str(result.inserted_id)}}
    )
    if update_result.matched_count == 0:
        # Rollback: delete the profile if user update fails
        profiles_collection.delete_one({"_id": result.inserted_id})
        raise HTTPException(status_code=500, detail="Failed to assign profile to user")

    # Return the created profile
    return ProfileResponse(
        id=str(db_profile["_id"]),
        raw_profile_text=db_profile["raw_profile_text"],
        city=db_profile["city"],
        area=db_profile["area"],
        budget_PKR=db_profile["budget_PKR"],
        sleep_schedule=db_profile.get("sleep_schedule"),
        cleanliness=db_profile.get("cleanliness"),
        noise_tolerance=db_profile.get("noise_tolerance"),
        study_habits=db_profile.get("study_habits"),
        food_pref=db_profile.get("food_pref"),
    )


# --- Get All Profiles ---
@router.get("/", response_model=List[ProfileResponse])
def get_profiles(current_user: UserResponse = Depends(get_user_from_cookie)):
    profiles_collection = get_profiles_collection()
    profiles = profiles_collection.find()
    return [
        ProfileResponse(
            id=str(profile["_id"]),
            raw_profile_text=profile["raw_profile_text"],
            city=profile["city"],
            area=profile["area"],
            budget_PKR=profile["budget_PKR"],
            sleep_schedule=profile.get("sleep_schedule"),
            cleanliness=profile.get("cleanliness"),
            noise_tolerance=profile.get("noise_tolerance"),
            study_habits=profile.get("study_habits"),
            food_pref=profile.get("food_pref"),
        )
        for profile in profiles
    ]


# --- Get Profile by ID ---
@router.get("/{profile_id}", response_model=ProfileResponse)
def get_profile(profile_id: str = Path(..., description="Profile ID"), current_user: UserResponse = Depends(get_user_from_cookie)):
    profiles_collection = get_profiles_collection()
    try:
        obj_id = ObjectId(profile_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid profile ID format")

    profile = profiles_collection.find_one({"_id": obj_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return ProfileResponse(
        id=str(profile["_id"]),
        raw_profile_text=profile["raw_profile_text"],
        city=profile["city"],
        area=profile["area"],
        budget_PKR=profile["budget_PKR"],
        sleep_schedule=profile.get("sleep_schedule"),
        cleanliness=profile.get("cleanliness"),
        noise_tolerance=profile.get("noise_tolerance"),
        study_habits=profile.get("study_habits"),
        food_pref=profile.get("food_pref"),
    )


# --- Delete Profile ---
@router.delete("/{profile_id}")
def delete_profile(profile_id: str = Path(..., description="Profile ID"), current_user: UserResponse = Depends(get_user_from_cookie)):
    profiles_collection = get_profiles_collection()
    try:
        obj_id = ObjectId(profile_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid profile ID format")

    result = profiles_collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"detail": "Profile deleted successfully"}


# --- Update Profile ---
@router.patch("/{profile_id}")
def update_profile(profile_id: str, update: dict, current_user: UserResponse = Depends(get_user_from_cookie)):
    profiles_collection = get_profiles_collection()
    try:
        obj_id = ObjectId(profile_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid profile ID format")

    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = profiles_collection.update_one({"_id": obj_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Profile not found")

    return {"detail": "Profile updated successfully"}