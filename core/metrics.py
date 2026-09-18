from __future__ import annotations

from io import BytesIO
from typing import Iterable

import pandas as pd


TYPE_ORDER = ["Journal", "Conference", "Book Chapter", "Book"]
QUARTILES = ["Q1", "Q2", "Q3", "Q4"]


def filter_records(
    frame: pd.DataFrame,
    years: Iterable[int] | None = None,
    faculty: Iterable[str] | None = None,
    publication_types: Iterable[str] | None = None,
    indexing: Iterable[str] | None = None,
    quartiles: Iterable[str] | None = None,
    include_duplicates: bool = True,
) -> pd.DataFrame:
    result = frame.copy()
    if years:
        result = result[result["Calendar Year"].isin(list(years))]
    if faculty:
        result = result[result["Faculty Name"].isin(list(faculty))]
    if publication_types:
        result = result[result["Publication Type"].isin(list(publication_types))]
    if indexing:
        selected = list(indexing)
        mask = pd.Series(False, index=result.index)
        if "SCI/SCIE" in selected:
            mask |= result["SCI_SCIE_Flag"].eq(1)
        if "ESCI" in selected:
            mask |= result["ESCI_Flag"].eq(1)
        if "Scopus" in selected:
            mask |= result["Scopus_Flag"].eq(1)
        result = result[mask]
    if quartiles:
        result = result[result["Quartile"].isin(list(quartiles))]
    if not include_duplicates and "Duplicate Review Decision" in result:
        result = result[result["Duplicate Review Decision"].ne("Exclude")]
    return result


def kpis(frame: pd.DataFrame) -> dict[str, int | float]:
    types = frame["Publication Type"].value_counts()
    impact = pd.to_numeric(frame["Impact Factor"], errors="coerce")
    q1 = int(frame["Q1_Flag"].sum())
    q2 = int(frame["Q2_Flag"].sum())
    return {
        "Total Publications": len(frame),
        "Journal Publications": int(types.get("Journal", 0)),
        "Conference Publications": int(types.get("Conference", 0)),
        "Book Chapters": int(types.get("Book Chapter", 0)),
        "Books": int(types.get("Book", 0)),
        "SCI/SCIE": int(frame["SCI_SCIE_Flag"].sum()),
        "ESCI": int(frame["ESCI_Flag"].sum()),
        "Scopus": int(frame["Scopus_Flag"].sum()),
        "Q1": q1,
        "Q2": q2,
        "Q3": int(frame["Q3_Flag"].sum()),
        "Q4": int(frame["Q4_Flag"].sum()),
        "Q1 + Q2": q1 + q2,
        "Average Impact Factor": float(impact.mean()) if impact.notna().any() else 0.0,
        "Maximum Impact Factor": float(impact.max()) if impact.notna().any() else 0.0,
    }


def faculty_year_matrix(frame: pd.DataFrame, metric: str) -> pd.DataFrame:
    masks = {
        "Total Publications": pd.Series(True, index=frame.index),
        "Journals": frame["Publication Type"].eq("Journal"),
        "Conferences": frame["Publication Type"].eq("Conference"),
        "SCI/SCIE": frame["SCI_SCIE_Flag"].eq(1),
        "Scopus": frame["Scopus_Flag"].eq(1),
        "Q1": frame["Q1_Flag"].eq(1),
        "Q2": frame["Q2_Flag"].eq(1),
        "Q1 + Q2": frame["Q1_Flag"].eq(1) | frame["Q2_Flag"].eq(1),
    }
    selected = frame[masks.get(metric, masks["Total Publications"])]
    if selected.empty:
        return pd.DataFrame()
    table = pd.crosstab(selected["Faculty Name"], selected["Calendar Year"])
    table = table.reindex(sorted(table.columns), axis=1)
    table.columns = [str(int(column)) if float(column).is_integer() else str(column) for column in table.columns]
    table["Total"] = table.sum(axis=1)
    return table.sort_values("Total", ascending=False)


def to_excel_bytes(frame: pd.DataFrame, sheet_name: str = "Publications") -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return buffer.getvalue()
