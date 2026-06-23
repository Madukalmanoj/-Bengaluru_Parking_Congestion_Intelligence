"""Central configuration — paths, bounds, and tunable model weights."""

from pathlib import Path

# ── Project / city context ───────────────────────────────────────────────────
CITY_NAME = "Bengaluru"
HACKATHON_TITLE = "Flipkart × Bengaluru Traffic Commission Hackathon"
TRAFFIC_AUTHORITY = "Bengaluru Traffic Police"

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
CSV_PATH = r"C:\Users\Manoj.M\Downloads\jan to may police violation_anonymized791b166 (1).csv"
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EDA_DIR = PROCESSED_DIR / "eda_summaries"

CLEAN_PARQUET = PROCESSED_DIR / "violations_clean.parquet"
CLUSTERS_PARQUET = PROCESSED_DIR / "hotspots_clusters.parquet"
SCORED_PARQUET = PROCESSED_DIR / "hotspots_scored.parquet"
VIOLATION_CLUSTERS_PARQUET = PROCESSED_DIR / "violation_clusters.parquet"
NETWORK_WEIGHTS_PARQUET = PROCESSED_DIR / "network_weights.parquet"
HOTSPOT_TRENDS_PARQUET = PROCESSED_DIR / "hotspot_monthly_trends.parquet"
OSM_GRAPH_PATH = PROCESSED_DIR / "bengaluru_drive_graph.graphml"
OSM_EDGE_BC_PATH = PROCESSED_DIR / "bengaluru_edge_betweenness.parquet"

# ── Geographic bounds (Bengaluru) ──────────────────────────────────────────
LAT_MIN, LAT_MAX = 12.7, 13.2
LON_MIN, LON_MAX = 77.4, 77.8
TIMEZONE = "Asia/Kolkata"

# ── DBSCAN hotspot detection ───────────────────────────────────────────────
DBSCAN_EPS_METERS = 75
DBSCAN_EPS_RADIANS = DBSCAN_EPS_METERS / 6_371_000
DBSCAN_MIN_SAMPLES = 5

# ── Peak-hour windows (Bengaluru IST rush hour) ─────────────────────────────
PEAK_HOUR_WINDOWS = [(8, 10), (17.5, 20.5)]

# ── Congestion Impact Score weights (must sum to 1.0) ────────────────────────
SCORE_WEIGHTS = {
    "violation_density": 0.35,
    "location_criticality": 0.20,
    "violation_severity": 0.15,
    "peak_hour_weight": 0.10,
    "recurrence_persistence": 0.10,
    "network_flow_weight": 0.10,
}

LOCATION_CRITICALITY = {
    "junction_named": 1.0,
    "keyword_match": 0.65,
    "default": 0.25,
}

LOCATION_KEYWORDS = [
    "main road", "ring road", "outer ring road", "orr", "cross", "junction",
    "flyover", "highway", "metro", "silk board", "hosur road", "sarjapur",
    "whitefield", "koramangala", "mg road", "hebbal", "electronic city",
    "marathahalli", "btm", "indiranagar", "bellandur", "madiwala",
]

VIOLATION_SEVERITY = {
    "PARKING NEAR ROAD CROSSING": 1.0,
    "PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS": 0.98,
    "PARKING IN A MAIN ROAD": 0.95,
    "DOUBLE PARKING": 0.90,
    "PARKING OPPOSITE TO ANOTHER PARKED VEHICLE": 0.85,
    "PARKING ON FOOTPATH": 0.80,
    "PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC": 0.75,
    "NO PARKING": 0.60,
    "WRONG PARKING": 0.55,
    "PARKING OTHER THAN BUS STOP": 0.50,
}
DEFAULT_VIOLATION_SEVERITY = 0.50

# ── OSM / road-network weighting ─────────────────────────────────────────────
OSM_ENABLED = True
OSM_AUTO_TRY = False  # use cached OSM graph if present; pass --osm to download
OSM_PLACE_NAME = "Bengaluru, Karnataka, India"
OSM_BETWEENNESS_SAMPLE_K = 800

ROAD_CLASS_WEIGHTS = {
    "motorway": 1.0,
    "motorway_link": 0.95,
    "trunk": 0.95,
    "trunk_link": 0.90,
    "primary": 0.85,
    "primary_link": 0.80,
    "secondary": 0.70,
    "secondary_link": 0.65,
    "tertiary": 0.55,
    "tertiary_link": 0.50,
    "unclassified": 0.40,
    "residential": 0.35,
    "living_street": 0.30,
    "service": 0.25,
}
DEFAULT_ROAD_CLASS_WEIGHT = 0.40
NETWORK_ROAD_CLASS_BLEND = 0.60
NETWORK_BETWEENNESS_BLEND = 0.40

# ── Patrol simulator defaults ────────────────────────────────────────────────
PATROL_DEFAULT_HOURS = [8, 9, 17, 18, 19]
PATROL_DEFAULT_ZONES = 10
HIGH_IMPACT_SCORE_THRESHOLD = 50.0

# ── Dashboard defaults ───────────────────────────────────────────────────────
ENFORCEMENT_EXPORT_TOP_N = 50
ENFORCEMENT_EXPORT_FILENAME = "bengaluru_enforcement_priority_list.csv"
MAP_MAX_MARKERS = 150
MAP_CENTER = (12.9716, 77.5946)
MAP_ZOOM = 11
