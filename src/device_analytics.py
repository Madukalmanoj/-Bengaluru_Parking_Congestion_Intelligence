"""Camera/device capture infrastructure analytics."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config


def device_infrastructure_summary(
    violations: pd.DataFrame,
    scored: pd.DataFrame,
    assignments: pd.DataFrame | None = None,
) -> dict:
    """Summarize existing automated capture pipeline (device_id, SCITA push)."""
    total_devices = violations["device_id"].nunique()
    scita_rate = violations["data_sent_to_scita"].mean() * 100 if len(violations) else 0

    top_devices = (
        violations.groupby("device_id")
        .agg(
            captures=("id", "count"),
            scita_push_rate=("data_sent_to_scita", "mean"),
            police_station=("police_station", lambda s: s.mode().iloc[0] if len(s) else ""),
        )
        .reset_index()
        .sort_values("captures", ascending=False)
        .head(20)
    )
    top_devices["scita_push_rate"] = (top_devices["scita_push_rate"] * 100).round(1)

    high_impact_device_coverage = None
    if assignments is not None and config.VIOLATION_CLUSTERS_PARQUET.exists():
        top_clusters = set(scored.head(50)["cluster_id"])
        merged = violations.merge(assignments, on="id", how="inner")
        hi = merged[merged["cluster_id"].isin(top_clusters)]
        devices_in_hotspots = hi["device_id"].nunique()
        high_impact_device_coverage = {
            "devices_covering_top_50_hotspots": int(devices_in_hotspots),
            "pct_of_all_devices": round(100 * devices_in_hotspots / max(total_devices, 1), 1),
            "captures_in_top_hotspots": int(len(hi)),
        }

    return {
        "total_devices": int(total_devices),
        "total_captures": len(violations),
        "scita_push_rate_pct": round(scita_rate, 1),
        "top_devices": top_devices,
        "high_impact_coverage": high_impact_device_coverage,
    }
