import os
import json
from typing import Dict, List, Any, Optional
from groq import Groq

# ----------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("⚠ No GROQ_API_KEY found. MatchExplainerAgent will use fallback logic.")

# Output schema for the explanation agent
EXPLANATION_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary_explanation": {"type": "string"},
        "negotiation_checklist": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "suggestion": {"type": "string"},
                    "category": {"type": "string"},
                },
                "required": ["suggestion", "category"],
            },
        },
    },
    "required": ["summary_explanation", "negotiation_checklist"],
}


class MatchExplainerAgent:
    """
    Converts match score, reasons, and red flags into a human-friendly summary
    and actionable negotiation checklist using Groq LLM, with a graceful fallback.
    """

    def __init__(self, api_key: Optional[str] = GROQ_API_KEY, model_name: str = "openai/gpt-oss-120b"):
        if not api_key:
            self.client = None
        else:
            self.client = Groq(api_key=api_key)
        self.model_name = model_name

    def _get_system_prompt(self) -> str:
        """System prompt guiding LLM to output structured explanation and checklist."""
        return (
            "You are a compassionate and expert Roommate Match Translator and Negotiator. "
            "Your job is to synthesize the provided Match Score Data and Red Flag Data into "
            "a short, human-friendly summary and actionable negotiation checklist.\n\n"
            "⚠ OUTPUT RULE: Return JSON exactly matching keys: 'summary_explanation' and "
            "'negotiation_checklist'. Each checklist item must have 'suggestion' and 'category'. "
            "Do not add extra commentary.\n\n"
            "Use only 'HIGH' and 'MEDIUM' severity red flags to create 2–3 actionable suggestions. "
            "If no red flags, return empty checklist."
        )

    def _rule_based_fallback(self, match_score: int, match_reasons: List[str], red_flags: List[Dict[str, Any]]) -> Dict[str, Any]:
        """A simple, rule-based fallback to generate a basic explanation."""
        summary = f"This match has a compatibility score of {match_score}/100. Key positive points are: {', '.join(match_reasons)}."
        
        negotiation_checklist = []
        for flag in red_flags:
            if flag['severity'] in ["HIGH", "MEDIUM"]:
                if "Budget" in flag['type']:
                    negotiation_checklist.append({
                        "suggestion": "Discuss and agree on a clear budget for rent and shared expenses.",
                        "category": "Budget"
                    })
                elif "Sleep" in flag['type']:
                    negotiation_checklist.append({
                        "suggestion": "Set clear rules for noise and movement in the morning and late at night.",
                        "category": "Sleep Schedule"
                    })
                elif "Cleanliness" in flag['type']:
                    negotiation_checklist.append({
                        "suggestion": "Create a cleaning schedule to manage expectations and avoid conflict.",
                        "category": "Cleanliness"
                    })
                else: # For other medium/high flags like noise, study habits
                    negotiation_checklist.append({
                        "suggestion": f"Discuss expectations regarding {flag['type']} to find a compromise.",
                        "category": flag['type'].replace(" Mismatch", "")
                    })
        
        # Remove duplicate suggestions
        seen_categories = set()
        unique_checklist = []
        for item in negotiation_checklist:
            if item['category'] not in seen_categories:
                seen_categories.add(item['category'])
                unique_checklist.append(item)
                
        # Limit to 3 suggestions to keep it concise
        return {
            "summary_explanation": summary,
            "negotiation_checklist": unique_checklist[:3]
        }

    def generate_explanation(
        self, match_score: int, match_reasons: List[str], red_flags: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Main method: generates structured explanation and negotiation checklist."""
        
        if not self.client:
            print("⚠ Groq client not initialized. Using rule-based fallback.")
            return self._rule_based_fallback(match_score, match_reasons, red_flags)

        system_prompt = self._get_system_prompt()

        user_prompt = (
            f"Match Score: {match_score}/100\n"
            f"Reasons: {json.dumps(match_reasons)}\n"
            f"Red Flags: {json.dumps(red_flags)}\n\n"
            "Generate the JSON output as per schema."
        )

        tool = {
            "type": "function",
            "function": {
                "name": "return_explanation",
                "description": "Returns the summary explanation and negotiation checklist.",
                "parameters": EXPLANATION_OUTPUT_SCHEMA,
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
                tool_choice={"type": "function", "function": {"name": "return_explanation"}},
                temperature=0.0,
            )

            tool_calls = chat_completion.choices[0].message.tool_calls
            if not tool_calls:
                # Fallback if LLM doesn't call the tool for some reason
                print("⚠ LLM did not call tool. Using rule-based fallback.")
                return self._rule_based_fallback(match_score, match_reasons, red_flags)

            function_args_str = tool_calls[0].function.arguments
            return json.loads(function_args_str)

        except Exception as e:
            print(f"⚠ Groq API/Execution Error: {e}. Falling back to rule-based logic.")
            return self._rule_based_fallback(match_score, match_reasons, red_flags)

# Global instance
match_explainer_agent: Optional[MatchExplainerAgent] = None
try:
    match_explainer_agent = MatchExplainerAgent(api_key=GROQ_API_KEY)
except Exception as e:
    print(f"⚠ Failed to initialize MatchExplainerAgent: {e}")