from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core.patent_metrics import filter_patents, patent_excel_bytes, patent_kpis
from .components import metric_cards
from .theme import PATENT_COLORS, style_figure


DISPLAY_COLUMNS = [
    "Patent_ID",
    "Title_of_Patent",
    "Patent_Number_Raw",
    "Patent_Type",
    "Publication_Date",
    "Publication_Year",
    "Granted_Date",
    "Granted_Year",
    "Patent_Status",
    "Attribution_Status",
    "Possible_Patent_Duplicate",
    "Patent_Duplicate_Review_Decision",
    "Source_Sheet",
    "Source_Row",
]


def render(master: pd.DataFrame, attribution: pd.DataFrame) -> None:
    st.header("Patents")
    st.caption("Institutional patent totals and faculty-patent credits are reported separately.")
    if master.empty:
        st.info("No Patents sheet was detected in the uploaded workbook.")
        return

    st.markdown("### Patent Filters")
    first = st.columns(3)
    second = st.columns(3)
    publication_years = first[0].multiselect(
        "Publication Year", sorted(int(value) for value in master["Publication_Year"].dropna().unique())
    )
    granted_years = first[1].multiselect(
        "Granted Year", sorted(int(value) for value in master["Granted_Year"].dropna().unique())
    )
    faculty = first[2].multiselect("Patent Faculty", sorted(attribution["Faculty_Name"].dropna().unique()))
    patent_types = second[0].multiselect("Patent Type", sorted(master["Patent_Type"].dropna().unique()))
    statuses = second[1].multiselect("Patent Status", sorted(master["Patent_Status"].dropna().unique()))
    duplicate_mode = second[2].selectbox(
        "Duplicate Review State",
        ["Include all patents", "Exclude user-marked duplicates"],
        help="Only patents explicitly marked Exclude on Data Quality are omitted.",
    )
    filtered_master, filtered_attribution = filter_patents(
        master,
        attribution,
        publication_years,
        granted_years,
        faculty,
        patent_types,
        statuses,
        duplicate_mode == "Include all patents",
    )
    if filtered_master.empty:
        st.info("No patents match the current filters.")
        return

    metric_cards(
        patent_kpis(filtered_master, filtered_attribution),
        ["Total Patents", "Published Patents", "Granted Patents", "Faculty Involved", "Multi-Faculty Patents", "Review Required"],
        desktop_columns=3,
    )

    left, right = st.columns(2)
    with left:
        published = (
            filtered_master.dropna(subset=["Publication_Year"])
            .groupby("Publication_Year")["Patent_ID"].nunique().reset_index(name="Patents")
            .sort_values("Publication_Year")
        )
        published["Publication Year Label"] = published["Publication_Year"].astype("Int64").astype(str)
        publication_year_order = published["Publication Year Label"].tolist()
        fig = px.bar(
            published,
            x="Publication Year Label",
            y="Patents",
            labels={"Publication Year Label": "Publication Year"},
            category_orders={"Publication Year Label": publication_year_order},
            title="Patent Output by Publication Year",
            color_discrete_sequence=[PATENT_COLORS["Published Patents"]],
        )
        st.plotly_chart(style_figure(fig), width="stretch")
    with right:
        granted = (
            filtered_master.dropna(subset=["Granted_Year"])
            .groupby("Granted_Year")["Patent_ID"].nunique().reset_index(name="Patents")
            .sort_values("Granted_Year")
        )
        granted["Granted Year Label"] = granted["Granted_Year"].astype("Int64").astype(str)
        granted_year_order = granted["Granted Year Label"].tolist()
        fig = px.bar(
            granted,
            x="Granted Year Label",
            y="Patents",
            labels={"Granted Year Label": "Granted Year"},
            category_orders={"Granted Year Label": granted_year_order},
            title="Patents Granted by Year",
            color_discrete_sequence=[PATENT_COLORS["Granted Patents"]],
        )
        st.plotly_chart(style_figure(fig), width="stretch")

    left, right = st.columns(2)
    with left:
        faculty_counts = filtered_attribution.groupby("Faculty_Name")["Patent_ID"].nunique().sort_values()
        fig = px.bar(
            x=faculty_counts.values,
            y=faculty_counts.index,
            orientation="h",
            labels={"x": "Faculty Patent Credits", "y": "Faculty Name"},
            title="Faculty-wise Patent Contribution",
            color_discrete_sequence=[PATENT_COLORS["Faculty Involved"]],
        )
        st.plotly_chart(style_figure(fig), width="stretch")
        st.caption(
            "Joint patents are credited to each bold faculty applicant; therefore faculty-credit totals may exceed distinct patent totals."
        )
    with right:
        type_counts = filtered_master.groupby("Patent_Type")["Patent_ID"].nunique().reset_index(name="Patents")
        fig = px.pie(type_counts, names="Patent_Type", values="Patents", hole=0.48, title="Patent Type Distribution")
        st.plotly_chart(style_figure(fig), width="stretch")

    published = filtered_master.dropna(subset=["Publication_Year"]).groupby("Publication_Year")["Patent_ID"].nunique()
    granted = filtered_master.dropna(subset=["Granted_Year"]).groupby("Granted_Year")["Patent_ID"].nunique()
    trend = pd.concat([published.rename("Published"), granted.rename("Granted")], axis=1).fillna(0).reset_index(names="Calendar Year")
    trend = trend.sort_values("Calendar Year")
    trend["Calendar Year Label"] = trend["Calendar Year"].astype("Int64").astype(str)
    calendar_year_order = trend["Calendar Year Label"].tolist()
    trend = trend.melt(id_vars=["Calendar Year", "Calendar Year Label"], var_name="Patent Event", value_name="Patents")
    fig = px.bar(
        trend,
        x="Calendar Year Label",
        y="Patents",
        color="Patent Event",
        barmode="group",
        labels={"Calendar Year Label": "Calendar Year"},
        category_orders={"Calendar Year Label": calendar_year_order},
        color_discrete_map={"Published": PATENT_COLORS["Published Patents"], "Granted": PATENT_COLORS["Granted Patents"]},
        title="Published vs Granted by Year",
    )
    st.plotly_chart(style_figure(fig), width="stretch")

    st.subheader("Patent Records")
    st.dataframe(filtered_master[DISPLAY_COLUMNS], width="stretch", hide_index=True, height=500)
    c1, c2 = st.columns(2)
    c1.download_button(
        "Download Patent Master CSV",
        filtered_master[DISPLAY_COLUMNS].to_csv(index=False).encode("utf-8-sig"),
        "patent_master.csv",
        "text/csv",
    )
    c2.download_button(
        "Download Patent Excel",
        patent_excel_bytes(filtered_master, filtered_attribution),
        "patents.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
