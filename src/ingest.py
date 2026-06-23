"""Load, clean, parse, validate, and cache violation records."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config


def parse_list_col(val) -> list:
    """Parse stringified JSON/list columns (violation_type, offence_code)."""
    if pd.isna(val) or val in ("NULL", ""):
        return []
    try:
        return json.loads(val)
    except Exception:
        try:
            return ast.literal_eval(val)
        except Exception:
            return []


DATETIME_COLS = [
    "created_datetime",
    "modified_datetime",
    "closed_datetime",
    "action_taken_timestamp",
    "data_sent_to_scita_timestamp",
    "validation_timestamp",
]


def load_raw_csv() -> pd.DataFrame:
    """Load the raw CSV from the configured path."""
    path = Path(config.CSV_PATH)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    return pd.read_csv(path, low_memory=False)


def clean_violations(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and enrich violation records."""
    out = df.copy()

    # Parse list columns
    out["violation_types"] = out["violation_type"].apply(parse_list_col)
    out["offence_codes"] = out["offence_code"].apply(parse_list_col)

    # Primary violation type (first in list, or Unknown)
    out["primary_violation"] = out["violation_types"].apply(
        lambda xs: xs[0] if xs else "UNKNOWN"
    )

    # Parse datetimes
    for col in DATETIME_COLS:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], utc=True, errors="coerce")

    # Local time features from created_datetime
    local = out["created_datetime"].dt.tz_convert(config.TIMEZONE)
    out["local_datetime"] = local
    out["hour"] = local.dt.hour + local.dt.minute / 60.0
    out["hour_of_day"] = local.dt.hour
    out["day_of_week"] = local.dt.dayofweek  # Mon=0
    out["day_name"] = local.dt.day_name()
    out["date"] = local.dt.date
    out["month"] = local.dt.to_period("M").astype(str)

    # Normalize junction
    out["junction_name"] = out["junction_name"].fillna("No Junction").astype(str)

    # Coordinate validation
    valid_lat = out["latitude"].between(config.LAT_MIN, config.LAT_MAX)
    valid_lon = out["longitude"].between(config.LON_MIN, config.LON_MAX)
    out["coord_valid"] = valid_lat & valid_lon

    before = len(out)
    out = out[out["coord_valid"]].copy()
    dropped_coords = before - len(out)

    # Deduplicate on id
    before_dedup = len(out)
    out = out.drop_duplicates(subset=["id"], keep="first")
    dropped_dupes = before_dedup - len(out)

    out.attrs["dropped_invalid_coords"] = dropped_coords
    out.attrs["dropped_duplicates"] = dropped_dupes
    return out


def ingest(force: bool = False) -> pd.DataFrame:
    """Run ingest pipeline; return cleaned DataFrame (cached as Parquet)."""
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if config.CLEAN_PARQUET.exists() and not force:
        print(f"Loading cached clean data from {config.CLEAN_PARQUET}")
        return pd.read_parquet(config.CLEAN_PARQUET)

    print(f"Reading raw CSV: {config.CSV_PATH}")
    raw = load_raw_csv()
    print(f"  Raw shape: {raw.shape}")
    print(f"  Columns: {list(raw.columns)}")

    cleaned = clean_violations(raw)
    print(f"  Clean shape: {cleaned.shape}")
    print(f"  Dropped invalid coords: {cleaned.attrs.get('dropped_invalid_coords', 0)}")
    print(f"  Dropped duplicate ids: {cleaned.attrs.get('dropped_duplicates', 0)}")

    cleaned.to_parquet(config.CLEAN_PARQUET, index=False)
    print(f"  Wrote {config.CLEAN_PARQUET}")
    return cleaned


def save_eda_summaries(df: pd.DataFrame) -> None:
    """Save EDA summary tables used to justify scoring weights."""
    config.EDA_DIR.mkdir(parents=True, exist_ok=True)

    summaries = {
        "by_violation_type": (
            df.explode("violation_types")
            .groupby("violation_types")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        ),
        "by_vehicle_type": df.groupby("vehicle_type").size().reset_index(name="count"),
        "by_police_station": (
            df.groupby(["police_station", "center_code"])
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        ),
        "by_hour": df.groupby("hour_of_day").size().reset_index(name="count"),
        "by_day_of_week": df.groupby("day_name").size().reset_index(name="count"),
        "by_junction": (
            df.groupby("junction_name")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
            .head(100)
        ),
    }

    for name, table in summaries.items():
        path = config.EDA_DIR / f"{name}.csv"
        table.to_csv(path, index=False)
        print(f"  EDA summary: {path}")


if __name__ == "__main__":
    force = "--force" in sys.argv
    df = ingest(force=force)
    save_eda_summaries(df)
    print("Ingest complete.")
