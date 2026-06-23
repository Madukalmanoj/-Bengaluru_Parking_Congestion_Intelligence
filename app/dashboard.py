"""Streamlit dashboard — Bengaluru parking violation hotspot intelligence."""

from __future__ import annotations

import hashlib
import sys
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config
from src.device_analytics import device_infrastructure_summary
from src.ingest import ingest
from src.hotspots import detect_hotspots
from src.scoring import build_enforcement_export, compute_scores
from src.simulator import simulate_patrol_coverage
from src.trends import build_hotspot_trends, get_cluster_trend_chart_data

st.set_page_config(
    page_title="Bengaluru Parking Congestion Intelligence",
    page_icon="🅿️",
    layout="wide",
)

VIEWS = (
    "Hotspot Map",
    "Leaderboard",
    "Trends",
    "Patrol Simulator",
    "Officer View",
    "Camera Network",
    "Enforcement Export",
)

IMPACT_TIERS = (
    ("High impact", "High", "#d73027"),
    ("Medium impact", "Medium", "#fc8d59"),
    ("Lower impact", "Low", "#4575b4"),
)

DASHBOARD_CSS = """
<style>
.block-container { padding-top: 1.2rem; }
.impact-legend {
    display: flex; flex-wrap: wrap; align-items: center; gap: 1.25rem;
    padding: 0.55rem 0; margin: 0;
}
.map-header {
    margin-bottom: 0.5rem;
    padding: 0.75rem 1rem 0.5rem;
    background: linear-gradient(90deg, rgba(215,48,39,0.08), rgba(252,141,89,0.06), rgba(69,117,180,0.08));
    border: 1px solid rgba(255,255,255,0.08); border-radius: 10px;
}
.map-header-title {
    font-size: 1.05rem; font-weight: 700; margin-bottom: 0.45rem;
    letter-spacing: 0.01em; line-height: 1.3;
}
.legend-item { display: inline-flex; align-items: center; gap: 0.45rem; font-size: 0.92rem; font-weight: 600; }
.legend-dot {
    width: 14px; height: 14px; border-radius: 50%; display: inline-block;
    box-shadow: 0 0 0 2px rgba(255,255,255,0.15);
}
.legend-meta { margin-left: auto; font-size: 0.82rem; opacity: 0.75; font-weight: 500; }
.view-nav-label { font-size: 0.95rem; font-weight: 700; margin: 0.5rem 0 0.25rem 0; letter-spacing: 0.02em; }
div[data-testid="stRadio"] > div[role="radiogroup"] {
    display: flex; flex-direction: row; flex-wrap: wrap; gap: 0.5rem;
    background: rgba(255,255,255,0.03); padding: 0.5rem; border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.08);
}
div[data-testid="stRadio"] > div[role="radiogroup"] > label {
    background: rgba(255,255,255,0.04); padding: 0.45rem 1rem !important;
    border-radius: 8px; border: 1px solid transparent; margin: 0 !important;
}
div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {
    border-color: rgba(252,141,89,0.45);
}
div[data-testid="stMetric"] {
    background: rgba(255,255,255,0.03); padding: 0.75rem; border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.06);
}
</style>
"""


@st.cache_data(show_spinner="Loading violation data…")
def load_violations() -> pd.DataFrame:
    return ingest(force=False)


@st.cache_data(show_spinner="Detecting hotspots…")
def load_hotspots(_violations: pd.DataFrame) -> pd.DataFrame:
    return detect_hotspots(_violations, force=False)


@st.cache_data(show_spinner="Computing impact scores…")
def load_scored(_clusters: pd.DataFrame) -> pd.DataFrame:
    if config.SCORED_PARQUET.exists():
        return pd.read_parquet(config.SCORED_PARQUET)
    return compute_scores(_clusters, force=False)


@st.cache_data(show_spinner=False)
def load_hotspot_trends() -> pd.DataFrame:
    if config.HOTSPOT_TRENDS_PARQUET.exists():
        return pd.read_parquet(config.HOTSPOT_TRENDS_PARQUET)
    violations = load_violations()
    assignments = load_cluster_assignments()
    return build_hotspot_trends(violations, assignments, force=False)


@st.cache_data(show_spinner=False)
def load_cluster_assignments() -> pd.DataFrame | None:
    path = config.VIOLATION_CLUSTERS_PARQUET
    if path.exists():
        return pd.read_parquet(path)
    return None


@st.cache_data(show_spinner=False)
def load_filter_options() -> dict:
    df = load_violations()
    return {
        "min_date": df["local_datetime"].min().date(),
        "max_date": df["local_datetime"].max().date(),
        "stations": sorted(df["police_station"].dropna().unique()),
        "vehicle_types": sorted(df["vehicle_type"].dropna().unique()),
        "violation_types": sorted(
            df.explode("violation_types")["violation_types"].dropna().unique()
        ),
    }


def _filters_key(filters: dict) -> str:
    payload = (
        str(filters.get("date_range")),
        tuple(filters.get("police_stations") or ()),
        tuple(filters.get("vehicle_types") or ()),
        tuple(filters.get("violation_types") or ()),
    )
    return hashlib.md5(repr(payload).encode()).hexdigest()


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    out = df
    date_range = filters.get("date_range")
    if date_range and len(date_range) == 2:
        start, end = date_range
        out = out[
            (out["local_datetime"].dt.date >= start)
            & (out["local_datetime"].dt.date <= end)
        ]
    if filters.get("police_stations"):
        out = out[out["police_station"].isin(filters["police_stations"])]
    if filters.get("vehicle_types"):
        out = out[out["vehicle_type"].isin(filters["vehicle_types"])]
    if filters.get("violation_types"):
        wanted = set(filters["violation_types"])
        out = out[
            out["violation_types"].apply(lambda xs: bool(set(xs) & wanted))
        ]
    return out


def _impact_tier(score: float, max_score: float) -> str:
    ratio = score / max(max_score, 1)
    if ratio >= 0.7:
        return "High"
    if ratio >= 0.4:
        return "Medium"
    return "Low"


def _short_location(location: str, limit: int = 72) -> str:
    text = str(location or "Address unavailable").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def render_impact_legend() -> None:
    items = "".join(
        f'<span class="legend-item">'
        f'<span class="legend-dot" style="background:{color};"></span>{label}</span>'
        for label, _, color in IMPACT_TIERS
    )
    st.markdown(
        f'<div class="map-header">'
        f'<div class="map-header-title">Bengaluru Hotspots · Congestion Impact Score</div>'
        f'<div class="impact-legend">{items}'
        f'<span class="legend-meta">Up to {config.MAP_MAX_MARKERS} hotspots · marker size = score</span>'
        f"</div></div>",
        unsafe_allow_html=True,
    )


def render_view_nav() -> str:
    st.markdown('<p class="view-nav-label">Dashboard view</p>', unsafe_allow_html=True)
    icons = {
        "Hotspot Map": "🗺️",
        "Leaderboard": "🏆",
        "Trends": "📈",
        "Patrol Simulator": "🚔",
        "Officer View": "📱",
        "Camera Network": "📷",
        "Enforcement Export": "📋",
    }
    labels = [f"{icons[v]} {v}" for v in VIEWS]
    choice = st.radio(
        "Dashboard view",
        labels,
        horizontal=True,
        label_visibility="collapsed",
        key="dashboard_view",
    )
    for view in VIEWS:
        if view in choice:
            return view
    return VIEWS[0]


def filter_scored_hotspots(
    scored: pd.DataFrame,
    filtered: pd.DataFrame,
    assignments: pd.DataFrame | None,
) -> pd.DataFrame:
    """Keep hotspots that have at least one violation in the filtered set."""
    if assignments is None or filtered.empty:
        if filtered.empty:
            return scored.iloc[0:0]
        stations = filtered["police_station"].unique()
        return scored[scored["dominant_police_station"].isin(stations)]

    active = (
        filtered[["id"]]
        .merge(assignments, on="id", how="inner")
        .loc[lambda d: d["cluster_id"] >= 0, "cluster_id"]
        .unique()
    )
    if len(active) == 0:
        return scored.iloc[0:0]
    return scored[scored["cluster_id"].isin(active)]


@st.cache_data(show_spinner=False)
def build_map_figure(scored_key: str, scored_csv: str) -> go.Figure:
    """Cached Plotly map with tier colors and formatted hover cards."""
    scored = pd.read_csv(StringIO(scored_csv))
    if scored.empty:
        fig = go.Figure()
        fig.update_layout(title="No hotspots match the current filters", height=520)
        return fig

    plot_df = scored.head(config.MAP_MAX_MARKERS).copy()
    max_score = plot_df["congestion_impact_score"].max()
    plot_df["impact_tier"] = plot_df["congestion_impact_score"].apply(
        lambda s: _impact_tier(s, max_score)
    )
    plot_df["marker_size"] = plot_df["congestion_impact_score"].clip(12, 28)
    plot_df["location_short"] = plot_df["sample_location"].apply(_short_location)

    hover_template = (
        "<b>%{customdata[0]}</b><br><br>"
        "📍 %{customdata[1]}<br>"
        "🔥 Impact: <b>%{customdata[2]:.1f}</b> · %{customdata[3]} tier<br>"
        "🚗 Violations: <b>%{customdata[4]}</b><br>"
        "⚠️ Top type: %{customdata[5]}<br>"
        "🏛️ Station: %{customdata[6]}<br>"
        "🕐 Patrol window: %{customdata[7]}<br>"
        "<extra></extra>"
    )

    fig = go.Figure()

    for label, tier, color in IMPACT_TIERS:
        subset = plot_df[plot_df["impact_tier"] == tier]
        if subset.empty:
            continue
        fig.add_trace(
            go.Scattermap(
                lat=subset["centroid_lat"],
                lon=subset["centroid_lon"],
                mode="markers",
                name=label,
                legendgroup=tier,
                showlegend=False,
                marker=dict(
                    size=subset["marker_size"],
                    color=color,
                    opacity=0.82,
                    sizemode="diameter",
                ),
                customdata=np.stack(
                    [
                        subset["dominant_junction"].fillna("No Junction"),
                        subset["location_short"],
                        subset["congestion_impact_score"],
                        subset["impact_tier"],
                        subset["violation_count"],
                        subset["dominant_violation"].fillna("Unknown"),
                        subset["dominant_police_station"],
                        subset["peak_hour_window"],
                    ],
                    axis=-1,
                ),
                hovertemplate=hover_template,
            )
        )

    fig.update_layout(
        height=520,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        map=dict(
            style="open-street-map",
            center=dict(lat=config.MAP_CENTER[0], lon=config.MAP_CENTER[1]),
            zoom=config.MAP_ZOOM,
        ),
        showlegend=False,
    )
    return fig


@st.cache_data(show_spinner=False)
def build_trend_figures(filtered_key: str, filtered_csv: str) -> tuple[go.Figure, go.Figure, go.Figure, go.Figure]:
    filtered = pd.read_csv(StringIO(filtered_csv), parse_dates=["local_datetime"])
    filtered["local_datetime"] = pd.to_datetime(filtered["local_datetime"], utc=True)
    filtered["day_of_week"] = filtered["day_of_week"].astype(int)
    filtered["hour_of_day"] = filtered["hour_of_day"].astype(int)

    daily = (
        filtered.groupby(filtered["local_datetime"].dt.date)
        .size()
        .reset_index(name="count")
    )
    daily.columns = ["date", "count"]
    fig_daily = px.line(
        daily, x="date", y="count", title="Bengaluru Parking Violations Over Time"
    )
    fig_daily.update_layout(height=350, margin={"t": 40})

    monthly = filtered.groupby("month").size().reset_index(name="count")
    fig_monthly = px.bar(
        monthly, x="month", y="count", title="Bengaluru Violations by Month"
    )
    fig_monthly.update_layout(height=350, margin={"t": 40})

    pivot = (
        filtered.groupby(["day_of_week", "hour_of_day"])
        .size()
        .reset_index(name="count")
    )
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    matrix = np.zeros((7, 24))
    for _, r in pivot.iterrows():
        matrix[int(r["day_of_week"]), int(r["hour_of_day"])] = r["count"]
    fig_heatmap = px.imshow(
        matrix,
        x=[f"{h:02d}" for h in range(24)],
        y=day_labels,
        color_continuous_scale="YlOrRd",
        labels={"color": "Violations"},
        aspect="auto",
        title="Bengaluru Violations by Hour × Day of Week (IST)",
    )
    fig_heatmap.update_layout(height=350, margin={"t": 40})

    station_chart = (
        filtered.groupby("police_station")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(15)
    )
    fig_station = px.bar(
        station_chart,
        x="count",
        y="police_station",
        orientation="h",
        title="Top 15 Bengaluru Police Stations by Violations",
    )
    fig_station.update_layout(height=400, margin={"t": 40})

    return fig_daily, fig_monthly, fig_heatmap, fig_station


def render_map(scored_visible: pd.DataFrame, filters: dict) -> None:
    render_impact_legend()
    key = _filters_key(filters)
    scored_csv = scored_visible.to_csv(index=False)
    fig = build_map_figure(f"{key}:{len(scored_visible)}", scored_csv)
    st.plotly_chart(fig, use_container_width=True, key="hotspot_map_chart")


def render_leaderboard(scored_visible: pd.DataFrame, top_n: int) -> None:
    st.subheader("Hotspot Leaderboard")
    display = scored_visible.head(top_n).copy()
    display["rank"] = np.arange(1, len(display) + 1)
    max_score = max(display["congestion_impact_score"].max(), 1)
    display["impact_tier"] = display["congestion_impact_score"].apply(
        lambda s: _impact_tier(s, max_score)
    )
    st.dataframe(
        display[
            [
                "rank",
                "impact_tier",
                "dominant_junction",
                "congestion_impact_score",
                "violation_count",
                "dominant_violation",
                "peak_hour_window",
                "dominant_police_station",
                "sample_location",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "rank": st.column_config.NumberColumn("Rank", width="small"),
            "impact_tier": st.column_config.TextColumn("Tier", width="small"),
            "dominant_junction": st.column_config.TextColumn("Junction", width="medium"),
            "congestion_impact_score": st.column_config.ProgressColumn(
                "Impact Score",
                min_value=0,
                max_value=100,
                format="%.1f",
                width="medium",
            ),
            "violation_count": st.column_config.NumberColumn("Violations", format="%d"),
            "dominant_violation": st.column_config.TextColumn("Top Violation", width="medium"),
            "peak_hour_window": st.column_config.TextColumn("Patrol Window (IST)", width="medium"),
            "dominant_police_station": st.column_config.TextColumn("Police Station", width="medium"),
            "sample_location": st.column_config.TextColumn("Location", width="large"),
        },
    )


def render_trends(filtered: pd.DataFrame, filters: dict, scored_visible: pd.DataFrame) -> None:
    cols = [
        "local_datetime",
        "month",
        "day_of_week",
        "hour_of_day",
        "police_station",
    ]
    filtered_csv = filtered[cols].to_csv(index=False)
    fig_daily, fig_monthly, fig_heatmap, fig_station = build_trend_figures(
        _filters_key(filters), filtered_csv
    )
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(fig_daily, use_container_width=True, key="trend_daily")
    with col_b:
        st.plotly_chart(fig_monthly, use_container_width=True, key="trend_monthly")
    st.plotly_chart(fig_heatmap, use_container_width=True, key="trend_heatmap")
    st.plotly_chart(fig_station, use_container_width=True, key="trend_station")

    st.markdown("---")
    st.subheader("Top Hotspot Month-over-Month Trends")
    st.caption("Identify worsening zones — rising violations month over month.")
    trends = load_hotspot_trends()
    if trends.empty or scored_visible.empty:
        st.info("Run `python run_pipeline.py` to generate hotspot trend data.")
        return

    options = scored_visible.head(20).reset_index(drop=True)
    labels = [
        f"#{i+1} {row.dominant_junction} ({row.congestion_impact_score:.0f})"
        for i, row in options.iterrows()
    ]
    pick = st.selectbox(
        "Select hotspot",
        range(len(options)),
        format_func=lambda i: labels[i],
        key="hotspot_trend_pick",
    )
    cluster_id = int(options.iloc[pick]["cluster_id"])
    chart_data = get_cluster_trend_chart_data(cluster_id, trends)
    direction = options.iloc[pick].get(
        "trend_direction",
        chart_data["trend_direction"].iloc[0] if len(chart_data) else "stable",
    )
    st.metric("Trend direction", str(direction).title())

    fig_hot = px.bar(
        chart_data,
        x="month",
        y="violation_count",
        title=f"Monthly violations — cluster {cluster_id}",
        color_discrete_sequence=["#fc8d59"],
    )
    fig_hot.update_layout(height=320, margin={"t": 40})
    st.plotly_chart(fig_hot, use_container_width=True, key="hotspot_mom")


def render_patrol_simulator(
    violations: pd.DataFrame,
    scored_all: pd.DataFrame,
    assignments: pd.DataFrame | None,
) -> None:
    st.subheader("Patrol Simulator — What-If Coverage")
    st.caption(
        "Estimate what % of high-impact violations you catch by patrolling "
        "top-N zones during selected IST hours."
    )
    if assignments is None:
        st.warning("Cluster assignments missing — run `python run_pipeline.py`.")
        return

    default_hours = getattr(config, "PATROL_DEFAULT_HOURS", [8, 9, 17, 18, 19])
    default_zones = getattr(config, "PATROL_DEFAULT_ZONES", 10)
    default_threshold = getattr(config, "HIGH_IMPACT_SCORE_THRESHOLD", 50.0)

    c1, c2, c3 = st.columns(3)
    with c1:
        patrol_hours = st.multiselect(
            "Patrol hours (IST)",
            list(range(24)),
            default=default_hours,
            format_func=lambda h: f"{h:02d}:00",
            key="sim_hours",
        )
    with c2:
        num_zones = st.slider(
            "Patrol zones visited", 3, 30, default_zones, key="sim_zones"
        )
    with c3:
        threshold = st.slider(
            "High-impact score threshold",
            30, 80, int(default_threshold), key="sim_threshold",
        )

    result = simulate_patrol_coverage(
        violations,
        scored_all,
        assignments,
        patrol_hours=patrol_hours,
        num_zones=num_zones,
        impact_threshold=float(threshold),
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("High-impact violations (total)", f"{result['total_high_impact_violations']:,}")
    m2.metric("Covered in patrol window", f"{result['violations_covered_in_window']:,}")
    m3.metric("Estimated coverage", f"{result['coverage_pct']}%")

    st.dataframe(
        result["zones_detail"],
        use_container_width=True,
        hide_index=True,
        column_config={
            "congestion_impact_score": st.column_config.ProgressColumn(
                "Impact", min_value=0, max_value=100, format="%.1f"
            ),
        },
    )


def render_officer_view(scored_visible: pd.DataFrame, top_n: int) -> None:
    st.subheader("Officer View — Field Patrol List")
    st.caption("Minimal mobile-friendly list: where to go, when, and why.")
    ranked = scored_visible.head(min(top_n, 15)).copy()
    ranked["rank"] = np.arange(1, len(ranked) + 1)
    max_s = ranked["congestion_impact_score"].max()

    for _, row in ranked.iterrows():
        tier = _impact_tier(row["congestion_impact_score"], max_s)
        color = next(c for _, t, c in IMPACT_TIERS if t == tier)
        st.markdown(
            f"""<div style="border-left:4px solid {color};padding:0.75rem 1rem;margin-bottom:0.75rem;
background:rgba(255,255,255,0.03);border-radius:0 8px 8px 0;">
<b>#{int(row['rank'])} · {row['dominant_junction']}</b> · Score <b>{row['congestion_impact_score']:.1f}</b><br>
<small>{_short_location(row.get('sample_location', ''), 90)}</small><br>
🕐 <b>{row['peak_hour_window']}</b> · 🏛️ {row['dominant_police_station']} · 🚗 {int(row['violation_count'])} violations
</div>""",
            unsafe_allow_html=True,
        )
        maps_url = f"https://www.google.com/maps?q={row['centroid_lat']},{row['centroid_lon']}"
        st.markdown(
            f'<a href="{maps_url}" target="_blank" style="display:inline-block;margin-bottom:1rem;'
            f'padding:0.4rem 0.85rem;background:rgba(252,141,89,0.15);border-radius:6px;'
            f'text-decoration:none;font-weight:600;">📍 Open in Maps #{int(row["rank"])}</a>',
            unsafe_allow_html=True,
        )


def render_camera_network(
    violations: pd.DataFrame,
    scored_all: pd.DataFrame,
    assignments: pd.DataFrame | None,
) -> None:
    st.subheader("Camera Capture Infrastructure")
    st.caption(
        "Prioritization layer on Bengaluru Traffic Police's existing device_id capture pipeline."
    )
    summary = device_infrastructure_summary(violations, scored_all, assignments)

    c1, c2, c3 = st.columns(3)
    c1.metric("Traffic cameras (devices)", f"{summary['total_devices']:,}")
    c2.metric("Total captures in dataset", f"{summary['total_captures']:,}")
    c3.metric("Pushed to SCITA (%)", f"{summary['scita_push_rate_pct']}%")

    if summary["high_impact_coverage"]:
        hi = summary["high_impact_coverage"]
        st.info(
            f"**{hi['devices_covering_top_50_hotspots']}** cameras ({hi['pct_of_all_devices']}% of fleet) "
            f"captured **{hi['captures_in_top_hotspots']:,}** violations in top-50 impact hotspots."
        )

    st.markdown("**Top capture devices**")
    st.dataframe(summary["top_devices"], use_container_width=True, hide_index=True)


def render_export(scored_visible: pd.DataFrame, top_n: int) -> None:
    st.subheader("Bengaluru Traffic Police — Enforcement Priority List")
    st.caption(
        "Ranked patrol zones with recommended IST time windows for each hotspot."
    )
    ranked = scored_visible.copy()
    ranked["rank"] = np.arange(1, len(ranked) + 1)
    export_df = build_enforcement_export(ranked, top_n=top_n)
    st.dataframe(export_df, use_container_width=True, hide_index=True)
    csv = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Bengaluru Enforcement Priority List (CSV)",
        csv,
        file_name=config.ENFORCEMENT_EXPORT_FILENAME,
        mime="text/csv",
        key="export_csv",
    )
    st.markdown("---")
    st.markdown("**Scoring methodology (summary)**")
    st.markdown(
        f"""
| Component | Weight |
|---|---|
| Violation density | {config.SCORE_WEIGHTS['violation_density']:.0%} |
| Location criticality | {config.SCORE_WEIGHTS['location_criticality']:.0%} |
| Violation severity | {config.SCORE_WEIGHTS['violation_severity']:.0%} |
| Peak-hour concentration | {config.SCORE_WEIGHTS['peak_hour_weight']:.0%} |
| Recurrence / persistence | {config.SCORE_WEIGHTS['recurrence_persistence']:.0%} |
| Road-network flow weight | {config.SCORE_WEIGHTS['network_flow_weight']:.0%} |

*Network weight uses OSM road class + betweenness when available; heuristic fallback offline.*
*No live traffic-sensor ground truth — proxy model for prioritization.*
        """
    )


def main() -> None:
    st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)
    st.title("🅿️ Bengaluru Parking & Congestion Intelligence")
    st.caption(
        "**Namma Bengaluru** · Flipkart × Bengaluru Traffic Commission — "
        "prioritize enforcement by **Congestion Impact Score**, not complaint volume."
    )

    violations = load_violations()
    clusters = load_hotspots(violations)
    scored_all = load_scored(clusters)
    assignments = load_cluster_assignments()
    options = load_filter_options()

    st.sidebar.markdown("**Flipkart × Bengaluru Traffic Commission**")
    st.sidebar.caption("Filters apply to trends, map, and export.")

    st.sidebar.header("Filters")
    date_range = st.sidebar.date_input(
        "Date range",
        value=(options["min_date"], options["max_date"]),
        min_value=options["min_date"],
        max_value=options["max_date"],
        key="date_range_filter",
    )
    police_stations = st.sidebar.multiselect(
        "Police station", options["stations"], default=[], key="station_filter"
    )
    vehicle_types = st.sidebar.multiselect(
        "Vehicle type", options["vehicle_types"], default=[], key="vehicle_filter"
    )
    violation_types = st.sidebar.multiselect(
        "Violation type", options["violation_types"], default=[], key="violation_filter"
    )
    top_n = st.sidebar.slider(
        "Top-N enforcement zones",
        10,
        100,
        config.ENFORCEMENT_EXPORT_TOP_N,
        key="top_n_slider",
    )

    if isinstance(date_range, tuple) and len(date_range) == 2:
        dr = date_range
    else:
        dr = (date_range, date_range)

    filters = {
        "date_range": dr,
        "police_stations": police_stations,
        "vehicle_types": vehicle_types,
        "violation_types": violation_types,
    }
    filtered = apply_filters(violations, filters)
    scored_visible = filter_scored_hotspots(scored_all, filtered, assignments)
    scored_visible = scored_visible.sort_values(
        "congestion_impact_score", ascending=False
    ).reset_index(drop=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Filtered violations", f"{len(filtered):,}")
    c2.metric("Hotspots (filtered)", f"{len(scored_visible):,}")
    c3.metric("Bengaluru police stations", f"{filtered['police_station'].nunique():,}")
    c4.metric(
        "Traffic cameras",
        f"{filtered['device_id'].nunique():,}",
        help="Existing Bengaluru Traffic Police camera capture infrastructure",
    )

    view = render_view_nav()

    if view == "Hotspot Map":
        render_map(scored_visible, filters)
    elif view == "Leaderboard":
        render_leaderboard(scored_visible, top_n)
    elif view == "Trends":
        render_trends(filtered, filters, scored_visible)
    elif view == "Patrol Simulator":
        render_patrol_simulator(violations, scored_all, assignments)
    elif view == "Officer View":
        render_officer_view(scored_visible, top_n)
    elif view == "Camera Network":
        render_camera_network(violations, scored_all, assignments)
    else:
        render_export(scored_visible, top_n)


if __name__ == "__main__":
    main()
