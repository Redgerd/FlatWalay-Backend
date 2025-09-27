# agents/room_hunter_agent.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from db.mongo import get_housing_collection
from models.housing import Housing  # Import full schema

class RoomHunterAgent:
    DEFAULT_REQUIRED_AMENITIES = ["Security guard", "WiFi"]
    MAX_REASON_LENGTH = 500

    def __init__(self, required_amenities: Optional[List[str]] = None):
        self.required_amenities = required_amenities or self.DEFAULT_REQUIRED_AMENITIES

    def score_listing(self, profile: Dict[str, Any], listing: Dict[str, Any]) -> Dict[str, Any]:
        score = 0
        reasons = []

        # City match
        city_profile = profile.get("city")
        city_listing = listing.get("city")
        if city_profile and city_listing:
            if city_profile == city_listing:
                score += 30
                reasons.append("City matches")
            else:
                reasons.append(f"City differs ({city_listing})")

        # Area match
        area_profile = profile.get("area")
        area_listing = listing.get("area")
        if area_profile and area_listing:
            if area_profile == area_listing:
                score += 25
                reasons.append("Preferred area")
            else:
                reasons.append(f"Different area ({area_listing})")

        # Budget check
        budget = profile.get("budget_PKR", 0)
        rent = listing.get("monthly_rent_PKR", 0)
        if budget >= rent:
            score += 25
            reasons.append("Within budget")
        else:
            reasons.append(f"Exceeds budget ({rent})")

        # Amenities check
        listing_amenities = listing.get("amenities", [])
        matched_amenities = [a for a in self.required_amenities if a in listing_amenities]
        score += 10 * len(matched_amenities)
        if matched_amenities:
            reasons.append(f"Amenities matched: {', '.join(matched_amenities)}")

        # Optional preference scoring
        optional_fields = ["sleep_schedule", "cleanliness", "noise_tolerance", "study_habits", "food_pref"]
        for field in optional_fields:
            profile_value = profile.get(field)
            listing_value = listing.get(field)
            if profile_value and listing_value:
                if profile_value == listing_value:
                    score += 5
                    reasons.append(f"{field.replace('_', ' ').title()} matches")
                else:
                    reasons.append(f"{field.replace('_', ' ').title()} differs")

        return {"score": score, "reasons": list(dict.fromkeys(reasons))}

    def get_top_housing_matches(self, profiles: List[Dict[str, Any]], top_n: int = 3) -> List[Housing]:
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
            reason_text = "; ".join(item["reasons"])[:self.MAX_REASON_LENGTH]
            results.append(Housing(
                _id=str(l.get("_id", "")),
                city=l["city"],
                area=l["area"],
                monthly_rent_PKR=l["monthly_rent_PKR"],
                rooms_available=l.get("rooms_available", 1),
                amenities=l.get("amenities", []),
                availability=l.get("availability", "Available"),
                latitude=l.get("latitude"),
                longitude=l.get("longitude"),
            ))
        return results


# Singleton instance
room_hunter_agent: RoomHunterAgent = RoomHunterAgent()
