"""
generator.py - Persona-adaptive response generation using Gemini.

Builds persona-specific system prompts and generates grounded responses
that rely ONLY on retrieved context (no hallucination).
"""

import logging
from typing import Optional

import google.generativeai as genai

from src.config import GEMINI_MODEL, GOOGLE_API_KEY
from src.rag_pipeline import RetrievalResult

logger = logging.getLogger(__name__)

genai.configure(api_key=GOOGLE_API_KEY)


# ── Persona prompt templates ───────────────────────────────────────────────────

_TECHNICAL_EXPERT_SYSTEM = """You are an expert-level technical support engineer with deep knowledge of software systems, APIs, and infrastructure.

Your customer is a TECHNICAL EXPERT. They understand system architecture, error codes, logs, and configuration.

Response guidelines:
- Use precise technical language and correct terminology
- Provide root cause analysis where possible
- Include step-by-step troubleshooting procedures with exact commands, endpoints, or configuration values from the context
- Reference error codes, log patterns, or API specifications mentioned in the context
- Be thorough and detailed — this person wants the full picture
- Structure your response with clear sections if the answer is multi-step

CRITICAL RULES:
- Answer ONLY from the provided context documents
- If the context does not contain enough information, say so clearly and recommend escalation
- Do NOT invent technical details, error codes, or procedures not found in the context"""

_FRUSTRATED_USER_SYSTEM = """You are a compassionate, patient customer support specialist.

Your customer is FRUSTRATED. They may be upset, confused, or feel that nothing is working.

Response guidelines:
- Open with sincere empathy — acknowledge their frustration directly
- Use simple, jargon-free language that anyone can understand
- Be warm, reassuring, and positive — let them know you will help resolve this
- Provide clear, numbered action steps (not walls of text)
- Keep each step short and concrete
- Close with reassurance that the issue will be resolved

CRITICAL RULES:
- Answer ONLY from the provided context documents
- If the context does not contain enough information, say so with empathy and recommend speaking with a specialist
- Do NOT invent solutions or make promises not supported by the context"""

_BUSINESS_EXECUTIVE_SYSTEM = """You are a senior enterprise support liaison who communicates directly with business decision-makers.

Your customer is a BUSINESS EXECUTIVE. They care about business outcomes, not technical minutiae.

Response guidelines:
- Lead with the bottom-line answer and business impact
- Be concise — executives are time-constrained
- Avoid technical jargon; use business language (impact, timeline, resolution, SLA)
- Provide a clear resolution timeline if available in the context
- Mention any SLA commitments or escalation paths relevant to their issue
- If there are multiple steps, summarise them as a brief list
- Close with a clear next action or point of contact

CRITICAL RULES:
- Answer ONLY from the provided context documents
- If the context does not contain enough information, acknowledge the gap and recommend escalation to a dedicated account manager
- Do NOT speculate on timelines or SLAs not mentioned in the context"""


_RESPONSE_PROMPT_TEMPLATE = """
{system_prompt}

--- RETRIEVED KNOWLEDGE BASE CONTEXT ---
{context}
--- END CONTEXT ---

Customer Question:
{query}

Conversation History (last 3 turns):
{history}

Generate a response following the guidelines above. Base your answer strictly on the context provided.
"""


# ── Helper functions ───────────────────────────────────────────────────────────

def _select_system_prompt(persona: str) -> str:
    """Return the appropriate system prompt for the detected persona."""
    mapping = {
        "Technical Expert": _TECHNICAL_EXPERT_SYSTEM,
        "Frustrated User": _FRUSTRATED_USER_SYSTEM,
        "Business Executive": _BUSINESS_EXECUTIVE_SYSTEM,
    }
    return mapping.get(persona, _FRUSTRATED_USER_SYSTEM)


def _format_context(chunks: list[RetrievalResult]) -> str:
    """Format retrieved chunks into a numbered context block."""
    if not chunks:
        return "No relevant documents retrieved."
    parts = []
    for i, chunk in enumerate(chunks, 1):
        source_label = f"{chunk.source}" + (f" (page {chunk.page})" if chunk.page else "")
        parts.append(
            f"[Document {i} | Source: {source_label} | Relevance: {chunk.similarity:.0%}]\n"
            f"{chunk.content}"
        )
    return "\n\n".join(parts)


def _format_history(history: list[dict]) -> str:
    """Format the last 3 conversation turns for the prompt."""
    recent = history[-3:] if len(history) > 3 else history
    if not recent:
        return "No prior conversation."
    lines = []
    for turn in recent:
        role = turn.get("role", "unknown").capitalize()
        content = turn.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_response(
    query: str,
    persona: str,
    retrieved_chunks: list[RetrievalResult],
    conversation_history: list[dict],
) -> str:
    """
    Generate a persona-adaptive support response grounded in retrieved context.

    Args:
        query: The customer's latest message.
        persona: One of 'Technical Expert', 'Frustrated User', 'Business Executive'.
        retrieved_chunks: Chunks returned by the RAG pipeline.
        conversation_history: Previous conversation turns.

    Returns:
        Generated response string.
    """
    system_prompt = _select_system_prompt(persona)
    context = _format_context(retrieved_chunks)
    history_text = _format_history(conversation_history)

    full_prompt = _RESPONSE_PROMPT_TEMPLATE.format(
        system_prompt=system_prompt,
        context=context,
        query=query,
        history=history_text,
    )

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=1024,
            ),
        )
        answer = response.text.strip()
        logger.info("Generated response (%d chars) for persona=%s", len(answer), persona)
        return answer

    except Exception as exc:
        logger.error("Response generation failed: %s", exc)
        return (
            "I'm sorry, I encountered a technical issue generating a response. "
            "Please try again or contact our support team directly."
        )
