"""
ContractIQ — Streamlit Frontend

Main application entry point with multi-page navigation.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import streamlit as st

# ─────────────────────────────────────────────
# Page Configuration
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="ContractIQ — AI Contract Intelligence",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Custom CSS for premium styling
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Global styling */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0f23 0%, #1a1a3e 100%);
    }

    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown span {
        color: #e0e0ff;
    }

    /* Card styling */
    .metric-card {
        background: linear-gradient(135deg, #1e1e3f 0%, #2a2a5f 100%);
        border: 1px solid rgba(100, 100, 255, 0.2);
        border-radius: 16px;
        padding: 24px;
        margin: 8px 0;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(100, 100, 255, 0.15);
    }

    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }

    .metric-label {
        font-size: 0.85rem;
        color: #8888aa;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 4px;
    }

    /* Upload area */
    .upload-area {
        border: 2px dashed rgba(100, 100, 255, 0.3);
        border-radius: 16px;
        padding: 48px;
        text-align: center;
        background: rgba(30, 30, 63, 0.5);
        transition: border-color 0.3s ease;
    }

    .upload-area:hover {
        border-color: rgba(100, 100, 255, 0.6);
    }

    /* Status badges */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .badge-high { background: rgba(255, 71, 87, 0.2); color: #ff4757; }
    .badge-medium { background: rgba(255, 165, 2, 0.2); color: #ffa502; }
    .badge-low { background: rgba(46, 213, 115, 0.2); color: #2ed573; }
    .badge-uploaded { background: rgba(100, 100, 255, 0.2); color: #6464ff; }
    .badge-processing { background: rgba(255, 165, 2, 0.2); color: #ffa502; }
    .badge-analyzed { background: rgba(46, 213, 115, 0.2); color: #2ed573; }

    /* Header */
    .app-header {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 50%, #2a1a5e 100%);
        padding: 32px;
        border-radius: 20px;
        margin-bottom: 24px;
        border: 1px solid rgba(100, 100, 255, 0.1);
    }

    .app-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }

    .app-subtitle {
        color: #8888bb;
        font-size: 1.1rem;
        margin-top: 8px;
    }

    /* Hide default streamlit elements & auto-generated page navigation */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stSidebarNav"] {display: none !important;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Session State Initialization
# ─────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "dashboard"


def logout():
    """Clear session and log out."""
    st.session_state.authenticated = False
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.current_page = "dashboard"
    st.rerun()


# ─────────────────────────────────────────────
# Authentication Gate
# ─────────────────────────────────────────────
if not st.session_state.authenticated:
    st.markdown("<style>[data-testid='stSidebar'] {display: none !important;}</style>", unsafe_allow_html=True)
    from frontend.pages.login import render_login_page
    render_login_page()
else:
    # ─────────────────────────────────────────
    # Sidebar Navigation
    # ─────────────────────────────────────────
    with st.sidebar:
        st.markdown("## ⚖️ ContractIQ")
        st.markdown(f"👤 **{st.session_state.user.get('full_name', 'User')}**")
        st.markdown(f"📧 {st.session_state.user.get('email', '')}")
        st.divider()

        # Navigation
        nav_items = {
            "dashboard": "📊 Dashboard",
            "upload": "📤 Upload Contract",
            "contracts": "📋 My Contracts",
            "review": "🔍 Review Queue",
            "compare": "🔄 Compare Versions",
            "analytics": "📈 Analytics",
        }

        for key, label in nav_items.items():
            if st.button(
                label,
                key=f"nav_{key}",
                use_container_width=True,
                type="primary" if st.session_state.current_page == key else "secondary",
            ):
                st.session_state.current_page = key
                st.rerun()

        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            logout()

    # ─────────────────────────────────────────
    # Page Router
    # ─────────────────────────────────────────
    page = st.session_state.current_page

    if page == "dashboard":
        from frontend.pages.dashboard import render_dashboard
        render_dashboard()
    elif page == "upload":
        from frontend.pages.upload import render_upload_page
        render_upload_page()
    elif page == "contracts":
        from frontend.pages.contracts import render_contracts_page
        render_contracts_page()
    elif page == "review":
        from frontend.pages.review import render_review_page
        render_review_page()
    elif page == "compare":
        from frontend.pages.compare import render_compare_page
        render_compare_page()
    elif page == "analytics":
        from frontend.pages.analytics import render_analytics_page
        render_analytics_page()
    elif page == "contract_detail":
        from frontend.pages.contract_detail import render_contract_detail_page
        render_contract_detail_page()

