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
    "http://localhost:3000",  
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Import and include users router
from routes.users.routes import router as users_router

app.include_router(users_router)

@app.get("/")
def read_root():
    return {
        "mongo_url": "Hello",
        "secret_key": "Hello"
    }
