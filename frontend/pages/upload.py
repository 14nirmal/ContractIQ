"""
ContractIQ — Upload Page

Contract upload page with drag-and-drop and processing status.
"""

import streamlit as st
from frontend.utils.api_client import upload_contract, analyze_contract


def render_upload_page():
    """Render the contract upload page."""

    # Header
    st.markdown("""
    <div class="app-header">
        <h1 class="app-title">📤 Upload Contract</h1>
        <p class="app-subtitle">Upload a contract for AI-powered analysis</p>
    </div>
    """, unsafe_allow_html=True)

    # Upload area
    st.markdown("### Select a file to upload")
    st.markdown("Supported formats: **PDF**, **DOCX**, **TXT** (max 20MB)")

    uploaded_file = st.file_uploader(
        "Drop your contract here",
        type=["pdf", "docx", "txt"],
        help="Upload a contract document for AI analysis",
        label_visibility="collapsed",
    )

    if uploaded_file:
        # File preview
        st.markdown("---")
        col1, col2, col3 = st.columns(3)

        with col1:
            file_type = uploaded_file.name.split(".")[-1].upper()
            icons = {"PDF": "📕", "DOCX": "📘", "TXT": "📄"}
            st.markdown(f"**{icons.get(file_type, '📄')} File:** {uploaded_file.name}")

        with col2:
            size_kb = uploaded_file.size / 1024
            if size_kb > 1024:
                st.markdown(f"**📦 Size:** {size_kb/1024:.1f} MB")
            else:
                st.markdown(f"**📦 Size:** {size_kb:.1f} KB")

        with col3:
            st.markdown(f"**📋 Type:** {file_type}")

        st.markdown("---")

        # Upload and analyze buttons
        btn_col1, btn_col2 = st.columns(2)

        with btn_col1:
            if st.button("📤 Upload Only", use_container_width=True):
                with st.spinner("Uploading and extracting text..."):
                    result = upload_contract(uploaded_file)
                    if result:
                        st.success(f"✅ Contract uploaded successfully!")
                        st.json({
                            "Contract ID": result["id"],
                            "Filename": result["filename"],
                            "Status": result["status"],
                            "Type": result.get("contract_type", "Not classified yet"),
                        })
                        st.session_state["last_uploaded_contract_id"] = result["id"]

        with btn_col2:
            if st.button("🚀 Upload & Analyze", use_container_width=True, type="primary"):
                # Step 1: Upload
                with st.spinner("📤 Uploading contract..."):
                    result = upload_contract(uploaded_file)

                if result:
                    st.success("✅ Upload complete!")
                    contract_id = result["id"]

                    # Step 2: Analyze
                    with st.spinner("🤖 Running AI analysis pipeline... This may take 30-60 seconds."):
                        analysis = analyze_contract(contract_id)

                    if analysis:
                        st.success("✅ Analysis complete!")
                        st.balloons()

                        # Show results summary
                        st.markdown("### 📊 Analysis Results")

                        res_col1, res_col2, res_col3 = st.columns(3)
                        with res_col1:
                            ct = analysis.get("contract_type", "Unknown")
                            conf = analysis.get("classification_confidence", 0)
                            st.metric("Contract Type", ct, f"{conf*100:.0f}% confidence")

                        with res_col2:
                            risk = analysis.get("overall_risk_score", 0)
                            risk_label = "🟢 Low" if risk < 40 else ("🟡 Medium" if risk < 70 else "🔴 High")
                            st.metric("Risk Score", f"{risk:.0f}/100", risk_label)

                        with res_col3:
                            status = analysis.get("status", "analyzed")
                            st.metric("Status", status.replace("_", " ").title())

                        # Navigate to contract details
                        st.info("Go to **My Contracts** to view full details, clauses, and risk analysis.")
                    else:
                        st.warning("Analysis is not yet available. It will be enabled after Phase 2.")

    # ─────────────────────────────────────────
    # Quick Tips
    # ─────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 💡 Tips")

    tip_col1, tip_col2, tip_col3 = st.columns(3)

    with tip_col1:
        st.markdown("""
        <div class="metric-card">
            <h4>📄 Supported Types</h4>
            <p style="color: #aaa;">NDA, Employment, Lease, Vendor, Service, Partnership, Licensing, Consulting</p>
        </div>
        """, unsafe_allow_html=True)

    with tip_col2:
        st.markdown("""
        <div class="metric-card">
            <h4>🤖 AI Analysis</h4>
            <p style="color: #aaa;">Our multi-agent AI extracts clauses, analyzes risks, and generates recommendations.</p>
        </div>
        """, unsafe_allow_html=True)

    with tip_col3:
        st.markdown("""
        <div class="metric-card">
            <h4>🔒 Privacy</h4>
            <p style="color: #aaa;">PII is automatically masked before sending to AI models. Your data stays private.</p>
        </div>
        """, unsafe_allow_html=True)
