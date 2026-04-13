from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DEFAULT_PRIORITY = "Medium"


REQUIRED_SHEETS = {
    "projects": {
        "project_id",
        "bu",
        "department",
        "project_name",
        "start_date",
        "due_date",
        "status",
        "priority",
    },
    "tasks": {
        "task_id",
        "project_id",
        "engineer",
        "department",
        "bu",
        "task_type",
        "assigned_date",
        "due_date",
        "completion_date",
        "status",
    },
    "performance": {
        "task_id",
        "rft",
        "otd",
        "rework_count",
        "delay_reason",
    },
    "feedback": {
        "task_id",
        "rating",
        "comments",
        "date",
    },
    "skill_matrix": {
        "engineer",
        "department",
        "skill",
        "category",
        "rating",
    },
    "engineer_master": {
        "engineer",
        "department",
        "availability_pct",
    },
}


@dataclass(frozen=True)
class ProcessedData:
    """Container for the normalized source tables loaded from Excel."""

    projects: pd.DataFrame
    tasks: pd.DataFrame
    performance: pd.DataFrame
    feedback: pd.DataFrame
    skill_matrix: pd.DataFrame
    engineer_master: pd.DataFrame


def bootstrap_master_data(workbook_path: Path) -> None:
    """Create a sample master workbook when the source file does not yet exist."""

    workbook_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        sample_projects().to_excel(writer, sheet_name="projects", index=False)
        sample_tasks().to_excel(writer, sheet_name="tasks", index=False)
        sample_performance().to_excel(writer, sheet_name="performance", index=False)
        sample_feedback().to_excel(writer, sheet_name="feedback", index=False)
        sample_skill_matrix().to_excel(writer, sheet_name="skill_matrix", index=False)
        sample_engineer_master().to_excel(writer, sheet_name="engineer_master", index=False)


def load_master_data(workbook_path: Path) -> ProcessedData:
    """Load, validate, and normalize the mandatory Excel workbook tables."""

    if not workbook_path.exists():
        bootstrap_master_data(workbook_path)

    workbook = pd.read_excel(workbook_path, sheet_name=None)
    validate_workbook(workbook)

    return ProcessedData(
        projects=normalize_projects(workbook["projects"]),
        tasks=normalize_tasks(workbook["tasks"]),
        performance=normalize_performance(workbook["performance"]),
        feedback=normalize_feedback(workbook["feedback"]),
        skill_matrix=normalize_skill_matrix(workbook["skill_matrix"]),
        engineer_master=normalize_engineer_master(workbook["engineer_master"]),
    )


def validate_workbook(workbook: dict[str, pd.DataFrame]) -> None:
    """Validate that all required sheets and columns are present."""

    missing_sheets = sorted(set(REQUIRED_SHEETS) - set(workbook))
    if missing_sheets:
        raise ValueError(f"Workbook is missing required sheets: {', '.join(missing_sheets)}")

    for sheet_name, required_columns in REQUIRED_SHEETS.items():
        actual_columns = set(workbook[sheet_name].columns.str.strip().str.lower())
        missing_columns = sorted(required_columns - actual_columns)
        if missing_columns:
            raise ValueError(
                f"Sheet '{sheet_name}' is missing required columns: {', '.join(missing_columns)}"
            )


def normalize_projects(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize project-level fields and coerce date columns safely."""

    projects = standardize_columns(df)
    for column in ["start_date", "due_date"]:
        projects[column] = pd.to_datetime(projects[column], errors="coerce")
    projects["priority"] = projects["priority"].fillna(DEFAULT_PRIORITY)
    return projects


def normalize_tasks(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize task fields and derive schedule variance in days."""

    tasks = standardize_columns(df)
    for column in ["assigned_date", "due_date", "completion_date"]:
        tasks[column] = pd.to_datetime(tasks[column], errors="coerce")
    tasks["schedule_variance_days"] = (
        tasks["completion_date"] - tasks["due_date"]
    ).dt.days
    tasks["schedule_variance_days"] = tasks["schedule_variance_days"].fillna(0)
    return tasks


def normalize_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize KPI performance flags and rework counts."""

    performance = standardize_columns(df)
    performance["rft"] = pd.to_numeric(performance["rft"], errors="coerce").fillna(0).astype(int)
    performance["otd"] = pd.to_numeric(performance["otd"], errors="coerce").fillna(0).astype(int)
    performance["rework_count"] = pd.to_numeric(
        performance["rework_count"], errors="coerce"
    ).fillna(0).astype(int)
    performance["delay_reason"] = performance["delay_reason"].fillna("")
    return performance


def normalize_skill_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize skill matrix ratings."""

    skills = standardize_columns(df)
    skills["rating"] = pd.to_numeric(skills["rating"], errors="coerce").fillna(0.0)
    return skills


def normalize_engineer_master(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize engineer availability percentages."""

    engineers = standardize_columns(df)
    engineers["availability_pct"] = pd.to_numeric(
        engineers["availability_pct"], errors="coerce"
    ).fillna(0.0)
    return engineers


def normalize_feedback(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize task feedback values and timestamps."""

    feedback = standardize_columns(df)
    feedback["rating"] = pd.to_numeric(
        feedback["rating"], errors="coerce"
    ).fillna(0.0)
    feedback["comments"] = feedback["comments"].fillna("")
    feedback["date"] = pd.to_datetime(feedback["date"], errors="coerce")
    return feedback


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of a DataFrame with normalized lowercase column names."""

    formatted = df.copy()
    formatted.columns = formatted.columns.str.strip().str.lower()
    return formatted


def build_power_bi_dataset(
    processed: ProcessedData,
    project_kpis: pd.DataFrame,
    utilization: pd.DataFrame,
    capability: pd.DataFrame,
) -> pd.DataFrame:
    """Create a task-grain, Power BI-ready dataset by merging all normalized tables."""

    latest_feedback = (
        processed.feedback.sort_values("date")
        .groupby("task_id", dropna=False)
        .tail(1)[["task_id", "rating", "comments", "date"]]
        .rename(
            columns={
                "rating": "feedback_rating",
                "comments": "feedback_comments",
                "date": "feedback_date",
            }
        )
    )
    project_feedback = (
        processed.feedback.merge(processed.tasks[["task_id", "project_id"]], on="task_id", how="left")
        .groupby("project_id", dropna=False)["rating"]
        .mean()
        .reset_index(name="avg_feedback_score")
    )

    dataset = (
        processed.tasks.merge(processed.projects, on="project_id", how="left", suffixes=("_task", "_project"))
        .merge(processed.performance, on="task_id", how="left")
        .merge(latest_feedback, on="task_id", how="left")
        .merge(project_kpis, on="project_id", how="left", suffixes=("", "_project_kpi"))
        .merge(utilization, on=["engineer", "department"], how="left")
        .merge(capability, on=["engineer", "department"], how="left")
        .merge(project_feedback, on="project_id", how="left")
    )

    numeric_fill_defaults = {
        "rft": 0.0,
        "otd": 0.0,
        "rework_count": 0,
        "feedback_rating": 0.0,
        "feedback_score": 0.0,
        "avg_feedback_score": 0.0,
        "workload_pct": 0.0,
        "utilization_pct": 0.0,
        "billable_utilization_pct": 0.0,
        "assigned_tasks": 0,
        "completed_tasks": 0,
        "overdue_tasks": 0,
        "capability_score": 0.0,
        "categories_covered": 0,
        "avg_rating": 0.0,
        "total_tasks": 0,
        "avg_rework_count": 0.0,
    }
    dataset = dataset.fillna(numeric_fill_defaults)
    dataset["feedback_comments"] = dataset["feedback_comments"].fillna("")
    dataset["delay_reason"] = dataset["delay_reason"].fillna("")
    dataset["rft_pct"] = (dataset["rft"] * 100).round(2)
    dataset["otd_pct"] = (dataset["otd"] * 100).round(2)
    dataset["portfolio_utilization_pct"] = round(utilization["utilization_pct"].mean(), 2)
    dataset["portfolio_workload_pct"] = round(utilization["workload_pct"].mean(), 2)
    dataset["portfolio_capability_score"] = round(capability["capability_score"].mean(), 2)
    return dataset.sort_values(["project_id", "task_id"]).reset_index(drop=True)


def sample_projects() -> pd.DataFrame:
    """Return sample project data that matches the mandatory workbook schema."""

    return pd.DataFrame(
        [
            ["P001", "Components", "Analyzer Delivery", "Aftermarket Analyzer Upgrade", "2026-01-03", "2026-02-15", "Completed", "High"],
            ["P002", "Manufacturing", "Analyzer Delivery", "Manufacturing Diagnostics Rollout", "2026-01-10", "2026-03-05", "Completed", "High"],
            ["P003", "Digital", "Analytics", "Telematics KPI Automation", "2026-02-01", "2026-03-28", "Completed", "Medium"],
            ["P004", "Quality", "Project Engineering", "Plant Quality Data Cleanup", "2026-02-12", "2026-04-12", "Completed", "Medium"],
        ],
        columns=[
            "project_id",
            "bu",
            "department",
            "project_name",
            "start_date",
            "due_date",
            "status",
            "priority",
        ],
    )


def sample_tasks() -> pd.DataFrame:
    """Return sample task data used to bootstrap a runnable workbook."""

    return pd.DataFrame(
        [
            ["T001", "P001", "Asha", "Analyzer Delivery", "Components", "Requirements", "2026-01-05", "2026-01-14", "2026-01-13", "Completed"],
            ["T002", "P001", "Asha", "Analyzer Delivery", "Components", "Configuration", "2026-01-15", "2026-01-29", "2026-01-30", "Completed"],
            ["T003", "P001", "Ishita", "Analytics", "Components", "Testing", "2026-01-30", "2026-02-12", "2026-02-10", "Completed"],
            ["T004", "P002", "Rohan", "Analyzer Delivery", "Manufacturing", "Data Mapping", "2026-01-18", "2026-02-05", "2026-02-06", "Completed"],
            ["T005", "P002", "Asha", "Analyzer Delivery", "Manufacturing", "Automation", "2026-02-06", "2026-02-18", "2026-02-21", "Completed"],
            ["T006", "P002", "Rohan", "Analyzer Delivery", "Manufacturing", "Go-Live Support", "2026-02-19", "2026-03-04", "2026-03-03", "Completed"],
            ["T007", "P003", "Ishita", "Analytics", "Digital", "KPI Design", "2026-02-03", "2026-02-20", "2026-02-18", "Completed"],
            ["T008", "P003", "Pranav", "Automation", "Digital", "Excel Integration", "2026-02-21", "2026-03-05", "2026-03-05", "Completed"],
            ["T009", "P003", "Rohan", "Analyzer Delivery", "Digital", "UAT Support", "2026-03-06", "2026-03-24", "2026-03-22", "Completed"],
            ["T010", "P004", "Nina", "Quality", "Quality", "Data Audit", "2026-02-15", "2026-03-12", "2026-03-11", "Completed"],
            ["T011", "P004", "Vikram", "Project Engineering", "Quality", "Cleanup Rules", "2026-03-13", "2026-03-29", "2026-03-29", "Completed"],
            ["T012", "P004", "Vikram", "Project Engineering", "Quality", "Validation Dashboard", "2026-03-30", "2026-04-10", "2026-04-10", "Completed"],
        ],
        columns=[
            "task_id",
            "project_id",
            "engineer",
            "department",
            "bu",
            "task_type",
            "assigned_date",
            "due_date",
            "completion_date",
            "status",
        ],
    )


def sample_performance() -> pd.DataFrame:
    """Return sample task performance metrics for KPI calculations."""

    return pd.DataFrame(
        [
            ["T001", 1, 1, 0, ""],
            ["T002", 1, 0, 0, "Configuration approval delay"],
            ["T003", 0, 1, 1, ""],
            ["T004", 1, 0, 0, "Source data clarification"],
            ["T005", 0, 0, 2, "Late scope change"],
            ["T006", 1, 1, 0, ""],
            ["T007", 1, 1, 0, ""],
            ["T008", 1, 1, 0, ""],
            ["T009", 1, 1, 0, ""],
            ["T010", 0, 1, 1, ""],
            ["T011", 1, 1, 0, ""],
            ["T012", 1, 1, 0, ""],
        ],
        columns=[
            "task_id",
            "rft",
            "otd",
            "rework_count",
            "delay_reason",
        ],
    )


def sample_skill_matrix() -> pd.DataFrame:
    """Return sample skill matrix records for weighted capability scoring."""

    return pd.DataFrame(
        [
            ["Asha", "Analyzer Delivery", "Analyzer Configuration", "Technical", 4.7],
            ["Asha", "Analyzer Delivery", "Excel Automation", "Tools", 4.5],
            ["Asha", "Analyzer Delivery", "Stakeholder Management", "Project", 4.4],
            ["Asha", "Analyzer Delivery", "Cummins Domain", "Business", 4.2],
            ["Rohan", "Analyzer Delivery", "SQL Diagnostics", "Technical", 4.1],
            ["Rohan", "Analyzer Delivery", "Power Query", "Tools", 4.6],
            ["Rohan", "Analyzer Delivery", "Delivery Coordination", "Project", 4.0],
            ["Rohan", "Analyzer Delivery", "Manufacturing Process", "Business", 3.9],
            ["Ishita", "Analytics", "Python Analytics", "Technical", 4.8],
            ["Ishita", "Analytics", "Power BI Modeling", "Tools", 4.4],
            ["Ishita", "Analytics", "Quality Planning", "Project", 4.5],
            ["Ishita", "Analytics", "Telematics", "Business", 4.1],
            ["Vikram", "Project Engineering", "Root Cause Analysis", "Technical", 4.0],
            ["Vikram", "Project Engineering", "Project Planner", "Tools", 3.8],
            ["Vikram", "Project Engineering", "Execution Control", "Project", 4.2],
            ["Vikram", "Project Engineering", "Plant Operations", "Business", 3.9],
            ["Nina", "Quality", "Validation Testing", "Technical", 4.2],
            ["Nina", "Quality", "Quality Checklists", "Tools", 4.1],
            ["Nina", "Quality", "Issue Escalation", "Project", 3.9],
            ["Nina", "Quality", "Quality Systems", "Business", 4.0],
            ["Pranav", "Automation", "Power Automate", "Technical", 4.4],
            ["Pranav", "Automation", "Excel Macros", "Tools", 4.5],
            ["Pranav", "Automation", "Release Readiness", "Project", 4.1],
            ["Pranav", "Automation", "Reporting Operations", "Business", 3.8],
        ],
        columns=["engineer", "department", "skill", "category", "rating"],
    )


def sample_engineer_master() -> pd.DataFrame:
    """Return sample engineer availability percentages."""

    return pd.DataFrame(
        [
            ["Asha", "Analyzer Delivery", 78],
            ["Rohan", "Analyzer Delivery", 82],
            ["Ishita", "Analytics", 90],
            ["Vikram", "Project Engineering", 94],
            ["Nina", "Quality", 72],
            ["Pranav", "Automation", 55],
        ],
        columns=[
            "engineer",
            "department",
            "availability_pct",
        ],
    )


def sample_feedback() -> pd.DataFrame:
    """Return sample task feedback records."""

    return pd.DataFrame(
        [
            ["T003", 4.6, "Strong collaboration and quick turnaround.", "2026-02-11"],
            ["T005", 4.1, "Needed tighter scope control.", "2026-02-22"],
            ["T008", 4.8, "Automation significantly improved reporting quality.", "2026-03-06"],
            ["T012", 4.3, "Solid execution with clear validation evidence.", "2026-04-11"],
        ],
        columns=["task_id", "rating", "comments", "date"],
    )
