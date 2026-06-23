"""Congestion Impact Score — explainable composite proxy per hotspot."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config


def _normalize_series(s: pd.Series) -> pd.Series:
    mn, mx = s.min(), s.max()
    if mx == mn:
        return pd.Series(0.5, index=s.index)
    return (s - mn) / (mx - mn)


def location_criticality(row: pd.Series, member_locations: str = "") -> float:
    junction = str(row.get("dominant_junction", "No Junction"))
    if junction and junction != "No Junction":
        return config.LOCATION_CRITICALITY["junction_named"]
    loc = str(row.get("sample_location", "") or member_locations).lower()
    for kw in config.LOCATION_KEYWORDS:
        if kw in loc:
            return config.LOCATION_CRITICALITY["keyword_match"]
    return config.LOCATION_CRITICALITY["default"]


def violation_severity_score(violation_types) -> float:
    if violation_types is None:
        return config.DEFAULT_VIOLATION_SEVERITY
    if isinstance(violation_types, float) and np.isnan(violation_types):
        return config.DEFAULT_VIOLATION_SEVERITY
    if isinstance(violation_types, (list, tuple, np.ndarray)):
        types = list(violation_types)
    elif isinstance(violation_types, str):
        types = [violation_types]
    else:
        return config.DEFAULT_VIOLATION_SEVERITY
    if not types:
        return config.DEFAULT_VIOLATION_SEVERITY
    weights = [
        config.VIOLATION_SEVERITY.get(vt, config.DEFAULT_VIOLATION_SEVERITY)
        for vt in types
    ]
    return float(np.mean(weights))


def compute_scores(clusters: pd.DataFrame, force: bool = False) -> pd.DataFrame:
    """Compute Congestion Impact Score for each hotspot cluster."""
    if config.SCORED_PARQUET.exists() and not force:
        print(f"Loading cached scores from {config.SCORED_PARQUET}")
        return pd.read_parquet(config.SCORED_PARQUET)

    df = clusters.copy()

    df["raw_density"] = df["violation_count"]
    df["norm_density"] = _normalize_series(df["raw_density"])

    df["raw_location_crit"] = df.apply(location_criticality, axis=1)
    df["norm_location_crit"] = _normalize_series(df["raw_location_crit"])

    df["raw_severity"] = df["violation_types_all"].apply(violation_severity_score)
    df["norm_severity"] = _normalize_series(df["raw_severity"])

    df["raw_peak_hour"] = df["peak_hour_fraction"].fillna(0)
    df["norm_peak_hour"] = _normalize_series(df["raw_peak_hour"])

    df["raw_recurrence"] = df["distinct_days"]
    df["norm_recurrence"] = _normalize_series(df["raw_recurrence"])

    if "network_flow_weight" in df.columns:
        df["raw_network_flow"] = df["network_flow_weight"].fillna(0.5)
    else:
        df["raw_network_flow"] = 0.5
    df["norm_network_flow"] = _normalize_series(df["raw_network_flow"])

    w = config.SCORE_WEIGHTS
    df["congestion_impact_score"] = (
        w["violation_density"] * df["norm_density"]
        + w["location_criticality"] * df["norm_location_crit"]
        + w["violation_severity"] * df["norm_severity"]
        + w["peak_hour_weight"] * df["norm_peak_hour"]
        + w["recurrence_persistence"] * df["norm_recurrence"]
        + w["network_flow_weight"] * df["norm_network_flow"]
    ) * 100

    df["congestion_impact_score"] = df["congestion_impact_score"].round(2)
    df = df.sort_values("congestion_impact_score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(config.SCORED_PARQUET, index=False)
    print(f"  Scored {len(df)} hotspots -> {config.SCORED_PARQUET}")
    return df


def build_enforcement_export(scored: pd.DataFrame, top_n: int | None = None) -> pd.DataFrame:
    n = top_n or config.ENFORCEMENT_EXPORT_TOP_N
    base_cols = [
        "rank", "cluster_id", "sample_location", "dominant_junction",
        "dominant_police_station", "congestion_impact_score", "violation_count",
        "dominant_violation", "peak_hour_window", "distinct_days",
    ]
    base_names = [
        "rank", "cluster_id", "location", "junction", "police_station",
        "congestion_impact_score", "violation_count", "dominant_violation_type",
        "recommended_patrol_window", "distinct_days_active",
    ]
    optional = ["network_source", "road_class", "trend_direction"]
    opt_cols = [c for c in optional if c in scored.columns]
    export = scored.head(n)[base_cols + opt_cols].copy()
    export.columns = base_names + opt_cols
    return export
