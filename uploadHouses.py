import json
import random
from bson.objectid import ObjectId
from typing import List, Dict

# ----------------------------------------------------------------------
# START: MongoDB Configuration (Commented out as external connection is not possible)
# ----------------------------------------------------------------------
from pymongo import MongoClient
MONGO_URI="mongodb+srv://xxhba777xx_db_user:8XIo2K60IwfJt3AC@flat-waley.cycp3kt.mongodb.net/"
DB_NAME="Flat-Waley"
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

def get_housing_collection():
    return db["housing"]

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
FILE_NAME = r"C:\Users\sa\OneDrive\Desktop\New folder\data\housing_listings_pakistan_400.json"

# Approximate geographical boundaries for Pakistan (for random generation)
LAT_MIN = 23.5  # Southern limit
LAT_MAX = 37.5  # Northern limit
LON_MIN = 60.5  # Western limit
LON_MAX = 78.0  # Eastern limit


def load_listings(file_name: str) -> List[Dict]:
    """Loads housing listing data from the specified JSON file."""
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            listings = json.load(f)
        print(f"✅ Successfully loaded {len(listings)} listings from {file_name}.")
        return listings
    except FileNotFoundError:
        print(f"❌ Error: The file '{file_name}' was not found. Please check the path.")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Error: The file '{file_name}' contains invalid JSON data: {e}")
        return []


def create_housing_documents(listings: List[Dict]) -> List[Dict]:
    """
    Processes listings to create MongoDB documents, adding _id, longitude, and latitude.
    """
    housing_documents = []
    
    print(f"Starting document creation and coordinate generation for {len(listings)} records...")

    for listing in listings:
        # 1. Generate unique MongoDB ID
        listing_obj_id = ObjectId()
        
        # 2. Generate random coordinates
        latitude = round(random.uniform(LAT_MIN, LAT_MAX), 6)
        longitude = round(random.uniform(LON_MIN, LON_MAX), 6)

        # 3. Create the Housing document
        # Map listing_id to a new field or keep it as-is, and use ObjectId for _id
        housing_doc = {
            "_id": listing_obj_id, 
            "listing_id": listing.get('listing_id', str(listing_obj_id)),
            **{k: v for k, v in listing.items() if k != 'listing_id'},
            "latitude": latitude,
            "longitude": longitude
        }
        
        # Ensure rent and rooms are integers
        housing_doc['monthly_rent_PKR'] = int(housing_doc.get('monthly_rent_PKR', 0))
        housing_doc['rooms_available'] = int(housing_doc.get('rooms_available', 1))

        housing_documents.append(housing_doc)
            
    print("✅ All housing documents created and augmented with coordinates successfully.")
    return housing_documents


def main():
    """Main execution function."""
    
    # 1. Load data
    listings = load_listings(FILE_NAME)
    if not listings:
        return
        
    # 2. Transform data
    documents_to_insert = create_housing_documents(listings)
    
    # --- SIMULATE INSERTION ---
    # The actual MongoDB insertion is commented out.
    # We will print the first 5 documents to show the structure.
    
    print("\n--- Sample Housing Documents (Ready for Insertion) ---")
    for doc in documents_to_insert[:5]:
        # Convert ObjectId to string for easy printing
        doc['_id'] = str(doc['_id'])
        print(json.dumps(doc, indent=4))
    
    # -------------------------------------------------
    # UNCOMMENT THIS SECTION TO PERFORM ACTUAL INSERTION:
    # -------------------------------------------------
    if not check_connection():
        print("\nCannot proceed with insertion due to MongoDB connection failure.")
        return
    
    housing_collection = get_housing_collection()
    print(f"\nConnected to Database: '{DB_NAME}'. Starting bulk insert...")
    
    try:
        result = housing_collection.insert_many(documents_to_insert, ordered=False)
        print(f"✅ Successfully inserted {len(result.inserted_ids)} documents into 'housing'.")
    
    except Exception as e:
        print(f"❌ Error inserting into 'housing': {e}")
        
    client.close()
    print("Connection closed.")


if __name__ == "__main__":
    main()