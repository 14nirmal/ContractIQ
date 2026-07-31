"""
ContractIQ — Analytics Page (Phase 4)

Interactive analytics dashboard with Plotly charts for agent metrics,
token usage, risk distributions, and audit logs.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from frontend.utils.api_client import get_analytics_metrics, get_analytics_trends


def render_analytics_page():
    """Render the advanced analytics dashboard."""

    st.markdown("""
    <div class="app-header">
        <h1 class="app-title">📈 Analytics</h1>
        <p class="app-subtitle">AI agent performance, model usage, and risk insights</p>
    </div>
    """, unsafe_allow_html=True)

    metrics = get_analytics_metrics()
    trends = get_analytics_trends()

    if not metrics and not trends:
        st.info("No analytics data available yet. Analyze some contracts to generate metrics.")
        return

    # ── Top-level KPI cards ──
    if metrics:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(
                f'<div class="metric-card">'
                f'<div style="font-size: 1.5rem;">📄</div>'
                f'<p class="metric-value">{metrics.get("total_contracts", 0)}</p>'
                f'<p class="metric-label">Total Contracts</p></div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f'<div class="metric-card">'
                f'<div style="font-size: 1.5rem;">🤖</div>'
                f'<p class="metric-value">{metrics.get("total_analyzed", 0)}</p>'
                f'<p class="metric-label">Analyzed</p></div>',
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                f'<div class="metric-card">'
                f'<div style="font-size: 1.5rem;">🔤</div>'
                f'<p class="metric-value">{metrics.get("total_tokens_used", 0):,}</p>'
                f'<p class="metric-label">Tokens Used</p></div>',
                unsafe_allow_html=True,
            )
        with col4:
            agent_count = len(metrics.get("agent_metrics", []))
            st.markdown(
                f'<div class="metric-card">'
                f'<div style="font-size: 1.5rem;">⚙️</div>'
                f'<p class="metric-value">{agent_count}</p>'
                f'<p class="metric-label">Active Agents</p></div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ── Agent Performance Chart ──
    agent_metrics = (metrics or {}).get("agent_metrics", [])
    if agent_metrics:
        st.markdown("### ⚙️ Agent Performance")
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            names = [a["agent_name"] for a in agent_metrics]
            durations = [a["avg_duration_ms"] for a in agent_metrics]

            fig = go.Figure(go.Bar(
                x=durations,
                y=names,
                orientation="h",
                marker=dict(
                    color=durations,
                    colorscale=[[0, "#6366f1"], [0.5, "#8b5cf6"], [1, "#ec4899"]],
                ),
                text=[f"{d:.0f}ms" for d in durations],
                textposition="auto",
            ))
            fig.update_layout(
                title="Avg Latency per Agent (ms)",
                xaxis_title="Milliseconds",
                yaxis_title="",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e0e0e0"),
                height=350,
                margin=dict(l=10, r=10, t=40, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_chart2:
            success_rates = [a["success_rate"] for a in agent_metrics]

            fig2 = go.Figure(go.Bar(
                x=success_rates,
                y=names,
                orientation="h",
                marker=dict(
                    color=["#00c853" if s >= 80 else ("#ff9800" if s >= 50 else "#ff3c3c") for s in success_rates],
                ),
                text=[f"{s:.0f}%" for s in success_rates],
                textposition="auto",
            ))
            fig2.update_layout(
                title="Success Rate per Agent (%)",
                xaxis_title="Success %",
                xaxis=dict(range=[0, 100]),
                yaxis_title="",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e0e0e0"),
                height=350,
                margin=dict(l=10, r=10, t=40, b=10),
            )
            st.plotly_chart(fig2, use_container_width=True)

    # ── Provider Usage Chart ──
    provider_metrics = (metrics or {}).get("provider_metrics", [])
    if provider_metrics:
        st.markdown("### 🌐 Model Provider Usage")
        col_p1, col_p2 = st.columns(2)

        with col_p1:
            labels = [f"{p['provider']}/{p['model'].split('/')[-1]}" for p in provider_metrics]
            tokens = [p["total_tokens"] for p in provider_metrics]

            fig3 = go.Figure(go.Pie(
                labels=labels,
                values=tokens,
                hole=0.45,
                marker=dict(colors=["#6366f1", "#ec4899", "#00c853", "#ff9800"]),
                textinfo="label+percent",
                textfont=dict(color="#e0e0e0"),
            ))
            fig3.update_layout(
                title="Token Distribution by Provider",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e0e0e0"),
                height=350,
                margin=dict(l=10, r=10, t=40, b=10),
                showlegend=False,
            )
            st.plotly_chart(fig3, use_container_width=True)

        with col_p2:
            for p in provider_metrics:
                model_short = p["model"].split("/")[-1]
                st.markdown(
                    f'<div class="metric-card" style="margin-bottom: 8px; padding: 10px;">'
                    f'<strong>{p["provider"]}</strong> / {model_short}<br>'
                    f'Calls: {p["total_calls"]} | '
                    f'Tokens: {p["total_tokens"]:,} | '
                    f'Avg Latency: {p["avg_latency_ms"]:.0f}ms'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("---")

    # ── Risk Distribution ──
    if trends:
        risk_dist = trends.get("risk_distribution", {})
        type_breakdown = trends.get("contract_type_breakdown", [])

        if risk_dist or type_breakdown:
            st.markdown("### 📊 Risk & Contract Insights")
            col_t1, col_t2 = st.columns(2)

            with col_t1:
                if risk_dist:
                    labels = list(risk_dist.keys())
                    values = list(risk_dist.values())
                    colors = {"High": "#ff3c3c", "Medium": "#ff9800", "Low": "#00c853"}

                    fig4 = go.Figure(go.Pie(
                        labels=labels,
                        values=values,
                        hole=0.45,
                        marker=dict(colors=[colors.get(l, "#666") for l in labels]),
                        textinfo="label+value",
                        textfont=dict(color="#e0e0e0"),
                    ))
                    fig4.update_layout(
                        title="Risk Distribution",
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#e0e0e0"),
                        height=350,
                        margin=dict(l=10, r=10, t=40, b=10),
                        showlegend=False,
                    )
                    st.plotly_chart(fig4, use_container_width=True)

            with col_t2:
                if type_breakdown:
                    types = [t["contract_type"] for t in type_breakdown]
                    counts = [t["count"] for t in type_breakdown]
                    avg_risks = [t["avg_risk_score"] for t in type_breakdown]

                    fig5 = go.Figure()
                    fig5.add_trace(go.Bar(
                        x=types, y=counts, name="Count",
                        marker_color="#6366f1",
                        yaxis="y",
                    ))
                    fig5.add_trace(go.Scatter(
                        x=types, y=avg_risks, name="Avg Risk",
                        mode="lines+markers",
                        marker=dict(color="#ec4899", size=10),
                        line=dict(color="#ec4899", width=2),
                        yaxis="y2",
                    ))
                    fig5.update_layout(
                        title="Contract Types & Avg Risk",
                        yaxis=dict(title="Count", side="left"),
                        yaxis2=dict(title="Avg Risk Score", side="right", overlaying="y", range=[0, 100]),
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#e0e0e0"),
                        height=350,
                        margin=dict(l=10, r=10, t=40, b=10),
                        legend=dict(orientation="h", y=-0.15),
                        barmode="group",
                    )
                    st.plotly_chart(fig5, use_container_width=True)

        # ── Audit Logs ──
        audit_logs = trends.get("audit_logs", [])
        if audit_logs:
            st.markdown("### 📝 Audit Trail")
            log_data = []
            for log in audit_logs[:30]:
                log_data.append({
                    "Action": log.get("action", ""),
                    "Resource": log.get("resource_type", "—"),
                    "Timestamp": log.get("timestamp", "")[:19].replace("T", " "),
                })

            st.dataframe(log_data, use_container_width=True, hide_index=True)
