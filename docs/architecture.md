# PDIS Architecture

## Overview

PDIS follows a simple layered batch-processing architecture designed for Excel-driven operations and Power BI consumption.

## Layers

1. `main.py`
   Orchestrates the full pipeline, triggers processing, and writes output files.
2. `src/data_processing.py`
   Loads `data/master_data.xlsx`, validates the six mandatory tables, normalizes schema, and prepares the Power BI dataset.
3. `src/kpi_engine.py`
   Computes project-level KPI metrics for Right First Time, On-Time Delivery, rework, feedback, and overall project health.
4. `src/utilization_engine.py`
   Aggregates task allocation by engineer and calculates utilization from the engineer master availability percentage.
5. `src/skill_matrix_engine.py`
   Applies weighted category scoring across the skill matrix to derive engineer capability scores and capability bands.
6. `src/report_generator.py`
   Exports processed sheets plus KPI summary, department performance, and engineer performance reports to Excel.

## Data Flow

1. Read the master workbook.
2. Validate workbook structure.
3. Normalize data types and derive operational fields.
4. Compute KPIs, utilization, and skill scores.
5. Merge outputs into a Power BI-ready fact-style dataset.
6. Export processed data and monthly report workbooks.

## Design Notes

- Modules are independent and testable.
- Business logic is kept out of file-writing concerns.
- Sample workbook bootstrapping allows the pipeline to run immediately in a clean repository.
- Output workbooks are business-user friendly while remaining suitable for Power BI ingestion.
