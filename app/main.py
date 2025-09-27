from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import os

load_dotenv()

app = FastAPI(
    title="FlatWalay API",
    description="API for FlatWalay project.",
    version="1.0.0",
    openapi_tags=[
        {"name": "Auth", "description": "Authentication related endpoints"},
        {"name": "Match", "description": "Roommate matching endpoints"},
        {"name": "Housing", "description": "Housing matching endpoints"},
    ],
    openapi_security=[{
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }]
)

# ------------------ CORS ------------------
origins = [
    "http://localhost:9002",  # Frontend origin
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# ------------------ MongoDB Check ------------------
from db.mongo import check_connection

@app.on_event("startup")
def startup_db_check():
    if check_connection():
        print("✅ MongoDB connected successfully")
    else:
        print("❌ Failed to connect to MongoDB")

# ------------------ Routers ------------------
from routes.users.routes import router as users_router
from routes.profiles.routes import router as profiles_router
from routes.parse_profile.routes import router as parse_router
from routes.match_scorer.routes import router as match_router
from routes.red_flag.route import router as flag_router
from routes.room_hunt.routes import router as room_hunter_router  
from routes.wingman.routes import router as wingman_router

# Include routers
app.include_router(users_router)
app.include_router(profiles_router)
app.include_router(parse_router)
app.include_router(match_router)
app.include_router(flag_router)
app.include_router(room_hunter_router)  # NEW: Housing matches
app.include_router(wingman_router)