"""What-if patrol simulator — coverage of high-impact violations."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config


def _parse_patrol_hours(hours: list[int]) -> set[int]:
    return set(int(h) for h in hours)


def simulate_patrol_coverage(
    violations: pd.DataFrame,
    scored: pd.DataFrame,
    assignments: pd.DataFrame,
    patrol_hours: list[int] | None = None,
    num_zones: int | None = None,
    impact_threshold: float | None = None,
) -> dict:
    """
    Estimate % of high-impact violations covered if patrol visits top-N zones
    during selected IST hours.
    """
    hours = _parse_patrol_hours(patrol_hours or config.PATROL_DEFAULT_HOURS)
    n_zones = num_zones or config.PATROL_DEFAULT_ZONES
    threshold = impact_threshold or config.HIGH_IMPACT_SCORE_THRESHOLD

    high_impact_clusters = set(
        scored.loc[scored["congestion_impact_score"] >= threshold, "cluster_id"]
    )
    top_zones = set(scored.head(n_zones)["cluster_id"])

    merged = violations.merge(assignments, on="id", how="inner")
    merged = merged[merged["cluster_id"] >= 0]
    merged = merged[merged["hour_of_day"].isin(hours)]

    high_impact_violations = violations.merge(assignments, on="id", how="inner")
    high_impact_violations = high_impact_violations[
        high_impact_violations["cluster_id"].isin(high_impact_clusters)
    ]

    patrol_window = merged[merged["cluster_id"].isin(top_zones)]
    covered = patrol_window["id"].nunique()
    total_high = max(high_impact_violations["id"].nunique(), 1)

    zone_detail = (
        patrol_window.groupby("cluster_id")
        .agg(violations_in_window=("id", "nunique"))
        .reset_index()
        .merge(
            scored[["cluster_id", "dominant_junction", "congestion_impact_score", "dominant_police_station"]],
            on="cluster_id",
        )
        .sort_values("congestion_impact_score", ascending=False)
    )

    return {
        "patrol_hours": sorted(hours),
        "num_zones": n_zones,
        "impact_threshold": threshold,
        "total_high_impact_violations": int(high_impact_violations["id"].nunique()),
        "violations_covered_in_window": int(covered),
        "coverage_pct": round(100.0 * covered / total_high, 1),
        "zones_detail": zone_detail,
    }
