from __future__ import annotations

from html import escape
from numbers import Integral, Real

import pandas as pd
import plotly.express as px
import streamlit as st

from core.metrics import QUARTILES, TYPE_ORDER
from .theme import COLORS, kpi_color, style_figure


def section_title(title: str, subtitle: str | None = None) -> None:
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)


def metric_cards(
    values: dict[str, object],
    labels: list[str],
    columns: int = 5,
    links: dict[str, str] | None = None,
    help_text: dict[str, str] | None = None,
    desktop_columns: int | None = None,
) -> None:
    del columns  # CSS controls responsive wrapping and keeps card heights aligned.
    links = links or {}
    help_text = help_text or {}
    cards: list[str] = []
    for position, label in enumerate(labels):
        value = values.get(label, 0)
        if isinstance(value, Integral):
            display = f"{int(value):,}"
        elif isinstance(value, Real):
            display = f"{float(value):,.2f}"
        else:
            display = str(value)
        card = (
            f'<div class="kpi-card" title="{escape(help_text.get(label, ''), quote=True)}" '
            f'style="background:{kpi_color(label, position)}">'
            f'<div class="kpi-label">{escape(label)}</div>'
            f'<div class="kpi-value">{escape(display)}</div></div>'
        )
        if label in links:
            card = f'<a class="kpi-link" href="{escape(links[label], quote=True)}">{card}</a>'
        cards.append(card)
    grid_style = f' style="--kpi-columns:{desktop_columns}"' if desktop_columns else ""
    st.markdown(f'<div class="kpi-grid"{grid_style}>{"".join(cards)}</div>', unsafe_allow_html=True)


def type_by_year(frame: pd.DataFrame, title: str = "Publication Output by Calendar Year") -> None:
    data = frame.dropna(subset=["Calendar Year"]).groupby(["Calendar Year", "Publication Type"]).size().reset_index(name="Publications")
    fig = px.bar(data, x="Calendar Year", y="Publications", color="Publication Type", barmode="stack",
                 category_orders={"Publication Type": TYPE_ORDER}, color_discrete_map=COLORS, title=title)
    st.plotly_chart(style_figure(fig), width="stretch")


def quartile_by_year(frame: pd.DataFrame, title: str = "Journal Quartile Distribution by Year") -> None:
    journals = frame[(frame["Publication Type"] == "Journal") & frame["Quartile"].isin(QUARTILES)]
    data = journals.groupby(["Calendar Year", "Quartile"]).size().reset_index(name="Journals")
    fig = px.bar(data, x="Calendar Year", y="Journals", color="Quartile", barmode="stack",
                 category_orders={"Quartile": QUARTILES}, color_discrete_map=COLORS, title=title)
    st.plotly_chart(style_figure(fig), width="stretch")


def indexing_by_year(frame: pd.DataFrame, title: str = "Indexing Trend") -> None:
    rows = []
    for year, group in frame.dropna(subset=["Calendar Year"]).groupby("Calendar Year"):
        rows.extend([
            {"Calendar Year": year, "Indexing": "SCI/SCIE", "Publications": int(group["SCI_SCIE_Flag"].sum())},
            {"Calendar Year": year, "Indexing": "ESCI", "Publications": int(group["ESCI_Flag"].sum())},
            {"Calendar Year": year, "Indexing": "Scopus", "Publications": int(group["Scopus_Flag"].sum())},
        ])
    data = pd.DataFrame(rows, columns=["Calendar Year", "Indexing", "Publications"])
    fig = px.bar(data, x="Calendar Year", y="Publications", color="Indexing", barmode="group",
                 color_discrete_map=COLORS, title=title)
    st.plotly_chart(style_figure(fig), width="stretch")


def empty_guard(frame: pd.DataFrame) -> bool:
    if frame.empty:
        st.info("No publication records match the current filters.")
        return True
    return False
