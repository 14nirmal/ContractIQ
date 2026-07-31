"""
ContractIQ — Retrieval Agent

Handles indexing contract chunks into ChromaDB and retrieval-augmented Q&A.
"""

import json
import logging
from typing import Any

from rag.embeddings import chunk_text
from rag.vector_store import index_chunks
from rag.retriever import retrieve_with_context, retrieve
from gateway.router import route_task

logger = logging.getLogger(__name__)


QA_PROMPT = """You are a legal contract expert answering questions based on contract text.

Use ONLY the provided contract passages to answer the question.
If the answer is not in the passages, say "I cannot find this information in the contract."

Provide your answer as a JSON object with these fields:
- "answer": your detailed answer to the question
- "evidence": an array of relevant text excerpts from the passages that support your answer
- "clause_references": an array of clause types that are relevant (e.g., "Termination", "Payment")
- "confidence": a float between 0.0 and 1.0

Contract Passages:
---
{context}
---

Question: {question}

Return ONLY valid JSON. No markdown, no code fences, no extra text."""


def index_contract(contract_id: str, text: str) -> dict[str, Any]:
    """
    Chunk contract text and index it into ChromaDB.

    Args:
        contract_id: Contract identifier
        text: Full cleaned contract text

    Returns:
        dict with keys: chunks_indexed, chunk_details
    """
    # Chunk the text
    chunks = chunk_text(text, chunk_size=512, chunk_overlap=64)

    if not chunks:
        logger.warning(f"No chunks generated for contract {contract_id}")
        return {"chunks_indexed": 0, "chunk_details": []}

    # Index into ChromaDB
    count = index_chunks(
        contract_id=contract_id,
        chunks=chunks,
        metadata_base={"source": "full_text"},
    )

    logger.info(f"Indexed {count} chunks for contract {contract_id}")

    return {
        "chunks_indexed": count,
        "chunk_details": [
            {"index": c["index"], "length": len(c["text"])}
            for c in chunks
        ],
    }


def answer_question(contract_id: str, question: str) -> dict[str, Any]:
    """
    Answer a question about a contract using RAG.

    Args:
        contract_id: Contract identifier
        question: Natural language question

    Returns:
        dict with keys: answer, evidence, clause_references, confidence,
                        model, provider, tokens_in, tokens_out, latency_ms
    """
    # Retrieve relevant context
    context = retrieve_with_context(contract_id, question, top_k=5)

    prompt = QA_PROMPT.format(context=context, question=question)

    messages = [
        {"role": "system", "content": "You are a legal contract expert. Always respond with valid JSON."},
        {"role": "user", "content": prompt},
    ]

    response = route_task(
        task="qa",
        messages=messages,
        temperature=0.1,
        max_tokens=1024,
    )

    # Parse response
    try:
        content = response["content"].strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)

        return {
            "answer": result.get("answer", "Unable to generate answer."),
            "evidence": result.get("evidence", []),
            "clause_references": result.get("clause_references", []),
            "confidence": max(0.0, min(1.0, float(result.get("confidence", 0.5)))),
            "model": response["model"],
            "provider": response["provider"],
            "tokens_in": response["tokens_in"],
            "tokens_out": response["tokens_out"],
            "latency_ms": response["latency_ms"],
        }

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse Q&A response: {e}")
        return {
            "answer": "Failed to process the question. Please try again.",
            "evidence": [],
            "clause_references": [],
            "confidence": 0.0,
            "model": response.get("model", "unknown"),
            "provider": response.get("provider", "unknown"),
            "tokens_in": response.get("tokens_in", 0),
            "tokens_out": response.get("tokens_out", 0),
            "latency_ms": response.get("latency_ms", 0),
        }
