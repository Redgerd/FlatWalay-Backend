# agent/profile_reader_agent.py
import os
import re
import json
from typing import Dict, Any
from groq import Groq
from pydantic import BaseModel, Field, conint, ValidationError


# --- Schema Definition ---
class RoommateProfileSchema(BaseModel):
    city: str
    area: str
    budget_PKR: conint(ge=0)
    cleanliness: str
    noise_tolerance: str
    sleep_schedule: str
    study_habits: str
    food_pref: str
    additional_notes: str


# --- Groq Profile Reader Agent ---
class GroqProfileReaderAgent:
    PHONE_NUMBER_REGEX = r'(?:\+92|03)\s?[-]?\s?\d{2,3}\s?[-]?\d{7,8}'

    def __init__(self, api_key: str, model_name: str = "openai/gpt-oss-120b"):
        if not api_key:
            raise ValueError("❌ Groq API key not provided. Please set GROQ_API_KEY.")
        self.client = Groq(api_key=api_key)
        self.model_name = model_name

    def _preprocess(self, raw_ad_text: str) -> str:
        """Remove sensitive info like phone numbers, normalize text."""
        text = raw_ad_text.strip().lower()
        return re.sub(self.PHONE_NUMBER_REGEX, '', text).strip()

    def _get_llm_response(self, preprocessed_text: str) -> Dict[str, Any]:
        """Call Groq LLM and enforce JSON schema output."""
        system_prompt = f"""
        You are a Senior Data Analyst parsing unstructured roommate advertisements from Pakistan.

    Your ONLY job is to extract structured roommate profile data into the schema below.
    ❌ Do NOT add commentary, ❌ Do NOT create new categories.
    ✅ Only return a valid JSON object.

    Use these exact options only (case-sensitive):

    * sleep_schedule: ["Night owl", "Early riser", "Flexible"]
    * cleanliness: ["Tidy", "Average", "Messy"]
    * noise_tolerance: ["Quiet", "Moderate", "Loud ok"]
    * study_habits: ["Online classes", "Late-night study", "Room study", "Library"]
    * food_pref: ["Flexible", "Non-veg", "Veg"]

    If information is missing or ambiguous, pick the closest option or default:
    - sleep_schedule → "Flexible"
    - cleanliness → "Average"
    - noise_tolerance → "Moderate"
    - study_habits → "Library"
    - food_pref → "Flexible"

    The final and ONLY output must strictly match this schema:
        Schema:
        {RoommateProfileSchema.schema_json(indent=2)}
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
        """Main method: takes raw ad text and returns structured JSON."""
        preprocessed_text = self._preprocess(raw_ad_text)
        try:
            llm_output = self._get_llm_response(preprocessed_text)
            validated_profile = RoommateProfileSchema(**llm_output)
            return validated_profile.dict()
        except ValidationError as ve:
            raise ValueError(f"Schema Validation Error: {ve.errors()}")


# --- Global agent instance for re-use across the app ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
agent_instance: GroqProfileReaderAgent | None = None

if GROQ_API_KEY:
    try:
        agent_instance = GroqProfileReaderAgent(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"⚠ Failed to initialize Groq Agent: {e}")
else:
    print("⚠ No GROQ_API_KEY found. AI parsing will not work.")
