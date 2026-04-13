from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_processed_dataset(
    output_path: Path,
    datasets: dict[str, pd.DataFrame],
) -> None:
    """Write processed datasets to a multi-sheet Excel workbook."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet_name, frame in datasets.items():
            frame.to_excel(writer, sheet_name=sheet_name[:31], index=False)


def write_monthly_report(
    output_path: Path,
    summary: pd.DataFrame,
    department_performance: pd.DataFrame,
    engineer_performance: pd.DataFrame,
    project_kpis: pd.DataFrame,
    utilization: pd.DataFrame,
    capability: pd.DataFrame,
    power_bi_dataset: pd.DataFrame,
) -> None:
    """Write the monthly management report with summary and performance tabs."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="KPI Summary", index=False)
        department_performance.to_excel(writer, sheet_name="Department Performance", index=False)
        engineer_performance.to_excel(writer, sheet_name="Engineer Performance", index=False)
        project_kpis.to_excel(writer, sheet_name="Project KPIs", index=False)
        utilization.to_excel(writer, sheet_name="Utilization", index=False)
        capability.to_excel(writer, sheet_name="Skill Matrix", index=False)
        power_bi_dataset.to_excel(writer, sheet_name="Power BI Dataset", index=False)


def build_department_performance(
    power_bi_dataset: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate performance metrics at department level for monthly reporting."""

    return (
        power_bi_dataset.groupby("department", dropna=False)
        .agg(
            projects_tracked=("project_id", "nunique"),
            engineers_tracked=("engineer", "nunique"),
            tasks_tracked=("task_id", "count"),
            rft_pct=("rft_pct", "mean"),
            otd_pct=("otd_pct", "mean"),
            avg_feedback_score=("avg_feedback_score", "mean"),
            avg_capability_score=("capability_score", "mean"),
            avg_workload_pct=("workload_pct", "mean"),
        )
        .reset_index()
        .sort_values("rft_pct", ascending=False)
    )


def build_engineer_performance(
    power_bi_dataset: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate performance metrics at engineer level for monthly reporting."""

    return (
        power_bi_dataset.groupby(["engineer", "department"], dropna=False)
        .agg(
            assigned_projects=("project_id", "nunique"),
            assigned_tasks=("task_id", "count"),
            rft_pct=("rft_pct", "mean"),
            otd_pct=("otd_pct", "mean"),
            avg_feedback_score=("feedback_rating", "mean"),
            capability_score=("capability_score", "mean"),
            workload_pct=("workload_pct", "mean"),
            allocation_flag=("allocation_flag", "last"),
        )
        .reset_index()
        .sort_values(["allocation_flag", "workload_pct"], ascending=[True, False])
    )
