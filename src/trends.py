"""Monthly hotspot trends — worsening vs improving zones."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config


def build_hotspot_trends(
    violations: pd.DataFrame,
    assignments: pd.DataFrame | None = None,
    force: bool = False,
) -> pd.DataFrame:
    """Per-cluster monthly violation counts + trend slope."""
    if config.HOTSPOT_TRENDS_PARQUET.exists() and not force:
        return pd.read_parquet(config.HOTSPOT_TRENDS_PARQUET)

    if assignments is None:
        path = config.VIOLATION_CLUSTERS_PARQUET
        if not path.exists():
            return pd.DataFrame()
        assignments = pd.read_parquet(path)

    merged = violations.merge(assignments, on="id", how="inner")
    merged = merged[merged["cluster_id"] >= 0]

    monthly = (
        merged.groupby(["cluster_id", "month"])
        .size()
        .reset_index(name="violation_count")
        .sort_values(["cluster_id", "month"])
    )

    slopes = []
    for cid, grp in monthly.groupby("cluster_id"):
        if len(grp) < 2:
            slope = 0.0
            direction = "stable"
        else:
            y = grp["violation_count"].values.astype(float)
            x = np.arange(len(y), dtype=float)
            slope = float(np.polyfit(x, y, 1)[0])
            if slope > 2:
                direction = "worsening"
            elif slope < -2:
                direction = "improving"
            else:
                direction = "stable"
        slopes.append(
            {
                "cluster_id": cid,
                "trend_slope": slope,
                "trend_direction": direction,
                "months_active": len(grp),
            }
        )

    summary = pd.DataFrame(slopes)
    trends = monthly.merge(summary, on="cluster_id", how="left")

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    trends.to_parquet(config.HOTSPOT_TRENDS_PARQUET, index=False)
    print(f"  Hotspot monthly trends -> {config.HOTSPOT_TRENDS_PARQUET}")
    return trends


def get_cluster_trend_chart_data(cluster_id: int, trends: pd.DataFrame) -> pd.DataFrame:
    return trends[trends["cluster_id"] == cluster_id].sort_values("month")
