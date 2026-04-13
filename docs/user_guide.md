# PDIS User Guide

## Prerequisites

- Python 3.10+
- Excel-compatible environment for reviewing generated workbooks

## Setup

```powershell
pip install -r requirements.txt
```

## Running the system

```powershell
python main.py
```

## Input file

Place the source workbook at `data/master_data.xlsx`.

Required sheets:

- `projects`
- `tasks`
- `performance`
- `feedback`
- `skill_matrix`
- `engineer_master`

If the file does not exist, PDIS creates a sample workbook automatically.

## Outputs

- `outputs/processed_data.xlsx`
  Contains normalized input sheets plus calculated KPI, utilization, skill, and Power BI dataset tabs.
- `outputs/monthly_report.xlsx`
  Contains KPI summary, department performance, engineer performance, project KPIs, utilization, skill matrix, and Power BI dataset tabs.

## KPI Definitions

- `RFT`: average of the `RFT` flag from the performance table
- `OTD`: average of the `OTD` flag from the performance table
- `Feedback`: average task rating from the feedback table

## Power BI Usage

Use the `power_bi_dataset` sheet from `outputs/processed_data.xlsx` or the `Power BI Dataset` sheet from `outputs/monthly_report.xlsx` as the import source for your dashboard model.

## Test run

```powershell
python -m pytest -q tests
```
