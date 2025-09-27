from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError
from datetime import datetime, timedelta
import os
from fastapi import HTTPException, status, Depends, Cookie
from fastapi.security import OAuth2PasswordBearer
from routes.users.users_response_schemas import UserResponse

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/token")


def create_access_token(user_id: str, username: str, email: str = None, listing_id: str = None, profile_id: str = None, is_verified: bool = False, expires_delta: timedelta = None) -> str:
    payload = {
        "sub": username,
        "id": user_id,
        "email": email,
        "listing_id": listing_id,
        "profile_id": profile_id,
        "is_verified": is_verified,
    }

    # Only add expiration if explicitly requested
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
        payload["exp"] = expire

    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Dependency to get user from cookie
def get_user_from_cookie(access_token: str = Cookie(None)):
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("id")
        email: str = payload.get("email")
        listing_id = payload.get("listing_id")
        profile_id = payload.get("profile_id")
        is_verified = payload.get("is_verified", False)

        if username is None or user_id is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
        return UserResponse(
            id=user_id, 
            username=username, 
            email=email,
            listing_id=listing_id, 
            profile_id=profile_id,
            is_verified=is_verified
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")