# agents/room_hunter_agent.py
import os
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from groq import Groq
from bson import ObjectId
from db.mongo import get_housing_collection
from models.housing import Housing

# --- Agent ---
class RoomHunterAgent:
    REQUIRED_AMENITIES = ["Security guard", "WiFi"]
    GROQ_MODEL = "openai/gpt-oss-120b"
    MAX_REASON_LENGTH = 500

    def __init__(self, api_key: Optional[str] = os.getenv("GROQ_API_KEY")):
        if not api_key:
            print("⚠ No GROQ_API_KEY found. RoomHunterAgent will use a rule-based fallback for explanations.")
            self.client = None
        else:
            self.client = Groq(api_key=api_key)

    def _generate_llm_reason(self, profile: Dict[str, Any], listing: Dict[str, Any], reasons: List[str]) -> str:
        """Generates a human-friendly reason using an LLM."""
        if not self.client:
            return "; ".join(reasons)[:self.MAX_REASON_LENGTH]

        profile_safe = {k: str(v) if isinstance(v, ObjectId) else v for k, v in profile.items()}
        listing_safe = {k: str(v) if isinstance(v, ObjectId) else v for k, v in listing.items()}

        system_prompt = (
            "You are a helpful Roommate Match Agent. Your job is to take a profile's preferences "
            "and a housing listing's details and generate a single, concise, human-friendly sentence "
            "explaining why the listing is a good match. Focus on key positive points like "
            "city, area, budget, and amenities. Do not mention negative points."
        )

        user_prompt = (
            f"User Profile: {json.dumps(profile_safe)}\n"
            f"Housing Listing: {json.dumps(listing_safe)}\n"
            f"Key matching reasons: {'; '.join(reasons)}\n"
            "Generate a one-sentence summary explaining why this listing is a great match. "
            "Start the sentence with 'This listing is a great match because...'"
        )

        try:
            chat_completion = self.client.chat.completions.create(
                model=self.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"⚠ LLM call failed: {e}. Falling back to rule-based reason.")
            return "; ".join(reasons)[:self.MAX_REASON_LENGTH]

    def score_listing(self, profile: Dict[str, Any], listing: Dict[str, Any]) -> Dict[str, Any]:
        """Rule-based scoring for a single listing."""
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

        # Optional preferences
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
        """Return top N housing listings for given profiles."""
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

        scored_listings.sort(key=lambda x: x["score"], reverse=True)
        top_listings = scored_listings[:top_n]

        results = []
        for item in top_listings:
            l = item["listing"]
            _id = str(l.get("_id"))  # Always use MongoDB _id
            reason_text = self._generate_llm_reason(profiles[0], l, item["reasons"])

            results.append(Housing(
                _id=_id,
                city=l.get("city"),
                area=l.get("area"),
                monthly_rent_PKR=l.get("monthly_rent_PKR"),
                rooms_available=l.get("rooms_available", 1),
                amenities=l.get("amenities", []),
                availability=l.get("availability", "Available"),
                latitude=l.get("latitude"),   # <-- Ensure latitude included
                longitude=l.get("longitude"), # <-- Ensure longitude included
                short_reason=reason_text
            ))
        return results

# Singleton instance
room_hunter_agent: RoomHunterAgent = RoomHunterAgent()
