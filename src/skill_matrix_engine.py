from __future__ import annotations

import pandas as pd


DEFAULT_SKILL_WEIGHTS = {
    "Technical": 0.40,
    "Tools": 0.20,
    "Project": 0.25,
    "Business": 0.15,
}


def calculate_skill_score(
    skills_df: pd.DataFrame,
    weights: dict[str, float] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate weighted capability scores and category-level scoring details."""

    weights = weights or DEFAULT_SKILL_WEIGHTS

    category_scores = (
        skills_df.groupby(["engineer", "department", "category"], dropna=False)["rating"]
        .mean()
        .reset_index()
    )

    weighted = category_scores.copy()
    weighted["weight"] = weighted["category"].map(weights).fillna(0.0)
    weighted["weighted_score"] = weighted["rating"] * weighted["weight"]

    capability = (
        weighted.groupby(["engineer", "department"], dropna=False)
        .agg(
            capability_score=("weighted_score", "sum"),
            categories_covered=("category", "nunique"),
            avg_rating=("rating", "mean"),
        )
        .reset_index()
        .sort_values("capability_score", ascending=False)
    )
    capability["capability_band"] = capability["capability_score"].apply(capability_band)

    return capability, weighted.sort_values(["engineer", "category"]).reset_index(drop=True)


def capability_band(score: float) -> str:
    """Map a capability score to a descriptive proficiency band."""

    if score >= 4.3:
        return "Expert"
    if score >= 3.6:
        return "Advanced"
    if score >= 2.8:
        return "Developing"
    return "Needs Support"
