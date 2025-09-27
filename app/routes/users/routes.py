from fastapi import APIRouter, HTTPException, Path, Depends, Response
from models.user import UserCreate
from routes.users.users_response_schemas import UserResponse, LoginRequest, LoginResponse
from utils.jwt_utils import create_access_token, get_user_from_cookie
from db.mongo import get_users_collection
from passlib.context import CryptContext
from bson import ObjectId
from typing import List
import bcrypt
from fastapi.security import OAuth2PasswordRequestForm
import os

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

router = APIRouter(prefix="/users", tags=["Users"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register", response_model=UserResponse)
def register_user(request: UserCreate):
    users_collection = get_users_collection()
    if users_collection.find_one({"username": request.username}):
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = bcrypt.hashpw(request.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = UserCreate(
        username=request.username,
        password=hashed_password,
        listing_id=request.listing_id,
        profile_id=request.profile_id,
    )
    result = users_collection.insert_one(user.dict(by_alias=True))
    db_user = users_collection.find_one({"_id": result.inserted_id})

    token = create_access_token(
        str(db_user["_id"]),
        db_user["username"],
        db_user.get("listing_id"),
        db_user.get("profile_id"),
    )
    users_collection.update_one({"_id": result.inserted_id}, {"$set": {"token": token}})

    return UserResponse(
        id=str(db_user["_id"]),
        username=db_user["username"],
        listing_id=db_user.get("listing_id"),
        profile_id=db_user.get("profile_id"),
    )


@router.post("/register-user")
def register_user_public(username: str, password: str, listing_id: str = None, profile_id: str = None):
    users_collection = get_users_collection()
    if users_collection.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = {
        "_id": ObjectId(),
        "username": username,
        "password": hashed_password,
        "listing_id": listing_id,
        "profile_id": profile_id,
    }
    users_collection.insert_one(user)
    return {"message": "User registered successfully"}


@router.post("/login", response_model=LoginResponse)
def login_user(request: LoginRequest, response: Response):
    users_collection = get_users_collection()
    user_data = users_collection.find_one({"username": request.username})
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not bcrypt.checkpw(request.password.encode("utf-8"), user_data["password"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(
        str(user_data["_id"]),
        user_data["username"],
        user_data.get("listing_id"),
        user_data.get("profile_id"),
    )
    users_collection.update_one({"_id": user_data["_id"]}, {"$set": {"token": token}})

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=False,
        secure=False,   # Set True if HTTPS
        samesite="lax"  # Or 'none' if cross-site
    )

    return LoginResponse(
        id=str(user_data["_id"]),
        username=user_data["username"],
        token=token,
        listing_id=user_data.get("listing_id"),
        profile_id=user_data.get("profile_id"),
    )


@router.post("/token")
def login_token(form_data: OAuth2PasswordRequestForm = Depends()):
    users_collection = get_users_collection()
    user_data = users_collection.find_one({"username": form_data.username})
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not bcrypt.checkpw(form_data.password.encode("utf-8"), user_data["password"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(
        str(user_data["_id"]),
        user_data["username"],
        user_data.get("listing_id"),
        user_data.get("profile_id"),
    )
    users_collection.update_one({"_id": user_data["_id"]}, {"$set": {"token": token}})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout_user(response: Response, current_user: UserResponse = Depends(get_user_from_cookie)):
    users_collection = get_users_collection()
    result = users_collection.update_one({"_id": ObjectId(current_user.id)}, {"$unset": {"token": ""}})
    response.delete_cookie("access_token")
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found or already logged out")
    return {"message": "Successfully logged out"}


@router.get("/all", response_model=List[UserResponse])
def get_all_users():
    users_collection = get_users_collection()
    users = users_collection.find()
    return [
        UserResponse(
            id=str(user["_id"]),
            username=user["username"],
            listing_id=user.get("listing_id"),
            profile_id=user.get("profile_id"),
        )
        for user in users
    ]


@router.delete("/{user_id}")
def delete_user(user_id: str = Path(..., description="The ID of the user to delete")):
    users_collection = get_users_collection()
    try:
        obj_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    result = users_collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"detail": "User deleted successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: UserResponse = Depends(get_user_from_cookie)):
    return current_user


@router.patch("/{user_id}")
def update_user(user_id: str, update: dict):
    users_collection = get_users_collection()
    try:
        obj_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    update_fields = {}
    if "username" in update:
        update_fields["username"] = update["username"]
    if "password" in update and update["password"]:
        update_fields["password"] = bcrypt.hashpw(update["password"].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    if "listing_id" in update:
        update_fields["listing_id"] = update["listing_id"]
    if "profile_id" in update:
        update_fields["profile_id"] = update["profile_id"]

    if not update_fields:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    result = users_collection.update_one({"_id": obj_id}, {"$set": update_fields})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"detail": "User updated successfully"}