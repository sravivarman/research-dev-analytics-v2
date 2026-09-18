from __future__ import annotations

import pandas as pd
import streamlit as st

from core.metrics import to_excel_bytes


DISPLAY_COLUMNS = ["Faculty Name", "Calendar Year", "Publication Type", "Title", "Journal / Outlet Name", "Indexing Raw", "Quartile",
                   "Impact Factor", "DOI", "Publisher", "Original Authors", "First Bold Author", "Source Sheet", "Source Row",
                   "Possible Duplicate", "Duplicate Classification", "Duplicate Review Decision"]


def render(frame: pd.DataFrame) -> None:
    st.header("Publication Details")
    c1, c2, c3 = st.columns(3)
    title = c1.text_input("Search by title")
    doi = c2.text_input("Search by DOI")
    author = c3.text_input("Search by author")
    result = frame.copy()
    if title:
        result = result[result["Title"].str.contains(title, case=False, na=False, regex=False)]
    if doi:
        result = result[result["DOI"].str.contains(doi, case=False, na=False, regex=False)]
    if author:
        result = result[
            result["Faculty Name"].str.contains(author, case=False, na=False, regex=False)
            | result["Original Authors"].str.contains(author, case=False, na=False, regex=False)
        ]
    st.caption(f"{len(result):,} matching publication records")
    st.dataframe(result[DISPLAY_COLUMNS], width="stretch", hide_index=True, height=540)
    c1, c2 = st.columns(2)
    c1.download_button("Download filtered CSV", result[DISPLAY_COLUMNS].to_csv(index=False).encode("utf-8-sig"), "publication_details.csv", "text/csv")
    c2.download_button("Download filtered Excel", to_excel_bytes(result[DISPLAY_COLUMNS]), "publication_details.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
