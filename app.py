from __future__ import annotations

import smtplib
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.data_processing import (
    ProcessedData,
    REQUIRED_SHEETS,
    build_power_bi_dataset,
    load_master_data,
    normalize_engineer_master,
    normalize_feedback,
    normalize_performance,
    normalize_projects,
    normalize_skill_matrix,
    normalize_tasks,
    sample_engineer_master,
    sample_feedback,
    sample_performance,
    sample_projects,
    sample_skill_matrix,
    sample_tasks,
)
from src.kpi_engine import calculate_kpi
from src.report_generator import build_department_performance, build_engineer_performance
from src.skill_matrix_engine import calculate_skill_score
from src.utilization_engine import calculate_utilization


ROOT = Path(__file__).resolve().parent
LOCAL_WORKBOOK = ROOT / "data" / "master_data.xlsx"
SHEET_ORDER = [
    "projects",
    "tasks",
    "performance",
    "feedback",
    "skill_matrix",
    "engineer_master",
]


st.set_page_config(
    page_title="PANSOFT KPI Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)


def build_sample_processed_data() -> ProcessedData:
    return ProcessedData(
        projects=normalize_projects(sample_projects()),
        tasks=normalize_tasks(sample_tasks()),
        performance=normalize_performance(sample_performance()),
        feedback=normalize_feedback(sample_feedback()),
        skill_matrix=normalize_skill_matrix(sample_skill_matrix()),
        engineer_master=normalize_engineer_master(sample_engineer_master()),
    )


def load_uploaded_workbook(uploaded_file) -> ProcessedData:
    workbook = pd.read_excel(uploaded_file, sheet_name=None)
    missing_sheets = sorted(set(REQUIRED_SHEETS) - set(workbook))
    if missing_sheets:
        raise ValueError(
            "Workbook is missing required sheets: " + ", ".join(missing_sheets)
        )

    return ProcessedData(
        projects=normalize_projects(workbook["projects"]),
        tasks=normalize_tasks(workbook["tasks"]),
        performance=normalize_performance(workbook["performance"]),
        feedback=normalize_feedback(workbook["feedback"]),
        skill_matrix=normalize_skill_matrix(workbook["skill_matrix"]),
        engineer_master=normalize_engineer_master(workbook["engineer_master"]),
    )


def get_processed_data(uploaded_file) -> tuple[ProcessedData, str]:
    if uploaded_file is not None:
        return load_uploaded_workbook(uploaded_file), "Uploaded workbook"
    if LOCAL_WORKBOOK.exists():
        return load_master_data(LOCAL_WORKBOOK), "Repository workbook"
    return build_sample_processed_data(), "Built-in sample data"


def build_dashboard_dataset(processed: ProcessedData) -> dict[str, pd.DataFrame]:
    project_kpis, kpi_summary = calculate_kpi(
        processed.projects,
        processed.tasks,
        processed.performance,
        processed.feedback,
    )
    utilization = calculate_utilization(processed.tasks, processed.engineer_master)
    capability, skill_breakdown = calculate_skill_score(processed.skill_matrix)
    power_bi_dataset = build_power_bi_dataset(processed, project_kpis, utilization, capability)
    department_performance = build_department_performance(power_bi_dataset)
    engineer_performance = build_engineer_performance(power_bi_dataset)

    return {
        "project_kpis": project_kpis,
        "kpi_summary": kpi_summary,
        "utilization": utilization,
        "capability": capability,
        "skill_breakdown": skill_breakdown,
        "power_bi_dataset": power_bi_dataset,
        "department_performance": department_performance,
        "engineer_performance": engineer_performance,
    }


def metric_status(value: float, good: float, warn: float) -> str:
    if value >= good:
        return "Strong"
    if value >= warn:
        return "Watch"
    return "At Risk"


def workbook_template_bytes() -> bytes:
    sample_tables = {
        "projects": sample_projects(),
        "tasks": sample_tasks(),
        "performance": sample_performance(),
        "feedback": sample_feedback(),
        "skill_matrix": sample_skill_matrix(),
        "engineer_master": sample_engineer_master(),
    }
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name in SHEET_ORDER:
            sample_tables[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)
    buffer.seek(0)
    return buffer.getvalue()


def report_excel_bytes(kpi_summary_df: pd.DataFrame, operational_summary_df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        kpi_summary_df.to_excel(writer, sheet_name="KPI Summary", index=False)
        operational_summary_df.to_excel(writer, sheet_name="Operational Snapshot", index=False)
    buffer.seek(0)
    return buffer.getvalue()


def build_pdf_table(frame: pd.DataFrame) -> Table:
    table_data = [list(frame.columns)] + frame.astype(str).values.tolist()
    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f4ec")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def report_pdf_bytes(
    source_name: str,
    kpi_summary_df: pd.DataFrame,
    operational_summary_df: pd.DataFrame,
    project_snapshot_df: pd.DataFrame,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=32,
        rightMargin=32,
        topMargin=32,
        bottomMargin=32,
    )
    styles = getSampleStyleSheet()
    story: list[Any] = [
        Paragraph("PANSOFT Delivery Intelligence Report", styles["Title"]),
        Spacer(1, 8),
        Paragraph(f"Data source: {source_name}", styles["Normal"]),
        Spacer(1, 14),
        Paragraph("KPI Summary", styles["Heading2"]),
        build_pdf_table(kpi_summary_df),
        Spacer(1, 12),
        Paragraph("Operational Snapshot", styles["Heading2"]),
        build_pdf_table(operational_summary_df),
        Spacer(1, 12),
        Paragraph("Project Health Snapshot", styles["Heading2"]),
        build_pdf_table(project_snapshot_df),
    ]
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def smtp_settings() -> dict[str, Any] | None:
    if "smtp" not in st.secrets:
        return None
    smtp_config = dict(st.secrets["smtp"])
    required_fields = {"host", "port", "username", "password", "from_email"}
    if not required_fields.issubset(smtp_config):
        return None
    smtp_config["use_tls"] = bool(smtp_config.get("use_tls", True))
    return smtp_config


def send_report_email(
    smtp_config: dict[str, Any],
    recipients: list[str],
    subject: str,
    body: str,
    summary_excel: bytes,
    summary_pdf: bytes,
) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = smtp_config["from_email"]
    message["To"] = ", ".join(recipients)
    message.set_content(body)
    message.add_attachment(
        summary_excel,
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="dashboard_summary.xlsx",
    )
    message.add_attachment(
        summary_pdf,
        maintype="application",
        subtype="pdf",
        filename="dashboard_report.pdf",
    )

    with smtplib.SMTP(smtp_config["host"], int(smtp_config["port"])) as server:
        if smtp_config.get("use_tls", True):
            server.starttls()
        server.login(smtp_config["username"], smtp_config["password"])
        server.send_message(message)


st.markdown(
    """
    <style>
    :root {
        --paper: #f6f3ea;
        --ink: #1d2a32;
        --teal: #0f766e;
        --gold: #d97706;
        --brick: #b45309;
        --panel: rgba(255,255,255,0.82);
        --line: rgba(29,42,50,0.08);
    }
    .stApp {
        background:
            radial-gradient(circle at top right, rgba(217,119,6,0.18), transparent 24%),
            radial-gradient(circle at left top, rgba(15,118,110,0.16), transparent 20%),
            linear-gradient(180deg, #f7f4ec 0%, #efe7d6 100%);
        color: var(--ink);
    }
    [data-testid="stSidebar"] {
        background: rgba(29,42,50,0.95);
    }
    .hero {
        padding: 2rem 2.2rem;
        border: 1px solid var(--line);
        border-radius: 28px;
        background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(255,248,235,0.7));
        box-shadow: 0 20px 50px rgba(29,42,50,0.10);
        margin-bottom: 1.25rem;
    }
    .hero h1 {
        font-size: 2.6rem;
        margin: 0;
        letter-spacing: -0.04em;
    }
    .hero p {
        font-size: 1rem;
        margin: 0.6rem 0 0;
        max-width: 48rem;
    }
    .metric-shell {
        border-radius: 24px;
        padding: 1.1rem 1.1rem 0.8rem;
        background: var(--panel);
        border: 1px solid var(--line);
        box-shadow: 0 18px 45px rgba(29,42,50,0.08);
    }
    .metric-label {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #53616a;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        margin: 0.2rem 0;
    }
    .metric-tag {
        display: inline-block;
        padding: 0.28rem 0.7rem;
        border-radius: 999px;
        background: rgba(15,118,110,0.10);
        color: var(--teal);
        font-size: 0.82rem;
        font-weight: 600;
    }
    .section-title {
        font-size: 1.1rem;
        font-weight: 700;
        margin: 0.4rem 0 0.8rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <h1>Delivery Intelligence Dashboard</h1>
        <p>
            Unified KPI, utilization, and capability tracking for engineering delivery teams.
            Use the built-in sample workbook, the repository workbook, or upload your own Excel file.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Workbook Source")
    uploaded_workbook = st.file_uploader(
        "Upload master workbook",
        type=["xlsx", "xls"],
        help="Upload a workbook containing the six required sheets used by the backend pipeline.",
    )
    st.caption("Required sheets: " + ", ".join(SHEET_ORDER))
    st.download_button(
        "Download template workbook",
        data=workbook_template_bytes(),
        file_name="pansoft_master_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

try:
    processed, source_label = get_processed_data(uploaded_workbook)
    dashboard = build_dashboard_dataset(processed)
except Exception as exc:
    st.error(f"Unable to load dashboard data: {exc}")
    st.stop()

project_kpis = dashboard["project_kpis"]
kpi_summary = dashboard["kpi_summary"].set_index("metric")
utilization = dashboard["utilization"]
capability = dashboard["capability"]
power_bi_dataset = dashboard["power_bi_dataset"]

avg_utilization = utilization["utilization_pct"].mean()
top_engineer = utilization.iloc[0]
top_capability = capability.iloc[0]
project_snapshot_df = project_kpis[
    ["project_name", "rft", "otd", "feedback_score", "project_health"]
].rename(
    columns={
        "project_name": "Project",
        "rft": "RFT",
        "otd": "OTD",
        "feedback_score": "Feedback",
        "project_health": "Health",
    }
)
operational_summary_df = pd.DataFrame(
    {
        "Metric": [
            "Top Utilization",
            "Top Capability",
            "Projects Tracked",
            "Engineers Tracked",
            "Data Source",
        ],
        "Value": [
            f"{top_engineer['engineer']} ({top_engineer['utilization_pct']:.1f}%)",
            f"{top_capability['engineer']} ({top_capability['capability_score']:.2f})",
            project_kpis["project_id"].nunique(),
            utilization["engineer"].nunique(),
            source_label,
        ],
    }
)
kpi_summary_export_df = dashboard["kpi_summary"].copy()
summary_excel = report_excel_bytes(kpi_summary_export_df, operational_summary_df)
summary_pdf = report_pdf_bytes(
    source_label,
    kpi_summary_export_df,
    operational_summary_df,
    project_snapshot_df,
)
mail_settings = smtp_settings()

action_cols = st.columns([1.2, 1.2, 1.6])
with action_cols[0]:
    st.download_button(
        "Download Summary Table",
        data=summary_excel,
        file_name="dashboard_summary.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
with action_cols[1]:
    st.download_button(
        "Download PDF Report",
        data=summary_pdf,
        file_name="dashboard_report.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
with action_cols[2]:
    with st.popover("Send Report to Mail"):
        st.caption("Sends the summary workbook and PDF report as email attachments.")
        recipients_raw = st.text_input(
            "Recipients",
            placeholder="manager@company.com, team@company.com",
            help="Separate multiple email addresses with commas.",
        )
        mail_subject = st.text_input(
            "Subject",
            value="PANSOFT Delivery Intelligence Report",
        )
        mail_body = st.text_area(
            "Email body",
            value="Please find attached the latest dashboard summary table and PDF report.",
            height=120,
        )
        if mail_settings is None:
            st.info(
                "Email sending is not configured yet. Add SMTP credentials in Streamlit secrets to enable this button."
            )
        if st.button("Send Report", use_container_width=True, disabled=mail_settings is None):
            recipients = [email.strip() for email in recipients_raw.split(",") if email.strip()]
            if not recipients:
                st.error("Enter at least one recipient email address.")
            else:
                try:
                    send_report_email(
                        smtp_config=mail_settings,
                        recipients=recipients,
                        subject=mail_subject,
                        body=mail_body,
                        summary_excel=summary_excel,
                        summary_pdf=summary_pdf,
                    )
                except Exception as exc:
                    st.error(f"Email send failed: {exc}")
                else:
                    st.success("Report email sent successfully.")

metric_cols = st.columns(4)
metric_specs = [
    (
        "Right First Time",
        f"{kpi_summary.loc['RFT', 'value']:.1f}%",
        metric_status(float(kpi_summary.loc["RFT", "value"]), 96, 92),
    ),
    (
        "On-Time Delivery",
        f"{kpi_summary.loc['OTD', 'value']:.1f}%",
        metric_status(float(kpi_summary.loc["OTD", "value"]), 94, 90),
    ),
    (
        "Avg. Utilization",
        f"{avg_utilization:.1f}%",
        metric_status(float(avg_utilization), 82, 70),
    ),
    (
        "Top Capability",
        f"{top_capability['capability_score']:.2f}",
        str(top_capability["engineer"]),
    ),
]

for col, (label, value, tag) in zip(metric_cols, metric_specs):
    with col:
        st.markdown(
            f"""
            <div class="metric-shell">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
                <div class="metric-tag">{tag}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

left, right = st.columns([1.2, 1])

with left:
    st.markdown('<div class="section-title">Project Delivery Performance</div>', unsafe_allow_html=True)
    chart_df = project_kpis[["project_name", "rft", "otd"]].melt(
        id_vars="project_name",
        value_vars=["rft", "otd"],
        var_name="Metric",
        value_name="Score",
    )
    fig_delivery = px.bar(
        chart_df,
        x="project_name",
        y="Score",
        color="Metric",
        barmode="group",
        text_auto=".0%",
        color_discrete_map={"rft": "#0f766e", "otd": "#d97706"},
    )
    fig_delivery.update_layout(
        height=380,
        yaxis_tickformat=".0%",
        margin=dict(l=10, r=10, t=10, b=10),
        legend_title_text="",
        plot_bgcolor="rgba(255,255,255,0)",
        paper_bgcolor="rgba(255,255,255,0)",
        xaxis_title="",
        yaxis_title="",
    )
    st.plotly_chart(fig_delivery, use_container_width=True)

with right:
    st.markdown('<div class="section-title">Engineering Utilization</div>', unsafe_allow_html=True)
    fig_util = px.bar(
        utilization,
        x="utilization_pct",
        y="engineer",
        orientation="h",
        text="utilization_pct",
        color="utilization_pct",
        color_continuous_scale=["#f4d7a1", "#d97706", "#8a4b08"],
    )
    fig_util.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig_util.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=10, b=10),
        coloraxis_showscale=False,
        plot_bgcolor="rgba(255,255,255,0)",
        paper_bgcolor="rgba(255,255,255,0)",
        yaxis=dict(categoryorder="total ascending"),
        xaxis_title="Utilization %",
        yaxis_title="",
    )
    st.plotly_chart(fig_util, use_container_width=True)

bottom_left, bottom_right = st.columns([1, 1.2])

with bottom_left:
    st.markdown('<div class="section-title">Capability Ranking</div>', unsafe_allow_html=True)
    fig_skill = px.bar(
        capability,
        x="capability_score",
        y="engineer",
        orientation="h",
        text="capability_score",
        color="capability_score",
        color_continuous_scale=["#d5ebe8", "#0f766e", "#083b39"],
    )
    fig_skill.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig_skill.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=10, b=10),
        coloraxis_showscale=False,
        plot_bgcolor="rgba(255,255,255,0)",
        paper_bgcolor="rgba(255,255,255,0)",
        yaxis=dict(categoryorder="total ascending"),
        xaxis_title="Capability Score",
        yaxis_title="",
    )
    st.plotly_chart(fig_skill, use_container_width=True)

with bottom_right:
    st.markdown('<div class="section-title">Operational Snapshot</div>', unsafe_allow_html=True)
    snapshot_cols = st.columns(2)
    with snapshot_cols[0]:
        st.dataframe(
            project_snapshot_df,
            use_container_width=True,
            hide_index=True,
        )
    with snapshot_cols[1]:
        st.dataframe(operational_summary_df, use_container_width=True, hide_index=True)

st.markdown('<div class="section-title">Data Health</div>', unsafe_allow_html=True)
health_cols = st.columns(3)
health_cols[0].info(f"Projects loaded: {len(processed.projects)}")
health_cols[1].info(f"Tasks loaded: {len(processed.tasks)}")
health_cols[2].info(f"Power BI rows: {len(power_bi_dataset)}")
