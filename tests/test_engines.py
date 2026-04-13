import pandas as pd

from src.data_processing import (
    build_power_bi_dataset,
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


def test_kpi_engine_returns_expected_metrics():
    project_kpis, summary = calculate_kpi(
        projects_df=sample_projects().assign(
            start_date=lambda df: pd.to_datetime(df["start_date"]),
            due_date=lambda df: pd.to_datetime(df["due_date"]),
        ),
        tasks_df=sample_tasks().assign(
            assigned_date=lambda df: pd.to_datetime(df["assigned_date"]),
            due_date=lambda df: pd.to_datetime(df["due_date"]),
            completion_date=lambda df: pd.to_datetime(df["completion_date"]),
            schedule_variance_days=lambda df: (
                pd.to_datetime(df["completion_date"]) - pd.to_datetime(df["due_date"])
            ).dt.days,
        ),
        performance_df=sample_performance(),
        feedback_df=sample_feedback(),
    )

    assert len(project_kpis) == 4
    assert set(summary["metric"]) >= {"RFT", "OTD", "Feedback"}


def test_utilization_engine_calculates_capacity_ratio():
    tasks = sample_tasks().assign(
        assigned_date=lambda df: pd.to_datetime(df["assigned_date"]),
        due_date=lambda df: pd.to_datetime(df["due_date"]),
        completion_date=lambda df: pd.to_datetime(df["completion_date"]),
        schedule_variance_days=lambda df: (
            pd.to_datetime(df["completion_date"]) - pd.to_datetime(df["due_date"])
        ).dt.days,
    )
    utilization = calculate_utilization(tasks, sample_engineer_master())

    assert "utilization_pct" in utilization.columns
    assert "workload_pct" in utilization.columns
    assert "allocation_flag" in utilization.columns
    assert utilization["allocation_flag"].isin(["Overloaded", "Balanced", "Underutilized"]).all()


def test_skill_matrix_engine_applies_weighted_scores():
    capability, weighted = calculate_skill_score(sample_skill_matrix())

    assert len(capability) == 6
    assert "weighted_score" in weighted.columns
    assert capability.iloc[0]["capability_score"] >= capability.iloc[-1]["capability_score"]


def test_power_bi_dataset_contains_rollups():
    projects = sample_projects().assign(
        start_date=lambda df: pd.to_datetime(df["start_date"]),
        due_date=lambda df: pd.to_datetime(df["due_date"]),
    )
    tasks = sample_tasks().assign(
        assigned_date=lambda df: pd.to_datetime(df["assigned_date"]),
        due_date=lambda df: pd.to_datetime(df["due_date"]),
        completion_date=lambda df: pd.to_datetime(df["completion_date"]),
        schedule_variance_days=lambda df: (
            pd.to_datetime(df["completion_date"]) - pd.to_datetime(df["due_date"])
        ).dt.days,
    )
    feedback = sample_feedback()
    performance = sample_performance()
    engineers = sample_engineer_master()
    skills = sample_skill_matrix()

    project_kpis, _ = calculate_kpi(projects, tasks, performance, feedback)
    utilization = calculate_utilization(tasks, engineers)
    capability, _ = calculate_skill_score(skills)

    processed = type(
        "ProcessedDataStub",
        (),
        {
            "projects": projects,
            "tasks": tasks,
            "performance": performance,
            "feedback": feedback,
            "skill_matrix": skills,
            "engineer_master": engineers,
        },
    )()
    dataset = build_power_bi_dataset(processed, project_kpis, utilization, capability)

    assert "portfolio_utilization_pct" in dataset.columns
    assert "rft_pct" in dataset.columns
    assert "feedback_rating" in dataset.columns


def test_report_aggregations_create_department_and_engineer_views():
    projects = sample_projects().assign(
        start_date=lambda df: pd.to_datetime(df["start_date"]),
        due_date=lambda df: pd.to_datetime(df["due_date"]),
    )
    tasks = sample_tasks().assign(
        assigned_date=lambda df: pd.to_datetime(df["assigned_date"]),
        due_date=lambda df: pd.to_datetime(df["due_date"]),
        completion_date=lambda df: pd.to_datetime(df["completion_date"]),
        schedule_variance_days=lambda df: (
            pd.to_datetime(df["completion_date"]) - pd.to_datetime(df["due_date"])
        ).dt.days,
    )
    project_kpis, _ = calculate_kpi(projects, tasks, sample_performance(), sample_feedback())
    utilization = calculate_utilization(tasks, sample_engineer_master())
    capability, _ = calculate_skill_score(sample_skill_matrix())
    processed = type(
        "ProcessedDataStub",
        (),
        {
            "projects": projects,
            "tasks": tasks,
            "performance": sample_performance(),
            "feedback": sample_feedback(),
            "skill_matrix": sample_skill_matrix(),
            "engineer_master": sample_engineer_master(),
        },
    )()
    dataset = build_power_bi_dataset(processed, project_kpis, utilization, capability)

    department_view = build_department_performance(dataset)
    engineer_view = build_engineer_performance(dataset)

    assert "department" in department_view.columns
    assert "engineer" in engineer_view.columns
