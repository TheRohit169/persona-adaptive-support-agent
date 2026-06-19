"""
handoff.py - Generate structured human handoff summaries.

When a conversation is escalated, this module produces a JSON summary
that gives a human agent everything they need to continue seamlessly.
"""

import json
import logging
from typing import Any

import google.generativeai as genai

from src.config import GEMINI_MODEL, GOOGLE_API_KEY
from src.rag_pipeline import RetrievalResult

logger = logging.getLogger(__name__)

genai.configure(api_key=GOOGLE_API_KEY)


_HANDOFF_PROMPT = """You are a customer support operations specialist. A conversation is being escalated to a human agent.

Generate a concise, structured handoff summary in VALID JSON only (no markdown fences, no preamble).

Use EXACTLY this schema:
{{
  "persona": "<detected persona>",
  "issue": "<one-sentence summary of the core customer problem>",
  "conversation_history": [
    {{"role": "<user|assistant>", "content": "<message>"}}
  ],
  "documents_used": ["<filename1>", "<filename2>"],
  "attempted_steps": ["<step 1>", "<step 2>"],
  "confidence_score": <float 0-1>,
  "recommendation": "<one sentence on what the human agent should do next>"
}}

Context:
- Detected Persona: {persona}
- Escalation Reason: {escalation_reason}
- Retrieval Confidence: {confidence_score}
- Documents retrieved: {documents}
- Conversation History: {history}

Respond ONLY with the JSON object."""


def generate_handoff_summary(
    persona: str,
    escalation_reason: str,
    conversation_history: list[dict],
    retrieved_chunks: list[RetrievalResult],
    confidence_score: float,
) -> dict[str, Any]:
    """
    Generate a structured handoff summary for the human agent.

    Args:
        persona: Detected customer persona.
        escalation_reason: Why the conversation is being escalated.
        conversation_history: Full conversation turns list.
        retrieved_chunks: Documents used during the conversation.
        confidence_score: Best retrieval confidence score.

    Returns:
        Dictionary matching the handoff schema.
    """
    history_text = json.dumps(conversation_history, indent=2)
    docs_list = list({c.source for c in retrieved_chunks}) if retrieved_chunks else []
    docs_text = json.dumps(docs_list)

    prompt = _HANDOFF_PROMPT.format(
        persona=persona,
        escalation_reason=escalation_reason,
        confidence_score=f"{confidence_score:.3f}",
        documents=docs_text,
        history=history_text,
    )

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=1024,
            ),
        )
        raw = response.text.strip()

        # Strip markdown fences if present
        import re
        cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()

        summary = json.loads(cleaned)
        logger.info("Handoff summary generated successfully.")
        return summary

    except json.JSONDecodeError as exc:
        logger.error("Failed to parse handoff JSON: %s", exc)
        return _fallback_summary(
            persona, escalation_reason, conversation_history, docs_list, confidence_score
        )
    except Exception as exc:
        logger.error("Handoff generation failed: %s", exc)
        return _fallback_summary(
            persona, escalation_reason, conversation_history, docs_list, confidence_score
        )


def _fallback_summary(
    persona: str,
    escalation_reason: str,
    conversation_history: list[dict],
    documents_used: list[str],
    confidence_score: float,
) -> dict[str, Any]:
    """Construct a minimal handoff summary when LLM generation fails."""
    last_user_msg = ""
    for turn in reversed(conversation_history):
        if turn.get("role") == "user":
            last_user_msg = turn.get("content", "")
            break

    return {
        "persona": persona,
        "issue": last_user_msg[:200] if last_user_msg else "Unknown issue",
        "conversation_history": conversation_history,
        "documents_used": documents_used,
        "attempted_steps": ["Automated response attempted", "Escalation triggered"],
        "confidence_score": round(confidence_score, 3),
        "recommendation": (
            f"Review escalation reason: {escalation_reason}. "
            "Contact customer directly to resolve."
        ),
    }


def format_handoff_for_display(summary: dict[str, Any]) -> str:
    """Pretty-print the handoff summary as formatted JSON string."""
    return json.dumps(summary, indent=2, ensure_ascii=False)
