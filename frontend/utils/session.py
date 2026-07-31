"""
ContractIQ — Session Management

Streamlit session state utilities.
"""

import streamlit as st


def init_session():
    """Initialize all session state variables."""
    defaults = {
        "authenticated": False,
        "token": None,
        "user": None,
        "current_page": "dashboard",
        "selected_contract": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_auth(token: str, user: dict):
    """Set authentication state after successful login."""
    st.session_state.authenticated = True
    st.session_state.token = token
    st.session_state.user = user


def clear_auth():
    """Clear authentication state."""
    st.session_state.authenticated = False
    st.session_state.token = None
    st.session_state.user = None


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return st.session_state.get("authenticated", False)


def get_token() -> str | None:
    """Get current JWT token."""
    return st.session_state.get("token")


def get_user() -> dict | None:
    """Get current user data."""
    return st.session_state.get("user")
