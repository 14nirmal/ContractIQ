"""
ContractIQ — Contracts List Page

View and manage all uploaded contracts.
"""

import streamlit as st
from frontend.utils.api_client import list_contracts, get_contract, delete_contract, analyze_contract


def render_contracts_page():
    """Render the contracts list page."""

    # Header
    st.markdown("""
    <div class="app-header">
        <h1 class="app-title">📋 My Contracts</h1>
        <p class="app-subtitle">View and manage your uploaded contracts</p>
    </div>
    """, unsafe_allow_html=True)

    # Fetch contracts
    result = list_contracts(page=1, page_size=50)

    if not result or not result.get("contracts"):
        st.info("No contracts uploaded yet. Go to **Upload Contract** to get started!")
        return

    contracts = result["contracts"]
    total = result["total"]

    st.markdown(f"**{total}** contracts found")
    st.markdown("---")

    # Contract list
    for contract in contracts:
        with st.container():
            col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 1.5, 1.5, 1.5, 1.5])

            with col1:
                file_icons = {"pdf": "📕", "docx": "📘", "txt": "📄"}
                icon = file_icons.get(contract.get("file_type", ""), "📄")
                st.markdown(f"**{icon} {contract['filename']}**")

            with col2:
                ct = contract.get("contract_type")
                st.write(ct if ct else "—")

            with col3:
                status = contract.get("status", "uploaded")
                badge_class = {
                    "uploaded": "uploaded",
                    "processing": "processing",
                    "analyzed": "analyzed",
                    "review_pending": "medium",
                    "approved": "low",
                    "rejected": "high",
                }.get(status, "uploaded")
                st.markdown(
                    f'<span class="badge badge-{badge_class}">{status}</span>',
                    unsafe_allow_html=True,
                )

            with col4:
                risk = contract.get("overall_risk_score")
                if risk is not None:
                    risk_class = "low" if risk < 40 else ("medium" if risk < 70 else "high")
                    st.markdown(
                        f'<span class="badge badge-{risk_class}">{risk:.0f}/100</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.write("—")

            with col5:
                if contract.get("status") == "uploaded":
                    if st.button("🤖 Analyze", key=f"analyze_{contract['id']}", use_container_width=True):
                        with st.spinner("Analyzing..."):
                            analyze_contract(contract["id"])
                        st.rerun()
                elif contract.get("status") in ["analyzed", "approved", "rejected", "review_pending"]:
                    if st.button("📄 View", key=f"view_{contract['id']}", use_container_width=True):
                        st.session_state.selected_contract = contract["id"]
                        st.session_state.current_page = "contract_detail"
                        st.rerun()

            with col6:
                if st.button("🗑️", key=f"delete_{contract['id']}"):
                    if delete_contract(contract["id"]):
                        st.success("Deleted!")
                        st.rerun()

        st.markdown('<hr style="border-color: rgba(100,100,255,0.1);">', unsafe_allow_html=True)
