"""
app.py - Persona-Adaptive Customer Support Agent
Main Streamlit application entry point.

Orchestrates: Persona Detection → RAG Retrieval → Adaptive Response →
              Escalation Check → Human Handoff Summary
"""

import logging
import sys
import os
import streamlit as st

#   Path setup 
sys.path.insert(0, os.path.dirname(__file__))

from src.classifier import detect_persona
from src.rag_pipeline import ingest_documents, is_knowledge_base_ready, retrieve
from src.generator import generate_response
from src.escalator import evaluate_escalation
from src.handoff import generate_handoff_summary, format_handoff_for_display
from src.config import GOOGLE_API_KEY

#   Logging 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

#   Page config 
st.set_page_config(
    page_title="AI Support Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

#   CSS  ─
st.markdown(
    """
<style>
/* Global font */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Chat bubbles */
.user-message {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 14px 18px;
    border-radius: 18px 18px 4px 18px;
    margin: 8px 0;
    margin-left: 20%;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
    font-size: 14px;
    line-height: 1.6;
}

.assistant-message {
    background: #f8f9fc;
    border: 1px solid #e2e8f0;
    color: #1a202c;
    padding: 14px 18px;
    border-radius: 18px 18px 18px 4px;
    margin: 8px 0;
    margin-right: 20%;
    box-shadow: 0 2px 4px rgba(0,0,0,0.06);
    font-size: 14px;
    line-height: 1.6;
}

/* Persona badges */
.persona-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}

.persona-technical {
    background: #dbeafe;
    color: #1e40af;
    border: 1px solid #bfdbfe;
}

.persona-frustrated {
    background: #fee2e2;
    color: #991b1b;
    border: 1px solid #fecaca;
}

.persona-executive {
    background: #d1fae5;
    color: #065f46;
    border: 1px solid #a7f3d0;
}

/* Confidence bar */
.confidence-container {
    background: #f1f5f9;
    border-radius: 8px;
    padding: 10px 14px;
    margin: 6px 0;
    font-size: 12px;
    color: #64748b;
}

/* Source chip */
.source-chip {
    display: inline-block;
    background: #ede9fe;
    color: #4c1d95;
    border: 1px solid #c4b5fd;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 500;
    margin: 2px 3px;
}

/* Escalation banner */
.escalation-banner {
    background: linear-gradient(135deg, #fff7ed, #fef3c7);
    border: 2px solid #f59e0b;
    border-radius: 12px;
    padding: 16px 20px;
    margin: 12px 0;
}

.escalation-banner h4 {
    color: #92400e;
    margin: 0 0 6px 0;
    font-size: 14px;
}

.escalation-banner p {
    color: #78350f;
    margin: 0;
    font-size: 13px;
}

/* Sidebar stats */
.stat-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 12px 16px;
    margin: 8px 0;
    text-align: center;
}

.stat-label {
    font-size: 11px;
    color: #94a3b8;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.stat-value {
    font-size: 24px;
    font-weight: 700;
    color: #1e293b;
    margin-top: 2px;
}

/* Handoff summary */
.handoff-container {
    background: #0f172a;
    color: #e2e8f0;
    border-radius: 10px;
    padding: 16px;
    font-family: 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.6;
    overflow-x: auto;
}

/* Section headers */
.section-header {
    color: #64748b;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin: 16px 0 8px 0;
}

/* Welcome screen */
.welcome-card {
    background: linear-gradient(135deg, #667eea10, #764ba220);
    border: 1px solid #667eea30;
    border-radius: 16px;
    padding: 32px;
    text-align: center;
    margin: 40px auto;
    max-width: 600px;
}
</style>
""",
    unsafe_allow_html=True,
)


#   Session state initialization 

def init_session_state() -> None:
    """Initialize all session state variables."""
    defaults = {
        "messages": [],          
        "ui_turns": [],           
        "dissatisfaction_count": 0,
        "escalated": False,
        "handoff_summary": None,
        "kb_ready": False,
        "ingestion_done": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


#   Knowledge base setup 

def ensure_knowledge_base() -> bool:
    """
    Check if the knowledge base is ready; ingest if not.
    Returns True if the KB is ready for retrieval.
    """
    if st.session_state.get("kb_ready"):
        return True

    if is_knowledge_base_ready():
        st.session_state["kb_ready"] = True
        return True

    # Need to ingest
    with st.spinner("🔄 Initializing knowledge base — this only runs once…"):
        try:
            n = ingest_documents()
            if n > 0:
                st.session_state["kb_ready"] = True
                st.success(f"✅ Knowledge base ready: {n} document chunks indexed.")
                return True
            else:
                st.error("❌ No documents found in the data/ directory. Add files and restart.")
                return False
        except Exception as exc:
            st.error(f"❌ Knowledge base ingestion failed: {exc}")
            logger.error("Ingestion error: %s", exc, exc_info=True)
            return False


#   UI helpers 

PERSONA_ICONS = {
    "Technical Expert": "🔧",
    "Frustrated User": "😤",
    "Business Executive": "💼",
}

PERSONA_CSS = {
    "Technical Expert": "persona-technical",
    "Frustrated User": "persona-frustrated",
    "Business Executive": "persona-executive",
}

TRIGGER_ICONS = {
    "low_confidence": "📉",
    "no_documents": "📭",
    "sensitive_topic": "🔒",
    "user_dissatisfaction": "😔",
    "none": "✅",
}


def render_persona_badge(persona: str, confidence: float) -> None:
    css_class = PERSONA_CSS.get(persona, "persona-technical")
    icon = PERSONA_ICONS.get(persona, "👤")
    st.markdown(
        f'<span class="persona-badge {css_class}">{icon} {persona}</span>',
        unsafe_allow_html=True,
    )
    st.caption(f"Persona confidence: {confidence:.0%}")


def render_source_chips(sources: list[str]) -> None:
    if not sources:
        return
    chips = " ".join(f'<span class="source-chip">📄 {s}</span>' for s in sources)
    st.markdown(f'<div style="margin:4px 0">{chips}</div>', unsafe_allow_html=True)


def render_confidence_bar(score: float) -> None:
    color = "#10b981" if score >= 0.6 else "#f59e0b" if score >= 0.45 else "#ef4444"
    bar_html = f"""
    <div class="confidence-container">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
            <span>Retrieval Confidence</span>
            <strong style="color:{color}">{score:.0%}</strong>
        </div>
        <div style="background:#e2e8f0;border-radius:4px;height:6px">
            <div style="background:{color};width:{score*100:.0f}%;height:6px;border-radius:4px;transition:width 0.3s"></div>
        </div>
    </div>
    """
    st.markdown(bar_html, unsafe_allow_html=True)


def render_escalation_banner(reason: str, trigger: str) -> None:
    icon = TRIGGER_ICONS.get(trigger, "⚠️")
    st.markdown(
        f"""
<div class="escalation-banner">
    <h4>{icon} Escalated to Human Agent</h4>
    <p>{reason}</p>
</div>
""",
        unsafe_allow_html=True,
    )


#   Sidebar 

def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## 🤖 Support Agent")
        st.caption("Persona-Adaptive AI · Powered by Gemini")
        st.divider()

        # Stats
        turns = st.session_state.get("ui_turns", [])
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f'<div class="stat-card"><div class="stat-label">Messages</div>'
                f'<div class="stat-value">{len(turns)}</div></div>',
                unsafe_allow_html=True,
            )
        with col2:
            dissatisfaction = st.session_state.get("dissatisfaction_count", 0)
            st.markdown(
                f'<div class="stat-card"><div class="stat-label">Frustration</div>'
                f'<div class="stat-value" style="color:{"#ef4444" if dissatisfaction >= 1 else "#10b981"}">'
                f'{dissatisfaction}</div></div>',
                unsafe_allow_html=True,
            )

        st.divider()

        # KB status
        if st.session_state.get("kb_ready"):
            st.success("📚 Knowledge base: Ready")
        else:
            st.warning("📚 Knowledge base: Not loaded")

        if st.session_state.get("escalated"):
            st.error("🚨 Status: Escalated")
        else:
            st.info("✅ Status: Active")

        st.divider()

        # Persona legend
        st.markdown("**Persona Types**")
        st.markdown("🔧 **Technical Expert** — API, auth, debugging")
        st.markdown("😤 **Frustrated User** — Support, complaints")
        st.markdown("💼 **Business Executive** — SLA, impact, costs")

        st.divider()

        # Reset button
        if st.button("🔄 New Conversation", use_container_width=True):
            for key in ["messages", "ui_turns", "dissatisfaction_count", "escalated", "handoff_summary"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

        # Force re-ingest
        if st.button("🗄️ Re-index Knowledge Base", use_container_width=True):
            st.session_state["kb_ready"] = False
            with st.spinner("Re-indexing…"):
                try:
                    n = ingest_documents(force=True)
                    st.session_state["kb_ready"] = True
                    st.success(f"✅ Re-indexed {n} chunks.")
                except Exception as exc:
                    st.error(f"Error: {exc}")

        st.divider()
        st.caption("YourSaaS Product · AI Support v1.0")


#   Chat UI 

def render_chat_history() -> None:
    """Render the complete conversation history."""
    turns = st.session_state.get("ui_turns", [])

    if not turns:
        st.markdown(
            """
<div class="welcome-card">
    <h2 style="color:#1e293b;margin-bottom:12px">👋 Welcome to AI Support</h2>
    <p style="color:#64748b;margin-bottom:20px">
        I'm your intelligent support assistant. I adapt to your communication style 
        and pull from our knowledge base to give you accurate answers.
    </p>
    <p style="color:#94a3b8;font-size:13px">Try asking about login issues, API authentication, 
    billing, password reset, MFA, or subscription plans.</p>
</div>
""",
            unsafe_allow_html=True,
        )
        return

    for turn in turns:
        # User message
        st.markdown(
            f'<div class="user-message">👤 {turn["user_message"]}</div>',
            unsafe_allow_html=True,
        )

        # Metadata row
        meta_col1, meta_col2 = st.columns([2, 3])
        with meta_col1:
            render_persona_badge(turn["persona"], turn["persona_confidence"])
        with meta_col2:
            render_confidence_bar(turn["retrieval_confidence"])

        # Sources
        if turn.get("sources"):
            render_source_chips(turn["sources"])

        # Escalation banner
        if turn.get("escalated"):
            render_escalation_banner(turn["escalation_reason"], turn["escalation_trigger"])

        # Assistant response
        st.markdown(
            f'<div class="assistant-message">🤖 {turn["assistant_message"]}</div>',
            unsafe_allow_html=True,
        )

        # Handoff summary
        if turn.get("handoff_summary"):
            with st.expander("📋 Human Handoff Summary (JSON)", expanded=False):
                st.code(
                    format_handoff_for_display(turn["handoff_summary"]),
                    language="json",
                )

        st.divider()


#   Core processing 

def process_message(user_input: str) -> None:
    """
    Full pipeline for a single user message:
    1. Detect persona
    2. Retrieve context from KB
    3. Evaluate escalation
    4. Generate response (or handoff)
    5. Store results in session state
    """
    conversation_history = st.session_state.get("messages", [])
    dissatisfaction_count = st.session_state.get("dissatisfaction_count", 0)

    with st.spinner("🔍 Analyzing your message…"):
        # Step 1: Persona detection
        persona_result = detect_persona(user_input, conversation_history)
        persona = persona_result["persona"]
        persona_confidence = persona_result["confidence"]

        # Step 2: RAG retrieval
        retrieved_chunks = retrieve(user_input)
        best_similarity = max((c.similarity for c in retrieved_chunks), default=0.0)
        sources = list({c.source for c in retrieved_chunks})

        # Step 3: Escalation evaluation
        escalation = evaluate_escalation(
            message=user_input,
            retrieved_chunks=retrieved_chunks,
            dissatisfaction_count=dissatisfaction_count,
        )
        st.session_state["dissatisfaction_count"] = escalation["dissatisfaction_count"]

        handoff_summary = None

        if escalation["should_escalate"]:
            st.session_state["escalated"] = True

            # Step 4a: Generate empathetic escalation message
            escalation_msg = _build_escalation_message(
                persona, escalation["reason"], escalation["trigger"]
            )

            # Step 5a: Generate handoff summary
            handoff_summary = generate_handoff_summary(
                persona=persona,
                escalation_reason=escalation["reason"],
                conversation_history=conversation_history,
                retrieved_chunks=retrieved_chunks,
                confidence_score=best_similarity,
            )
            st.session_state["handoff_summary"] = handoff_summary
            assistant_message = escalation_msg

        else:
            # Step 4b: Generate adaptive response
            assistant_message = generate_response(
                query=user_input,
                persona=persona,
                retrieved_chunks=retrieved_chunks,
                conversation_history=conversation_history,
            )

    #   Update session state 

    # Append to raw conversation history
    st.session_state["messages"].append({"role": "user", "content": user_input})
    st.session_state["messages"].append({"role": "assistant", "content": assistant_message})

    # Append to UI turns
    st.session_state["ui_turns"].append(
        {
            "user_message": user_input,
            "assistant_message": assistant_message,
            "persona": persona,
            "persona_confidence": persona_confidence,
            "persona_reasoning": persona_result["reasoning"],
            "retrieval_confidence": best_similarity,
            "sources": sources,
            "escalated": escalation["should_escalate"],
            "escalation_reason": escalation.get("reason", ""),
            "escalation_trigger": escalation.get("trigger", "none"),
            "handoff_summary": handoff_summary,
        }
    )


def _build_escalation_message(persona: str, reason: str, trigger: str) -> str:
    """Build a persona-appropriate escalation message for the user."""
    if persona == "Technical Expert":
        return (
            f"I'm transferring this conversation to a senior technical specialist. "
            f"**Reason:** {reason} "
            f"Your full context and conversation history have been packaged and sent to the agent. "
            f"A specialist will reach out shortly to provide the in-depth technical resolution you need."
        )
    elif persona == "Business Executive":
        return (
            f"This issue requires attention from a senior account specialist. "
            f"I've escalated your case with full context to ensure a swift resolution. "
            f"**Reason for escalation:** {reason} "
            f"A member of our enterprise team will contact you within the hour to address this and its business impact."
        )
    else:  # Frustrated User
        return (
            f"I completely understand your frustration, and I want to make sure you get the help you deserve. "
            f"I've escalated your case to one of our senior human agents who will have full context of our conversation. "
            f"You'll hear from them very shortly. I'm sorry this hasn't been resolved faster — we're on it."
        )


#   Main  

def main() -> None:
    init_session_state()

    # Validate API key
    if not GOOGLE_API_KEY:
        st.error(
            "⚠️ **GOOGLE_API_KEY not set.** "
            "Create a `.env` file with your API key (copy `.env.example`) and restart."
        )
        st.stop()

    render_sidebar()

    # Header
    st.markdown("# 🤖 Persona-Adaptive Support Agent")
    st.caption(
        "Powered by Gemini 2.5 Flash · RAG with ChromaDB · Persona Detection · Auto-Escalation"
    )
    st.divider()

    # KB initialization
    kb_ok = ensure_knowledge_base()

    if not kb_ok:
        st.warning(
            "The knowledge base could not be initialized. "
            "Make sure the `data/` directory contains support documents and try again."
        )
        st.stop()

    # Render chat history
    render_chat_history()

    # Already escalated – show persistent notice
    if st.session_state.get("escalated"):
        st.info(
            "🚨 This conversation has been escalated to a human agent. "
            "You can start a new conversation using the sidebar button."
        )

    # Input
    user_input = st.chat_input(
        "Describe your issue… (e.g. 'I can't log in', 'API returning 429', 'Need a refund')",
        disabled=st.session_state.get("escalated", False),
    )

    if user_input and user_input.strip():
        process_message(user_input.strip())
        st.rerun()


if __name__ == "__main__":
    main()
