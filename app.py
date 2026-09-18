from __future__ import annotations

from datetime import datetime
import hashlib

import pandas as pd
import streamlit as st

from core.author_mapper import (
    UNMAPPED,
    apply_author_mappings,
    apply_row_resolutions,
    load_mapping,
    load_row_resolutions,
)
from core.excel_parser import parse_workbook
from core.metrics import TYPE_ORDER, filter_records
from core.normalizer import add_duplicate_flags
from core.patent_parser import (
    PATENT_ATTRIBUTION_COLUMNS,
    PATENT_MASTER_COLUMNS,
    normalize_patent_attributions,
    parse_patents,
)
from core.patent_state import (
    apply_patent_attribution_resolutions,
    apply_patent_duplicate_decisions,
    load_patent_attribution_resolutions,
    load_patent_duplicate_decisions,
)
from core.review_state import apply_duplicate_decisions, load_duplicate_decisions
from ui_pages import author_mapping, data_quality, faculty_analysis, journal_quality, overview, patents, publication_details, year_analysis
from ui_pages.theme import DASHBOARD_CSS


st.set_page_config(page_title="Faculty Publication Analytics Dashboard", page_icon="📚", layout="wide")
st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner="Reading workbook and rich-text author formatting…")
def cached_parse(file_bytes: bytes) -> tuple[pd.DataFrame, dict[str, object]]:
    return parse_workbook(file_bytes)


@st.cache_data(show_spinner="Reading optional Patents sheet and all bold faculty applicants…")
def cached_patent_parse(file_bytes: bytes) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    return parse_patents(file_bytes)


def landing() -> None:
    st.title("Faculty Publication Analytics Dashboard")
    st.write("Upload the original Excel publication workbook. No preprocessing is required.")
    st.info("The workbook remains in this browser session. Only author-name mappings are saved locally.")


def upload_control() -> None:
    if "upload_version" not in st.session_state:
        st.session_state.upload_version = 0
    uploaded = st.file_uploader(
        "Upload Publication Workbook", type=["xlsx"], key=f"workbook_upload_{st.session_state.upload_version}"
    )
    if uploaded is not None:
        data = uploaded.getvalue()
        digest = hashlib.sha256(data).hexdigest()
        if st.session_state.get("workbook_hash") != digest:
            st.session_state.workbook_bytes = data
            st.session_state.workbook_name = uploaded.name
            st.session_state.workbook_hash = digest
            st.session_state.upload_timestamp = datetime.now().astimezone()


def top_filters(frame: pd.DataFrame) -> tuple[list[int], list[str], list[str], list[str], list[str], bool]:
    st.markdown("### Dashboard Filters")
    first = st.columns([1.0, 1.35, 1.1])
    second = st.columns([1.0, 1.0, 1.35])
    all_years = sorted(int(year) for year in frame["Calendar Year"].dropna().unique())
    years = first[0].multiselect("Calendar Year", all_years, placeholder="All calendar years")
    faculty_options = sorted(frame["Faculty Name"].dropna().unique())
    faculty = first[1].multiselect("Faculty", faculty_options, placeholder="All faculty")
    publication_types = first[2].multiselect("Publication Type", TYPE_ORDER, placeholder="All publication types")
    indexing = second[0].multiselect("Indexing", ["SCI/SCIE", "ESCI", "Scopus"], placeholder="All indexing")
    quartiles = second[1].multiselect("Quartile", ["Q1", "Q2", "Q3", "Q4"], placeholder="All quartiles")
    duplicate_mode = second[2].selectbox(
        "Reviewed duplicates",
        ["Include all records", "Exclude user-marked duplicates"],
        help="Only rows explicitly marked Exclude on the Data Quality page are removed.",
    )
    return years, faculty, publication_types, indexing, quartiles, duplicate_mode == "Include all records"


landing()
upload_control()

if "workbook_bytes" not in st.session_state:
    st.stop()

try:
    raw_frame, metadata = cached_parse(st.session_state.workbook_bytes)
except ValueError as exc:
    st.error(str(exc))
    if st.button("Choose a different workbook"):
        for key in ["workbook_bytes", "workbook_name", "workbook_hash", "upload_timestamp"]:
            st.session_state.pop(key, None)
        st.session_state.upload_version += 1
        st.rerun()
    st.stop()

if raw_frame.empty:
    st.error("No publication rows were found in the recognized Journal, Conf, Chapter, or Books sheets.")
    st.stop()

raw_frame = add_duplicate_flags(raw_frame)
mapped_frame = apply_author_mappings(raw_frame, load_mapping())
master = apply_row_resolutions(mapped_frame, load_row_resolutions())
master = apply_duplicate_decisions(master, load_duplicate_decisions())
try:
    patent_master, patent_attribution, patent_metadata = cached_patent_parse(st.session_state.workbook_bytes)
except (ValueError, KeyError) as exc:
    patent_master = pd.DataFrame(columns=PATENT_MASTER_COLUMNS)
    patent_attribution = pd.DataFrame(columns=PATENT_ATTRIBUTION_COLUMNS)
    patent_metadata = {"detected": True, "sheet": "Patents", "warnings": [str(exc)], "processed_rows": 0}
if not patent_master.empty:
    patent_attribution = normalize_patent_attributions(patent_attribution, master, load_mapping())
    patent_master, patent_attribution = apply_patent_attribution_resolutions(
        patent_master, patent_attribution, load_patent_attribution_resolutions()
    )
    patent_master = apply_patent_duplicate_decisions(patent_master, load_patent_duplicate_decisions())
timestamp = st.session_state.upload_timestamp.strftime("%d %b %Y, %I:%M %p %Z")
detected_sheets = list(metadata["detected_sheets"])
if patent_metadata.get("detected") and patent_metadata.get("sheet"):
    detected_sheets.append(str(patent_metadata["sheet"]))
st.markdown(
    f"<div class='workbook-banner'><b>{st.session_state.workbook_name}</b> &nbsp;·&nbsp; Uploaded {timestamp} &nbsp;·&nbsp; "
    f"{len(master):,} publication rows &nbsp;·&nbsp; {len(patent_master):,} patent rows &nbsp;·&nbsp; "
    f"Sheets: {', '.join(detected_sheets) or 'None'} &nbsp;·&nbsp; "
    f"Calendar years: {', '.join(map(str, metadata['years'])) or 'None detected'}</div>",
    unsafe_allow_html=True,
)
for warning in metadata["warnings"]:
    st.warning(warning)
for warning in patent_metadata.get("warnings", []):
    st.warning(f"Patents: {warning}")

with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Page",
        ["Overview", "Patents", "Faculty Profile", "Journal Quality", "Year Analysis", "Publication Details", "Data Quality", "Author Mapping"],
        label_visibility="collapsed",
    )
    st.divider()
    if st.button("Replace Workbook", width="stretch"):
        for key in ["workbook_bytes", "workbook_name", "workbook_hash", "upload_timestamp"]:
            st.session_state.pop(key, None)
        st.session_state.upload_version += 1
        st.rerun()

filter_pages = {"Overview", "Faculty Profile", "Journal Quality", "Year Analysis", "Publication Details"}
if page in filter_pages:
    years, faculty, publication_types, indexing, quartiles, include_duplicates = top_filters(master)
    filtered = filter_records(master, years, faculty, publication_types, indexing, quartiles, include_duplicates)
else:
    filtered = master

if page == "Overview":
    overview.render(filtered, master, patent_master, patent_attribution)
elif page == "Patents":
    patents.render(patent_master, patent_attribution)
elif page == "Faculty Profile":
    faculty_analysis.render(filtered, patent_master, patent_attribution)
elif page == "Journal Quality":
    journal_quality.render(filtered)
elif page == "Year Analysis":
    year_analysis.render(filtered)
elif page == "Publication Details":
    publication_details.render(filtered)
elif page == "Data Quality":
    data_quality.render(master, patent_master, patent_attribution)
elif page == "Author Mapping":
    author_mapping.render(raw_frame)
