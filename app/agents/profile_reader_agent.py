import os
import re
import json
from typing import Dict, Any, Optional
from groq import Groq
from pydantic import ValidationError
from models.profile import ProfileCreate, SleepSchedule, Cleanliness, NoiseTolerance, StudyHabits, FoodPref

# --- Low-Bandwidth and Offline Alternative Imports ---
import sqlite3
import time

# Groq Profile Reader Agent with Offline Capabilities
class ProfileReaderAgent:
    PHONE_NUMBER_REGEX = r'(?:\+92|03)\s?[-]?\s?\d{2,3}\s?[-]?\d{7,8}'

    def __init__(self, api_key: str, model_name: str = "openai/gpt-oss-120b", cache_db_path: str = "profile_cache.db"):
        if not api_key:
            raise ValueError("❌ Groq API key not provided. Please set GROQ_API_KEY.")
        self.client = Groq(api_key=api_key)
        self.model_name = model_name
        self.cache_db_path = cache_db_path
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite database for caching parsed profiles."""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parsed_profiles (
                raw_text TEXT PRIMARY KEY,
                parsed_json TEXT,
                timestamp INTEGER
            )
        """)
        conn.commit()
        conn.close()

    def _get_from_cache(self, raw_ad_text: str) -> Optional[Dict[str, Any]]:
        """Retrieves a parsed profile from the cache if it exists."""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT parsed_json FROM parsed_profiles WHERE raw_text = ?", (raw_ad_text,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return json.loads(result[0])
        return None

    def _save_to_cache(self, raw_ad_text: str, parsed_profile: Dict[str, Any]):
        """Saves a newly parsed profile to the cache."""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO parsed_profiles (raw_text, parsed_json, timestamp) VALUES (?, ?, ?)",
            (raw_ad_text, json.dumps(parsed_profile), int(time.time()))
        )
        conn.commit()
        conn.close()

    def _rule_based_fallback(self, preprocessed_text: str) -> Dict[str, Any]:
        """A simple, rule-based parser for use when the API fails."""
        profile = {
            "sleep_schedule": "Flexible",
            "cleanliness": "Average",
            "noise_tolerance": "Moderate",
            "study_habits": "Library",
            "food_pref": "Flexible"
        }
        text = preprocessed_text.lower()
        
        # Simple keyword matching for each category
        if any(keyword in text for keyword in ["early bird", "wakes up early", "morning person"]):
            profile["sleep_schedule"] = "Early Bird"
        elif any(keyword in text for keyword in ["night owl", "stays up late", "late night"]):
            profile["sleep_schedule"] = "Night Owl"

        if any(keyword in text for keyword in ["neat freak", "very clean", "super tidy"]):
            profile["cleanliness"] = "Very Clean"
        elif any(keyword in text for keyword in ["a bit messy", "don't mind mess", "relaxed about cleaning"]):
            profile["cleanliness"] = "A Bit Messy"

        if any(keyword in text for keyword in ["quiet person", "need quiet", "low noise"]):
            profile["noise_tolerance"] = "Low"
        elif any(keyword in text for keyword in ["loud music", "parties", "friends over"]):
            profile["noise_tolerance"] = "High"

        if any(keyword in text for keyword in ["study a lot", "focus", "serious student"]):
            profile["study_habits"] = "Quiet Room"
        elif any(keyword in text for keyword in ["chill", "easygoing", "study on bed"]):
            profile["study_habits"] = "Common Area"
        
        if any(keyword in text for keyword in ["vegetarian", "veg"]):
            profile["food_pref"] = "Vegetarian Only"
        elif any(keyword in text for keyword in ["eat out", "no cooking"]):
            profile["food_pref"] = "Eats Out"
        
        return profile

    def _preprocess(self, raw_ad_text: str) -> str:
        """Remove sensitive info like phone numbers, normalize text."""
        text = raw_ad_text.strip().lower()
        return re.sub(self.PHONE_NUMBER_REGEX, '', text).strip()

    def _get_llm_response(self, preprocessed_text: str) -> Dict[str, Any]:
        """Call Groq LLM and enforce JSON schema output using Enum values."""
        system_prompt = f"""
        You are a Senior Data Analyst parsing unstructured roommate advertisements from Pakistan.

        Your ONLY job is to extract structured roommate profile data into the schema below.
        ❌ Do NOT add commentary, ❌ Do NOT create new categories.
        ✅ Only return a valid JSON object.

        Use these exact options only (case-sensitive):

        * sleep_schedule: {[e.value for e in SleepSchedule]}
        * cleanliness: {[e.value for e in Cleanliness]}
        * noise_tolerance: {[e.value for e in NoiseTolerance]}
        * study_habits: {[e.value for e in StudyHabits]}
        * food_pref: {[e.value for e in FoodPref]}

        If information is missing or ambiguous, pick the closest option or default:
        - sleep_schedule → "Flexible"
        - cleanliness → "Average"
        - noise_tolerance → "Moderate"
        - study_habits → "Library"
        - food_pref → "Flexible"

        The final and ONLY output must strictly match this schema:
        {ProfileCreate.schema_json(indent=2)}
        """

        chat_completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Parse this messy ad text: {preprocessed_text}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        return json.loads(chat_completion.choices[0].message.content)

    def parse_profile(self, raw_ad_text: str) -> Dict[str, Any]:
        """Main method: takes raw ad text and returns structured JSON using ProfileCreate schema."""
        preprocessed_text = self._preprocess(raw_ad_text)
        
        # 1. Check for cached response
        cached_profile = self._get_from_cache(preprocessed_text)
        if cached_profile:
            print("✅ Returning cached profile.")
            return cached_profile
        
        try:
            # 2. Try to get response from Groq API
            llm_output = self._get_llm_response(preprocessed_text)
            
            # 3. Validate and save to cache
            validated_profile = ProfileCreate(**llm_output)
            self._save_to_cache(preprocessed_text, validated_profile.dict())
            return validated_profile.dict()

        except Exception as e:
            # 4. Graceful Fallback on API failure
            print(f"⚠ Groq API call failed: {e}. Falling back to rule-based parser.")
            rule_based_output = self._rule_based_fallback(preprocessed_text)
            
            try:
                # 5. Validate fallback output
                validated_profile = ProfileCreate(**rule_based_output)
                return validated_profile.dict()
            except ValidationError as ve:
                # This should not happen if rule-based logic is correct
                raise ValueError(f"Fallback Schema Validation Error: {ve.errors()}")


# Global agent instance for re-use across the app
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
profile_reader: Optional[ProfileReaderAgent] = None

if GROQ_API_KEY:
    try:
        profile_reader = ProfileReaderAgent(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"⚠ Failed to initialize Groq Agent: {e}")
else:
    print("⚠ No GROQ_API_KEY found. AI parsing will not work.")
    # Initialize a dummy agent for testing fallback logic without API key