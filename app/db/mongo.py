from pymongo import MongoClient
import gridfs
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "roommate_finder")

# Create global client
client = MongoClient(MONGO_URI)

# Database reference
db = client[DB_NAME]

# GridFS for file uploads (optional)
fs = gridfs.GridFS(db)


# ----- Collection helpers -----
def get_users_collection():
    return db["users"]

def get_housing_collection():
    return db["housing"]

def get_profiles_collection():
    return db["profiles"]

def check_connection():
    """Check if MongoDB connection works"""
    try:
        client.admin.command("ping")
        return True
    except Exception as e:
        print("❌ MongoDB connection failed:", e)
        return False