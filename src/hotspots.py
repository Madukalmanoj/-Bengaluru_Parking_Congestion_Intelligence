"""Spatial hotspot detection via DBSCAN and jurisdiction rollups."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config


def _dominant(values: list[str]) -> str:
    if not values:
        return "UNKNOWN"
    return Counter(values).most_common(1)[0][0]


def _mode_or_default(series: pd.Series, default):
    m = series.mode()
    return m.iloc[0] if len(m) else default


def run_dbscan(df: pd.DataFrame) -> pd.DataFrame:
    """Cluster violation points with DBSCAN (haversine metric)."""
    coords = df[["latitude", "longitude"]].values
    coords_rad = np.radians(coords)

    print(
        f"Running DBSCAN (eps={config.DBSCAN_EPS_METERS}m, "
        f"min_samples={config.DBSCAN_MIN_SAMPLES}) on {len(df):,} points..."
    )
    clustering = DBSCAN(
        eps=config.DBSCAN_EPS_RADIANS,
        min_samples=config.DBSCAN_MIN_SAMPLES,
        metric="haversine",
        algorithm="ball_tree",
        n_jobs=-1,
    )
    labels = clustering.fit_predict(coords_rad)
    df = df.copy()
    df["cluster_id"] = labels
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    noise = (labels == -1).sum()
    print(f"  Found {n_clusters} clusters, {noise:,} noise points")
    return df


def build_cluster_table(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate cluster-level stats from labeled points."""
    clustered = df[df["cluster_id"] >= 0].copy()
    if clustered.empty:
        return pd.DataFrame()

    rows = []
    for cid, grp in clustered.groupby("cluster_id"):
        all_vtypes: list[str] = []
        for vts in grp["violation_types"]:
            all_vtypes.extend(vts)

        peak_mask = grp.apply(
            lambda r: _in_peak_window(r["hour"]), axis=1
        )
        dates = grp["date"].nunique()

        rows.append(
            {
                "cluster_id": int(cid),
                "centroid_lat": grp["latitude"].mean(),
                "centroid_lon": grp["longitude"].mean(),
                "violation_count": len(grp),
                "distinct_days": dates,
                "dominant_violation": _dominant(all_vtypes),
                "violation_types_all": list(set(all_vtypes)),
                "peak_hour_fraction": peak_mask.mean(),
                "dominant_junction": _dominant(grp["junction_name"].tolist()),
                "dominant_police_station": _dominant(grp["police_station"].tolist()),
                "dominant_center_code": _mode_or_default(grp["center_code"], grp["center_code"].iloc[0]),
                "sample_location": _mode_or_default(grp["location"], "")
                if "location" in grp.columns
                else "",
                "peak_hour_window": _recommend_patrol_window(grp),
                "first_seen": grp["local_datetime"].min(),
                "last_seen": grp["local_datetime"].max(),
            }
        )

    return pd.DataFrame(rows).sort_values("violation_count", ascending=False)


def _in_peak_window(hour: float) -> bool:
    for start, end in config.PEAK_HOUR_WINDOWS:
        if start <= hour < end:
            return True
    return False


def _recommend_patrol_window(grp: pd.DataFrame) -> str:
    """Recommend patrol window based on top 2 hours of violations."""
    hours = grp["hour_of_day"].value_counts().head(2).index.tolist()
    if not hours:
        return "08:00–10:00"
    windows = []
    for h in sorted(hours):
        start = f"{int(h):02d}:00"
        end = f"{int(h)+1:02d}:00"
        windows.append(f"{start}–{end}")
    return " & ".join(windows)


def junction_rollup(df: pd.DataFrame) -> pd.DataFrame:
    """Roll up violations by junction name."""
    rows = []
    for jname, grp in df.groupby("junction_name"):
        all_vtypes: list[str] = []
        for vts in grp["violation_types"]:
            all_vtypes.extend(vts)
        rows.append(
            {
                "rollup_type": "junction",
                "name": jname,
                "centroid_lat": grp["latitude"].mean(),
                "centroid_lon": grp["longitude"].mean(),
                "violation_count": len(grp),
                "distinct_days": grp["date"].nunique(),
                "dominant_violation": _dominant(all_vtypes),
                "dominant_police_station": _dominant(grp["police_station"].tolist()),
                "peak_hour_window": _recommend_patrol_window(grp),
            }
        )
    return pd.DataFrame(rows).sort_values("violation_count", ascending=False)


def station_rollup(df: pd.DataFrame) -> pd.DataFrame:
    """Roll up violations by police station / center code."""
    rows = []
    for (station, code), grp in df.groupby(["police_station", "center_code"]):
        all_vtypes: list[str] = []
        for vts in grp["violation_types"]:
            all_vtypes.extend(vts)
        rows.append(
            {
                "rollup_type": "police_station",
                "name": station,
                "center_code": code,
                "centroid_lat": grp["latitude"].mean(),
                "centroid_lon": grp["longitude"].mean(),
                "violation_count": len(grp),
                "distinct_days": grp["date"].nunique(),
                "dominant_violation": _dominant(all_vtypes),
                "peak_hour_window": _recommend_patrol_window(grp),
            }
        )
    return pd.DataFrame(rows).sort_values("violation_count", ascending=False)


def detect_hotspots(df: pd.DataFrame, force: bool = False) -> pd.DataFrame:
    """Run hotspot detection and cache cluster table."""
    if config.CLUSTERS_PARQUET.exists() and not force:
        print(f"Loading cached clusters from {config.CLUSTERS_PARQUET}")
        return pd.read_parquet(config.CLUSTERS_PARQUET)

    labeled = run_dbscan(df)
    clusters = build_cluster_table(labeled)

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    clusters.to_parquet(config.CLUSTERS_PARQUET, index=False)
    labeled[["id", "cluster_id"]].to_parquet(config.VIOLATION_CLUSTERS_PARQUET, index=False)

    junctions = junction_rollup(df)
    stations = station_rollup(df)
    junctions.to_parquet(config.PROCESSED_DIR / "rollup_junction.parquet", index=False)
    stations.to_parquet(config.PROCESSED_DIR / "rollup_station.parquet", index=False)

    print(f"  Wrote {len(clusters)} clusters to {config.CLUSTERS_PARQUET}")
    return clusters


if __name__ == "__main__":
    from ingest import ingest

    force = "--force" in sys.argv
    violations = ingest(force=force)
    detect_hotspots(violations, force=force)
