"""
ContractIQ — Compare Page (Phase 4)

Side-by-side contract comparison with clause diffs and risk deltas.
"""

import streamlit as st
from frontend.utils.api_client import list_contracts, compare_contracts


def render_compare_page():
    """Render the contract comparison page."""

    st.markdown("""
    <div class="app-header">
        <h1 class="app-title">🔄 Compare Contracts</h1>
        <p class="app-subtitle">Side-by-side clause comparison with risk analysis</p>
    </div>
    """, unsafe_allow_html=True)

    # Fetch user's analyzed contracts
    result = list_contracts(page=1, page_size=100)
    if not result or not result.get("contracts"):
        st.info("Upload and analyze at least two contracts to use comparison.")
        return

    analyzed = [c for c in result["contracts"] if c.get("status") in ["analyzed", "approved", "rejected", "review_pending"]]
    if len(analyzed) < 2:
        st.info("You need at least **2 analyzed contracts** to compare. Go to **My Contracts** and analyze more.")
        return

    # Contract selection
    options = {f"{c['filename']} ({c.get('contract_type', '—')}) — Risk: {(c.get('overall_risk_score') or 0.0):.0f}": c["id"] for c in analyzed}
    labels = list(options.keys())

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 📄 Contract A")
        selection_a = st.selectbox("Select first contract", labels, key="compare_a")
    with col2:
        st.markdown("#### 📄 Contract B")
        default_b = 1 if len(labels) > 1 else 0
        selection_b = st.selectbox("Select second contract", labels, index=default_b, key="compare_b")

    if selection_a == selection_b:
        st.warning("Please select two **different** contracts to compare.")
        return

    if st.button("🔍 Compare", type="primary", use_container_width=True):
        with st.spinner("Comparing contracts..."):
            comparison = compare_contracts(options[selection_a], options[selection_b])

        if not comparison:
            return

        st.markdown("---")

        # Risk score comparison
        risk_a = comparison.get("risk_score_a", 0) or 0
        risk_b = comparison.get("risk_score_b", 0) or 0
        delta = comparison.get("risk_delta", 0)

        st.markdown("### 📊 Risk Score Comparison")
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            risk_class_a = "high" if risk_a >= 70 else ("medium" if risk_a >= 40 else "low")
            st.markdown(
                f'<div class="metric-card">'
                f'<p class="metric-label">Contract A</p>'
                f'<p class="metric-value"><span class="badge badge-{risk_class_a}">{risk_a:.0f}/100</span></p>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_r2:
            risk_class_b = "high" if risk_b >= 70 else ("medium" if risk_b >= 40 else "low")
            st.markdown(
                f'<div class="metric-card">'
                f'<p class="metric-label">Contract B</p>'
                f'<p class="metric-value"><span class="badge badge-{risk_class_b}">{risk_b:.0f}/100</span></p>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_r3:
            delta_icon = "🔺" if delta > 0 else ("🔻" if delta < 0 else "➖")
            delta_color = "#ff3c3c" if delta > 0 else ("#00c853" if delta < 0 else "#888")
            st.markdown(
                f'<div class="metric-card">'
                f'<p class="metric-label">Risk Change</p>'
                f'<p class="metric-value" style="color: {delta_color};">{delta_icon} {delta:+.1f}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Summary
        st.markdown(f"**Summary:** {comparison.get('summary', '')}")

        # Change counters
        st.markdown("### 📋 Change Summary")
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        with col_c1:
            st.metric("Added", comparison.get("total_added", 0))
        with col_c2:
            st.metric("Removed", comparison.get("total_removed", 0))
        with col_c3:
            st.metric("Modified", comparison.get("total_modified", 0))
        with col_c4:
            st.metric("Unchanged", comparison.get("total_unchanged", 0))

        # Clause diffs
        diffs = comparison.get("clause_diffs", [])
        if diffs:
            st.markdown("### 🔀 Clause-Level Differences")
            for diff in diffs:
                change = diff.get("change_type", "unchanged")
                ct = diff.get("clause_type", "Unknown")
                impact = diff.get("risk_impact", "unchanged")

                # Color coding
                colors = {
                    "added": ("#00c853", "✅ Added"),
                    "removed": ("#ff3c3c", "❌ Removed"),
                    "modified": ("#ff9800", "✏️ Modified"),
                    "unchanged": ("#666", "➖ Unchanged"),
                }
                color, label = colors.get(change, ("#666", change))

                impact_tag = ""
                if impact == "increased":
                    impact_tag = "🔴 [Risk ↑]"
                elif impact == "decreased":
                    impact_tag = "🟢 [Risk ↓]"

                with st.expander(f"{label} — {ct} {impact_tag}".strip(), expanded=(change != "unchanged")):
                    if change in ("removed", "modified") and diff.get("text_a"):
                        st.markdown(f"**Contract A** (Risk: {diff.get('risk_a', '—')})")
                        st.code(diff["text_a"][:500], language=None)

                    if change in ("added", "modified") and diff.get("text_b"):
                        st.markdown(f"**Contract B** (Risk: {diff.get('risk_b', '—')})")
                        st.code(diff["text_b"][:500], language=None)
