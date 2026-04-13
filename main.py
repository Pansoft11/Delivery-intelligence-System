from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_processing import build_power_bi_dataset, load_master_data
from src.kpi_engine import calculate_kpi
from src.report_generator import (
    build_department_performance,
    build_engineer_performance,
    write_monthly_report,
    write_processed_dataset,
)
from src.skill_matrix_engine import calculate_skill_score
from src.utilization_engine import calculate_utilization


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "master_data.xlsx"
PROCESSED_OUTPUT = ROOT / "outputs" / "processed_data.xlsx"
MONTHLY_REPORT_OUTPUT = ROOT / "outputs" / "monthly_report.xlsx"


def build_system_outputs() -> dict[str, pd.DataFrame]:
    """Run the end-to-end PDIS workflow and return the calculated datasets."""

    processed = load_master_data(DATA_PATH)

    project_kpis, kpi_summary = calculate_kpi(
        projects_df=processed.projects,
        tasks_df=processed.tasks,
        performance_df=processed.performance,
        feedback_df=processed.feedback,
    )
    utilization = calculate_utilization(
        tasks_df=processed.tasks,
        engineers_df=processed.engineer_master,
    )
    capability, skill_breakdown = calculate_skill_score(processed.skill_matrix)
    power_bi_dataset = build_power_bi_dataset(
        processed=processed,
        project_kpis=project_kpis,
        utilization=utilization,
        capability=capability,
    )
    department_performance = build_department_performance(power_bi_dataset)
    engineer_performance = build_engineer_performance(power_bi_dataset)

    executive_summary = pd.concat(
        [
            kpi_summary,
            pd.DataFrame(
                [
                    {
                        "metric": "Average Utilization",
                        "value": round(utilization["utilization_pct"].mean(), 2),
                        "target": 80,
                        "unit": "%",
                    },
                    {
                        "metric": "Average Workload",
                        "value": round(utilization["workload_pct"].mean(), 2),
                        "target": 80,
                        "unit": "%",
                    },
                    {
                        "metric": "Average Capability",
                        "value": round(capability["capability_score"].mean(), 2),
                        "target": 4.0,
                        "unit": "/5",
                    },
                    {
                        "metric": "Overloaded Engineers",
                        "value": int(utilization["allocation_flag"].eq("Overloaded").sum()),
                        "target": 0,
                        "unit": "count",
                    },
                    {
                        "metric": "Underutilized Engineers",
                        "value": int(utilization["allocation_flag"].eq("Underutilized").sum()),
                        "target": 0,
                        "unit": "count",
                    },
                ]
            ),
        ],
        ignore_index=True,
    )

    write_processed_dataset(
        PROCESSED_OUTPUT,
        {
            "projects": processed.projects,
            "tasks": processed.tasks,
            "performance": processed.performance,
            "feedback": processed.feedback,
            "skill_matrix": processed.skill_matrix,
            "engineer_master": processed.engineer_master,
            "project_kpis": project_kpis,
            "utilization": utilization,
            "capability_scores": capability,
            "skill_breakdown": skill_breakdown,
            "power_bi_dataset": power_bi_dataset,
            "department_performance": department_performance,
            "engineer_performance": engineer_performance,
        },
    )
    write_monthly_report(
        MONTHLY_REPORT_OUTPUT,
        summary=executive_summary,
        department_performance=department_performance,
        engineer_performance=engineer_performance,
        project_kpis=project_kpis,
        utilization=utilization,
        capability=capability,
        power_bi_dataset=power_bi_dataset,
    )

    return {
        "executive_summary": executive_summary,
        "project_kpis": project_kpis,
        "utilization": utilization,
        "capability_scores": capability,
        "skill_breakdown": skill_breakdown,
        "power_bi_dataset": power_bi_dataset,
        "department_performance": department_performance,
        "engineer_performance": engineer_performance,
    }


def main() -> None:
    """Execute the PDIS pipeline and print generated artifact locations."""

    outputs = build_system_outputs()
    print("PDIS pipeline completed successfully.")
    print(f"Projects tracked: {len(outputs['project_kpis'])}")
    print(f"Engineers tracked: {len(outputs['capability_scores'])}")
    print(f"Processed dataset: {PROCESSED_OUTPUT}")
    print(f"Monthly report: {MONTHLY_REPORT_OUTPUT}")


if __name__ == "__main__":
    main()
