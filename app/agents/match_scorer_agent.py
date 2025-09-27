# agents/match_scorer_agent.py
from typing import List, Dict, Any, Union
from pydantic import BaseModel
from groq import Groq
from db.mongo import get_profiles_collection
import os
from routes.profiles.profiles_response_schemas import ProfileResponse

# --- Result Schema ---
class MatchResult(BaseModel):
    profile_id: str
    score: int
    reasons: List[str]

# --- Main Agent ---
class MatchScorerAgent:
    GROQ_MODEL = "openai/gpt-oss-120b"

    def __init__(self):
        if "GROQ_API_KEY" not in os.environ:
            raise EnvironmentError("GROQ_API_KEY not found.")
        self.client = Groq(api_key=os.environ["GROQ_API_KEY"])

    def score_profiles(
        self, profile_a: Union[Dict[str, Any], ProfileResponse], profile_b: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute compatibility score between two profiles using actual profile data.
        """
        profile_a_dict = profile_a.dict() if isinstance(profile_a, ProfileResponse) else profile_a

        score = 0
        reasons = []

        # Example scoring logic:
        # 1. Budget similarity
        budget_diff = abs(profile_a_dict.get("budget_PKR", 0) - profile_b.get("budget_PKR", 0))
        if budget_diff <= 10000:
            score += 30
            reasons.append("Budgets are similar")
        elif budget_diff <= 30000:
            score += 15
            reasons.append("Budgets are moderately compatible")
        else:
            reasons.append("Budgets differ significantly")

        # 2. Sleep schedule match
        if profile_a_dict.get("sleep_schedule") and profile_a_dict.get("sleep_schedule") == profile_b.get("sleep_schedule"):
            score += 20
            reasons.append("Sleep schedules match")

        # 3. Cleanliness match
        if profile_a_dict.get("cleanliness") and profile_a_dict.get("cleanliness") == profile_b.get("cleanliness"):
            score += 20
            reasons.append("Cleanliness preferences match")

        # 4. Noise tolerance match
        if profile_a_dict.get("noise_tolerance") and profile_a_dict.get("noise_tolerance") == profile_b.get("noise_tolerance"):
            score += 15
            reasons.append("Noise tolerance matches")

        # 5. Study habits match
        if profile_a_dict.get("study_habits") and profile_a_dict.get("study_habits") == profile_b.get("study_habits"):
            score += 15
            reasons.append("Study habits match")

        return {"score": min(score, 100), "reasons": reasons}

    def get_best_matches(
        self, user_profile: Union[Dict[str, Any], ProfileResponse], top_n: int = 5
    ) -> List[MatchResult]:
        """
        Returns top N recommended roommate profiles for the given user profile.
        Compares against ALL profiles in the database, skipping the user's own profile.
        """
        user_profile_dict = user_profile.dict() if isinstance(user_profile, ProfileResponse) else user_profile

        profiles_collection = get_profiles_collection()
        candidate_profiles = list(profiles_collection.find())

        results: List[MatchResult] = []

        for candidate in candidate_profiles:
            if str(candidate["_id"]) == user_profile_dict.get("id"):
                continue  # Skip the user's own profile
            score_data = self.score_profiles(user_profile_dict, candidate)
            results.append(MatchResult(
                profile_id=str(candidate["_id"]),
                score=score_data["score"],
                reasons=score_data["reasons"]
            ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_n]

# --- Singleton instance ---
match_scorer_agent: MatchScorerAgent | None = None
if "GROQ_API_KEY" in os.environ:
    try:
        match_scorer_agent = MatchScorerAgent()
    except Exception as e:
        print(f"⚠ Failed to initialize MatchScorerAgent: {e}")
else:
    print("⚠ No GROQ_API_KEY found. Match scoring will not work.")
