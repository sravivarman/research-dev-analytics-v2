from __future__ import annotations

import re

import plotly.graph_objects as go


PUBLICATION_TYPE_COLORS = {
    "Journal": "#1D4ED8",
    "Conference": "#0891B2",
    "Book Chapter": "#7C3AED",
    "Book": "#EA580C",
}

INDEXING_COLORS = {
    "SCI/SCIE": "#2563EB",
    "ESCI": "#F59E0B",
    "Scopus": "#10B981",
}

QUARTILE_COLORS = {
    "Q1": "#16A34A",
    "Q2": "#2563EB",
    "Q3": "#F59E0B",
    "Q4": "#DC2626",
}

PATENT_COLORS = {
    "Total Patents": "#7C3AED",
    "Published Patents": "#2563EB",
    "Granted Patents": "#16A34A",
    "Faculty Involved": "#0891B2",
    "Review Required": "#F59E0B",
}

COLORS = {**PUBLICATION_TYPE_COLORS, **INDEXING_COLORS, **QUARTILE_COLORS}

KPI_COLORS = {
    "Total Publications": "#2563EB",
    "Journal Publications": "#0F766E",
    "Journals": "#0F766E",
    "Total Journals": "#0F766E",
    "Conference Publications": "#7C3AED",
    "Conferences": "#7C3AED",
    "SCI/SCIE": "#DC2626",
    "Scopus": "#0284C7",
    "Q1": "#16A34A",
    "Q2": "#2563EB",
    "Q1 + Q2": "#9333EA",
    "ESCI": "#F59E0B",
    "Q3": "#F59E0B",
    "Q4": "#DC2626",
    "Book Chapters": "#475569",
    "Books": "#334155",
    **PATENT_COLORS,
    "Multi-Faculty Patents": "#0F766E",
    "Total Patent Credits": "#7C3AED",
    "Published Patent Credits": "#2563EB",
    "Granted Patent Credits": "#16A34A",
}

_FALLBACK_KPI_COLORS = ["#475569", "#0369A1", "#7C3AED", "#0F766E", "#B45309", "#BE123C"]


def kpi_color(label: str, position: int = 0) -> str:
    if label in KPI_COLORS:
        return KPI_COLORS[label]
    lowered = label.lower()
    semantic = [
        (r"unmapped|invalid|unrecognized", "#DC2626"),
        (r"unresolved|missing", "#D97706"),
        (r"duplicate", "#7C3AED"),
        (r"mapped|processed|source|occurrence", "#0F766E"),
        (r"impact|percentage", "#0369A1"),
    ]
    for pattern, color in semantic:
        if re.search(pattern, lowered):
            return color
    return _FALLBACK_KPI_COLORS[position % len(_FALLBACK_KPI_COLORS)]


def style_figure(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#F8FAFC", "family": "Inter, Segoe UI, sans-serif", "size": 13},
        title={"font": {"color": "#F8FAFC", "size": 19}, "x": 0.01, "xanchor": "left"},
        legend={
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"color": "#E2E8F0"},
            "title": {"font": {"color": "#F8FAFC"}},
        },
        hoverlabel={"bgcolor": "#0F172A", "bordercolor": "#64748B", "font": {"color": "#F8FAFC"}},
        margin={"l": 50, "r": 24, "t": 62, "b": 48},
        bargap=0.22,
        bargroupgap=0.08,
    )
    axis_style = {
        "showgrid": True,
        "gridcolor": "#374151",
        "gridwidth": 1,
        "zerolinecolor": "#4B5563",
        "linecolor": "#4B5563",
        "tickfont": {"color": "#CBD5E1"},
        "title_font": {"color": "#F8FAFC"},
    }
    fig.update_xaxes(**axis_style)
    fig.update_yaxes(**axis_style)
    fig.update_traces(marker_opacity=1.0, marker_line_width=0, selector={"type": "bar"})
    fig.update_traces(marker_opacity=1.0, marker_line_width=0, selector={"type": "histogram"})
    return fig


DASHBOARD_CSS = """
<style>
:root {
    --dashboard-bg: #0B1220;
    --panel-bg: #111827;
    --panel-border: #293548;
    --text-primary: #F8FAFC;
    --text-secondary: #CBD5E1;
}
.stApp, [data-testid="stAppViewContainer"] { background: var(--dashboard-bg); color: var(--text-primary); }
[data-testid="stHeader"] { background: rgba(11, 18, 32, 0.92); }
[data-testid="stSidebar"] { background: #0F172A; border-right: 1px solid var(--panel-border); }
.block-container { max-width: 1500px; padding-top: 1.35rem; padding-bottom: 3rem; }
h1, h2, h3, h4 { color: var(--text-primary) !important; letter-spacing: -0.015em; }
p, .stCaption, [data-testid="stCaptionContainer"] { color: var(--text-secondary); }
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(var(--kpi-columns, 4), minmax(0, 1fr));
    gap: 0.85rem;
    margin: 0.35rem 0 1.15rem 0;
}
.kpi-link { color: inherit !important; text-decoration: none !important; }
.kpi-link:hover .kpi-card { transform: translateY(-1px); box-shadow: 0 10px 24px rgba(0,0,0,0.28); }
.kpi-card {
    min-height: 108px;
    border-radius: 12px;
    padding: 0.95rem 1.05rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    border: 1px solid rgba(255,255,255,0.16);
    box-shadow: 0 8px 20px rgba(0,0,0,0.22);
    overflow: hidden;
}
.kpi-label {
    color: #FFFFFF !important;
    font-size: 0.88rem;
    font-weight: 650;
    line-height: 1.25;
    opacity: 0.98;
}
.kpi-value {
    color: #FFFFFF !important;
    font-size: 2rem;
    font-weight: 800;
    line-height: 1;
    margin-top: 0.65rem;
    letter-spacing: -0.03em;
}
.workbook-banner, .info-banner {
    background: #172033;
    border-left: 4px solid #3B82F6;
    color: #E2E8F0 !important;
    padding: 0.78rem 1rem;
    border-radius: 7px;
    margin: 0.45rem 0 0.95rem 0;
    box-shadow: 0 4px 12px rgba(0,0,0,0.14);
}
.workbook-banner b, .info-banner b { color: #FFFFFF; }
[data-testid="stPlotlyChart"] {
    background: #111827;
    border: 1px solid #293548;
    border-radius: 12px;
    padding: 0.25rem;
    box-shadow: 0 7px 18px rgba(0,0,0,0.16);
}
[data-testid="stDataFrame"] { border: 1px solid #293548; border-radius: 8px; overflow: hidden; }
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div { border-color: #475569; }
@media (max-width: 1050px) {
    .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 600px) {
    .kpi-grid { grid-template-columns: 1fr; gap: 0.65rem; }
    .kpi-card { min-height: 96px; }
    .kpi-value { font-size: 1.75rem; }
}
</style>
"""
