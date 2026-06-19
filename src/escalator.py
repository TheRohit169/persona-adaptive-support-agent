"""
escalator.py - Configurable escalation engine.

Escalates a conversation to a human agent when:
  1. Retrieval confidence is below the threshold
  2. No relevant documents were found
  3. The query touches a sensitive topic (billing, refund, legal, etc.)
  4. The customer has expressed dissatisfaction across 2+ consecutive interactions
"""

import logging
from typing import Optional, TypedDict

from src.config import (
    DISSATISFACTION_ESCALATION_LIMIT,
    ESCALATION_CONFIDENCE_THRESHOLD,
    FRUSTRATION_PHRASES,
    SENSITIVE_TOPICS,
)
from src.rag_pipeline import RetrievalResult

logger = logging.getLogger(__name__)


class EscalationDecision(TypedDict):
    should_escalate: bool
    reason: str
    trigger: str  # 'low_confidence' | 'no_documents' | 'sensitive_topic' | 'user_dissatisfaction' | 'none'
    dissatisfaction_count: int


def _check_sensitive_topic(message: str) -> Optional[str]:
    """Return the matched sensitive topic keyword if found, else None."""
    lower = message.lower()
    for topic in SENSITIVE_TOPICS:
        if topic in lower:
            return topic
    return None


def _check_frustration(message: str) -> bool:
    """Return True if the message contains frustration indicators."""
    lower = message.lower()
    return any(phrase in lower for phrase in FRUSTRATION_PHRASES)


def _compute_best_similarity(chunks: list[RetrievalResult]) -> float:
    """Return the highest similarity score from retrieved chunks."""
    if not chunks:
        return 0.0
    return max(c.similarity for c in chunks)


def evaluate_escalation(
    message: str,
    retrieved_chunks: list[RetrievalResult],
    dissatisfaction_count: int,
) -> EscalationDecision:
    """
    Decide whether the current interaction warrants human escalation.

    Args:
        message: The latest customer message.
        retrieved_chunks: Chunks returned from the RAG pipeline.
        dissatisfaction_count: Running count of frustrated messages this session.

    Returns:
        EscalationDecision with escalation status, reason, trigger, and updated count.
    """
    # Update dissatisfaction counter
    new_count = dissatisfaction_count
    if _check_frustration(message):
        new_count += 1
        logger.debug("Dissatisfaction count incremented to %d", new_count)

    # Check 1: No documents retrieved 
    if not retrieved_chunks:
        logger.info("Escalating: no relevant documents found.")
        return EscalationDecision(
            should_escalate=True,
            reason="No relevant information was found in the knowledge base for this query.",
            trigger="no_documents",
            dissatisfaction_count=new_count,
        )

    # Check 2: Low retrieval confidence 
    best_similarity = _compute_best_similarity(retrieved_chunks)
    if best_similarity < ESCALATION_CONFIDENCE_THRESHOLD:
        logger.info(
            "Escalating: low retrieval confidence (%.3f < %.3f).",
            best_similarity,
            ESCALATION_CONFIDENCE_THRESHOLD,
        )
        return EscalationDecision(
            should_escalate=True,
            reason=(
                f"Retrieval confidence ({best_similarity:.0%}) is below the threshold "
                f"({ESCALATION_CONFIDENCE_THRESHOLD:.0%}). The answer may not be reliable."
            ),
            trigger="low_confidence",
            dissatisfaction_count=new_count,
        )

    # Check 3: Sensitive topic detected 
    sensitive_match = _check_sensitive_topic(message)
    if sensitive_match:
        logger.info("Escalating: sensitive topic detected ('%s').", sensitive_match)
        return EscalationDecision(
            should_escalate=True,
            reason=(
                f"This query involves a sensitive topic ('{sensitive_match}') "
                "that requires review by a specialist."
            ),
            trigger="sensitive_topic",
            dissatisfaction_count=new_count,
        )

    # Check 4: Persistent user dissatisfaction 
    if new_count >= DISSATISFACTION_ESCALATION_LIMIT:
        logger.info(
            "Escalating: user dissatisfaction threshold reached (%d interactions).", new_count
        )
        return EscalationDecision(
            should_escalate=True,
            reason=(
                f"The customer has expressed dissatisfaction in {new_count} consecutive "
                "interactions. Human intervention is recommended."
            ),
            trigger="user_dissatisfaction",
            dissatisfaction_count=new_count,
        )

    # No escalation needed
    return EscalationDecision(
        should_escalate=False,
        reason="No escalation required.",
        trigger="none",
        dissatisfaction_count=new_count,
    )

