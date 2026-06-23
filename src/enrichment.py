"""OSM road-network weighting + heuristic fallback for traffic-flow proxy."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config


def _highway_weight(highway) -> float:
    if highway is None:
        return config.DEFAULT_ROAD_CLASS_WEIGHT
    if isinstance(highway, list):
        highway = highway[0] if highway else "unclassified"
    return config.ROAD_CLASS_WEIGHTS.get(str(highway), config.DEFAULT_ROAD_CLASS_WEIGHT)


def _heuristic_network_weight(row: pd.Series) -> float:
    """Fallback when OSM unavailable — arterial keywords + junction boost."""
    junction = str(row.get("dominant_junction", "No Junction"))
    if junction and junction != "No Junction":
        loc_crit = config.LOCATION_CRITICALITY["junction_named"]
    else:
        loc = str(row.get("sample_location", "")).lower()
        loc_crit = config.LOCATION_CRITICALITY["keyword_match"] if any(
            kw in loc for kw in config.LOCATION_KEYWORDS
        ) else config.LOCATION_CRITICALITY["default"]
    peak = float(row.get("peak_hour_fraction", 0) or 0)
    return min(1.0, 0.55 * loc_crit + 0.45 * peak)


def _load_graph():
    import osmnx as ox

    if config.OSM_GRAPH_PATH.exists():
        return ox.load_graphml(config.OSM_GRAPH_PATH)

    print(f"  Downloading OSM drive network for {config.OSM_PLACE_NAME}...")
    G = ox.graph_from_place(config.OSM_PLACE_NAME, network_type="drive")
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(G, config.OSM_GRAPH_PATH)
    print(f"  Cached graph -> {config.OSM_GRAPH_PATH}")
    return G


def _load_edge_betweenness(G):
    import networkx as nx

    if config.OSM_EDGE_BC_PATH.exists():
        bc_df = pd.read_parquet(config.OSM_EDGE_BC_PATH)
        return {
            (int(r.u), int(r.v), int(r.k)): float(r.betweenness)
            for r in bc_df.itertuples()
        }

    print("  Computing sampled edge betweenness (one-time, may take a few minutes)...")
    k = min(config.OSM_BETWEENNESS_SAMPLE_K, max(G.number_of_edges(), 1))
    bc = nx.edge_betweenness_centrality(G, k=k, seed=42)
    rows = [
        {"u": u, "v": v, "k": key, "betweenness": val}
        for (u, v, key), val in bc.items()
    ]
    bc_df = pd.DataFrame(rows)
    bc_df.to_parquet(config.OSM_EDGE_BC_PATH, index=False)
    return bc


def _osm_network_weights(clusters: pd.DataFrame) -> pd.DataFrame | None:
    try:
        import osmnx as ox
    except ImportError:
        print("  OSM skipped: install osmnx + networkx for road-network weighting.")
        return None

    try:
        G = _load_graph()
        edge_bc = _load_edge_betweenness(G)
        max_bc = max(edge_bc.values()) if edge_bc else 1.0

        lons = clusters["centroid_lon"].values
        lats = clusters["centroid_lat"].values
        nearest = ox.distance.nearest_edges(G, lons, lats)

        road_weights = []
        bc_norms = []
        road_classes = []

        for u, v, k in nearest:
            data = G.edges[u, v, k]
            hw = _highway_weight(data.get("highway"))
            road_weights.append(hw)
            road_classes.append(
                data.get("highway", "unclassified")
                if not isinstance(data.get("highway"), list)
                else data.get("highway", ["unclassified"])[0]
            )
            bc_norms.append(edge_bc.get((u, v, k), 0.0) / max_bc)

        combined = (
            config.NETWORK_ROAD_CLASS_BLEND * np.array(road_weights)
            + config.NETWORK_BETWEENNESS_BLEND * np.array(bc_norms)
        )

        out = clusters[["cluster_id"]].copy()
        out["network_flow_weight"] = combined
        out["road_class"] = road_classes
        out["network_source"] = "osm"
        print(f"  OSM network weights applied to {len(out)} hotspots.")
        return out
    except Exception as exc:
        print(f"  OSM enrichment failed, using heuristic fallback: {exc}")
        return None


def enrich_network_weights(
    clusters: pd.DataFrame, force: bool = False, use_osm: bool = False
) -> pd.DataFrame:
    """Add network_flow_weight, road_class, network_source to clusters."""
    if config.NETWORK_WEIGHTS_PARQUET.exists() and not force:
        weights = pd.read_parquet(config.NETWORK_WEIGHTS_PARQUET)
        return clusters.drop(
            columns=["network_flow_weight", "road_class", "network_source"], errors="ignore"
        ).merge(weights, on="cluster_id", how="left")

    df = clusters.copy()
    df["network_flow_weight"] = df.apply(_heuristic_network_weight, axis=1)
    df["road_class"] = "heuristic"
    df["network_source"] = "heuristic"

    try_osm = use_osm or config.OSM_GRAPH_PATH.exists()
    if try_osm and config.OSM_ENABLED:
        osm = _osm_network_weights(df)
        if osm is not None:
            df = df.drop(columns=["network_flow_weight", "road_class", "network_source"], errors="ignore")
            df = df.merge(osm, on="cluster_id", how="left")

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df[["cluster_id", "network_flow_weight", "road_class", "network_source"]].to_parquet(
        config.NETWORK_WEIGHTS_PARQUET, index=False
    )
    return df


def enrich_with_osm(clusters: pd.DataFrame, force: bool = False, use_osm: bool = False) -> pd.DataFrame:
    return enrich_network_weights(clusters, force=force, use_osm=use_osm)
