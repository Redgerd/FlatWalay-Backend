# agent/profile_reader_agent.py
import os
import re
import json
from typing import Dict, Any
from groq import Groq
from pydantic import BaseModel, Field, conint, ValidationError


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


class GroqProfileReaderAgent:
    PHONE_NUMBER_REGEX = r'(?:\+92|03)\s?[-]?\s?\d{2,3}\s?[-]?\d{7,8}'

    def __init__(self, api_key: str, model_name: str = "openai/gpt-oss-120b"):
        if not api_key:
            raise ValueError("❌ Groq API key not provided.")
        self.client = Groq(api_key=api_key)
        self.model_name = model_name

    def _preprocess(self, raw_ad_text: str) -> str:
        text = raw_ad_text.strip().lower()
        text = re.sub(self.PHONE_NUMBER_REGEX, '', text).strip()
        return text

    def _get_llm_response(self, preprocessed_text: str) -> Dict[str, Any]:
        system_prompt = f"""
        You are a Senior Data Analyst parsing unstructured roommate advertisements from Pakistan...
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
