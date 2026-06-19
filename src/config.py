"""
config.py - Central configuration for the Persona-Adaptive Support Agent.
Loads environment variables and exposes typed constants used across modules.
"""

import os
from dotenv import load_dotenv

load_dotenv()


# Google / Gemini 
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL: str = "gemini-2.5-flash"
EMBEDDING_MODEL: str = "models/gemini-embedding-001"

# ChromaDB 
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
CHROMA_COLLECTION_NAME: str = "support_knowledge_base"

#  RAG Pipeline
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
MAX_RETRIEVAL_CHUNKS: int = int(os.getenv("MAX_RETRIEVAL_CHUNKS", "3"))

# Escalation 
ESCALATION_CONFIDENCE_THRESHOLD: float = float(
    os.getenv("ESCALATION_CONFIDENCE_THRESHOLD", "0.45")
)
DISSATISFACTION_ESCALATION_LIMIT: int = 2

SENSITIVE_TOPICS: list[str] = [
    "billing",
    "refund",
    "chargeback",
    "legal",
    "account deletion",
    "delete account",
    "fraud",
    "dispute",
]

FRUSTRATION_PHRASES: list[str] = [
    "still not working",
    "nothing helped",
    "i already tried that",
    "this is ridiculous",
    "doesn't work",
    "not working",
    "useless",
    "terrible",
    "horrible",
    "worst",
    "hate this",
    "fed up",
    "completely broken",
]

# Data directory 
DATA_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
