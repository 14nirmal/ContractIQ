"""
ContractIQ — API Client

HTTP client wrapper for backend API calls with JWT token handling and timeout safeguards.
"""

import os
import httpx
import streamlit as st


def get_backend_url() -> str:
    """Get backend URL dynamically from Streamlit secrets, env vars, or local fallback."""
    url = None
    try:
        if hasattr(st, "secrets") and "BACKEND_URL" in st.secrets:
            url = st.secrets["BACKEND_URL"]
    except Exception:
        pass
    if not url:
        url = os.getenv("BACKEND_URL", "http://localhost:8000")
    return url.strip().rstrip("/")


BACKEND_URL = get_backend_url()


def get_headers() -> dict:
    """Get authorization headers with JWT token."""
    token = st.session_state.get("token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def handle_response(response: httpx.Response) -> dict | list | None:
    """Handle API response with safe JSON parsing and error handling."""
    if response.status_code == 401:
        st.session_state.authenticated = False
        st.session_state.token = None
        st.error("Invalid email or password, or session expired.")
        return None

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", "An error occurred")
        except Exception:
            detail = f"Server status {response.status_code}. Render instances sleep after 15 mins of inactivity. Please wait 20–30 seconds for the backend to finish spinning up, then try again."
        st.error(f"Error: {detail}")
        return None

    if response.status_code == 204:
        return None

    try:
        return response.json()
    except Exception:
        st.error("Backend is initializing. Please wait a few seconds and try again.")
        return None


def safe_request(method: str, endpoint: str, timeout: int = 60, **kwargs) -> dict | list | None:
    """Execute HTTP request with timeout protection and safe error reporting."""
    full_url = f"{BACKEND_URL}{endpoint}"
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(method, full_url, **kwargs)
        return handle_response(response)
    except httpx.TimeoutException:
        st.error("Server connection timed out (Render free instances sleep after 15 minutes). Please wait 15–20 seconds and click again!")
        return None
    except httpx.RequestError as req_err:
        st.error(f"Network error connecting to backend: {req_err}")
        return None
    except Exception as err:
        st.error(f"Request failed: {err}")
        return None


# ─────────────────────────────────────────────
# Auth Endpoints
# ─────────────────────────────────────────────
def signup(email: str, password: str, full_name: str) -> dict | None:
    """Register a new user."""
    return safe_request(
        "POST",
        "/api/signup",
        json={"email": email, "password": password, "full_name": full_name},
        timeout=60,
    )


def login(email: str, password: str) -> dict | None:
    """Authenticate and get JWT token."""
    return safe_request(
        "POST",
        "/api/login",
        json={"email": email, "password": password},
        timeout=60,
    )


# ─────────────────────────────────────────────
# Contract Endpoints
# ─────────────────────────────────────────────
def upload_contract(file) -> dict | None:
    """Upload a contract file."""
    return safe_request(
        "POST",
        "/api/upload",
        files={"file": (file.name, file.getvalue(), file.type)},
        headers=get_headers(),
        timeout=120,
    )


def list_contracts(page: int = 1, page_size: int = 20) -> dict | None:
    """List user's contracts."""
    return safe_request(
        "GET",
        "/api/contracts",
        params={"page": page, "page_size": page_size},
        headers=get_headers(),
        timeout=60,
    )


def get_contract(contract_id: str) -> dict | None:
    """Get contract details."""
    return safe_request(
        "GET",
        f"/api/contract/{contract_id}",
        headers=get_headers(),
        timeout=60,
    )


def delete_contract(contract_id: str) -> bool:
    """Delete a contract."""
    res = safe_request(
        "DELETE",
        f"/api/contract/{contract_id}",
        headers=get_headers(),
        timeout=60,
    )
    return res is not None


def analyze_contract(contract_id: str) -> dict | None:
    """Trigger contract analysis via LangGraph workflow."""
    return safe_request(
        "POST",
        "/api/analyze",
        json={"contract_id": contract_id},
        headers=get_headers(),
        timeout=300,
    )


def ask_question(contract_id: str, question: str) -> dict | None:
    """Ask a question about a contract."""
    return safe_request(
        "POST",
        "/api/ask",
        json={"contract_id": contract_id, "question": question},
        headers=get_headers(),
        timeout=90,
    )


# ─────────────────────────────────────────────
# Dashboard Endpoints
# ─────────────────────────────────────────────
def get_dashboard_stats() -> dict | None:
    """Get dashboard analytics."""
    return safe_request(
        "GET",
        "/api/dashboard",
        headers=get_headers(),
        timeout=60,
    )


# ─────────────────────────────────────────────
# Review Endpoints (Phase 4)
# ─────────────────────────────────────────────
def get_review_queue() -> dict | None:
    """Fetch contracts pending human review."""
    return safe_request(
        "GET",
        "/api/review/queue",
        headers=get_headers(),
        timeout=60,
    )


def submit_review_decision(contract_id: str, decision: str, notes: str | None = None) -> dict | None:
    """Submit a review decision for a contract."""
    return safe_request(
        "POST",
        f"/api/review/{contract_id}/decision",
        json={"decision": decision, "notes": notes},
        headers=get_headers(),
        timeout=60,
    )


# ─────────────────────────────────────────────
# Comparison Endpoints (Phase 4)
# ─────────────────────────────────────────────
def compare_contracts(contract_a_id: str, contract_b_id: str) -> dict | None:
    """Compare two contracts."""
    return safe_request(
        "POST",
        "/api/compare",
        json={"contract_a_id": contract_a_id, "contract_b_id": contract_b_id},
        headers=get_headers(),
        timeout=60,
    )


# ─────────────────────────────────────────────
# Analytics Endpoints (Phase 4)
# ─────────────────────────────────────────────
def get_analytics_metrics() -> dict | None:
    """Get agent execution metrics and model usage stats."""
    return safe_request(
        "GET",
        "/api/analytics/metrics",
        headers=get_headers(),
        timeout=60,
    )


def get_analytics_trends() -> dict | None:
    """Get risk trends, contract type distribution, and audit logs."""
    return safe_request(
        "GET",
        "/api/analytics/trends",
        headers=get_headers(),
        timeout=60,
    )
