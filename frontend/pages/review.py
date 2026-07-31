"""
ContractIQ — Review Queue Page (Phase 4)

Human-in-the-loop review interface for flagged contracts.
"""

import streamlit as st
from frontend.utils.api_client import get_review_queue, submit_review_decision


def render_review_page():
    """Render the HITL review queue page."""

    st.markdown("""
    <div class="app-header">
        <h1 class="app-title">🔍 Review Queue</h1>
        <p class="app-subtitle">Contracts flagged for human review</p>
    </div>
    """, unsafe_allow_html=True)

    result = get_review_queue()

    if not result or not result.get("contracts"):
        st.info("🎉 No contracts pending review. All contracts are cleared!")
        return

    contracts = result["contracts"]
    st.markdown(f"**{result['total']}** contract(s) awaiting review")
    st.markdown("---")

    for contract in contracts:
        risk = contract.get("overall_risk_score", 0) or 0
        risk_class = "high" if risk >= 70 else ("medium" if risk >= 40 else "low")
        review_status = contract.get("review_status", "pending")

        with st.expander(
            f"{'📕' if contract.get('file_type') == 'pdf' else '📄'} "
            f"{contract['filename']} — "
            f"Risk: {risk:.0f}/100 | Status: {review_status}",
            expanded=(review_status == "pending"),
        ):
            # Contract info header
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Type:** {contract.get('contract_type', '—')}")
            with col2:
                st.markdown(
                    f'**Risk:** <span class="badge badge-{risk_class}">{risk:.0f}/100</span>',
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(f"**Requires Review:** {'⚠️ Yes' if contract.get('requires_human_review') else 'No'}")

            # Summary
            summary = contract.get("summary") or {}
            if isinstance(summary, dict) and summary.get("executive_summary"):
                st.markdown("#### 📋 Executive Summary")
                st.write(summary["executive_summary"])

            # High-risk clauses
            clauses = contract.get("clauses", [])
            high_risk = [c for c in clauses if c.get("risk_level") == "High"]
            if high_risk:
                st.markdown("#### ⚠️ High-Risk Clauses")
                for clause in high_risk:
                    score = clause.get("risk_score") or 0.0
                    st.markdown(
                        f'<div style="background: rgba(255,60,60,0.08); border-left: 3px solid #ff3c3c; '
                        f'padding: 12px; border-radius: 8px; margin-bottom: 8px;">'
                        f'<strong>{clause["clause_type"]}</strong> — '
                        f'Score: {score:.0f}/100<br>'
                        f'<em>{clause.get("explanation", "")}</em><br>'
                        f'<strong>Suggested:</strong> {clause.get("suggested_modification", "—")}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            # Recommendations
            recommendations = contract.get("recommendations", [])
            if recommendations:
                st.markdown("#### 💡 Recommendations")
                for rec in recommendations[:5]:
                    if isinstance(rec, dict):
                        priority = rec.get("priority", "Medium")
                        badge = "high" if priority == "High" else ("medium" if priority == "Medium" else "low")
                        st.markdown(
                            f'<span class="badge badge-{badge}">{priority}</span> {rec.get("description", "")}',
                            unsafe_allow_html=True,
                        )

            # Decision section
            if review_status == "pending":
                st.markdown("#### ✍️ Your Decision")
                notes = st.text_area(
                    "Review notes (optional)",
                    key=f"notes_{contract['id']}",
                    placeholder="Add any notes about your decision...",
                )

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    if st.button("✅ Approve", key=f"approve_{contract['id']}", use_container_width=True, type="primary"):
                        res = submit_review_decision(contract["id"], "approved", notes)
                        if res:
                            st.success("Contract approved!")
                            st.rerun()
                with col_b:
                    if st.button("🔄 Request Revision", key=f"revise_{contract['id']}", use_container_width=True):
                        res = submit_review_decision(contract["id"], "revision_requested", notes)
                        if res:
                            st.warning("Revision requested.")
                            st.rerun()
                with col_c:
                    if st.button("❌ Reject", key=f"reject_{contract['id']}", use_container_width=True):
                        res = submit_review_decision(contract["id"], "rejected", notes)
                        if res:
                            st.error("Contract rejected.")
                            st.rerun()
            else:
                badge = {"approved": "low", "rejected": "high", "revision_requested": "medium"}.get(review_status, "medium")
                st.markdown(
                    f'**Decision:** <span class="badge badge-{badge}">{review_status.replace("_", " ").title()}</span>',
                    unsafe_allow_html=True,
                )
                if contract.get("review_notes"):
                    st.markdown(f"**Notes:** {contract['review_notes']}")
