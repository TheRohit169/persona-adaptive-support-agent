"""
rag_pipeline.py - Complete RAG pipeline for the support knowledge base.

Responsibilities:
  • Ingest TXT, Markdown, and PDF documents from the data/ directory
  • Chunk documents using RecursiveCharacterTextSplitter
  • Generate embeddings with Gemini text-embedding-004
  • Store/retrieve from ChromaDB (persisted locally)
  • Return top-k chunks with similarity scores
"""
import logging
import os
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer
from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from src.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    DATA_DIR,
    MAX_RETRIEVAL_CHUNKS,
)

logger = logging.getLogger(__name__)

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

#   Embedding helper                              ─

def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate local embeddings for document chunks using SentenceTransformer."""
    return embedding_model.encode(texts, convert_to_numpy=True).tolist()

def embed_query(text: str) -> list[float]:
    """Generate local embedding for a user query using SentenceTransformer."""
    return embedding_model.encode(text, convert_to_numpy=True).tolist()

#   Document loaders                              ─

def load_txt(file_path: Path) -> list[Document]:
    """Load a plain-text file as a single Document."""
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        return [
            Document(
                page_content=text,
                metadata={"source": file_path.name, "page": 0, "section": file_path.stem},
            )
        ]
    except Exception as exc:
        logger.error("Failed to load TXT %s: %s", file_path, exc)
        return []


def load_markdown(file_path: Path) -> list[Document]:
    """Load a Markdown file as a single Document."""
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        return [
            Document(
                page_content=text,
                metadata={"source": file_path.name, "page": 0, "section": file_path.stem},
            )
        ]
    except Exception as exc:
        logger.error("Failed to load Markdown %s: %s", file_path, exc)
        return []


def load_pdf(file_path: Path) -> list[Document]:
    """
    Load a PDF file page-by-page using pypdf.
    Each page becomes a separate Document with page metadata.
    """
    docs: list[Document] = []
    try:
        reader = PdfReader(str(file_path))
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                docs.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": file_path.name,
                            "page": page_num + 1,
                            "section": file_path.stem,
                        },
                    )
                )
    except Exception as exc:
        logger.error("Failed to load PDF %s: %s", file_path, exc)
    return docs


#   Ingestion                                  

def load_all_documents(data_dir: str = DATA_DIR) -> list[Document]:
    """
    Walk the data directory and load all supported file types.
    Supported: .txt, .md, .pdf
    """
    documents: list[Document] = []
    data_path = Path(data_dir)

    if not data_path.exists():
        logger.warning("Data directory does not exist: %s", data_dir)
        return documents

    for file_path in sorted(data_path.iterdir()):
        suffix = file_path.suffix.lower()
        if suffix == ".txt":
            documents.extend(load_txt(file_path))
        elif suffix == ".md":
            documents.extend(load_markdown(file_path))
        elif suffix == ".pdf":
            documents.extend(load_pdf(file_path))
        else:
            logger.debug("Skipping unsupported file: %s", file_path.name)

    logger.info("Loaded %d raw documents from %s", len(documents), data_dir)
    return documents


def chunk_documents(documents: list[Document]) -> list[Document]:
    """Split documents into overlapping chunks for better retrieval granularity."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    logger.info("Created %d chunks from %d documents", len(chunks), len(documents))
    return chunks


#   ChromaDB client                               

def get_chroma_client() -> chromadb.PersistentClient:
    """Return a persistent ChromaDB client."""
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)


def get_or_create_collection(client: chromadb.PersistentClient) -> chromadb.Collection:
    """Get the knowledge base collection, creating it if needed."""
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


#   Public API                                 ─

def ingest_documents(force: bool = False) -> int:
    """
    Ingest all documents from the data directory into ChromaDB.

    Args:
        force: If True, drop and rebuild the collection even if it already exists.

    Returns:
        Number of chunks stored.
    """
    client = get_chroma_client()

    if force:
        try:
            client.delete_collection(CHROMA_COLLECTION_NAME)
            logger.info("Dropped existing collection for re-ingestion.")
        except Exception:
            pass

    collection = get_or_create_collection(client)

    # Skip if already populated
    existing = collection.count()
    if existing > 0 and not force:
        logger.info("Collection already has %d chunks. Skipping ingestion.", existing)
        return existing

    documents = load_all_documents()
    if not documents:
        logger.warning("No documents found to ingest.")
        return 0

    chunks = chunk_documents(documents)
    texts = [c.page_content for c in chunks]
    metadatas = [c.metadata for c in chunks]
    ids = [f"chunk_{i}" for i in range(len(chunks))]

    logger.info("Generating embeddings for %d chunks…", len(chunks))
    embeddings = embed_texts(texts)

    collection.add(
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )
    logger.info("Ingested %d chunks into ChromaDB.", len(chunks))
    return len(chunks)


class RetrievalResult:
    """Container for a single retrieved chunk and its metadata."""

    def __init__(
        self,
        content: str,
        source: str,
        page: int,
        section: str,
        distance: float,
    ):
        self.content = content
        self.source = source
        self.page = page
        self.section = section
        # Convert cosine distance [0, 2] → similarity score [0, 1]
        self.similarity = max(0.0, 1.0 - distance / 2.0)

    def __repr__(self) -> str:  # pragma: no cover
        return f"RetrievalResult(source={self.source!r}, similarity={self.similarity:.3f})"


def retrieve(query: str, top_k: int = MAX_RETRIEVAL_CHUNKS) -> list[RetrievalResult]:
    """
    Retrieve the top-k most relevant chunks for a query.

    Args:
        query: The customer's question or message.
        top_k: Number of chunks to return.

    Returns:
        List of RetrievalResult objects sorted by descending similarity.
    """
    try:
        client = get_chroma_client()
        collection = get_or_create_collection(client)

        if collection.count() == 0:
            logger.warning("Collection is empty. Run ingest_documents() first.")
            return []

        query_embedding = embed_query(query)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        retrieved: list[RetrievalResult] = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(docs, metas, distances):
            retrieved.append(
                RetrievalResult(
                    content=doc,
                    source=meta.get("source", "unknown"),
                    page=int(meta.get("page", 0)),
                    section=meta.get("section", ""),
                    distance=float(dist),
                )
            )

        retrieved.sort(key=lambda r: r.similarity, reverse=True)
        logger.info(
            "Retrieved %d chunks; top similarity=%.3f",
            len(retrieved),
            retrieved[0].similarity if retrieved else 0.0,
        )
        return retrieved

    except Exception as exc:
        logger.error("Retrieval failed: %s", exc)
        return []


def is_knowledge_base_ready() -> bool:
    """Return True if the ChromaDB collection is populated and ready."""
    try:
        client = get_chroma_client()
        collection = get_or_create_collection(client)
        return collection.count() > 0
    except Exception:
        return False
