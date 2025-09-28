import os
import re
import json
from typing import List, Dict, Any, Union
from pydantic import BaseModel
from groq import Groq
from db.mongo import get_profiles_collection
from routes.profiles.profiles_response_schemas import ProfileResponse

# --- Result Schema ---
class MatchResult(BaseModel):
    profile_id: str
    score: int
    reasons: List[str]

# --- Main Agent ---
class MatchScorerAgent:
    GROQ_MODEL = "openai/gpt-oss-120b"

    def __init__(self):  # <-- fix here
        if "GROQ_API_KEY" not in os.environ:
            # We don't raise an error here to allow the fallback to work.
            print("⚠ GROQ_API_KEY not found. Agent will use fallback logic.")
            self.client = None
        else:
            self.client = Groq(api_key=os.environ["GROQ_API_KEY"])

    def _rule_based_fallback(self, profile_a: Dict[str, Any], profile_b: Dict[str, Any]) -> Dict[str, Any]:
        """
        A simple, rule-based scorer for use when the API is not available.
        This provides a graceful fallback and ensures the system doesn't crash.
        """
        score = 0
        reasons = []

        # 1. Budget similarity (Exact logic from the original code)
        budget_diff = abs(profile_a.get("budget_PKR", 0) - profile_b.get("budget_PKR", 0))
        if budget_diff <= 10000:
            score += 30
            reasons.append("Budgets are similar")
        elif budget_diff <= 30000:
            score += 15
            reasons.append("Budgets are moderately compatible")
        else:
            reasons.append("Budgets differ significantly")

        # 2. Match on core preferences
        if profile_a.get("sleep_schedule") == profile_b.get("sleep_schedule"):
            score += 20
            reasons.append("Sleep schedules match")
        if profile_a.get("cleanliness") == profile_b.get("cleanliness"):
            score += 20
            reasons.append("Cleanliness preferences match")
        if profile_a.get("noise_tolerance") == profile_b.get("noise_tolerance"):
            score += 15
            reasons.append("Noise tolerance matches")
        if profile_a.get("study_habits") == profile_b.get("study_habits"):
            score += 15
            reasons.append("Study habits match")
        
        return {"score": min(score, 100), "reasons": reasons}

    def _score_profiles_llm(self, profile_a: Dict[str, Any], profile_b: Dict[str, Any]) -> Dict[str, Any]:
        """
        Uses Groq LLM to compute a nuanced compatibility score and reasons.
        """
        system_prompt = """
        You are a Roommate Compatibility Analyst. Your task is to analyze two roommate profiles and determine their compatibility.
        Provide a single JSON object as your output. The JSON must contain a 'score' (an integer from 0 to 100) and a list of 'reasons' (strings) for that score.
        A score of 100 means a perfect match, while 0 means a terrible match. Base your score on all provided information, including personality traits, habits, and budget.
        Be concise and direct in your analysis.
        """
        
        user_prompt = f"""
        Profile A: {json.dumps(profile_a, indent=2)}
        ---
        Profile B: {json.dumps(profile_b, indent=2)}
        ---
        Based on these two profiles, what is the compatibility score out of 100?
        Provide the score and 2-3 key reasons in a JSON format.
        """

        chat_completion = self.client.chat.completions.create(
            model=self.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )

        return json.loads(chat_completion.choices[0].message.content)

    def score_profiles(
        self, profile_a: Union[Dict[str, Any], ProfileResponse], profile_b: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute compatibility score using a tiered approach: LLM first, then rule-based fallback.
        """
        profile_a_dict = profile_a.dict() if isinstance(profile_a, ProfileResponse) else profile_a
        
        if self.client:
            try:
                # Tier 1: LLM-based scoring
                llm_output = self._score_profiles_llm(profile_a_dict, profile_b)
                # Ensure the LLM output is a valid number and list
                score = min(max(int(llm_output.get("score", 0)), 0), 100)
                reasons = llm_output.get("reasons", [])
                return {"score": score, "reasons": reasons}
            except Exception as e:
                # Tier 2: Fallback to rule-based scoring on API failure
                print(f"⚠ Groq API call failed for scoring: {e}. Falling back to rule-based logic.")
                return self._rule_based_fallback(profile_a_dict, profile_b)
        else:
            # Tier 3: Use rule-based scoring directly if no API key is available
            print("⚠ No Groq client. Using rule-based scoring.")
            return self._rule_based_fallback(profile_a_dict, profile_b)

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
try:
    match_scorer_agent = MatchScorerAgent()
except Exception as e:
    print(f"⚠ Failed to initialize MatchScorerAgent: {e}")

