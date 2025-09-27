from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

import os

load_dotenv()

app = FastAPI(
    title="FlatWalay API",
    description="API for FlatWalay project.",
    version="1.0.0",
    openapi_tags=[{"name": "Auth", "description": "Authentication related endpoints"}],
    openapi_security=[{
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }]
)

origins = [
    "http://localhost:9002",  
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

from db.mongo import check_connection

@app.on_event("startup")
def startup_db_check():
    if check_connection():
        print("✅ MongoDB connected successfully")
    else:
        print("❌ Failed to connect to MongoDB")

# Import and include users router
from routes.users.routes import router as users_router
from routes.profiles.routes import router as profiles_router
from routes.parse_profile.routes import router as parse_router
from routes.match_scorer.routes import router as match_router  
from routes.red_flag.route import router as flag_router

app.include_router(users_router)
app.include_router(profiles_router)
app.include_router(parse_router)
app.include_router(match_router)
app.include_router(flag_router)