"""
ContractIQ — Embedding Service

Text chunking and embedding generation using BAAI/bge-small-en-v1.5.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Lazy-loaded model to avoid loading at import time
_model = None


def _get_model():
    """Lazy-load the embedding model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading embedding model: BAAI/bge-small-en-v1.5")
        _model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        logger.info("Embedding model loaded successfully")
    return _model


# ─────────────────────────────────────────────
# Text Chunking
# ─────────────────────────────────────────────
def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[dict[str, Any]]:
    """
    Split text into overlapping chunks suitable for embedding.

    Args:
        text: Full contract text
        chunk_size: Maximum characters per chunk
        chunk_overlap: Character overlap between consecutive chunks

    Returns:
        List of dicts with keys: text, index, start_char, end_char
    """
    if not text or not text.strip():
        return []

    chunks = []
    start = 0
    index = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence-ending punctuation near the boundary
            search_start = max(end - 100, start)
            last_period = text.rfind(". ", search_start, end)
            last_newline = text.rfind("\n", search_start, end)

            break_point = max(last_period, last_newline)
            if break_point > start:
                end = break_point + 1

        chunk_text_content = text[start:end].strip()
        if chunk_text_content:
            chunks.append({
                "text": chunk_text_content,
                "index": index,
                "start_char": start,
                "end_char": end,
            })
            index += 1

        start = end - chunk_overlap
        if start >= len(text):
            break

    logger.info(f"Chunked text into {len(chunks)} chunks (size={chunk_size}, overlap={chunk_overlap})")
    return chunks


# ─────────────────────────────────────────────
# Embedding Generation
# ─────────────────────────────────────────────
def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of text strings.

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors (384-dim for bge-small-en-v1.5)
    """
    if not texts:
        return []

    model = _get_model()
    # bge models recommend prepending "Represent this sentence:" for retrieval
    prefixed_texts = [f"Represent this sentence: {t}" for t in texts]
    embeddings = model.encode(prefixed_texts, normalize_embeddings=True, show_progress_bar=False)
    return embeddings.tolist()


def generate_query_embedding(query: str) -> list[float]:
    """
    Generate embedding for a search query.

    Args:
        query: Search query text

    Returns:
        Embedding vector (384-dim)
    """
    model = _get_model()
    # bge models recommend prepending "Represent this sentence for searching relevant passages:"
    prefixed = f"Represent this sentence for searching relevant passages: {query}"
    embedding = model.encode([prefixed], normalize_embeddings=True, show_progress_bar=False)
    return embedding[0].tolist()
