#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm


TABLE_NAME = "network_stats"
DEFAULT_DB_PATH = Path("ai_data/network_stats.db")
DEFAULT_DAYS = 365
DEFAULT_SITES = 100
DEFAULT_GROUPS = 5
DEFAULT_SEED = 42


@dataclass(frozen=True)
class MetricSpec:
    name: str
    min_value: float
    max_value: float
    base_low: float
    base_high: float
    trend_year: float
    week_amp: float
    year_amp: float
    load_weight: float
    quality_weight: float
    group_weight: float
    noise_share: float
    is_integer: bool
    use_group: bool


METRIC_SPECS: dict[str, MetricSpec] = {
    "calls": MetricSpec(
        name="calls",
        min_value=0,
        max_value=50000,
        base_low=9000,
        base_high=22000,
        trend_year=0.05,
        week_amp=0.20,
        year_amp=0.08,
        load_weight=0.55,
        quality_weight=0.06,
        group_weight=0.22,
        noise_share=0.07,
        is_integer=True,
        use_group=True,
    ),
    "traffic_cs": MetricSpec(
        name="traffic_cs",
        min_value=0,
        max_value=1000,
        base_low=180,
        base_high=430,
        trend_year=-0.02,
        week_amp=0.12,
        year_amp=0.10,
        load_weight=0.40,
        quality_weight=0.03,
        group_weight=0.18,
        noise_share=0.08,
        is_integer=False,
        use_group=True,
    ),
    "traffic_ps": MetricSpec(
        name="traffic_ps",
        min_value=0,
        max_value=5000,
        base_low=800,
        base_high=2000,
        trend_year=0.10,
        week_amp=0.16,
        year_amp=0.12,
        load_weight=0.52,
        quality_weight=0.05,
        group_weight=0.25,
        noise_share=0.09,
        is_integer=False,
        use_group=True,
    ),
    "pct_edrx": MetricSpec(
        name="pct_edrx",
        min_value=0,
        max_value=100,
        base_low=20,
        base_high=55,
        trend_year=0.03,
        week_amp=0.02,
        year_amp=0.18,
        load_weight=-0.12,
        quality_weight=0.30,
        group_weight=0.00,
        noise_share=0.06,
        is_integer=False,
        use_group=False,
    ),
    "drop_rate": MetricSpec(
        name="drop_rate",
        min_value=0,
        max_value=15,
        base_low=0.8,
        base_high=3.0,
        trend_year=0.005,
        week_amp=0.10,
        year_amp=0.00,
        load_weight=0.40,
        quality_weight=-0.40,
        group_weight=0.22,
        noise_share=0.18,
        is_integer=False,
        use_group=True,
    ),
    "latency_ms": MetricSpec(
        name="latency_ms",
        min_value=5,
        max_value=150,
        base_low=20,
        base_high=55,
        trend_year=0.0,
        week_amp=0.10,
        year_amp=0.08,
        load_weight=0.35,
        quality_weight=-0.30,
        group_weight=0.18,
        noise_share=0.10,
        is_integer=False,
        use_group=True,
    ),
    "conn_attempts": MetricSpec(
        name="conn_attempts",
        min_value=0,
        max_value=10000,
        base_low=2600,
        base_high=5200,
        trend_year=0.05,
        week_amp=0.18,
        year_amp=0.05,
        load_weight=0.45,
        quality_weight=0.02,
        group_weight=0.20,
        noise_share=0.08,
        is_integer=True,
        use_group=True,
    ),
    "handover_cnt": MetricSpec(
        name="handover_cnt",
        min_value=0,
        max_value=5000,
        base_low=450,
        base_high=1300,
        trend_year=0.03,
        week_amp=0.14,
        year_amp=0.02,
        load_weight=0.30,
        quality_weight=0.00,
        group_weight=0.00,
        noise_share=0.10,
        is_integer=True,
        use_group=False,
    ),
    "paging_succ": MetricSpec(
        name="paging_succ",
        min_value=80,
        max_value=100,
        base_low=93,
        base_high=99,
        trend_year=0.0,
        week_amp=0.02,
        year_amp=0.00,
        load_weight=-0.10,
        quality_weight=0.25,
        group_weight=0.10,
        noise_share=0.01,
        is_integer=False,
        use_group=True,
    ),
    "rrc_conn": MetricSpec(
        name="rrc_conn",
        min_value=0,
        max_value=20000,
        base_low=4500,
        base_high=9800,
        trend_year=0.08,
        week_amp=0.19,
        year_amp=0.10,
        load_weight=0.48,
        quality_weight=0.03,
        group_weight=0.21,
        noise_share=0.08,
        is_integer=True,
        use_group=True,
    ),
    "dl_mbps": MetricSpec(
        name="dl_mbps",
        min_value=0,
        max_value=50,
        base_low=10,
        base_high=24,
        trend_year=0.12,
        week_amp=0.11,
        year_amp=0.12,
        load_weight=0.24,
        quality_weight=0.08,
        group_weight=0.20,
        noise_share=0.08,
        is_integer=False,
        use_group=True,
    ),
    "ul_mbps": MetricSpec(
        name="ul_mbps",
        min_value=0,
        max_value=20,
        base_low=4,
        base_high=10,
        trend_year=0.10,
        week_amp=0.10,
        year_amp=0.10,
        load_weight=0.20,
        quality_weight=0.05,
        group_weight=0.18,
        noise_share=0.08,
        is_integer=False,
        use_group=True,
    ),
    "prb_util": MetricSpec(
        name="prb_util",
        min_value=0,
        max_value=100,
        base_low=30,
        base_high=60,
        trend_year=0.05,
        week_amp=0.18,
        year_amp=0.14,
        load_weight=0.50,
        quality_weight=-0.04,
        group_weight=0.28,
        noise_share=0.06,
        is_integer=False,
        use_group=True,
    ),
    "cell_load": MetricSpec(
        name="cell_load",
        min_value=0,
        max_value=100,
        base_low=35,
        base_high=65,
        trend_year=0.04,
        week_amp=0.16,
        year_amp=0.12,
        load_weight=0.46,
        quality_weight=-0.03,
        group_weight=0.24,
        noise_share=0.06,
        is_integer=False,
        use_group=True,
    ),
    "paging_vol": MetricSpec(
        name="paging_vol",
        min_value=0,
        max_value=100000,
        base_low=14000,
        base_high=36000,
        trend_year=0.06,
        week_amp=0.20,
        year_amp=0.06,
        load_weight=0.52,
        quality_weight=0.02,
        group_weight=0.22,
        noise_share=0.08,
        is_integer=True,
        use_group=True,
    ),
}


CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    dt DATE NOT NULL,
    ne TEXT NOT NULL,
    calls INTEGER NOT NULL,
    traffic_cs REAL NOT NULL,
    traffic_ps REAL NOT NULL,
    pct_edrx REAL NOT NULL,
    drop_rate REAL NOT NULL,
    latency_ms REAL NOT NULL,
    conn_attempts INTEGER NOT NULL,
    handover_cnt INTEGER NOT NULL,
    paging_succ REAL NOT NULL,
    rrc_conn INTEGER NOT NULL,
    dl_mbps REAL NOT NULL,
    ul_mbps REAL NOT NULL,
    prb_util REAL NOT NULL,
    cell_load REAL NOT NULL,
    paging_vol INTEGER NOT NULL,
    PRIMARY KEY (dt, ne)
);
"""


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate fake network statistics and write to SQLite."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to SQLite DB file (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--table",
        default=TABLE_NAME,
        help=f"Target table name (default: {TABLE_NAME})",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create-schema", help="Create DB schema only.")
    create_parser.set_defaults(command="create-schema")

    gen_parser = subparsers.add_parser("generate", help="Generate and insert fake data.")
    gen_parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    gen_parser.add_argument("--sites", type=int, default=DEFAULT_SITES)
    gen_parser.add_argument("--groups", type=int, default=DEFAULT_GROUPS)
    gen_parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    gen_parser.add_argument(
        "--if-exists",
        choices=["replace", "append"],
        default="replace",
        help="How to write table if it exists.",
    )
    gen_parser.add_argument(
        "--start-date",
        default=None,
        help="Start date YYYY-MM-DD. Default: today - (days-1).",
    )
    gen_parser.set_defaults(command="generate")

    return parser


def make_ne_codes(n_sites: int) -> list[str]:
    return [f"bs-{idx:02d}" for idx in range(1, n_sites + 1)]


def assign_groups(ne_codes: list[str], groups_count: int) -> dict[str, int]:
    if groups_count < 1:
        raise ValueError("groups_count must be >= 1")
    if groups_count > len(ne_codes):
        raise ValueError("groups_count cannot be greater than number of sites")
    group_size = int(np.ceil(len(ne_codes) / groups_count))
    mapping: dict[str, int] = {}
    for idx, ne in enumerate(ne_codes):
        mapping[ne] = min(idx // group_size, groups_count - 1)
    return mapping


def generate_base_frame(
    days: int,
    sites: int,
    groups: int,
    start_date: str | None,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if days < 1:
        raise ValueError("days must be >= 1")
    if sites < 1:
        raise ValueError("sites must be >= 1")
    if groups < 1:
        raise ValueError("groups must be >= 1")
    if groups > sites:
        raise ValueError("groups cannot be greater than sites")

    if start_date is None:
        end = pd.Timestamp.today().normalize()
        start = end - pd.Timedelta(days=days - 1)
    else:
        start = pd.Timestamp(start_date).normalize()

    dates = pd.date_range(start=start, periods=days, freq="D")
    ne_codes = make_ne_codes(sites)
    group_map = assign_groups(ne_codes, groups)

    df = pd.DataFrame(
        {
            "dt": np.repeat(dates.values, sites),
            "ne": np.tile(np.array(ne_codes), days),
        }
    )
    df["group_id"] = df["ne"].map(group_map).astype(int)

    day_idx = np.repeat(np.arange(days), sites)
    group_ids = df["group_id"].to_numpy()
    ne_idx_map = {ne: idx for idx, ne in enumerate(ne_codes)}
    site_idx = df["ne"].map(ne_idx_map).to_numpy()

    dt_series = pd.to_datetime(df["dt"])
    dow = dt_series.dt.dayofweek.to_numpy()
    doy = dt_series.dt.dayofyear.to_numpy()

    weekly_wave = np.where(dow < 5, 0.14, -0.10) + 0.06 * np.sin(2 * np.pi * day_idx / 7)
    yearly_wave = 0.12 * np.sin(2 * np.pi * doy / 365.0)
    trend_norm = day_idx / max(days - 1, 1)

    df["weekly_wave"] = weekly_wave
    df["yearly_wave"] = yearly_wave
    df["trend_norm"] = trend_norm

    return df, site_idx, group_ids, day_idx, trend_norm


def generate_latent_factors(
    *,
    days: int,
    sites: int,
    groups: int,
    site_idx: np.ndarray,
    group_ids: np.ndarray,
    day_idx: np.ndarray,
    trend_norm: np.ndarray,
    rng: np.random.Generator,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    site_phase = rng.uniform(-np.pi, np.pi, size=sites)
    site_load_level = rng.normal(0.0, 0.12, size=sites)
    site_quality_level = rng.normal(0.0, 0.11, size=sites)
    site_load_trend = rng.normal(0.0, 0.03, size=sites)
    site_quality_trend = rng.normal(0.0, 0.02, size=sites)

    group_week_phase = rng.uniform(-np.pi, np.pi, size=groups)
    group_year_phase = rng.uniform(-np.pi, np.pi, size=groups)
    group_load_amp = rng.uniform(0.10, 0.25, size=groups)
    group_quality_amp = rng.uniform(0.08, 0.20, size=groups)
    group_load_trend = rng.uniform(-0.03, 0.08, size=groups)
    group_quality_trend = rng.uniform(-0.04, 0.04, size=groups)

    site_personal_load = (
        site_load_level[site_idx]
        + site_load_trend[site_idx] * trend_norm
        + 0.10 * np.sin(2 * np.pi * day_idx / 14 + site_phase[site_idx])
    )
    site_personal_quality = (
        site_quality_level[site_idx]
        + site_quality_trend[site_idx] * trend_norm
        + 0.08 * np.cos(2 * np.pi * day_idx / 21 + site_phase[site_idx])
    )

    group_load = (
        group_load_amp[group_ids]
        * (
            np.sin(2 * np.pi * day_idx / 7 + group_week_phase[group_ids])
            + 0.75 * np.sin(2 * np.pi * day_idx / 30 + group_week_phase[group_ids] / 2)
            + 0.85 * np.sin(2 * np.pi * day_idx / 365 + group_year_phase[group_ids])
        )
        + group_load_trend[group_ids] * trend_norm
    )

    group_quality = (
        group_quality_amp[group_ids]
        * (
            np.cos(2 * np.pi * day_idx / 7 + group_week_phase[group_ids] / 2)
            + 0.7 * np.cos(2 * np.pi * day_idx / 365 + group_year_phase[group_ids])
        )
        + group_quality_trend[group_ids] * trend_norm
    )

    total_load = site_personal_load + group_load
    quality_factor = site_personal_quality + group_quality - 0.25 * total_load
    return site_personal_load, group_load, quality_factor


def _clip_metric(values: np.ndarray, spec: MetricSpec) -> np.ndarray:
    clipped = np.clip(values, spec.min_value, spec.max_value)
    if spec.is_integer:
        return np.rint(clipped).astype(int)
    return clipped


def generate_metric(
    *,
    spec: MetricSpec,
    rng: np.random.Generator,
    sites: int,
    site_idx: np.ndarray,
    group_ids: np.ndarray,
    trend_norm: np.ndarray,
    weekly_wave: np.ndarray,
    yearly_wave: np.ndarray,
    personal_load: np.ndarray,
    group_load: np.ndarray,
    quality_factor: np.ndarray,
) -> np.ndarray:
    base_per_site = rng.uniform(spec.base_low, spec.base_high, size=sites)
    base_signal = base_per_site[site_idx]
    group_component = spec.group_weight * group_load if spec.use_group else 0.0
    load_component = spec.load_weight * (
        personal_load + (group_load if spec.use_group else 0.0)
    )

    signal = (
        base_signal
        * (
            1
            + spec.trend_year * trend_norm
            + spec.week_amp * weekly_wave
            + spec.year_amp * yearly_wave
            + load_component
            + spec.quality_weight * quality_factor
            + group_component
        )
    )

    noise = rng.normal(0.0, spec.noise_share * np.maximum(base_signal, 1.0), size=len(signal))
    return _clip_metric(signal + noise, spec)


def add_cross_metric_relations(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    calls_norm = df["calls"] / max(float(df["calls"].max()), 1.0)
    ps_norm = df["traffic_ps"] / max(float(df["traffic_ps"].max()), 1.0)
    drop_norm = df["drop_rate"] / max(float(df["drop_rate"].max()), 1.0)

    df["traffic_ps"] = np.clip(
        df["traffic_ps"] * (0.88 + 0.25 * calls_norm), 0, METRIC_SPECS["traffic_ps"].max_value
    )
    df["traffic_cs"] = np.clip(
        df["traffic_cs"] * (0.90 + 0.20 * calls_norm), 0, METRIC_SPECS["traffic_cs"].max_value
    )
    df["conn_attempts"] = np.rint(
        np.clip(df["conn_attempts"] * (0.72 + 0.46 * calls_norm), 0, METRIC_SPECS["conn_attempts"].max_value)
    ).astype(int)
    df["rrc_conn"] = np.rint(
        np.clip(df["rrc_conn"] * (0.70 + 0.45 * calls_norm), 0, METRIC_SPECS["rrc_conn"].max_value)
    ).astype(int)

    df["prb_util"] = np.clip(
        0.55 * df["prb_util"] + 35 * calls_norm + 18 * ps_norm + rng.normal(0, 1.5, len(df)),
        0,
        METRIC_SPECS["prb_util"].max_value,
    )
    df["cell_load"] = np.clip(
        0.52 * df["cell_load"] + 0.62 * df["prb_util"] + 10 * calls_norm + rng.normal(0, 2.0, len(df)),
        0,
        METRIC_SPECS["cell_load"].max_value,
    )

    df["drop_rate"] = np.clip(
        0.65 * df["drop_rate"] + 0.07 * df["cell_load"] + 0.03 * df["prb_util"] + rng.normal(0, 0.25, len(df)),
        METRIC_SPECS["drop_rate"].min_value,
        METRIC_SPECS["drop_rate"].max_value,
    )
    df["latency_ms"] = np.clip(
        0.70 * df["latency_ms"] + 0.35 * df["drop_rate"] * 5 + 0.10 * df["cell_load"] + rng.normal(0, 1.2, len(df)),
        METRIC_SPECS["latency_ms"].min_value,
        METRIC_SPECS["latency_ms"].max_value,
    )
    df["paging_succ"] = np.clip(
        99.4 - 0.70 * df["drop_rate"] - 0.02 * df["latency_ms"] + rng.normal(0, 0.18, len(df)),
        METRIC_SPECS["paging_succ"].min_value,
        METRIC_SPECS["paging_succ"].max_value,
    )

    df["dl_mbps"] = np.clip(
        0.35 * df["dl_mbps"] + 0.015 * df["traffic_ps"] + 0.00035 * df["calls"] - 0.10 * drop_norm * 10,
        0,
        METRIC_SPECS["dl_mbps"].max_value,
    )
    df["ul_mbps"] = np.clip(
        0.40 * df["ul_mbps"] + 0.009 * df["traffic_ps"] + 0.00018 * df["calls"] - 0.07 * drop_norm * 10,
        0,
        METRIC_SPECS["ul_mbps"].max_value,
    )
    df["paging_vol"] = np.rint(
        np.clip(
            0.63 * df["paging_vol"] + 5.5 * df["conn_attempts"] + 0.20 * df["calls"] + rng.normal(0, 1200, len(df)),
            0,
            METRIC_SPECS["paging_vol"].max_value,
        )
    ).astype(int)
    return df


def inject_incidents(df: pd.DataFrame, rng: np.random.Generator, days: int, groups: int) -> pd.DataFrame:
    unique_dates = pd.to_datetime(df["dt"]).drop_duplicates().to_numpy()
    unique_ne = df["ne"].drop_duplicates().to_numpy()

    single_events = max(10, days // 20)
    for _ in tqdm(range(single_events), desc="Single-site incidents", leave=False):
        dt_pick = rng.choice(unique_dates)
        ne_pick = rng.choice(unique_ne)
        mask = (df["dt"] == dt_pick) & (df["ne"] == ne_pick)
        if not mask.any():
            continue
        df.loc[mask, "drop_rate"] *= rng.uniform(1.8, 2.8)
        df.loc[mask, "latency_ms"] *= rng.uniform(1.5, 2.3)
        df.loc[mask, "paging_succ"] *= rng.uniform(0.90, 0.97)
        df.loc[mask, "prb_util"] *= rng.uniform(1.10, 1.35)
        df.loc[mask, "cell_load"] *= rng.uniform(1.08, 1.32)
        df.loc[mask, "traffic_ps"] *= rng.uniform(0.65, 0.90)
        df.loc[mask, "calls"] = np.rint(df.loc[mask, "calls"] * rng.uniform(0.70, 0.95)).astype(int)

    group_events = max(6, days // 45)
    for _ in tqdm(range(group_events), desc="Group incidents", leave=False):
        dt_pick = rng.choice(unique_dates)
        group_pick = int(rng.integers(0, groups))
        mask = (df["dt"] == dt_pick) & (df["group_id"] == group_pick)
        if not mask.any():
            continue
        df.loc[mask, "drop_rate"] *= rng.uniform(1.4, 2.0)
        df.loc[mask, "latency_ms"] *= rng.uniform(1.25, 1.70)
        df.loc[mask, "paging_succ"] *= rng.uniform(0.93, 0.99)
        df.loc[mask, "prb_util"] *= rng.uniform(1.12, 1.30)
        df.loc[mask, "cell_load"] *= rng.uniform(1.08, 1.24)
        df.loc[mask, "conn_attempts"] = np.rint(
            df.loc[mask, "conn_attempts"] * rng.uniform(0.85, 1.05)
        ).astype(int)

    for metric_name, spec in METRIC_SPECS.items():
        df[metric_name] = _clip_metric(df[metric_name].to_numpy(), spec)

    return df


def generate_fake_stats(
    *,
    days: int,
    sites: int,
    groups: int,
    seed: int,
    start_date: str | None,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df, site_idx, group_ids, day_idx, trend_norm = generate_base_frame(
        days=days,
        sites=sites,
        groups=groups,
        start_date=start_date,
    )

    personal_load, group_load, quality_factor = generate_latent_factors(
        days=days,
        sites=sites,
        groups=groups,
        site_idx=site_idx,
        group_ids=group_ids,
        day_idx=day_idx,
        trend_norm=trend_norm,
        rng=rng,
    )

    weekly_wave = df["weekly_wave"].to_numpy()
    yearly_wave = df["yearly_wave"].to_numpy()

    for spec in tqdm(METRIC_SPECS.values(), desc="Generating metrics"):
        df[spec.name] = generate_metric(
            spec=spec,
            rng=rng,
            sites=sites,
            site_idx=site_idx,
            group_ids=group_ids,
            trend_norm=trend_norm,
            weekly_wave=weekly_wave,
            yearly_wave=yearly_wave,
            personal_load=personal_load,
            group_load=group_load,
            quality_factor=quality_factor,
        )

    df = add_cross_metric_relations(df, rng)
    df = inject_incidents(df, rng=rng, days=days, groups=groups)

    int_columns = [spec.name for spec in METRIC_SPECS.values() if spec.is_integer]
    for col in int_columns:
        df[col] = df[col].astype(int)

    ordered_cols = [
        "dt",
        "ne",
        "calls",
        "traffic_cs",
        "traffic_ps",
        "pct_edrx",
        "drop_rate",
        "latency_ms",
        "conn_attempts",
        "handover_cnt",
        "paging_succ",
        "rrc_conn",
        "dl_mbps",
        "ul_mbps",
        "prb_util",
        "cell_load",
        "paging_vol",
    ]
    return df[ordered_cols + ["group_id"]]


def create_schema(conn: sqlite3.Connection, table_name: str = TABLE_NAME) -> None:
    sql = CREATE_TABLE_SQL.replace(TABLE_NAME, table_name)
    conn.execute(sql)
    conn.commit()


def write_to_sqlite(
    df: pd.DataFrame,
    *,
    db_path: Path,
    table_name: str,
    if_exists: str,
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        create_schema(conn=conn, table_name=table_name)
        save_df = df.drop(columns=["group_id"], errors="ignore").copy()
        save_df["dt"] = pd.to_datetime(save_df["dt"]).dt.strftime("%Y-%m-%d")
        save_df.to_sql(
            table_name,
            conn,
            if_exists=if_exists,
            index=False,
            method="multi",
            chunksize=3000,
        )


def run_create_schema(args: argparse.Namespace) -> None:
    args.db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.db) as conn:
        create_schema(conn=conn, table_name=args.table)
    print(f"Schema created: db={args.db} table={args.table}")


def run_generate(args: argparse.Namespace) -> None:
    df = generate_fake_stats(
        days=args.days,
        sites=args.sites,
        groups=args.groups,
        seed=args.seed,
        start_date=args.start_date,
    )
    write_to_sqlite(
        df,
        db_path=args.db,
        table_name=args.table,
        if_exists=args.if_exists,
    )
    print(
        "Generated rows: "
        f"{len(df)} (days={args.days}, sites={args.sites}, groups={args.groups}) "
        f"-> {args.db}:{args.table}"
    )


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    if args.command == "create-schema":
        run_create_schema(args)
    elif args.command == "generate":
        run_generate(args)
    else:
        raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
