"""
ContractIQ — Login / Signup Page

Authentication page with tabbed login and signup forms.
"""

import streamlit as st
from frontend.utils.api_client import login, signup
from frontend.utils.session import set_auth


def render_login_page():
    """Render the login/signup page."""

    # Centered layout
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # Header
        st.markdown("""
        <div style="text-align: center; padding: 40px 0 20px 0;">
            <h1 style="font-size: 3rem; margin-bottom: 0;">⚖️</h1>
            <h1 class="app-title" style="font-size: 2.5rem;">ContractIQ</h1>
            <p class="app-subtitle">Enterprise AI Contract Intelligence Platform</p>
        </div>
        """, unsafe_allow_html=True)

        # Tabs for Login / Signup
        tab_login, tab_signup = st.tabs(["🔑 Login", "📝 Sign Up"])

        with tab_login:
            st.markdown("#### Welcome Back")
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="you@company.com", key="login_email")
                password = st.text_input("Password", type="password", placeholder="••••••••", key="login_pass")
                submitted = st.form_submit_button("Login", use_container_width=True, type="primary")

                if submitted:
                    if not email or not password:
                        st.error("Please fill in all fields.")
                    else:
                        with st.spinner("Authenticating..."):
                            result = login(email, password)
                            if result:
                                set_auth(
                                    token=result["access_token"],
                                    user=result["user"],
                                )
                                st.success("Login successful!")
                                st.rerun()

        with tab_signup:
            st.markdown("#### Create Account")
            with st.form("signup_form"):
                full_name = st.text_input("Full Name", placeholder="John Doe", key="signup_name")
                email = st.text_input("Email", placeholder="you@company.com", key="signup_email")
                password = st.text_input("Password", type="password", placeholder="Min 8 characters", key="signup_pass")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="••••••••", key="signup_confirm")
                submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")

                if submitted:
                    if not full_name or not email or not password:
                        st.error("Please fill in all fields.")
                    elif password != confirm_password:
                        st.error("Passwords do not match.")
                    elif len(password) < 8:
                        st.error("Password must be at least 8 characters.")
                    else:
                        with st.spinner("Creating account..."):
                            result = signup(email, password, full_name)
                            if result:
                                set_auth(
                                    token=result["access_token"],
                                    user=result["user"],
                                )
                                st.success("Account created successfully!")
                                st.rerun()

        # Footer
        st.markdown("""
        <div style="text-align: center; padding: 40px 0; color: #666;">
            <p style="font-size: 0.8rem;">
                Powered by LangGraph • Multi-Agent AI • FastAPI
            </p>
        </div>
        """, unsafe_allow_html=True)
