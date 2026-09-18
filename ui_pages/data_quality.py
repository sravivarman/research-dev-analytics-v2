from __future__ import annotations

import pandas as pd
import streamlit as st

from core.author_mapper import UNMAPPED
from core.patent_state import (
    load_patent_attribution_resolutions,
    load_patent_duplicate_decisions,
    save_patent_attribution_resolutions,
    save_patent_duplicate_decisions,
)
from core.quality_checks import UNMAPPED_HELP, UNRESOLVED_HELP, quality_counts, quality_tables
from core.review_state import load_duplicate_decisions, save_duplicate_decisions
from .components import metric_cards


def _duplicate_review(frame: pd.DataFrame) -> None:
    st.subheader("Duplicate Review")
    st.caption(
        "Candidates remain in all publication totals. Mark a row Exclude only after review, then use the dashboard filter to omit user-marked rows."
    )
    candidates = quality_tables(frame)["Possible Duplicates"].copy()
    if candidates.empty:
        st.success("No possible duplicate records were detected.")
        return
    edited = st.data_editor(
        candidates,
        column_config={
            "Publication ID": st.column_config.TextColumn(disabled=True),
            "Duplicate Classification": st.column_config.TextColumn(disabled=True),
            "Duplicate Reason": st.column_config.TextColumn(disabled=True),
            "Duplicate Review Decision": st.column_config.SelectboxColumn(
                options=["Unreviewed", "Include", "Exclude"], required=True
            ),
        },
        disabled=[column for column in candidates.columns if column != "Duplicate Review Decision"],
        hide_index=True,
        width="stretch",
        key="duplicate_review_editor",
    )
    if st.button("Save Duplicate Decisions", type="primary"):
        decisions = load_duplicate_decisions()
        for _, row in edited.iterrows():
            publication_id = str(row["Publication ID"])
            decision = str(row["Duplicate Review Decision"])
            if decision in {"Include", "Exclude"}:
                decisions[publication_id] = decision
            else:
                decisions.pop(publication_id, None)
        save_duplicate_decisions(decisions)
        st.success("Duplicate decisions saved. Dashboard calculations are refreshing.")
        st.rerun()


def _patent_duplicate_review(master: pd.DataFrame) -> None:
    st.subheader("Patent Duplicate Review")
    candidates = master[master["Possible_Patent_Duplicate"].eq("Yes")].copy()
    if candidates.empty:
        st.success("No possible patent duplicates were detected.")
        return
    columns = [
        "Patent_ID", "Patent_Duplicate_Classification", "Patent_Duplicate_Reason",
        "Patent_Duplicate_Review_Decision", "Patent_Number_Raw", "Title_of_Patent", "Source_Row",
    ]
    edited = st.data_editor(
        candidates[columns],
        column_config={
            "Patent_Duplicate_Review_Decision": st.column_config.SelectboxColumn(
                options=["Unreviewed", "Include", "Exclude"], required=True
            )
        },
        disabled=[column for column in columns if column != "Patent_Duplicate_Review_Decision"],
        hide_index=True,
        width="stretch",
        key="patent_duplicate_review_editor",
    )
    if st.button("Save Patent Duplicate Decisions", type="primary"):
        decisions = load_patent_duplicate_decisions()
        for _, row in edited.iterrows():
            decision = str(row["Patent_Duplicate_Review_Decision"])
            if decision in {"Include", "Exclude"}:
                decisions[str(row["Patent_ID"])] = decision
            else:
                decisions.pop(str(row["Patent_ID"]), None)
        save_patent_duplicate_decisions(decisions)
        st.success("Patent duplicate decisions saved.")
        st.rerun()


def _patent_attribution_review(
    master: pd.DataFrame, attribution: pd.DataFrame, publication_frame: pd.DataFrame
) -> None:
    st.subheader("Patent Attribution Review")
    unresolved = master[master["Attribution_Status"].eq("REVIEW REQUIRED")]
    if unresolved.empty:
        st.success("No patent attribution rows require review.")
        return
    st.caption("Select every canonical faculty who should receive credit. No selection is made automatically.")
    canonical_options = sorted(
        value
        for value in publication_frame["Faculty Name"].dropna().unique()
        if value != UNMAPPED
    )
    existing = load_patent_attribution_resolutions()
    selections: dict[str, list[str]] = {}
    for _, row in unresolved.iterrows():
        patent_id = str(row["Patent_ID"])
        detected = attribution.loc[attribution["Patent_ID"].eq(patent_id), "Original_Extracted_Name"].tolist()
        with st.expander(f"{row['Source_Sheet']}:{int(row['Source_Row'])} — {row['Title_of_Patent']}"):
            st.write(f"**Patent Number:** {row['Patent_Number_Raw']}")
            st.write(f"**Original Name of Faculty cell:** {row['Original_Faculty_Cell']}")
            st.write(f"**Bold names detected:** {row['Bold_Names_Detected'] or 'None'}")
            reason = (
                "No bold faculty was detected in a multi-person cell."
                if row["Patent_Attribution_Method"] == "No Bold / Multiple People"
                else f"Unrecognized extracted identities: {', '.join(detected) or 'None'}"
            )
            st.write(f"**Reason:** {reason}")
            selections[patent_id] = st.multiselect(
                "Manual faculty selection",
                canonical_options,
                default=existing.get(patent_id, []),
                key=f"patent_attribution_{patent_id}",
            )
    if st.button("Save Patent Attribution Resolutions", type="primary"):
        resolutions = load_patent_attribution_resolutions()
        for patent_id, selected in selections.items():
            if selected:
                resolutions[patent_id] = selected
            else:
                resolutions.pop(patent_id, None)
        save_patent_attribution_resolutions(resolutions)
        st.success("Patent faculty resolutions saved.")
        st.rerun()


def render(
    frame: pd.DataFrame,
    patent_master: pd.DataFrame | None = None,
    patent_attribution: pd.DataFrame | None = None,
) -> None:
    st.header("Data Quality")
    st.caption("Every issue retains its source sheet and row. Review decisions never modify the uploaded workbook.")
    counts = quality_counts(frame)
    metric_cards(
        counts,
        list(counts),
        5,
        links={
            "Unmapped author records": "#unmapped-records",
            "Unresolved author mappings": "#unresolved-mappings",
        },
        help_text={
            "Unmapped author records": UNMAPPED_HELP,
            "Unresolved author mappings": UNRESOLVED_HELP,
        },
    )
    st.info(
        f"Source publication baseline: {len(frame):,} rows. Author consolidation changes faculty attribution only. "
        f"Rows explicitly marked Exclude: {counts['User-excluded duplicate rows']:,}."
    )

    _duplicate_review(frame)
    for title, table in quality_tables(frame).items():
        if title == "Possible Duplicates":
            continue
        anchor = title.lower().replace(" ", "-")
        st.markdown(f'<div id="{anchor}"></div>', unsafe_allow_html=True)
        with st.expander(f"{title} ({len(table):,})", expanded=title == "Unmapped Records"):
            if title == "Unmapped Records":
                st.caption(UNMAPPED_HELP)
            elif title == "Unresolved Mappings":
                st.caption(UNRESOLVED_HELP)
            if table.empty:
                st.success("No records in this category.")
            else:
                st.dataframe(table, width="stretch", hide_index=True)

    st.divider()
    st.header("Patent Data Quality")
    if patent_master is None or patent_attribution is None or patent_master.empty:
        st.info("No Patents sheet was detected; publication data-quality checks remain available above.")
        return
    attributed_ids = patent_attribution["Patent_ID"].nunique()
    patent_counts = {
        "Total Patent Rows": len(patent_master),
        "Successfully Parsed Patents": int(patent_master["Title_of_Patent"].ne("").sum()),
        "Patents With Faculty Attribution": int(attributed_ids),
        "Patent Attribution Review Required": int(patent_master["Attribution_Status"].eq("REVIEW REQUIRED").sum()),
        "Patent Rows Without Publication Date": int(patent_master["Publication_Date_Status"].eq("Missing").sum()),
        "Not Yet Granted / No Granted Date": int(patent_master["Granted_Date_Status"].eq("Missing").sum()),
        "Patent Rows Without Patent Number": int(patent_master["Patent_Number_Raw"].eq("").sum()),
        "Possible Patent Duplicates": int(patent_master["Possible_Patent_Duplicate"].eq("Yes").sum()),
        "Unrecognized Faculty Identities": int(
            patent_attribution.loc[
                patent_attribution["Mapping_Status"].eq("Review Required"), "Original_Extracted_Name"
            ].nunique()
        ),
    }
    metric_cards(patent_counts, list(patent_counts), desktop_columns=3)
    st.caption(
        "A missing Granted Date means Not Yet Granted / No Granted Date; it is not treated as an invalid date."
    )
    _patent_attribution_review(patent_master, patent_attribution, frame)
    _patent_duplicate_review(patent_master)

    invalid_dates = patent_master[
        patent_master["Publication_Date_Status"].eq("Invalid")
        | patent_master["Granted_Date_Status"].eq("Invalid")
    ]
    with st.expander(f"Invalid Patent Dates ({len(invalid_dates):,})"):
        if invalid_dates.empty:
            st.success("No invalid patent dates were detected.")
        else:
            st.dataframe(
                invalid_dates[["Source_Row", "Title_of_Patent", "Publication_Date_Status", "Granted_Date_Status"]],
                width="stretch",
                hide_index=True,
            )
