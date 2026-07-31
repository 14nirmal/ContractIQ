"""
ContractIQ — Dashboard Page

Main dashboard with Plotly charts and key metrics.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from frontend.utils.api_client import get_dashboard_stats


def create_metric_card(label: str, value: str, icon: str) -> str:
    """Generate HTML for a metric card."""
    return f"""
    <div class="metric-card">
        <div style="font-size: 1.5rem; margin-bottom: 8px;">{icon}</div>
        <p class="metric-value">{value}</p>
        <p class="metric-label">{label}</p>
    </div>
    """


def render_dashboard():
    """Render the dashboard page."""

    # Header
    st.markdown("""
    <div class="app-header">
        <h1 class="app-title">📊 Dashboard</h1>
        <p class="app-subtitle">Real-time contract intelligence analytics</p>
    </div>
    """, unsafe_allow_html=True)

    # Fetch dashboard data
    stats = get_dashboard_stats()

    if not stats:
        # Show empty state with placeholder metrics
        stats = {
            "total_contracts": 0,
            "contracts_analyzed": 0,
            "average_risk_score": 0.0,
            "high_risk_contracts": 0,
            "pending_reviews": 0,
            "avg_processing_time_ms": 0,
            "total_tokens_used": 0,
            "risk_distribution": {},
            "contract_type_distribution": {},
            "recent_uploads": [],
            "model_usage": {},
        }

    # ─────────────────────────────────────────
    # Key Metrics Row
    # ─────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(create_metric_card(
            "Total Contracts",
            str(stats["total_contracts"]),
            "📄"
        ), unsafe_allow_html=True)

    with col2:
        st.markdown(create_metric_card(
            "Analyzed",
            str(stats["contracts_analyzed"]),
            "✅"
        ), unsafe_allow_html=True)

    with col3:
        risk_score = stats["average_risk_score"]
        st.markdown(create_metric_card(
            "Avg Risk Score",
            f"{risk_score:.1f}",
            "⚠️"
        ), unsafe_allow_html=True)

    with col4:
        st.markdown(create_metric_card(
            "High Risk",
            str(stats["high_risk_contracts"]),
            "🔴"
        ), unsafe_allow_html=True)

    with col5:
        st.markdown(create_metric_card(
            "Pending Reviews",
            str(stats["pending_reviews"]),
            "👁️"
        ), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ─────────────────────────────────────────
    # Charts Row
    # ─────────────────────────────────────────
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("#### Risk Distribution")
        risk_dist = stats.get("risk_distribution", {})
        if risk_dist:
            colors = {"high": "#ff4757", "medium": "#ffa502", "low": "#2ed573"}
            fig = go.Figure(data=[go.Pie(
                labels=[k.capitalize() for k in risk_dist.keys()],
                values=list(risk_dist.values()),
                hole=0.6,
                marker_colors=[colors.get(k, "#667eea") for k in risk_dist.keys()],
                textinfo="label+percent",
                textfont=dict(color="white", size=14),
            )])
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
                showlegend=False,
                height=350,
                margin=dict(t=20, b=20, l=20, r=20),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No risk data available yet. Upload and analyze contracts to see distribution.")

    with chart_col2:
        st.markdown("#### Contract Types")
        type_dist = stats.get("contract_type_distribution", {})
        if type_dist:
            fig = go.Figure(data=[go.Bar(
                x=list(type_dist.keys()),
                y=list(type_dist.values()),
                marker=dict(
                    color=list(type_dist.values()),
                    colorscale=[[0, "#667eea"], [1, "#764ba2"]],
                ),
                text=list(type_dist.values()),
                textposition="auto",
                textfont=dict(color="white"),
            )])
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="rgba(100,100,255,0.1)"),
                height=350,
                margin=dict(t=20, b=40, l=40, r=20),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No contract type data yet. Upload and analyze contracts to see breakdown.")

    # ─────────────────────────────────────────
    # Secondary Metrics & Model Usage
    # ─────────────────────────────────────────
    sec_col1, sec_col2 = st.columns(2)

    with sec_col1:
        st.markdown("#### Model Usage")
        model_usage = stats.get("model_usage", {})
        if model_usage:
            models = list(model_usage.keys())
            calls = [v["calls"] for v in model_usage.values()]
            tokens = [v["tokens"] for v in model_usage.values()]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="API Calls",
                x=models, y=calls,
                marker_color="#667eea",
                text=calls, textposition="auto",
                textfont=dict(color="white"),
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="rgba(100,100,255,0.1)"),
                height=350,
                margin=dict(t=20, b=40, l=40, r=20),
                barmode="group",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No model usage data yet.")

    with sec_col2:
        st.markdown("#### Performance")
        perf_col1, perf_col2 = st.columns(2)
        with perf_col1:
            avg_time = stats.get("avg_processing_time_ms", 0)
            if avg_time > 0:
                st.metric("Avg Processing Time", f"{avg_time/1000:.1f}s")
            else:
                st.metric("Avg Processing Time", "—")
        with perf_col2:
            total_tokens = stats.get("total_tokens_used", 0)
            if total_tokens > 1000:
                st.metric("Total Tokens", f"{total_tokens/1000:.1f}K")
            else:
                st.metric("Total Tokens", str(total_tokens))

    # ─────────────────────────────────────────
    # Recent Uploads Table
    # ─────────────────────────────────────────
    st.markdown("#### Recent Uploads")
    recent = stats.get("recent_uploads", [])
    if recent:
        for contract in recent:
            risk = contract.get("overall_risk_score")
            risk_class = "low"
            if risk and risk > 70:
                risk_class = "high"
            elif risk and risk > 40:
                risk_class = "medium"

            status = contract.get("status", "uploaded")
            c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 1])
            with c1:
                st.write(f"📄 {contract.get('filename', 'Unknown')}")
            with c2:
                st.write(contract.get("contract_type", "—"))
            with c3:
                st.markdown(f'<span class="badge badge-{status}">{status}</span>', unsafe_allow_html=True)
            with c4:
                if risk is not None:
                    st.markdown(f'<span class="badge badge-{risk_class}">Risk: {risk:.0f}</span>', unsafe_allow_html=True)
                else:
                    st.write("—")
            with c5:
                if contract.get("status") in ["analyzed", "approved", "rejected", "review_pending"]:
                    if st.button("📄 View", key=f"dash_view_{contract['id']}", use_container_width=True):
                        st.session_state.selected_contract = contract["id"]
                        st.session_state.current_page = "contract_detail"
                        st.rerun()
                else:
                    st.write(contract.get("file_type", "").upper())
    else:
        st.info("No contracts uploaded yet. Go to **Upload Contract** to get started!")
