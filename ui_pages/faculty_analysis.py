from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core.metrics import kpis, to_excel_bytes
from core.patent_metrics import patent_excel_bytes
from .components import empty_guard, indexing_by_year, metric_cards, quartile_by_year, type_by_year


def render(
    frame: pd.DataFrame,
    patent_master: pd.DataFrame | None = None,
    patent_attribution: pd.DataFrame | None = None,
) -> None:
    st.header("Faculty Profile")
    st.caption("Individual publication output, indexing coverage and journal-quality profile.")
    if empty_guard(frame):
        return
    faculty = st.selectbox("Select Faculty", sorted(frame["Faculty Name"].dropna().unique()), key="faculty_page_selector")
    selected = frame[frame["Faculty Name"] == faculty]
    st.subheader(faculty)
    values = kpis(selected)
    values["Journals"] = values["Journal Publications"]
    values["Conferences"] = values["Conference Publications"]
    metric_cards(values, ["Total Publications", "Journals", "Conferences", "Book Chapters", "Books",
                                 "SCI/SCIE", "ESCI", "Scopus", "Q1", "Q2", "Q3", "Q4", "Q1 + Q2", "Average Impact Factor"], 5)
    left, right = st.columns(2)
    with left:
        type_by_year(selected, "Publication Trend by Calendar Year")
        quartile_by_year(selected, "Quartile Trend by Calendar Year")
    with right:
        journal_conf = selected[selected["Publication Type"].isin(["Journal", "Conference"])]
        type_by_year(journal_conf, "Journal vs Conference by Calendar Year")
        indexing_by_year(selected, "Indexing by Calendar Year")
    columns = ["Calendar Year", "Publication Type", "Title", "Journal / Outlet Name", "Indexing Raw", "Quartile", "Impact Factor", "DOI",
               "Source Sheet", "Source Row", "Possible Duplicate", "Duplicate Review Decision"]
    st.subheader("Faculty Publication Records")
    st.dataframe(selected[columns], width="stretch", hide_index=True)
    c1, c2 = st.columns(2)
    c1.download_button("Download CSV", selected[columns].to_csv(index=False).encode("utf-8-sig"), f"{faculty}_publications.csv", "text/csv")
    c2.download_button("Download Excel", to_excel_bytes(selected[columns], "Faculty Publications"), f"{faculty}_publications.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    if patent_master is None or patent_attribution is None:
        return
    faculty_links = patent_attribution[patent_attribution["Faculty_Name"].eq(faculty)]
    faculty_patents = patent_master[patent_master["Patent_ID"].isin(faculty_links["Patent_ID"])].copy()
    st.divider()
    st.subheader("Patent Summary")
    patent_values = {
        "Total Patent Credits": int(faculty_links["Patent_ID"].nunique()),
        "Published Patent Credits": int(faculty_patents.loc[faculty_patents["Publication_Date"].notna(), "Patent_ID"].nunique()),
        "Granted Patent Credits": int(faculty_patents.loc[faculty_patents["Granted_Date"].notna(), "Patent_ID"].nunique()),
    }
    metric_cards(patent_values, list(patent_values), desktop_columns=3)
    patent_columns = [
        "Title_of_Patent", "Patent_Number_Raw", "Patent_Type", "Publication_Date", "Granted_Date", "Patent_Status", "Source_Row"
    ]
    if faculty_patents.empty:
        st.info("No patents are credited to this faculty member.")
    else:
        st.dataframe(faculty_patents[patent_columns], width="stretch", hide_index=True)
        c1, c2 = st.columns(2)
        c1.download_button(
            "Download Faculty Patent CSV",
            faculty_patents[patent_columns].to_csv(index=False).encode("utf-8-sig"),
            f"{faculty}_patents.csv",
            "text/csv",
        )
        c2.download_button(
            "Download Faculty Patent Excel",
            patent_excel_bytes(faculty_patents, faculty_links),
            f"{faculty}_patents.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
