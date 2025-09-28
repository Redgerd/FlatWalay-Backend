import os
import re
import json
from typing import Dict, Any, Optional
from groq import Groq

# ----------------------------
# Global Groq API key check
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("⚠ No GROQ_API_KEY found. RedFlagAgent will use fallback logic.")

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
    Detect potential roommate conflicts between two profiles using Groq LLM with a rule-based fallback.
    """

    def __init__(self, api_key: Optional[str] = GROQ_API_KEY, model_name: str = "openai/gpt-oss-120b"):
        if not api_key:
            self.client = None
        else:
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

    def _rule_based_fallback(self, pair_id: str, profile_a: Dict[str, Any], profile_b: Dict[str, Any]) -> Dict[str, Any]:
        """A simple, rule-based conflict detector for when the API is not available."""
        red_flags = []
        
        # Conflict 1: Sleep Schedule
        if (profile_a.get("sleep_schedule") == "Early Bird" and profile_b.get("sleep_schedule") == "Night Owl") or \
           (profile_a.get("sleep_schedule") == "Night Owl" and profile_b.get("sleep_schedule") == "Early Bird"):
            red_flags.append({
                "type": "Sleep Schedule Mismatch",
                "severity": "HIGH",
                "evidence": "One is an Early Bird, the other is a Night Owl."
            })

        # Conflict 2: Cleanliness
        if (profile_a.get("cleanliness") == "Very Clean" and profile_b.get("cleanliness") == "A Bit Messy") or \
           (profile_a.get("cleanliness") == "A Bit Messy" and profile_b.get("cleanliness") == "Very Clean"):
            red_flags.append({
                "type": "Cleanliness Mismatch",
                "severity": "HIGH",
                "evidence": "One is a neat freak, the other is relaxed about cleanliness."
            })
        
        # Conflict 3: Noise Tolerance
        if (profile_a.get("noise_tolerance") == "Low" and profile_b.get("noise_tolerance") == "High") or \
           (profile_a.get("noise_tolerance") == "High" and profile_b.get("noise_tolerance") == "Low"):
            red_flags.append({
                "type": "Noise Tolerance Mismatch",
                "severity": "MEDIUM",
                "evidence": "One prefers quiet, the other tolerates noise."
            })

        # Conflict 4: Study Habits
        if (profile_a.get("study_habits") == "Quiet Room" and profile_b.get("study_habits") == "Common Area") or \
           (profile_a.get("study_habits") == "Common Area" and profile_b.get("study_habits") == "Quiet Room"):
            red_flags.append({
                "type": "Study Habits Mismatch",
                "severity": "MEDIUM",
                "evidence": "One needs a quiet room to study, the other is fine with a common area."
            })
        
        # Conflict 5: Budget
        budget_diff_pkr = abs(profile_a.get("budget_PKR", 0) - profile_b.get("budget_PKR", 0))
        if budget_diff_pkr > 30000:
            red_flags.append({
                "type": "Budget Mismatch",
                "severity": "HIGH",
                "evidence": f"Budgets differ by more than {budget_diff_pkr} PKR."
            })
        elif budget_diff_pkr > 10000:
            red_flags.append({
                "type": "Budget Mismatch",
                "severity": "MEDIUM",
                "evidence": f"Budgets differ by more than {budget_diff_pkr} PKR."
            })
            
        return {"pair_id": pair_id, "red_flags": red_flags}

    def detect_conflicts(self, profile_a: Dict[str, Any], profile_b: Dict[str, Any]) -> Dict[str, Any]:
        """Main method: Takes two profiles and returns structured red-flag JSON."""
        pair_id = f"{profile_a.get('id', 'P-A')}_{profile_b.get('id', 'P-B')}"
        
        # Check if Groq client is available
        if not self.client:
            print("⚠ Groq client not initialized. Using rule-based fallback.")
            return self._rule_based_fallback(pair_id, profile_a, profile_b)
        
        # Attempt to use the Groq API
        try:
            system_prompt = self._get_system_prompt()
            user_prompt = (
                f"--- Profile A ---\n{json.dumps(profile_a)}\n\n"
                f"--- Profile B ---\n{json.dumps(profile_b)}\n\n"
                f"Analyze conflicts and return a JSON object with 'pair_id': '{pair_id}' "
                f"and structured 'red_flags' list."
            )

            tool = {
                "type": "function",
                "function": {
                    "name": "return_conflicts",
                    "description": "Returns structured red flags for roommate conflicts.",
                    "parameters": CONFLICT_OUTPUT_SCHEMA,
                },
            }

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
                # Fallback if LLM doesn't call the tool for some reason
                print("⚠ LLM did not call tool. Using rule-based fallback.")
                return self._rule_based_fallback(pair_id, profile_a, profile_b)

            function_args_str = tool_calls[0].function.arguments
            return json.loads(function_args_str)

        except Exception as e:
            print(f"⚠ Groq API/Execution Error: {e}. Falling back to rule-based logic.")
            return self._rule_based_fallback(pair_id, profile_a, profile_b)

# Global instance for reuse
red_flag_agent: Optional[RedFlagAgent] = None
try:
    red_flag_agent = RedFlagAgent(api_key=GROQ_API_KEY)
except Exception as e:
    print(f"⚠ Failed to initialize RedFlagAgent: {e}")