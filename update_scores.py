"""Fast refresh: enrichment + scoring + trends (skips DBSCAN)."""

import pandas as pd

import config
from src.enrichment import enrich_network_weights
from src.ingest import ingest
from src.scoring import compute_scores
from src.trends import build_hotspot_trends


def main(use_osm: bool = False) -> None:
    clusters = pd.read_parquet(config.CLUSTERS_PARQUET)
    violations = ingest()
    assignments = pd.read_parquet(config.VIOLATION_CLUSTERS_PARQUET)

    clusters = enrich_network_weights(clusters, force=True, use_osm=use_osm)
    scored = compute_scores(clusters, force=True)
    trends = build_hotspot_trends(violations, assignments, force=True)

    scored = scored.merge(
        trends[["cluster_id", "trend_direction", "trend_slope"]].drop_duplicates("cluster_id"),
        on="cluster_id",
        how="left",
    )
    scored.to_parquet(config.SCORED_PARQUET, index=False)
    print("Updated:", config.SCORED_PARQUET)
    if "network_source" in scored.columns:
        print("Network:", scored["network_source"].value_counts().to_dict())
    print("Trends:", trends["trend_direction"].value_counts().to_dict())
    print("Top score:", scored["congestion_impact_score"].max())


if __name__ == "__main__":
    import sys
    main(use_osm="--osm" in sys.argv)
