import os
import re
import json
from typing import Dict, Any
from groq import Groq

# ----------------------------
# Global Groq API key check
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("⚠ No GROQ_API_KEY found. RedFlagAgent will not work.")


# Conflict Output Schema
CONFLICT_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "pair_id": {"type": "string"},
        "red_flags": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "severity": {"type": "string"},
                    "evidence": {"type": "string"},
                },
                "required": ["type", "severity", "evidence"],
            },
        },
    },
    "required": ["pair_id", "red_flags"],
}


class RedFlagAgent:
    """
    Detect potential roommate conflicts between two profiles using Groq LLM.
    """

    def __init__(self, api_key: str = GROQ_API_KEY, model_name: str = "openai/gpt-oss-120b"):
        if not api_key:
            raise ValueError("❌ Groq API key not provided. Please set GROQ_API_KEY.")
        self.client = Groq(api_key=api_key)
        self.model_name = model_name

    def _get_system_prompt(self) -> str:
        """System prompt guiding LLM to output strictly structured conflict JSON."""
        return (
            "You are the Ultimate Roommate Conflict Analysis Engine. "
            "Your job is to detect and report ALL factual conflicts between two roommate profiles.\n\n"
            "⚠ OUTPUT RULE: Must return JSON matching schema exactly with keys: "
            "'pair_id', 'red_flags'. Each red_flag object must have 'type', 'severity', 'evidence'. "
            "Do not add commentary or extra fields.\n\n"
            "Severity rubric:\n"
            "- HIGH: Dealbreaker, significant daily discomfort (Sleep, Major Cleanliness, Budget>30%)\n"
            "- MEDIUM: Manageable friction (Study, Food, Noise mismatches)\n"
            "- LOW: Minor nuisance (small differences)\n\n"
            "Compare fields: Sleep, Cleanliness, Noise, Study, Food, Budget. Evidence must be concise."
        )

    def detect_conflicts(self, profile_a: Dict[str, Any], profile_b: Dict[str, Any]) -> Dict[str, Any]:
        """Main method: Takes two profiles and returns structured red-flag JSON."""
        pair_id = f"{profile_a.get('id', 'P-A')}_{profile_b.get('id', 'P-B')}"

        system_prompt = self._get_system_prompt()
        user_prompt = (
            f"--- Profile A ---\n{json.dumps(profile_a)}\n\n"
            f"--- Profile B ---\n{json.dumps(profile_b)}\n\n"
            f"Analyze conflicts and return a JSON object with 'pair_id': '{pair_id}' "
            f"and structured 'red_flags' list."
        )

        # Define tool/schema for structured output
        tool = {
            "type": "function",
            "function": {
                "name": "return_conflicts",
                "description": "Returns structured red flags for roommate conflicts.",
                "parameters": CONFLICT_OUTPUT_SCHEMA,
            },
        }

        try:
            chat_completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                tools=[tool],
                tool_choice={"type": "function", "function": {"name": "return_conflicts"}},
                temperature=0.0,
            )

            tool_calls = chat_completion.choices[0].message.tool_calls
            if not tool_calls:
                return {"pair_id": pair_id, "red_flags": []}

            function_args_str = tool_calls[0].function.arguments
            return json.loads(function_args_str)

        except Exception as e:
            raise RuntimeError(f"Groq API/Execution Error: {e}")


# Global instance for reuse
red_flag_agent: RedFlagAgent | None = None
if GROQ_API_KEY:
    try:
        red_flag_agent = RedFlagAgent()
    except Exception as e:
        print(f"⚠ Failed to initialize RedFlagAgent: {e}")
