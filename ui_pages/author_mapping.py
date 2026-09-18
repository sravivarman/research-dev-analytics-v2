from __future__ import annotations

import pandas as pd
import streamlit as st

from core.author_mapper import (
    UNMAPPED,
    apply_author_mappings,
    load_mapping,
    load_row_resolutions,
    mapping_summary,
    save_mapping,
    save_row_resolutions,
)
from .components import metric_cards


def _manual_resolution_section(raw_frame: pd.DataFrame, saved_mapping: dict[str, str]) -> None:
    st.subheader("Manual Resolution for Unmapped Rows")
    st.caption("No faculty is selected automatically. Choose a canonical faculty only after reviewing the source row.")
    mapped = apply_author_mappings(raw_frame, saved_mapping)
    unresolved = mapped[mapped["Faculty Name"].eq(UNMAPPED)].copy()
    existing = load_row_resolutions()
    if unresolved.empty:
        st.success("There are no unresolved publication rows.")
        return

    canonical_options = sorted(name for name in mapped["Faculty Name"].dropna().unique() if name != UNMAPPED)
    for canonical in existing.values():
        if canonical not in canonical_options:
            canonical_options.append(canonical)
    unresolved["Credited Canonical Faculty"] = unresolved["Publication ID"].map(existing).fillna("")
    columns = ["Publication ID", "Source Sheet", "Source Row", "Title", "Original Authors", "Credited Canonical Faculty"]
    edited = st.data_editor(
        unresolved[columns],
        column_config={
            "Publication ID": st.column_config.TextColumn(disabled=True),
            "Source Sheet": st.column_config.TextColumn(disabled=True),
            "Source Row": st.column_config.NumberColumn(disabled=True),
            "Title": st.column_config.TextColumn(disabled=True),
            "Original Authors": st.column_config.TextColumn(disabled=True),
            "Credited Canonical Faculty": st.column_config.SelectboxColumn(
                options=[""] + sorted(canonical_options), required=False
            ),
        },
        disabled=["Publication ID", "Source Sheet", "Source Row", "Title", "Original Authors"],
        hide_index=True,
        width="stretch",
        key="unmapped_resolution_editor",
    )
    if st.button("Save Manual Resolutions", type="primary"):
        resolutions = load_row_resolutions()
        for _, row in edited.iterrows():
            publication_id = str(row["Publication ID"])
            canonical = str(row["Credited Canonical Faculty"] or "").strip()
            if canonical:
                resolutions[publication_id] = canonical
            else:
                resolutions.pop(publication_id, None)
        save_row_resolutions(resolutions)
        st.success("Manual row resolutions saved. Dashboard calculations are refreshing.")
        st.rerun()


def render(raw_frame: pd.DataFrame) -> None:
    st.header("Author Mapping")
    st.caption("Review proposed consolidations and persist approved canonical names. The uploaded workbook is never modified.")
    saved = load_mapping()
    summary = mapping_summary(raw_frame, saved)
    unresolved_variants = summary[summary["Mapping Status"].eq("Auto-normalized")]
    metric_cards(
        {
            "Observed variants": len(summary[summary["Observed Name"].ne(UNMAPPED)]),
            "Unresolved proposals": len(unresolved_variants),
            "User-approved mappings": int(summary["Mapping Status"].eq("User mapped").sum()),
            "Unmapped source rows": int((raw_frame["Original Faculty Name"] == UNMAPPED).sum()),
        },
        ["Observed variants", "Unresolved proposals", "User-approved mappings", "Unmapped source rows"],
        4,
    )

    _manual_resolution_section(raw_frame, saved)
    st.divider()
    st.subheader("Review and Merge Author Variants")

    editable_summary = summary[summary["Observed Name"].ne(UNMAPPED)].copy()
    left, right = st.columns([1.3, 1])
    scope = left.selectbox("Variant view", ["Unresolved proposals", "All observed variants"])
    visible = (
        editable_summary[editable_summary["Mapping Status"].eq("Auto-normalized")].copy()
        if scope == "Unresolved proposals"
        else editable_summary.copy()
    )
    right.caption("Auto-normalized names are proposals until saved. Direct names retain their observed spelling.")

    if visible.empty:
        st.success("No unresolved mapping proposals remain.")
    else:
        edited = st.data_editor(
            visible,
            column_config={
                "Observed Name": st.column_config.TextColumn(disabled=True),
                "Canonical Faculty Name": st.column_config.TextColumn(required=True),
                "Number of Occurrences": st.column_config.NumberColumn(disabled=True),
                "Journal Count": st.column_config.NumberColumn(disabled=True),
                "Conference Count": st.column_config.NumberColumn(disabled=True),
                "Mapping Status": st.column_config.TextColumn(disabled=True),
            },
            disabled=["Observed Name", "Number of Occurrences", "Journal Count", "Conference Count", "Mapping Status"],
            hide_index=True,
            width="stretch",
            key=f"author_mapping_editor_{scope}",
        )
        if st.button("Save Reviewed Mappings", type="primary"):
            updated = load_mapping()
            updated.update(dict(zip(edited["Observed Name"], edited["Canonical Faculty Name"])))
            save_mapping(updated)
            st.success("Mappings saved to author_mapping.json. Dashboard calculations are refreshing.")
            st.rerun()

    with st.expander("Quick merge multiple variants"):
        observed_options = sorted(editable_summary["Observed Name"].unique())
        selected = st.multiselect("Observed variants to merge", observed_options)
        canonical_options = sorted(editable_summary["Canonical Faculty Name"].unique())
        target = st.selectbox("Canonical faculty", canonical_options) if canonical_options else ""
        custom_target = st.text_input("Or enter a new canonical faculty name")
        if st.button("Merge Selected Variants"):
            canonical = custom_target.strip() or target
            if not selected or not canonical:
                st.error("Select at least one observed variant and a canonical faculty name.")
            else:
                updated = load_mapping()
                updated.update({variant: canonical for variant in selected})
                save_mapping(updated)
                st.success(f"Merged {len(selected)} variant(s) into {canonical}.")
                st.rerun()
