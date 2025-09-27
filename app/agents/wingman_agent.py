import os
import json
from typing import Dict, List, Any
from groq import Groq

# ----------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("⚠ No GROQ_API_KEY found. MatchExplainerAgent will not work.")

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
    and actionable negotiation checklist using Groq LLM.
    """

    def __init__(self, api_key: str = GROQ_API_KEY, model_name: str = "openai/gpt-oss-120b"):
        if not api_key:
            raise ValueError("❌ Groq API key not provided. Please set GROQ_API_KEY.")
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

    def generate_explanation(
        self, match_score: int, match_reasons: List[str], red_flags: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Main method: generates structured explanation and negotiation checklist."""
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
                return {"summary_explanation": "Could not generate structured output.", "negotiation_checklist": []}

            function_args_str = tool_calls[0].function.arguments
            return json.loads(function_args_str)

        except Exception as e:
            raise RuntimeError(f"Groq API/Execution Error: {e}")


# Global instance
match_explainer_agent: MatchExplainerAgent | None = None
if GROQ_API_KEY:
    try:
        match_explainer_agent = MatchExplainerAgent()
    except Exception as e:
        print(f"⚠ Failed to initialize MatchExplainerAgent: {e}")
