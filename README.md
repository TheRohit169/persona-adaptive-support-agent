# 🤖 Persona-Adaptive Customer Support Agent

> An intelligent AI support agent that detects customer personas, retrieves relevant knowledge using RAG, adapts its communication style, escalates sensitive cases, and generates structured human handoff summaries.

---

## 📋 Project Overview

This project is a production-quality AI Engineering internship project that demonstrates how modern LLM-powered applications are built. It implements a complete customer support pipeline that:

1. **Detects customer persona** from natural language using structured Gemini output
2. **Retrieves relevant context** from a knowledge base using semantic search (RAG)
3. **Adapts its response tone** based on whether the user is a technical expert, frustrated user, or business executive
4. **Escalates automatically** when confidence is low, topics are sensitive, or the user is repeatedly unhappy
5. **Generates structured handoff summaries** so human agents can take over seamlessly
6. **Runs through a Streamlit chat interface** with real-time persona and confidence display

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎭 Persona Detection | Classifies users as Technical Expert, Frustrated User, or Business Executive |
| 📚 RAG Pipeline | Ingests TXT, Markdown, and PDF docs; chunks and embeds with Gemini |
| 🎨 Adaptive Responses | Persona-specific prompts: technical depth, empathy, or executive brevity |
| 🔺 Escalation Engine | Configurable confidence threshold, sensitive topic detection, frustration tracking |
| 📋 Handoff Summaries | Structured JSON for seamless human agent takeover |
| 💬 Streamlit UI | Professional chat interface with persona badges, confidence bars, source chips |
| 🧠 Conversation Memory | Multi-turn context maintained in Streamlit session state |
| 📊 Sentiment Tracking | Frustration phrases detected and escalation counter incremented |

---

## 🏗️ Architecture

```
User Query
    │
    ▼
┌          ─┐
│   Persona Detection │  ← Gemini 2.5 Flash (structured JSON)
│   (classifier.py)   │
└     ┬     ┘
           │ persona + confidence
           ▼
┌          ─┐
│   RAG Retrieval     │  ← Gemini text-embedding-004 + ChromaDB
│   (rag_pipeline.py) │
└     ┬     ┘
           │ top-3 chunks + similarity scores
           ▼
┌          ─┐
│   Escalation Check  │  ← Confidence threshold + sensitive topics + frustration
│   (escalator.py)    │
└     ┬     ┘
           │
    ┌   ┴   ┐
    │             │
    ▼             ▼
Escalate?        No
    │             │
    ▼             ▼
┌    ─┐   ┌          ─┐
│ Handoff │   │  Adaptive Response  │ ← Persona-specific prompt + context
│Summary  │   │  (generator.py)     │
│(JSON)   │   └          ─┘
└    ─┘          │
    │                │
    └    ┬   ─┘
             ▼
     Streamlit UI Response
     (persona badge, confidence bar, sources, response)
```

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| LLM (chat + persona) | Google Gemini 2.5 Flash |
| Embeddings | Gemini text-embedding-004 |
| Vector Store | ChromaDB (persistent local) |
| Document Chunking | LangChain RecursiveCharacterTextSplitter |
| PDF Parsing | pypdf |
| UI | Streamlit |
| Language | Python 3.11+ |

---

## 🚀 Setup Instructions

### Prerequisites

- Python 3.11 or higher
- A [Google AI Studio API key](https://aistudio.google.com/app/apikey)

### 1. Clone or extract the project

```bash
cd persona-support-agent
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
# OR
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set your Google API key:

```env
GOOGLE_API_KEY=your_actual_api_key_here
```

### 5. Run the application

```bash
streamlit run app.py
```

The app will:
1. Start on `http://localhost:8501`
2. Automatically ingest all documents in `data/` into ChromaDB on first run
3. Embeddings are cached in `chroma_db/` — subsequent runs skip ingestion

---

## 🔑 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_API_KEY` | *(required)* | Your Google Gemini API key |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | ChromaDB persistence directory |
| `ESCALATION_CONFIDENCE_THRESHOLD` | `0.45` | Minimum retrieval score before escalation |
| `MAX_RETRIEVAL_CHUNKS` | `3` | Number of top chunks to retrieve per query |
| `CHUNK_SIZE` | `500` | Character size for document chunks |
| `CHUNK_OVERLAP` | `50` | Overlap between consecutive chunks |

---

## 💬 Example Queries

### Technical Expert
- "I'm getting a 401 `invalid_token` error on my OAuth access token refresh. The PKCE flow is completing but the token exchange is returning 400. Logs show `invalid_grant`."
- "My API calls to `/v1/reports/generate` are being throttled at 10 RPM even on the Enterprise plan. What are the burst limits?"
- "SAML assertion validation is failing with `ERR_AUTH_008`. What attributes does the ACS require?"

### Frustrated User
- "This is ridiculous! I can't log in and nothing works. I've tried everything!"
- "I've been locked out of my account for 3 hours and your support is useless."
- "Still not working after clearing cookies. I'm so fed up."

### Business Executive
- "Our team of 15 has been unable to access the dashboard for 2 hours. What is the business impact and resolution timeline?"
- "We're on the Professional plan. What SLA credits are we entitled to for this outage?"
- "We need to upgrade to Enterprise for SSO and audit log compliance. What are the timelines?"

---

## 🔺 Escalation Logic

The escalation engine triggers when **any** of the following conditions are met:

| Trigger | Condition |
|---|---|
| `no_documents` | No relevant chunks retrieved from the KB |
| `low_confidence` | Best retrieval similarity score < 45% (configurable) |
| `sensitive_topic` | Message contains: billing, refund, chargeback, legal, account deletion, fraud |
| `user_dissatisfaction` | Frustration phrases detected in 2+ consecutive messages |

**Frustration phrases tracked:**
> "still not working", "nothing helped", "I already tried that", "this is ridiculous", "doesn't work", "useless", "terrible", "horrible", "fed up", "completely broken"

---

## 📁 Project Structure

```
persona-support-agent/
├  app.py                      # Streamlit app + orchestration
├  requirements.txt            # Python dependencies
├  .env.example                # Environment template
├  README.md                   # This file
│
├  data/                       # Knowledge base documents
│   ├  password_reset_guide.pdf
│   ├  api_authentication_guide.md
│   ├  billing_policy.md
│   ├  refund_policy.md
│   ├  account_security.md
│   ├  login_issues.txt
│   ├  payment_failures.txt
│   ├  api_rate_limits.txt
│   ├  cookie_troubleshooting.txt
│   ├  system_outages.txt
│   ├  email_verification.txt
│   ├  service_sla.txt
│   ├  subscription_upgrade.txt
│   ├  dashboard_access.txt
│   └  multi_factor_auth.txt
│
├  chroma_db/                  # ChromaDB persistence (auto-created)
│
└  src/
    ├  __init__.py
    ├  config.py               # All configuration + env loading
    ├  classifier.py           # Persona detection (Gemini structured JSON)
    ├  rag_pipeline.py         # Document ingestion, embedding, retrieval
    ├  generator.py            # Persona-adaptive response generation
    ├  escalator.py            # Escalation decision engine
    └  handoff.py              # Human handoff summary generation
```

---

## 🔮 Future Improvements

1. **Streaming Responses** — Stream Gemini tokens to the UI for faster perceived response time
2. **Multi-language Support** — Detect customer language and respond in the same language
3. **Ticket Integration** — Auto-create support tickets in Jira/Zendesk on escalation
4. **Analytics Dashboard** — Track persona distribution, escalation rates, confidence trends
5. **Custom Knowledge Bases** — Upload documents directly via the UI without file system access
6. **Feedback Loop** — Thumbs up/down to improve retrieval quality over time
7. **Agent Persona Switching** — Allow agents to override the detected persona
8. **Voice Input** — Integrate Whisper API for voice-to-text support queries
9. **Hybrid Retrieval** — Combine semantic search with BM25 for better recall
10. **A/B Testing** — Test different prompt templates and measure resolution rates

---

## 🏗️ Module Descriptions

| Module | Responsibility |
|---|---|
| `config.py` | Single source of truth for all config; loads from `.env` |
| `classifier.py` | Calls Gemini with a strict JSON schema prompt to classify the user's persona |
| `rag_pipeline.py` | Loads, chunks, embeds, and stores documents; handles retrieval with similarity scoring |
| `generator.py` | Selects persona-appropriate system prompt and generates a grounded response |
| `escalator.py` | Stateless decision function that evaluates all escalation triggers |
| `handoff.py` | Generates a structured JSON summary for human agents using Gemini |

---

## 📜 License

MIT License — feel free to use, modify, and extend for educational or commercial purposes.

---

*Built with ❤️ as an AI Engineering internship project demonstrating production-quality RAG, persona detection, and adaptive AI design.*
