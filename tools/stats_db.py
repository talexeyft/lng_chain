#!/usr/bin/env python3
"""
Выполнение read-only SQL-запросов к локальной SQLite-базе статистики (ai_data/network_stats.db).
Основная таблица для запросов: hour_stats.
"""
from __future__ import annotations

import secrets
import sqlite3
from pathlib import Path


def _default_db_path() -> Path:
    """Путь к БД; основная таблица — hour_stats."""
    return Path(__file__).resolve().parent.parent / "ai_data" / "network_stats.db"


def _data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "ai_data"


def _is_select_only(sql: str) -> bool:
    """Проверяет, что запрос — только SELECT (игнорируя пробелы и переводы строк)."""
    s = sql.strip()
    if not s:
        return False
    first_line = s.split("\n")[0].split("--")[0].strip()
    return first_line.upper().startswith("SELECT")


def run_stats_query(
    sql: str,
    max_rows: int = 500,
    db_path: Path | None = None,
    save_to_file: bool = False,
) -> str:
    """
    Выполняет read-only SQL (только SELECT) к БД статистики.
    Если save_to_file=False: возвращает результат в виде текстовой таблицы (TSV).
    Если save_to_file=True: сохраняет результат в ai_data/query_<id>.tsv и возвращает
    путь к файлу и краткую сводку (число строк, колонки), не занимая контекст полным дампом.
    """
    if not _is_select_only(sql):
        return "Ошибка: разрешены только SELECT-запросы."

    path = db_path if db_path is not None else _default_db_path()
    if not path.exists():
        return f"База не найдена: {path}"

    try:
        with sqlite3.connect(path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(sql)
            rows = cur.fetchmany(max_rows)
            names = [d[0] for d in cur.description] if cur.description else []
    except sqlite3.Error as e:
        return f"Ошибка SQL: {e}"

    if not names:
        return "Запрос выполнен, результат пуст или не является выборкой."

    lines = ["\t".join(names)]
    for row in rows:
        lines.append("\t".join(str(c) if c is not None else "" for c in row))
    table_text = "\n".join(lines)

    if save_to_file:
        out_dir = _data_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        file_id = secrets.token_hex(4)
        out_path = out_dir / f"query_{file_id}.tsv"
        out_path.write_text(table_text, encoding="utf-8")
        rel_path = f"ai_data/query_{file_id}.tsv"
        cols = ", ".join(names)
        return f"Сохранено: {rel_path}\nСтрок: {len(rows)}, колонки: {cols}"
    return table_text
