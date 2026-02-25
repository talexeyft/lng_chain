#!/usr/bin/env python3
"""
Загрузка почасовой статистики 3G из xlsx в SQLite (таблица hour_stats).
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd
from tqdm import tqdm

TABLE_NAME = "hour_stats"
DEFAULT_DB_PATH = Path("ai_data/network_stats.db")
DEFAULT_XLSX = Path("srcdata/3 пример часовая статистика 3G.xlsx")

# SQLite не любит NaN — заменяем на NULL при вставке
CHUNK_SIZE = 5000


def create_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hour_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dt TEXT NOT NULL,
            cellname INTEGER NOT NULL,
            cs_traffic REAL,
            ps_traffic REAL,
            cell_availability REAL,
            cssr_amr REAL,
            voice_dcr REAL,
            rrc_cssr REAL,
            rrc_dcr REAL,
            packet_ssr REAL,
            hsdpa_sr REAL,
            rab_ps_dcr_user REAL,
            hsdpa_end_usr_thrp REAL,
            sho_factor REAL,
            sho_sr REAL,
            rtwp REAL,
            cs_att REAL,
            ps_att REAL,
            branch INTEGER,
            active_user REAL,
            code_block REAL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS ix_hour_stats_dt ON hour_stats(dt)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_hour_stats_cellname ON hour_stats(cellname)")


def load_xlsx(xlsx_path: Path) -> pd.DataFrame:
    df = pd.read_excel(xlsx_path, sheet_name="Sheet1")
    # DT может прийти строкой "07.11.2025 10:00:00"
    if df["DT"].dtype == object:
        df["DT"] = pd.to_datetime(df["DT"], format="%d.%m.%Y %H:%M:%S", errors="coerce")
    df = df.dropna(subset=["DT"])
    df["DT"] = df["DT"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df = df.rename(columns=str.lower)
    return df


def insert_chunk(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    cols = [
        "dt", "cellname", "cs_traffic", "ps_traffic", "cell_availability",
        "cssr_amr", "voice_dcr", "rrc_cssr", "rrc_dcr", "packet_ssr",
        "hsdpa_sr", "rab_ps_dcr_user", "hsdpa_end_usr_thrp", "sho_factor",
        "sho_sr", "rtwp", "cs_att", "ps_att", "branch", "active_user", "code_block"
    ]
    placeholders = ", ".join(["?"] * len(cols))
    sql = f"INSERT INTO {TABLE_NAME} ({', '.join(cols)}) VALUES ({placeholders})"
    rows = []
    for _, row in df.iterrows():
        rows.append(tuple(None if pd.isna(row[c]) else row[c] for c in cols))
    conn.executemany(sql, rows)
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Загрузка xlsx почасовой статистики 3G в SQLite hour_stats")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Путь к SQLite БД")
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX, help="Путь к xlsx файлу")
    ap.add_argument("--if-exists", choices=("fail", "replace", "append"), default="replace",
                    help="replace — пересоздать таблицу; append — добавить к существующим")
    args = ap.parse_args()

    if not args.xlsx.exists():
        print(f"Файл не найден: {args.xlsx}")
        raise SystemExit(1)

    args.db.parent.mkdir(parents=True, exist_ok=True)
    df = load_xlsx(args.xlsx)
    print(f"Загружено из xlsx: {len(df)} строк")

    with sqlite3.connect(args.db) as conn:
        if args.if_exists == "replace":
            conn.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
        create_schema(conn)
        if args.if_exists == "replace":
            total = 0
            for start in tqdm(range(0, len(df), CHUNK_SIZE), desc="Вставка"):
                chunk = df.iloc[start : start + CHUNK_SIZE]
                total += insert_chunk(conn, chunk)
            print(f"Записано в {args.db}: таблица {TABLE_NAME}, строк: {total}")
        else:
            total = 0
            for start in tqdm(range(0, len(df), CHUNK_SIZE), desc="Вставка"):
                chunk = df.iloc[start : start + CHUNK_SIZE]
                total += insert_chunk(conn, chunk)
            print(f"Добавлено в {args.db}: таблица {TABLE_NAME}, строк: {total}")


if __name__ == "__main__":
    main()
