from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_OVERLOADED_THRESHOLD = 90.0
DEFAULT_UNDERUTILIZED_THRESHOLD = 60.0
DEFAULT_WORKLOAD_SCALER = 70.0


def calculate_utilization(
    tasks_df: pd.DataFrame,
    engineers_df: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate engineer workload, utilization bands, and allocation flags."""

    engineer_hours = (
        tasks_df.groupby(["engineer", "department"], dropna=False)
        .agg(
            assigned_tasks=("task_id", "count"),
            completed_tasks=("status", lambda series: series.str.lower().eq("completed").sum()),
            overdue_tasks=("schedule_variance_days", lambda series: (series > 0).sum()),
        )
        .reset_index()
    )

    utilization = engineers_df.merge(
        engineer_hours,
        on=["engineer", "department"],
        how="left",
    ).fillna(
        {
            "assigned_tasks": 0,
            "completed_tasks": 0,
            "overdue_tasks": 0,
        }
    )
    active_task_average = max(utilization["assigned_tasks"].replace(0, np.nan).mean(), 1.0)
    capacity_factor = np.where(
        utilization["availability_pct"] > 0,
        100 / utilization["availability_pct"],
        0.0,
    )
    utilization["workload_pct"] = np.where(
        utilization["assigned_tasks"] > 0,
        (utilization["assigned_tasks"] / active_task_average) * capacity_factor * DEFAULT_WORKLOAD_SCALER,
        0.0,
    ).round(2)
    utilization["utilization_pct"] = utilization["workload_pct"].clip(upper=100)
    utilization["billable_utilization_pct"] = utilization["utilization_pct"]
    utilization["utilization_band"] = utilization["utilization_pct"].apply(utilization_band)
    utilization["allocation_flag"] = utilization["workload_pct"].apply(allocation_flag)
    return utilization.sort_values("utilization_pct", ascending=False).reset_index(drop=True)


def utilization_band(utilization_pct: float) -> str:
    """Map a utilization percentage to a descriptive utilization band."""

    if utilization_pct >= 90:
        return "High"
    if utilization_pct >= 70:
        return "Optimal"
    if utilization_pct >= 50:
        return "Low"
    return "Bench"


def allocation_flag(workload_pct: float) -> str:
    """Flag engineers as overloaded, underutilized, or balanced."""

    if workload_pct > DEFAULT_OVERLOADED_THRESHOLD:
        return "Overloaded"
    if workload_pct < DEFAULT_UNDERUTILIZED_THRESHOLD:
        return "Underutilized"
    return "Balanced"
