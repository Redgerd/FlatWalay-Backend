import json
from pymongo import MongoClient
from bson.objectid import ObjectId
import bcrypt
import os
import gridfs
from typing import List, Dict

MONGO_URI="mongodb+srv://xxhba777xx_db_user:8XIo2K60IwfJt3AC@flat-waley.cycp3kt.mongodb.net/"
DB_NAME="Flat-Waley"

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
# ----------------------------------------------------------------------
# END: MongoDB Configuration
# ----------------------------------------------------------------------


# --- Data Insertion Configuration ---
FILE_NAME = r"C:\Users\sa\Downloads\synthetic_roommate_profiles_pakistan_400.json"
DEFAULT_PASSWORD = "testpassword123"


def load_profiles(file_name: str) -> List[Dict]:
    """Loads profile data from the specified JSON file."""
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            profiles = json.load(f)
        print(f"✅ Successfully loaded {len(profiles)} profiles from {file_name}.")
        return profiles
    except FileNotFoundError:
        print(f"❌ Error: The file '{file_name}' was not found. Please check the path.")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Error: The file '{file_name}' contains invalid JSON data: {e}")
        return []


def create_user_and_profile_documents(profiles: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Processes profiles to create linked MongoDB documents.
    """
    user_documents = []
    profile_documents = []
    
    # Hash the password once outside the loop
    hashed_password_bytes = bcrypt.hashpw(DEFAULT_PASSWORD.encode("utf-8"), bcrypt.gensalt())
    hashed_password = hashed_password_bytes.decode("utf-8")

    print(f"Starting document creation and password hashing for {len(profiles)} records...")

    for profile in profiles:
        # 1. Generate unique IDs
        user_obj_id = ObjectId()
        profile_obj_id = ObjectId()
        username = f"user_{profile['id']}" # e.g., 'user_R-001'

        # 2. Create the Profile document
        profile_doc = {
            "_id": profile_obj_id, 
            **{k: v for k, v in profile.items() if k != 'id'}
        }
        # Ensure budget is an integer
        profile_doc['budget_PKR'] = int(profile_doc.get('budget_PKR', 0))

        # 3. Create the User document, linking the profile ID
        user_doc = {
            "_id": user_obj_id,
            "username": username,
            "password": hashed_password, 
            "listing_id": None, 
            # Note: The ID is stored as a string, matching your UserResponse schema
            "profile_id": str(profile_obj_id), 
        }

        user_documents.append(user_doc)
        profile_documents.append(profile_doc)
        
    print("✅ All user and profile documents created successfully.")
    return {
        "users": user_documents,
        "profiles": profile_documents
    }


def main():
    """Main execution function."""
    profiles = load_profiles(FILE_NAME)
    if not profiles:
        return
        
    if not check_connection():
        print("\nCannot proceed with insertion due to MongoDB connection failure.")
        return

    documents = create_user_and_profile_documents(profiles)
    
    # Get collection references using your provided helper functions
    users_collection = get_users_collection()
    profiles_collection = get_profiles_collection()
    
    collections_to_insert = {
        "users": (users_collection, documents["users"]),
        "profiles": (profiles_collection, documents["profiles"])
    }

    print(f"\nConnected to Database: '{DB_NAME}'. Starting bulk insert...")

    # Insert data into MongoDB
    for collection_name, (collection, documents) in collections_to_insert.items():
        if not documents:
            continue
            
        try:
            result = collection.insert_many(documents, ordered=False)
            print(f"✅ Successfully inserted {len(result.inserted_ids)} documents into '{collection_name}'.")

        except Exception as e:
            print(f"❌ Error inserting into '{collection_name}': {e}")
            
    # Closing the client is good practice, though not strictly required for a script exiting immediately
    client.close()
    print("Connection closed.")


if __name__ == "__main__":
    main()