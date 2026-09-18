from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core.metrics import TYPE_ORDER, kpis
from core.patent_metrics import patent_kpis
from core.quality_checks import UNMAPPED_HELP, UNRESOLVED_HELP, quality_counts
from .components import empty_guard, indexing_by_year, metric_cards, quartile_by_year, type_by_year
from .theme import COLORS, style_figure


def render(
    frame: pd.DataFrame,
    full_frame: pd.DataFrame | None = None,
    patent_master: pd.DataFrame | None = None,
    patent_attribution: pd.DataFrame | None = None,
) -> None:
    st.header("Executive Overview")
    st.caption("Institutional publication performance by calendar year, faculty contribution and journal quality.")
    full_frame = full_frame if full_frame is not None else frame

    quality = quality_counts(full_frame)
    st.markdown("#### Data Quality Status")
    status = {
        "Unmapped records": quality["Unmapped author records"],
        "Unresolved author mappings": quality["Unresolved author mappings"],
        "Possible duplicates": quality["Possible duplicate rows"],
        "Missing quartiles": quality["Missing journal quartiles"],
    }
    metric_cards(
        status,
        list(status),
        4,
        help_text={
            "Unmapped records": UNMAPPED_HELP,
            "Unresolved author mappings": UNRESOLVED_HELP,
        },
    )
    if any(status.values()):
        st.warning("Review outstanding items on the Data Quality and Author Mapping pages before final reporting.")
    else:
        st.success("All tracked data-quality checks are resolved.")

    if empty_guard(frame):
        return
    values = kpis(frame)
    st.markdown("#### Publication Performance")
    metric_cards(
        values,
        [
            "Total Publications",
            "Journal Publications",
            "Conference Publications",
            "SCI/SCIE",
            "Scopus",
            "Q1",
            "Q2",
            "Q3",
            "Q4",
        ],
        desktop_columns=3,
    )
    excluded = int(
        full_frame.get("Duplicate Review Decision", pd.Series(index=full_frame.index, dtype=str)).eq("Exclude").sum()
    )
    st.markdown(
        f"<div class='info-banner'><b>Source baseline:</b> {len(full_frame):,} rows. "
        "Author consolidations only reassign faculty attribution; they do not change publication totals. "
        f"User-marked duplicate exclusions: {excluded:,}.</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)
    with left:
        type_by_year(frame)
    with right:
        indexing_by_year(frame, "SCI/SCIE, ESCI and Scopus Trend")

    limit = st.selectbox("Faculty chart scope", ["Top 10", "Top 15", "All"], index=0)
    data = frame.groupby(["Faculty Name", "Publication Type"]).size().reset_index(name="Publications")
    totals = data.groupby("Faculty Name")["Publications"].sum().sort_values(ascending=False)
    if limit != "All":
        totals = totals.head(int(limit.split()[1]))
    data = data[data["Faculty Name"].isin(totals.index)]
    fig = px.bar(data, y="Faculty Name", x="Publications", color="Publication Type", orientation="h", barmode="stack",
                 category_orders={"Faculty Name": list(reversed(totals.index.tolist())), "Publication Type": TYPE_ORDER},
                 color_discrete_map=COLORS, title="Faculty-wise Publication Contribution")
    st.plotly_chart(style_figure(fig), width="stretch")

    left, right = st.columns(2)
    with left:
        quartile_by_year(frame)
    with right:
        journals = frame[(frame["Publication Type"] == "Journal") & frame["Quartile"].isin(["Q1", "Q2", "Q3", "Q4"])]
        quartiles = journals.groupby(["Faculty Name", "Quartile"]).size().reset_index(name="Journals")
        faculty_totals = quartiles.groupby("Faculty Name")["Journals"].sum().sort_values(ascending=False).head(15)
        quartiles = quartiles[quartiles["Faculty Name"].isin(faculty_totals.index)]
        fig = px.bar(
            quartiles,
            y="Faculty Name",
            x="Journals",
            color="Quartile",
            orientation="h",
            barmode="stack",
            category_orders={"Faculty Name": list(reversed(faculty_totals.index.tolist())), "Quartile": ["Q1", "Q2", "Q3", "Q4"]},
            color_discrete_map=COLORS,
            title="Faculty-wise Q1/Q2/Q3/Q4",
        )
        st.plotly_chart(style_figure(fig), width="stretch")

    if patent_master is not None and patent_attribution is not None and not patent_master.empty:
        st.divider()
        st.subheader("Patent Summary")
        st.caption("Patents are separate R&D outputs and are not included in Total Publications.")
        metric_cards(
            patent_kpis(patent_master, patent_attribution),
            ["Total Patents", "Published Patents", "Granted Patents", "Faculty Involved"],
            desktop_columns=4,
        )
