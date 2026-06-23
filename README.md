# Bengaluru Parking Violation & Congestion Intelligence

**Flipkart × Bengaluru Traffic Commission Hackathon**

AI-driven enforcement prioritization for **Namma Bengaluru** — detects illegal-parking hotspots, quantifies **congestion impact** (not just violation count), and outputs targeted patrol plans for Bengaluru Traffic Police.

## Problem Coverage

| Challenge | Implementation |
|---|---|
| Detect illegal-parking hotspots | DBSCAN spatial clustering on 298k BTP records |
| Quantify traffic-flow impact | **Congestion Impact Score** + road-network weight (OSM or heuristic) |
| Prioritize enforcement zones | Ranked map, leaderboard, CSV export |
| Reactive patrol → targeted patrol | Patrol simulator + IST time windows |
| No violation vs impact heatmap | Impact-weighted map (not raw density) |
| Existing camera infrastructure | Camera Network dashboard (`device_id`, SCITA push rate) |

## Quick Start

```bash
pip install -r requirements.txt
python run_pipeline.py              # ~2–5 min first run (cached after)
python run_pipeline.py --osm        # optional: download OSM road graph (needs internet once)
streamlit run app/dashboard.py
```

## Architecture

```
config.py               ← paths, weights, OSM settings
src/ingest.py           ← clean + cache violations
src/hotspots.py         ← DBSCAN clustering
src/enrichment.py       ← OSM road class + betweenness (offline cache) OR heuristic fallback
src/scoring.py          ← Congestion Impact Score (6 components)
src/trends.py           ← monthly hotspot trends (worsening / improving)
src/simulator.py        ← what-if patrol coverage
src/device_analytics.py ← camera capture infrastructure stats
app/dashboard.py        ← 7 views (map, leaderboard, trends, simulator, officer, cameras, export)
run_pipeline.py         ← one-shot pipeline
```

## Congestion Impact Score

```
Score (0–100) =
    35% × violation density
  + 20% × location criticality (junction / ORR / corridor keywords)
  + 15% × violation severity
  + 10% × peak-hour concentration (Bengaluru IST rush hours)
  + 10% × recurrence / persistence
  + 10% × road-network flow weight (OSM arterial + betweenness, or heuristic offline)
```

**Network weight:** Snaps each hotspot to the nearest OpenStreetMap road edge. Arterials/trunk roads score higher than residential streets; edge betweenness adds structural importance. Cached locally after first `--osm` run.

> Still a **proxy model** — no live speed/queue sensors in the dataset. Honest for judges; tunable in `config.py`.

## Dashboard Views

1. **Hotspot Map** — tier-colored markers (red/orange/blue)
2. **Leaderboard** — ranked zones with progress bars
3. **Trends** — city patterns + per-hotspot month-over-month charts
4. **Patrol Simulator** — % high-impact violations covered for N zones × selected hours
5. **Officer View** — mobile-friendly patrol list with Google Maps links
6. **Camera Network** — device capture stats + coverage of top-50 hotspots
7. **Enforcement Export** — downloadable CSV for patrol teams

## Dataset

~298k anonymized Bengaluru parking violations. Path set once in `config.py` → `CSV_PATH`.

## Demo Script (2 min)

1. **Problem:** "Patrol-based enforcement can't prioritize by congestion impact."
2. **Detect:** Show pipeline → 970 hotspots from DBSCAN.
3. **Quantify:** Map colored by score, not count; explain 6-factor score + OSM weight.
4. **Simulate:** Patrol Simulator — "10 zones × 5 rush-hour slots → X% coverage."
5. **Deploy:** Officer View + Camera Network — sits on existing BTP capture pipeline.
6. **Export:** Download enforcement priority list with patrol windows.

## License

Hackathon demo — validate against live traffic data before production use.
