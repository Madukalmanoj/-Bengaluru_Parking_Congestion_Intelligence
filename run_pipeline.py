"""Run full data pipeline: ingest -> hotspots -> enrichment -> scoring -> trends."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.ingest import ingest, save_eda_summaries
from src.hotspots import detect_hotspots
from src.enrichment import enrich_network_weights
from src.scoring import compute_scores
from src.trends import build_hotspot_trends
import config


def main(force: bool = False, osm: bool = False) -> None:
    print("=== Phase 1: Ingest & Clean ===")
    violations = ingest(force=force)

    print("\n=== Phase 2: EDA Summaries ===")
    save_eda_summaries(violations)

    print("\n=== Phase 3: Hotspot Detection ===")
    clusters = detect_hotspots(violations, force=force)

    print("\n=== Phase 4: Road-Network / Traffic-Flow Weighting ===")
    clusters = enrich_network_weights(clusters, force=force or osm, use_osm=osm)

    print("\n=== Phase 5: Congestion Impact Scoring ===")
    scored = compute_scores(clusters, force=force or osm)

    print("\n=== Phase 6: Hotspot Monthly Trends ===")
    assignments = None
    if config.VIOLATION_CLUSTERS_PARQUET.exists():
        import pandas as pd
        assignments = pd.read_parquet(config.VIOLATION_CLUSTERS_PARQUET)
    trends = build_hotspot_trends(violations, assignments, force=force)

    if not trends.empty:
        scored = scored.merge(
            trends[["cluster_id", "trend_direction", "trend_slope"]].drop_duplicates("cluster_id"),
            on="cluster_id",
            how="left",
        )
        scored.to_parquet(config.SCORED_PARQUET, index=False)

    source = scored["network_source"].value_counts().to_dict() if "network_source" in scored.columns else {}
    print("\n=== Pipeline complete ===")
    print(f"  Violations: {len(violations):,}")
    print(f"  Hotspots:   {len(clusters):,}")
    print(f"  Top score:  {scored['congestion_impact_score'].max():.1f}")
    print(f"  Network weights: {source or 'heuristic only'}")


if __name__ == "__main__":
    force = "--force" in sys.argv
    osm = "--osm" in sys.argv
    main(force=force, osm=osm)
