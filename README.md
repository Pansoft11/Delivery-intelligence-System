# PANSOFT Delivery Intelligence System

This repository contains a Python analytics pipeline and a Streamlit dashboard for tracking delivery KPIs, utilization, and capability across engineering teams.

## What is ready now

- `app.py` is the Streamlit entrypoint for deployment.
- `main.py` runs the offline reporting pipeline and exports Excel outputs.
- `requirements.txt` now includes the packages needed by Streamlit Community Cloud.
- `.gitignore` excludes local caches, generated outputs, and secrets.
- `.streamlit/config.toml` provides a stable light theme for deployment.

## Run locally

```powershell
pip install -r requirements.txt
streamlit run app.py
```

For the Excel export pipeline:

```powershell
python main.py
```

## Workbook format

The dashboard accepts one Excel workbook with these required sheets:

- `projects`
- `tasks`
- `performance`
- `feedback`
- `skill_matrix`
- `engineer_master`

If you do not upload a workbook, the app uses `data/master_data.xlsx` when present, otherwise it falls back to built-in sample data.

## Push to GitHub

Run these commands from the project folder after creating an empty GitHub repository:

```powershell
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

## Deploy to Streamlit Community Cloud

1. Push this project to GitHub.
2. Open https://share.streamlit.io/ and sign in with GitHub.
3. Click `Create app`.
4. Select your repository, branch `main`, and file path `app.py`.
5. Click `Deploy`.

## Recommended repo contents

Keep these files in GitHub:

- `app.py`
- `main.py`
- `src/`
- `data/master_data.xlsx` if you want a default workbook in production
- `requirements.txt`
- `.streamlit/config.toml`
- `README.md`

## Notes for Streamlit deployment

- If you want users to upload their own workbook, the current app is already set up for that.
- If your future app needs API keys, place them in Streamlit secrets instead of hardcoding them.
- Generated report files under `outputs/` should stay out of GitHub.
