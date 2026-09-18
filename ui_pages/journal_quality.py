from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core.metrics import QUARTILES, kpis
from .components import empty_guard, metric_cards, quartile_by_year
from .theme import COLORS, style_figure


def render(frame: pd.DataFrame) -> None:
    st.header("Journal Quality")
    journals = frame[frame["Publication Type"] == "Journal"]
    if empty_guard(journals):
        return
    values = kpis(journals)
    values["Total Journals"] = values["Journal Publications"]
    values["Q1 + Q2 percentage"] = 100 * values["Q1 + Q2"] / max(values["Total Journals"], 1)
    metric_cards(values, ["Total Journals", "SCI/SCIE", "ESCI", "Scopus", "Q1", "Q2", "Q3", "Q4", "Q1 + Q2",
                                 "Q1 + Q2 percentage", "Average Impact Factor", "Maximum Impact Factor"], 6)
    qdata = journals[journals["Quartile"].isin(QUARTILES)].groupby(["Faculty Name", "Quartile"]).size().reset_index(name="Journals")
    totals = qdata.groupby("Faculty Name")["Journals"].sum().sort_values()
    fig = px.bar(qdata, y="Faculty Name", x="Journals", color="Quartile", orientation="h", barmode="stack",
                 category_orders={"Faculty Name": totals.index.tolist(), "Quartile": QUARTILES}, color_discrete_map=COLORS,
                 title="Faculty-wise Q1/Q2/Q3/Q4")
    st.plotly_chart(style_figure(fig), width="stretch")
    left, right = st.columns(2)
    with left:
        quartile_by_year(journals, "Year-wise Q1/Q2/Q3/Q4")
        sci = journals.groupby("Faculty Name")["SCI_SCIE_Flag"].sum().sort_values()
        fig = px.bar(
            x=sci.values,
            y=sci.index,
            orientation="h",
            labels={"x": "SCI/SCIE Journals", "y": "Faculty Name"},
            title="Faculty-wise SCI/SCIE Publications",
            color_discrete_sequence=[COLORS["SCI/SCIE"]],
        )
        st.plotly_chart(style_figure(fig), width="stretch")
    with right:
        ranking = journals.groupby("Faculty Name")[["Q1_Flag", "Q2_Flag"]].sum().sum(axis=1).sort_values()
        fig = px.bar(
            x=ranking.values,
            y=ranking.index,
            orientation="h",
            labels={"x": "Q1 + Q2 Journals", "y": "Faculty Name"},
            title="Faculty-wise Q1 + Q2 Ranking",
            color_discrete_sequence=[COLORS["Q2"]],
        )
        st.plotly_chart(style_figure(fig), width="stretch")
        impact = pd.to_numeric(journals["Impact Factor"], errors="coerce").dropna()
        fig = px.histogram(impact, nbins=min(20, max(5, len(impact))), labels={"value": "Impact Factor"},
                           title="Impact Factor Distribution", color_discrete_sequence=[COLORS["Scopus"]])
        st.plotly_chart(style_figure(fig), width="stretch")
