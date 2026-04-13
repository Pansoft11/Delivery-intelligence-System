from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class KPIThresholds:
    """Target thresholds used to classify overall project KPI health."""

    rft_target: float = 0.95
    otd_target: float = 0.95
    feedback_target: float = 4.3


def calculate_kpi(
    projects_df: pd.DataFrame,
    tasks_df: pd.DataFrame,
    performance_df: pd.DataFrame,
    feedback_df: pd.DataFrame,
    thresholds: KPIThresholds | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate project-level KPI outputs and a summary table."""

    thresholds = thresholds or KPIThresholds()

    task_metrics = (
        tasks_df.merge(performance_df, on="task_id", how="left")
        .groupby("project_id", dropna=False)
        .agg(
            total_tasks=("task_id", "count"),
            completed_tasks=("status", lambda series: series.str.lower().eq("completed").sum()),
            rft=("rft", "mean"),
            otd=("otd", "mean"),
            avg_rework_count=("rework_count", "mean"),
        )
        .reset_index()
    )

    feedback_kpi = (
        feedback_df.merge(tasks_df[["task_id", "project_id"]], on="task_id", how="left")
        .groupby("project_id", dropna=False)
        .agg(
            feedback_score=("rating", "mean"),
            feedback_count=("rating", "count"),
        )
        .reset_index()
    )

    project_kpis = (
        projects_df.merge(task_metrics, on="project_id", how="left")
        .merge(feedback_kpi, on="project_id", how="left")
        .fillna(
            {
                "total_tasks": 0,
                "completed_tasks": 0,
                "rft": 0.0,
                "otd": 0.0,
                "avg_rework_count": 0.0,
                "feedback_score": 0.0,
                "feedback_count": 0,
            }
        )
    )

    project_kpis["project_health"] = project_kpis.apply(
        lambda row: classify_project_health(
            rft=row["rft"],
            otd=row["otd"],
            feedback=row["feedback_score"],
            thresholds=thresholds,
        ),
        axis=1,
    )

    summary = pd.DataFrame(
        [
            {
                "metric": "RFT",
                "value": round(project_kpis["rft"].mean() * 100, 2),
                "target": thresholds.rft_target * 100,
                "unit": "%",
            },
            {
                "metric": "OTD",
                "value": round(project_kpis["otd"].mean() * 100, 2),
                "target": thresholds.otd_target * 100,
                "unit": "%",
            },
            {
                "metric": "Feedback",
                "value": round(
                    project_kpis["feedback_score"].replace(0, pd.NA).mean(skipna=True) or 0.0,
                    2,
                ),
                "target": thresholds.feedback_target,
                "unit": "/5",
            },
            {
                "metric": "Projects Tracked",
                "value": int(project_kpis["project_id"].nunique()),
                "target": 0,
                "unit": "count",
            },
        ]
    )

    return project_kpis, summary


def classify_project_health(
    rft: float,
    otd: float,
    feedback: float,
    thresholds: KPIThresholds,
) -> str:
    """Return a traffic-light status based on KPI threshold attainment."""

    passed = 0
    passed += int(rft >= thresholds.rft_target)
    passed += int(otd >= thresholds.otd_target)
    passed += int(feedback >= thresholds.feedback_target)

    if passed == 3:
        return "Green"
    if passed == 2:
        return "Amber"
    return "Red"
