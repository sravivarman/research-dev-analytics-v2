from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core.metrics import faculty_year_matrix, kpis
from .components import empty_guard, metric_cards, type_by_year
from .theme import COLORS, style_figure


def render(frame: pd.DataFrame) -> None:
    st.header("Year Analysis")
    if empty_guard(frame):
        return
    years = sorted(int(y) for y in frame["Calendar Year"].dropna().unique())
    if not years:
        st.info("No valid calendar years are available.")
        return
    selected_year = st.selectbox("Select Calendar Year", years, index=len(years) - 1)
    selected = frame[frame["Calendar Year"] == selected_year]
    metric_cards(kpis(selected), ["Total Publications", "Journal Publications", "Conference Publications", "Book Chapters", "Books",
                                        "SCI/SCIE", "ESCI", "Scopus", "Q1", "Q2", "Q3", "Q4"], 6)
    ranking = selected.groupby("Faculty Name").size().sort_values()
    fig = px.bar(
        x=ranking.values,
        y=ranking.index,
        orientation="h",
        labels={"x": "Publications", "y": "Faculty Name"},
        title=f"Faculty Ranking — {selected_year}",
        color_discrete_sequence=[COLORS["Journal"]],
    )
    st.plotly_chart(style_figure(fig), width="stretch")
    type_by_year(frame, "Comparison with Other Calendar Years")
    st.subheader("Faculty × Year Matrix")
    metric = st.selectbox("Matrix metric", ["Total Publications", "Journals", "Conferences", "SCI/SCIE", "Scopus", "Q1", "Q2", "Q1 + Q2"])
    matrix = faculty_year_matrix(frame, metric)
    if matrix.empty:
        st.info("No data is available for this matrix metric.")
    else:
        maximum = max(float(matrix.to_numpy().max()), 1.0)
        styled = matrix.style.map(
            lambda value: f"background-color: rgba(37, 99, 235, {0.12 + 0.70 * float(value) / maximum:.2f}); color: #F8FAFC"
        ).format("{:.0f}")
        st.dataframe(styled, width="stretch")
