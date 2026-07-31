"""
ContractIQ — RAG Retriever

Semantic search over contract chunks stored in ChromaDB.
"""

import logging
from typing import Any

from rag.embeddings import generate_query_embedding
from rag.vector_store import get_or_create_collection

logger = logging.getLogger(__name__)


def retrieve(
    contract_id: str,
    query: str,
    top_k: int = 5,
    where_filter: dict | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve the most relevant chunks from a contract's vector store.

    Args:
        contract_id: Contract identifier
        query: Natural language query
        top_k: Number of results to return
        where_filter: Optional ChromaDB metadata filter

    Returns:
        List of result dicts with keys: text, score, metadata
    """
    collection = get_or_create_collection(contract_id)

    # Check if collection has any documents
    if collection.count() == 0:
        logger.warning(f"No chunks indexed for contract {contract_id}")
        return []

    # Generate query embedding
    query_embedding = generate_query_embedding(query)

    # Build query kwargs
    query_kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": min(top_k, collection.count()),
    }
    if where_filter:
        query_kwargs["where"] = where_filter

    # Query ChromaDB
    results = collection.query(**query_kwargs)

    # Format results
    formatted = []
    if results and results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            score = 0.0
            if results["distances"] and results["distances"][0]:
                # ChromaDB returns distances; convert to similarity (cosine distance → similarity)
                score = max(0, 1 - results["distances"][0][i])

            metadata = {}
            if results["metadatas"] and results["metadatas"][0]:
                metadata = results["metadatas"][0][i]

            formatted.append({
                "text": doc,
                "score": round(score, 4),
                "metadata": metadata,
            })

    logger.info(f"Retrieved {len(formatted)} chunks for query on contract {contract_id}")
    return formatted


def retrieve_with_context(
    contract_id: str,
    query: str,
    top_k: int = 5,
) -> str:
    """
    Retrieve relevant chunks and format them as context string for LLM.

    Args:
        contract_id: Contract identifier
        query: Natural language query
        top_k: Number of results

    Returns:
        Formatted context string
    """
    results = retrieve(contract_id, query, top_k)

    if not results:
        return "No relevant context found in the contract."

    context_parts = []
    for i, r in enumerate(results, 1):
        score = r["score"]
        text = r["text"]
        context_parts.append(f"[Passage {i} | Relevance: {score:.2f}]\n{text}")

    return "\n\n---\n\n".join(context_parts)
