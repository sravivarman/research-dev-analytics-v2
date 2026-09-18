from __future__ import annotations

from io import BytesIO
from typing import Iterable

import pandas as pd


def filter_patents(
    master: pd.DataFrame,
    attribution: pd.DataFrame,
    publication_years: Iterable[int] | None = None,
    granted_years: Iterable[int] | None = None,
    faculty: Iterable[str] | None = None,
    patent_types: Iterable[str] | None = None,
    statuses: Iterable[str] | None = None,
    include_duplicates: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    result_master, result_attribution = master.copy(), attribution.copy()
    if publication_years:
        result_master = result_master[result_master["Publication_Year"].isin(list(publication_years))]
    if granted_years:
        result_master = result_master[result_master["Granted_Year"].isin(list(granted_years))]
    if patent_types:
        result_master = result_master[result_master["Patent_Type"].isin(list(patent_types))]
    if statuses:
        result_master = result_master[result_master["Patent_Status"].isin(list(statuses))]
    if not include_duplicates:
        result_master = result_master[result_master["Patent_Duplicate_Review_Decision"].ne("Exclude")]
    result_attribution = result_attribution[result_attribution["Patent_ID"].isin(result_master["Patent_ID"])]
    if faculty:
        result_attribution = result_attribution[result_attribution["Faculty_Name"].isin(list(faculty))]
        result_master = result_master[result_master["Patent_ID"].isin(result_attribution["Patent_ID"])]
    return result_master, result_attribution


def patent_kpis(master: pd.DataFrame, attribution: pd.DataFrame) -> dict[str, int]:
    counts = attribution.groupby("Patent_ID")["Faculty_Name"].nunique() if not attribution.empty else pd.Series(dtype=int)
    return {
        "Total Patents": int(master["Patent_ID"].nunique()),
        "Published Patents": int(master.loc[master["Publication_Date"].notna(), "Patent_ID"].nunique()),
        "Granted Patents": int(master.loc[master["Granted_Date"].notna(), "Patent_ID"].nunique()),
        "Faculty Involved": int(attribution["Faculty_Name"].nunique()),
        "Multi-Faculty Patents": int(counts.gt(1).sum()),
        "Review Required": int(master["Attribution_Status"].eq("REVIEW REQUIRED").sum()),
    }


def patent_excel_bytes(master: pd.DataFrame, attribution: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        master.to_excel(writer, index=False, sheet_name="Patent Master")
        attribution.to_excel(writer, index=False, sheet_name="Patent Faculty Attribution")
    return buffer.getvalue()
