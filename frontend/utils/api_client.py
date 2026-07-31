"""
ContractIQ — API Client

HTTP client wrapper for backend API calls with JWT token handling.
"""

import os
import httpx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def get_headers() -> dict:
    """Get authorization headers with JWT token."""
    token = st.session_state.get("token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def handle_response(response: httpx.Response) -> dict | list | None:
    """Handle API response, raise on errors."""
    if response.status_code == 401:
        st.session_state.authenticated = False
        st.session_state.token = None
        st.error("Session expired. Please log in again.")
        st.rerun()

    if response.status_code >= 400:
        detail = response.json().get("detail", "An error occurred")
        st.error(f"Error: {detail}")
        return None

    if response.status_code == 204:
        return None

    return response.json()


# ─────────────────────────────────────────────
# Auth Endpoints
# ─────────────────────────────────────────────
def signup(email: str, password: str, full_name: str) -> dict | None:
    """Register a new user."""
    with httpx.Client(timeout=30) as client:
        response = client.post(
            f"{BACKEND_URL}/api/signup",
            json={"email": email, "password": password, "full_name": full_name},
        )
    return handle_response(response)


def login(email: str, password: str) -> dict | None:
    """Authenticate and get JWT token."""
    with httpx.Client(timeout=30) as client:
        response = client.post(
            f"{BACKEND_URL}/api/login",
            json={"email": email, "password": password},
        )
    return handle_response(response)


# ─────────────────────────────────────────────
# Contract Endpoints
# ─────────────────────────────────────────────
def upload_contract(file) -> dict | None:
    """Upload a contract file."""
    with httpx.Client(timeout=120) as client:
        response = client.post(
            f"{BACKEND_URL}/api/upload",
            files={"file": (file.name, file.getvalue(), file.type)},
            headers=get_headers(),
        )
    return handle_response(response)


def list_contracts(page: int = 1, page_size: int = 20) -> dict | None:
    """List user's contracts."""
    with httpx.Client(timeout=30) as client:
        response = client.get(
            f"{BACKEND_URL}/api/contracts",
            params={"page": page, "page_size": page_size},
            headers=get_headers(),
        )
    return handle_response(response)


def get_contract(contract_id: str) -> dict | None:
    """Get contract details."""
    with httpx.Client(timeout=30) as client:
        response = client.get(
            f"{BACKEND_URL}/api/contract/{contract_id}",
            headers=get_headers(),
        )
    return handle_response(response)


def delete_contract(contract_id: str) -> bool:
    """Delete a contract."""
    with httpx.Client(timeout=30) as client:
        response = client.delete(
            f"{BACKEND_URL}/api/contract/{contract_id}",
            headers=get_headers(),
        )
    return response.status_code == 204


def analyze_contract(contract_id: str) -> dict | None:
    """Trigger contract analysis via LangGraph workflow."""
    with httpx.Client(timeout=300) as client:
        response = client.post(
            f"{BACKEND_URL}/api/analyze",
            json={"contract_id": contract_id},
            headers=get_headers(),
        )
    return handle_response(response)


def ask_question(contract_id: str, question: str) -> dict | None:
    """Ask a question about a contract."""
    with httpx.Client(timeout=60) as client:
        response = client.post(
            f"{BACKEND_URL}/api/ask",
            json={"contract_id": contract_id, "question": question},
            headers=get_headers(),
        )
    return handle_response(response)


# ─────────────────────────────────────────────
# Dashboard Endpoints
# ─────────────────────────────────────────────
def get_dashboard_stats() -> dict | None:
    """Get dashboard analytics."""
    with httpx.Client(timeout=30) as client:
        response = client.get(
            f"{BACKEND_URL}/api/dashboard",
            headers=get_headers(),
        )
    return handle_response(response)


# ─────────────────────────────────────────────
# Review Endpoints (Phase 4)
# ─────────────────────────────────────────────
def get_review_queue() -> dict | None:
    """Fetch contracts pending human review."""
    with httpx.Client(timeout=30) as client:
        response = client.get(
            f"{BACKEND_URL}/api/review/queue",
            headers=get_headers(),
        )
    return handle_response(response)


def submit_review_decision(contract_id: str, decision: str, notes: str | None = None) -> dict | None:
    """Submit a review decision for a contract."""
    with httpx.Client(timeout=30) as client:
        response = client.post(
            f"{BACKEND_URL}/api/review/{contract_id}/decision",
            json={"decision": decision, "notes": notes},
            headers=get_headers(),
        )
    return handle_response(response)


# ─────────────────────────────────────────────
# Comparison Endpoints (Phase 4)
# ─────────────────────────────────────────────
def compare_contracts(contract_a_id: str, contract_b_id: str) -> dict | None:
    """Compare two contracts."""
    with httpx.Client(timeout=60) as client:
        response = client.post(
            f"{BACKEND_URL}/api/compare",
            json={"contract_a_id": contract_a_id, "contract_b_id": contract_b_id},
            headers=get_headers(),
        )
    return handle_response(response)


# ─────────────────────────────────────────────
# Analytics Endpoints (Phase 4)
# ─────────────────────────────────────────────
def get_analytics_metrics() -> dict | None:
    """Get agent execution metrics and model usage stats."""
    with httpx.Client(timeout=30) as client:
        response = client.get(
            f"{BACKEND_URL}/api/analytics/metrics",
            headers=get_headers(),
        )
    return handle_response(response)


def get_analytics_trends() -> dict | None:
    """Get risk trends, contract type distribution, and audit logs."""
    with httpx.Client(timeout=30) as client:
        response = client.get(
            f"{BACKEND_URL}/api/analytics/trends",
            headers=get_headers(),
        )
    return handle_response(response)

