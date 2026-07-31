"""
ContractIQ — Vector Store (ChromaDB)

Manages ChromaDB collections for contract clause storage and retrieval.
"""

import logging
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.config import get_settings
from rag.embeddings import generate_embeddings

settings = get_settings()
logger = logging.getLogger(__name__)

# Lazy-loaded ChromaDB client
_client = None


def _get_client() -> chromadb.ClientAPI:
    """Get or create the ChromaDB persistent client."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info(f"ChromaDB client initialized at {settings.CHROMA_PERSIST_DIR}")
    return _client


def get_or_create_collection(contract_id: str) -> chromadb.Collection:
    """
    Get or create a ChromaDB collection for a specific contract.
    Each contract gets its own collection for isolation.
    """
    client = _get_client()
    collection_name = f"contract_{contract_id.replace('-', '_')[:50]}"
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"contract_id": contract_id, "hnsw:space": "cosine"},
    )
    return collection


def index_chunks(
    contract_id: str,
    chunks: list[dict[str, Any]],
    metadata_base: dict | None = None,
) -> int:
    """
    Index text chunks into ChromaDB for a specific contract.

    Args:
        contract_id: Contract identifier
        chunks: List of chunk dicts from embeddings.chunk_text()
        metadata_base: Additional metadata to attach to each chunk

    Returns:
        Number of chunks indexed
    """
    if not chunks:
        return 0

    collection = get_or_create_collection(contract_id)

    # Extract texts and generate embeddings
    texts = [c["text"] for c in chunks]
    embeddings = generate_embeddings(texts)

    # Prepare data for ChromaDB
    ids = [f"{contract_id}_chunk_{c['index']}" for c in chunks]
    metadatas = []
    for c in chunks:
        meta = {
            "contract_id": contract_id,
            "chunk_index": c["index"],
            "start_char": c["start_char"],
            "end_char": c["end_char"],
        }
        if metadata_base:
            meta.update(metadata_base)
        metadatas.append(meta)

    # Upsert into ChromaDB
    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    logger.info(f"Indexed {len(chunks)} chunks for contract {contract_id}")
    return len(chunks)


def delete_contract_index(contract_id: str) -> bool:
    """Delete the ChromaDB collection for a contract."""
    try:
        client = _get_client()
        collection_name = f"contract_{contract_id.replace('-', '_')[:50]}"
        client.delete_collection(collection_name)
        logger.info(f"Deleted ChromaDB collection for contract {contract_id}")
        return True
    except Exception as e:
        logger.warning(f"Failed to delete collection for {contract_id}: {e}")
        return False
