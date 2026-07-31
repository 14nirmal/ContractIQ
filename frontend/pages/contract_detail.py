"""
ContractIQ — Contract Detail Page (Phase 4)

Multi-tab detailed contract inspector with summary, clauses, risk,
compliance, recommendations, and RAG Q&A assistant.
"""

import streamlit as st
from frontend.utils.api_client import get_contract, ask_question


def render_contract_detail_page():
    """Render the multi-tab contract detail viewer."""

    contract_id = st.session_state.get("selected_contract")
    if not contract_id:
        st.warning("No contract selected. Go to **My Contracts** and click **📄 View** on an analyzed contract.")
        return

    contract = get_contract(contract_id)
    if not contract:
        st.error("Contract not found or access denied.")
        return

    # Header
    risk = contract.get("overall_risk_score", 0) or 0
    risk_class = "high" if risk >= 70 else ("medium" if risk >= 40 else "low")
    file_icon = {"pdf": "📕", "docx": "📘", "txt": "📄"}.get(contract.get("file_type", ""), "📄")

    st.markdown(f"""
    <div class="app-header">
        <h1 class="app-title">{file_icon} {contract['filename']}</h1>
        <p class="app-subtitle">
            {contract.get('contract_type', 'Unknown')} Contract —
            <span class="badge badge-{risk_class}">Risk: {risk:.0f}/100</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Back button
    if st.button("← Back to Contracts"):
        st.session_state.current_page = "contracts"
        st.rerun()

    # Tabs
    tab_overview, tab_clauses, tab_risk, tab_compliance, tab_recs, tab_qa = st.tabs([
        "📋 Overview", "📜 Clauses", "⚠️ Risk Analysis",
        "✅ Compliance", "💡 Recommendations", "💬 Ask AI",
    ])

    clauses = contract.get("clauses", [])
    summary = contract.get("summary") or {}
    recommendations = contract.get("recommendations", [])

    # ── Tab 1: Overview & Summary ──
    with tab_overview:
        if isinstance(summary, dict) and summary.get("executive_summary"):
            st.markdown("### 📋 Executive Summary")
            st.write(summary["executive_summary"])

            col1, col2 = st.columns(2)

            with col1:
                obligations = summary.get("key_obligations", [])
                if obligations:
                    st.markdown("#### 📌 Key Obligations")
                    for ob in obligations:
                        st.markdown(f"- {ob}")

                dates = summary.get("important_dates", [])
                if dates:
                    st.markdown("#### 📅 Important Dates")
                    for d in dates:
                        st.markdown(f"- {d}")

            with col2:
                financial = summary.get("financial_terms", [])
                if financial:
                    st.markdown("#### 💰 Financial Terms")
                    for f in financial:
                        st.markdown(f"- {f}")

                termination = summary.get("termination_conditions", [])
                if termination:
                    st.markdown("#### 🚪 Termination Conditions")
                    for t in termination:
                        st.markdown(f"- {t}")
        else:
            st.info("No summary available. This contract may not have been fully analyzed.")

        # Quick stats
        st.markdown("### 📊 Quick Stats")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        with col_s1:
            st.metric("Total Clauses", len(clauses))
        with col_s2:
            high_count = len([c for c in clauses if c.get("risk_level") == "High"])
            st.metric("High Risk Clauses", high_count)
        with col_s3:
            st.metric("Contract Type", contract.get("contract_type", "—"))
        with col_s4:
            time_ms = contract.get("processing_time_ms", 0) or 0
            st.metric("Processing Time", f"{time_ms / 1000:.1f}s")

    # ── Tab 2: Clauses ──
    with tab_clauses:
        if not clauses:
            st.info("No clauses extracted for this contract.")
        else:
            # Filter
            clause_types = sorted(set(c.get("clause_type", "Unknown") for c in clauses))
            filter_type = st.selectbox("Filter by clause type", ["All"] + clause_types)

            filtered = clauses if filter_type == "All" else [c for c in clauses if c.get("clause_type") == filter_type]

            for i, clause in enumerate(filtered, 1):
                risk_level = clause.get("risk_level") or "Low"
                confidence = clause.get("confidence") or 0.0
                risk_score = clause.get("risk_score") or 0.0
                badge_class = {"High": "high", "Medium": "medium", "Low": "low"}.get(risk_level, "low")

                with st.expander(
                    f"{i}. {clause.get('clause_type', 'Clause')} — "
                    f"Confidence: {confidence:.0%}",
                    expanded=False,
                ):
                    st.markdown(
                        f'<span class="badge badge-{badge_class}">{risk_level}</span> '
                        f'Score: {risk_score:.0f}/100',
                        unsafe_allow_html=True,
                    )
                    st.code(clause.get("text", ""), language=None)

    # ── Tab 3: Risk Analysis ──
    with tab_risk:
        if not clauses:
            st.info("No risk data available.")
        else:
            # Sort by risk score descending
            risk_clauses = sorted(clauses, key=lambda c: c.get("risk_score", 0) or 0, reverse=True)

            for clause in risk_clauses:
                risk_level = clause.get("risk_level", "Low") or "Low"
                risk_score = clause.get("risk_score", 0) or 0
                badge_class = {"High": "high", "Medium": "medium", "Low": "low"}.get(risk_level, "low")

                border_color = {"High": "#ff3c3c", "Medium": "#ff9800", "Low": "#00c853"}.get(risk_level, "#666")

                st.markdown(
                    f'<div style="background: rgba(100,100,255,0.04); border-left: 4px solid {border_color}; '
                    f'padding: 16px; border-radius: 8px; margin-bottom: 12px;">'
                    f'<strong>{clause["clause_type"]}</strong> '
                    f'<span class="badge badge-{badge_class}">{risk_level} — {risk_score:.0f}/100</span><br><br>'
                    f'<strong>Text:</strong> {clause.get("text", "")[:300]}...<br><br>'
                    f'<strong>Explanation:</strong> {clause.get("explanation", "—")}<br>'
                    f'<strong>Impact:</strong> {clause.get("impact", "—")}<br>'
                    f'<strong>Suggested Modification:</strong> {clause.get("suggested_modification", "—")}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Tab 4: Compliance ──
    with tab_compliance:
        if isinstance(summary, dict):
            high_risk_clauses = summary.get("high_risk_clauses", [])
            if high_risk_clauses:
                st.markdown("### ⚠️ High-Risk Clauses Flagged")
                for hrc in high_risk_clauses:
                    st.markdown(f'- 🔴 {hrc}')
            else:
                st.success("✅ No high-risk compliance issues flagged in the summary.")

        # Missing clause check from recommendations
        missing = [r for r in recommendations if isinstance(r, dict) and "missing" in r.get("description", "").lower()]
        if missing:
            st.markdown("### 🔍 Potential Missing Clauses")
            for m in missing:
                st.markdown(f'- ⚠️ {m.get("description", "")}')

        # Overall compliance indicator
        has_high_risk = any(c.get("risk_level") == "High" for c in clauses)
        if has_high_risk:
            st.warning("⚠️ This contract contains high-risk clauses that may require legal review before approval.")
        else:
            st.success("✅ No high-risk clauses detected. Contract appears compliant.")

    # ── Tab 5: Recommendations ──
    with tab_recs:
        if not recommendations:
            st.info("No recommendations generated for this contract.")
        else:
            # Group by priority
            for priority in ["High", "Medium", "Low"]:
                priority_recs = [r for r in recommendations if isinstance(r, dict) and r.get("priority") == priority]
                if priority_recs:
                    badge = {"High": "high", "Medium": "medium", "Low": "low"}[priority]
                    st.markdown(f'### <span class="badge badge-{badge}">{priority} Priority</span>', unsafe_allow_html=True)
                    for rec in priority_recs:
                        category = rec.get("category", "general")
                        clause_ref = rec.get("related_clause", "")
                        clause_text = f" (Clause: {clause_ref})" if clause_ref else ""
                        st.markdown(
                            f'- **[{category.title()}]** {rec.get("description", "")}{clause_text}'
                        )

    # ── Tab 6: RAG Q&A ──
    with tab_qa:
        st.markdown("### 💬 Ask AI About This Contract")
        st.markdown("Ask any question about this contract and get AI-powered answers backed by the contract text.")

        question = st.text_input(
            "Your question",
            placeholder="e.g., What are the termination conditions?",
            key="qa_question",
        )

        if st.button("🔍 Ask", type="primary") and question:
            with st.spinner("Analyzing contract..."):
                answer = ask_question(contract_id, question)

            if answer:
                st.markdown("#### 💡 Answer")
                st.write(answer.get("answer", "No answer available."))

                evidence = answer.get("evidence", [])
                if evidence:
                    st.markdown("#### 📚 Supporting Evidence")
                    for ev in evidence:
                        st.markdown(
                            f'<div style="background: rgba(100,100,255,0.06); padding: 10px; '
                            f'border-radius: 6px; margin-bottom: 6px; font-size: 0.9em;">'
                            f'{ev}</div>',
                            unsafe_allow_html=True,
                        )

                refs = answer.get("clause_references", [])
                if refs:
                    st.markdown(f"**Referenced Clauses:** {', '.join(refs)}")

                conf = answer.get("confidence", 0)
                conf_class = "low" if conf >= 0.7 else ("medium" if conf >= 0.4 else "high")
                st.markdown(
                    f'**Confidence:** <span class="badge badge-{conf_class}">{conf:.0%}</span>',
                    unsafe_allow_html=True,
                )
