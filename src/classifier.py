"""
classifier.py - Persona detection using Gemini structured JSON output + rule-based correction.

Detects one of three customer personas:
  • Technical Expert   – API errors, logs, auth config, error codes
  • Frustrated User    – emotional language, complaints, urgent tone
  • Business Executive – business impact, revenue, SLA, timelines
"""

import json
import logging
import re
from typing import TypedDict

import google.generativeai as genai

from src.config import GOOGLE_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

genai.configure(api_key=GOOGLE_API_KEY)


class PersonaResult(TypedDict):
    persona: str
    confidence: float
    reasoning: str


TECHNICAL_KEYWORDS = [
    "api", "authentication", "auth", "token", "bearer", "jwt",
    "header", "headers", "endpoint", "status code", "401", "403",
    "logs", "configuration", "config", "error details", "debug",
    "request", "response", "payload", "sdk", "rate limit", "database",
]

BUSINESS_KEYWORDS = [
    "business", "operations", "impact", "timeline", "sla",
    "revenue", "cost", "customers", "resolution", "downtime",
    "operational", "priority", "executive",
]

FRUSTRATED_KEYWORDS = [
    "frustrated", "angry", "nothing works", "tried everything",
    "not working", "urgent", "ridiculous", "terrible", "hate",
    "fed up", "useless", "worst", "again and again",
]


PERSONA_DETECTION_PROMPT = """You are an expert customer support analyst. Analyze the customer message and conversation history below to detect the customer's persona.

Choose EXACTLY ONE persona from:
1. "Technical Expert" - Uses technical terminology, asks about APIs, error codes, logs, authentication, configurations, rate limits, SDKs, or debugging steps.
2. "Frustrated User" - Expresses emotional distress, uses urgent language, complains something "doesn't work", says nothing is helping, or shows impatience.
3. "Business Executive" - Focuses on business impact, revenue loss, operational disruption, SLA compliance, timelines, or asks for executive summaries.

Important priority:
- If the message contains API/authentication/logs/token/header/status code/debugging terms, classify as "Technical Expert" even if it asks for help.
- If the message asks about impact, operations, SLA, timeline, or resolution, classify as "Business Executive".
- Classify as "Frustrated User" only when emotional dissatisfaction is the main signal.

Customer Message:
{message}

Conversation History (last 3 turns):
{history}

Respond ONLY with a valid JSON object. No markdown, no explanation outside JSON.

{{
  "persona": "<one of: Technical Expert | Frustrated User | Business Executive>",
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<one sentence explaining the classification>"
}}"""


def _rule_based_persona(message: str) -> PersonaResult | None:
    """High-confidence rules to correct obvious persona cases."""
    lower = message.lower()

    if any(word in lower for word in BUSINESS_KEYWORDS):
        return PersonaResult(
            persona="Business Executive",
            confidence=0.9,
            reasoning="Message focuses on business impact, operations, timeline, or resolution.",
        )

    if any(word in lower for word in TECHNICAL_KEYWORDS):
        return PersonaResult(
            persona="Technical Expert",
            confidence=0.9,
            reasoning="Message uses technical terms such as API, authentication, error details, logs, or configuration.",
        )

    if any(word in lower for word in FRUSTRATED_KEYWORDS):
        return PersonaResult(
            persona="Frustrated User",
            confidence=0.85,
            reasoning="Message expresses frustration, urgency, or repeated failure.",
        )

    return None


def detect_persona(message: str, conversation_history: list[dict]) -> PersonaResult:
    rule_result = _rule_based_persona(message)
    if rule_result:
        return rule_result

    history_text = _format_history(conversation_history)
    prompt = PERSONA_DETECTION_PROMPT.format(message=message, history=history_text)

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=256,
            ),
        )
        raw = response.text.strip()
        result = _parse_persona_json(raw)

        logger.info(
            "Persona detected: %s (confidence=%.2f)",
            result["persona"],
            result["confidence"],
        )
        return result

    except Exception as exc:
        logger.error("Persona detection failed: %s", exc)
        return PersonaResult(
            persona="Frustrated User",
            confidence=0.5,
            reasoning="Fallback persona assigned due to detection error.",
        )


def _format_history(history: list[dict]) -> str:
    recent = history[-3:] if len(history) > 3 else history
    if not recent:
        return "No prior conversation."

    lines = []
    for turn in recent:
        role = turn.get("role", "unknown").capitalize()
        content = turn.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _parse_persona_json(raw: str) -> PersonaResult:
    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("JSON parse failed (%s). Raw: %s", exc, raw[:200])
        return PersonaResult(
            persona="Frustrated User",
            confidence=0.5,
            reasoning="Could not parse persona JSON; defaulting to Frustrated User.",
        )

    valid_personas = {"Technical Expert", "Frustrated User", "Business Executive"}
    persona = data.get("persona", "Frustrated User")

    if persona not in valid_personas:
        persona = "Frustrated User"

    confidence = float(data.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))

    return PersonaResult(
        persona=persona,
        confidence=confidence,
        reasoning=str(data.get("reasoning", "No reasoning provided.")),
    )