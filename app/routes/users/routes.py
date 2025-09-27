from fastapi import APIRouter, HTTPException, Path, Depends, Response, Query, status
from models.user import UserCreate
from routes.users.users_response_schemas import UserResponse, LoginRequest, LoginResponse, EmailRequest, GoogleAuthSchema, UserLikes
from utils.jwt_utils import create_access_token, get_user_from_cookie
from db.mongo import get_users_collection, get_user_likes_collection
from passlib.context import CryptContext
from bson import ObjectId
from typing import List
import bcrypt
from fastapi.security import OAuth2PasswordRequestForm
import os
import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from fastapi.security import OAuth2PasswordRequestForm

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

router = APIRouter(prefix="/users", tags=["Users"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "fwala442@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "mxgc zjbv agtj ksam")
GOOGLE_CLIENT_ID=os.getenv("GOOGLE_CLIENT_ID")

@router.post("/register", response_model=UserResponse)
def register_user(request: UserCreate):
    users_collection = get_users_collection()

    # Check duplicate username
    if users_collection.find_one({"username": request.username}):
        raise HTTPException(status_code=400, detail="Username already exists")

    # Hash password
    hashed_password = bcrypt.hashpw(
        request.password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    # Create user object
    user = UserCreate(
        username=request.username,
        password=hashed_password,
        email=request.email,   # ✅ make sure UserCreate has this
        listing_id="",
        profile_id="",
        is_verified=False
    )

    # Insert user
    result = users_collection.insert_one(user.dict(by_alias=True))
    db_user = users_collection.find_one({"_id": result.inserted_id})

    # Create verification token (simple random string, not JWT)
    verification_token = secrets.token_urlsafe(32)

    # Update DB with verification token
    users_collection.update_one(
        {"_id": result.inserted_id}, {"$set": {"verification_token": verification_token, "is_verified": False}}
    )

    # Send verification email
    email_request = EmailRequest(email=db_user["email"], token=verification_token)
    send_verification_email(email_request)

    return UserResponse(
        id=str(db_user["_id"]),
        username=db_user["username"],
        listing_id=db_user.get("listing_id"),
        profile_id=db_user.get("profile_id"),
        email=db_user["email"]
    )


def send_verification_email(request: EmailRequest):
    users = get_users_collection()

    # ✅ Save token in DB
    users.update_one(
        {"email": request.email},
        {"$set": {"verification_token": request.token}}
    )

    try:
        sender = EMAIL_ADDRESS
        receiver = request.email
        password = EMAIL_PASSWORD

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = receiver
        msg["Subject"] = "Verify your email"

        verification_link = f"http://localhost:9002/verify-email?token={request.token}&email={receiver}"
        body = f"Click here to verify your email: {verification_link}"

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())

        return {"status": "success", "message": f"Verification email sent to {receiver}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/verify")
def verify_email(token: str = Query(...), email: str = Query(...)):
    users = get_users_collection()
    
    print(f"Verification attempt: email={email}, token={token}")
    
    # First, check if user exists by email
    user = users.find_one({"email": email})
    if not user:
        print(f"User not found for email: {email}")
        raise HTTPException(status_code=400, detail="User not found")
    
    print(f"User found: {user.get('username')}, verification_token: {user.get('verification_token')}")
    
    # Check if user has verification_token and if it matches
    if not user.get("verification_token"):
        print(f"No verification_token found for user: {email}")
        # If user is already verified, just return success
        if user.get("is_verified"):
            print(f"User {email} is already verified")
            return {"status": "success", "message": "Email already verified!"}
        else:
            raise HTTPException(status_code=400, detail="No verification token found. Please request a new verification email.")
    
    if user.get("verification_token") != token:
        print(f"Token mismatch for user: {email}")
        raise HTTPException(status_code=400, detail="Invalid verification token")
    
    # ✅ Mark verified
    users.update_one(
        {"email": email},
        {"$set": {"is_verified": True}, "$unset": {"verification_token": ""}}
    )
    
    # ✅ Create new JWT token with updated verification status
    new_token = create_access_token(
        str(user["_id"]),
        user["username"],
        user["email"],
        user.get("listing_id"),
        user.get("profile_id"),
        True  # Now verified
    )
    
    # ✅ Update user with new JWT token
    users.update_one(
        {"email": email},
        {"$set": {"token": new_token}}
    )

    print(f"Email verification successful for: {email}")
    return {"status": "success", "message": "Email verified successfully!", "access_token": new_token}

@router.post("/resend-verification")
def resend_verification_email(email: str):
    users = get_users_collection()
    
    user = users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("is_verified"):
        return {"message": "Email already verified"}
    
    # Generate new verification token
    verification_token = secrets.token_urlsafe(32)
    
    # Update user with new verification token
    users.update_one(
        {"email": email},
        {"$set": {"verification_token": verification_token}}
    )
    
    # Send verification email
    email_request = EmailRequest(email=email, token=verification_token)
    send_verification_email(email_request)
    
    return {"message": "Verification email sent successfully"}

@router.get("/check-verification/{email}")
def check_verification_status(email: str):
    users = get_users_collection()
    
    user = users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "email": email,
        "is_verified": user.get("is_verified", False),
        "has_verification_token": bool(user.get("verification_token")),
        "username": user.get("username")
    }

@router.post("/register-user")
def register_user_public(username: str, password: str, listing_id: str = None, profile_id: str = None, email: str = None):
    users_collection = get_users_collection()
    if users_collection.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = {
        "_id": ObjectId(),
        "username": username,
        "password": hashed_password,
        "email": email,
        "listing_id": listing_id,
        "profile_id": profile_id,
    }
    users_collection.insert_one(user)
    return {"message": "User registered successfully"}


@router.post("/login", response_model=LoginResponse)
def login_user(request: LoginRequest, response: Response):
    users_collection = get_users_collection()

    # 🔑 Look up by email instead of username
    user_data = users_collection.find_one({"email": request.email})
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # ✅ Check password
    if not bcrypt.checkpw(request.password.encode("utf-8"), user_data["password"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # ✅ Create access token
    token = create_access_token(
        str(user_data["_id"]),
        user_data["username"],
        user_data["email"],
        user_data.get("listing_id"),
        user_data.get("profile_id"),
        is_verified=user_data.get("is_verified", False)
    )

    # ✅ Save token in DB
    users_collection.update_one({"_id": user_data["_id"]}, {"$set": {"token": token}})

    # ✅ Set cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=False,
        secure=False,   # Set True if HTTPS
        samesite="lax"  # Or "none" if cross-site
    )

    # ✅ Return response
    return LoginResponse(
        id=str(user_data["_id"]),
        username=user_data["username"],
        email=user_data["email"],
        token=token,
        listing_id=user_data.get("listing_id"),
        profile_id=user_data.get("profile_id"),
        is_verified=user_data.get("is_verified", False),
    )


@router.post("/token")
def login_token(form_data: OAuth2PasswordRequestForm = Depends()):
    users_collection = get_users_collection()
    # Try to find user by email first, then by username for backward compatibility
    user_data = users_collection.find_one({"email": form_data.username}) or users_collection.find_one({"username": form_data.username})
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid email/username or password")

    if not bcrypt.checkpw(form_data.password.encode("utf-8"), user_data["password"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid email/username or password")

    token = create_access_token(
        str(user_data["_id"]),
        user_data["username"],
        user_data.get("email"),
        user_data.get("listing_id"),
        user_data.get("profile_id"),
        user_data.get("is_verified", False),
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
    return [UserResponse(**{**user, "id": str(user["_id"])}) for user in users]


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


@router.post("/google")
def google_login(payload: GoogleAuthSchema, response: Response):
    users_collection = get_users_collection()

    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google auth not configured"
        )

    # ✅ Verify Google token
    try:
        idinfo = google_id_token.verify_oauth2_token(
            payload.id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token"
        )

    email = idinfo.get("email")
    name = idinfo.get("name") or (email.split("@")[0] if email else None)

    if not email or not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token missing required claims"
        )

    # ✅ Check if user exists in Mongo
    user = users_collection.find_one({"email": email})

    if not user:
        # Create new user in Mongo
        new_user = {
            "username": name,
            "email": email,
            "password": "",        # since Google login skips password
            "is_verified": True,   # Google emails are already verified
            "listing_id": None,
            "profile_id": None,
        }
        result = users_collection.insert_one(new_user)
        user = users_collection.find_one({"_id": result.inserted_id})

    # ✅ Generate token
    token = create_access_token(
        str(user["_id"]),
        user["username"],
        user["email"],
        user.get("listing_id"),
        user.get("profile_id"),
        user.get("is_verified", True)  # Google users are automatically verified
    )

    # Update user with token in database
    users_collection.update_one({"_id": user["_id"]}, {"$set": {"token": token}})

    # Set cookie for authentication
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=False,
        secure=False,   # Set True if HTTPS
        samesite="lax"  # Or 'none' if cross-site
    )

    return {"access_token": token, "token_type": "bearer"}


@router.post("/like-profile/{profile_id}")
def like_profile(profile_id: str, current_user: UserResponse = Depends(get_user_from_cookie)):
    """Add a profile to the user's liked list"""
    collection = get_user_likes_collection()

    user_likes = collection.find_one({"user_id": current_user.id})
    if user_likes:
        if profile_id in user_likes.get("liked_profile_ids", []):
            return {"message": "Profile already liked"}
        collection.update_one({"user_id": current_user.id}, {"$push": {"liked_profile_ids": profile_id}})
    else:
        collection.insert_one({"user_id": current_user.id, "liked_profile_ids": [profile_id]})

    return {"message": f"Profile {profile_id} liked successfully"}

@router.post("/unlike-profile/{profile_id}")
def unlike_profile(profile_id: str, current_user: UserResponse = Depends(get_user_from_cookie)):
    """Remove a profile from the user's liked list"""
    collection = get_user_likes_collection()
    collection.update_one({"user_id": current_user.id}, {"$pull": {"liked_profile_ids": profile_id}})
    return {"message": f"Profile {profile_id} unliked successfully"}

@router.get("/liked-profiles", response_model=List[str])
def get_liked_profiles(current_user: UserResponse = Depends(get_user_from_cookie)):
    """Get all profiles liked by the current user"""
    collection = get_user_likes_collection()
    user_likes = collection.find_one({"user_id": current_user.id})
    return user_likes.get("liked_profile_ids", []) if user_likes else []