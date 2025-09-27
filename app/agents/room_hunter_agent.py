# agents/room_hunter_agent.py
from typing import List, Dict, Any
from pydantic import BaseModel
from db.mongo import get_housing_collection
import os

# --- Schema ---
class HousingMatch(BaseModel):
    listing_id: str
    city: str
    area: str
    monthly_rent_PKR: int
    rooms_available: int
    amenities: List[str]
    availability: str
    short_reason: str

# --- Agent ---
class RoomHunterAgent:
    REQUIRED_AMENITIES = ["Security guard", "WiFi"]

    def __init__(self):
        pass  # Optionally add LLM client here

    def score_listing(self, profile: Dict[str, Any], listing: Dict[str, Any]) -> Dict[str, Any]:
        score = 0
        reasons = []

        # City match
        if profile.get("city") == listing.get("city"):
            score += 30
            reasons.append("City matches")
        else:
            reasons.append(f"City differs ({listing.get('city')})")

        # Area match
        if profile.get("area") == listing.get("area"):
            score += 25
            reasons.append("Preferred area")
        else:
            reasons.append(f"Different area ({listing.get('area')})")

        # Budget check
        if profile.get("budget_PKR", 0) >= listing.get("monthly_rent_PKR", 0):
            score += 25
            reasons.append("Within budget")
        else:
            reasons.append(f"Exceeds budget ({listing.get('monthly_rent_PKR')})")

        # Amenities check
        matched_amenities = [a for a in self.REQUIRED_AMENITIES if a in listing.get("amenities", [])]
        score += 10 * len(matched_amenities)
        if matched_amenities:
            reasons.append(f"Amenities matched: {', '.join(matched_amenities)}")

        return {"score": score, "reasons": reasons}

    def get_top_housing_matches(self, profiles: List[Dict[str, Any]], top_n: int = 2) -> List[HousingMatch]:
        housing_collection = get_housing_collection()
        listings = list(housing_collection.find({"availability": "Available"}))

        scored_listings = []
        for listing in listings:
            total_score = 0
            combined_reasons = []
            for profile in profiles:
                res = self.score_listing(profile, listing)
                total_score += res["score"]
                combined_reasons.extend(res["reasons"])
            scored_listings.append({"listing": listing, "score": total_score, "reasons": combined_reasons})

        # Sort by score
        scored_listings.sort(key=lambda x: x["score"], reverse=True)
        top_listings = scored_listings[:top_n]

        results = []
        for item in top_listings:
            l = item["listing"]
            reason_text = "; ".join(item["reasons"])[:500]
            results.append(HousingMatch(
                listing_id=l["listing_id"],
                city=l["city"],
                area=l["area"],
                monthly_rent_PKR=l["monthly_rent_PKR"],
                rooms_available=l.get("rooms_available", 1),
                amenities=l.get("amenities", []),
                availability=l.get("availability", "Available"),
                short_reason=reason_text
            ))
        return results


# Singleton
room_hunter_agent: RoomHunterAgent = RoomHunterAgent()
