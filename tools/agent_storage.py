#!/usr/bin/env python3
"""
Сохранение и загрузка файлов агентом: постоянное хранилище и временные файлы.
Пути задаются через AGENT_STORAGE_PATH и AGENT_TEMP_PATH в .env.
"""
from __future__ import annotations

import os
from pathlib import Path


def _resolve_root(env_key: str, default_subdir: str) -> Path | None:
    raw = os.environ.get(env_key, "").strip()
    if not raw:
        return Path(__file__).resolve().parent.parent / "ai_data" / default_subdir
    path = Path(raw).expanduser().resolve()
    return path


def get_storage_root() -> Path:
    root = _resolve_root("AGENT_STORAGE_PATH", "agent_storage")
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_temp_root() -> Path:
    root = _resolve_root("AGENT_TEMP_PATH", "agent_temp")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_relative(path_str: str) -> Path | None:
    """Относительный путь без выхода за пределы (без '..')."""
    p = Path(path_str.strip()).expanduser()
    if not p.as_posix() or p.is_absolute():
        return None
    if ".." in p.parts:
        return None
    return p


def save_file(relative_path: str, content: str | bytes, temp: bool = False) -> str:
    """
    Сохраняет файл в AGENT_STORAGE_PATH или AGENT_TEMP_PATH.
    relative_path — путь внутри выбранной папки (например 'reports/summary.md').
    content — строка или bytes. temp=True — во временную папку.
    """
    rel = _safe_relative(relative_path)
    if rel is None:
        return "Ошибка: недопустимый путь (нужен относительный без '..')."

    root = get_temp_root() if temp else get_storage_root()
    full = root / rel
    try:
        full.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            full.write_text(content, encoding="utf-8")
        else:
            full.write_bytes(content)
        return f"Сохранено: {full}"
    except OSError as e:
        return f"Ошибка записи: {e}"


def load_file(relative_path: str, from_temp: bool = False) -> str:
    """
    Загружает содержимое файла из хранилища или временной папки.
    Возвращает текст или сообщение об ошибке.
    """
    rel = _safe_relative(relative_path)
    if rel is None:
        return "Ошибка: недопустимый путь."

    root = get_temp_root() if from_temp else get_storage_root()
    full = root / rel
    if not full.exists():
        return f"Файл не найден: {relative_path}"
    if not full.is_file():
        return f"Не файл: {relative_path}"
    try:
        return full.read_text(encoding="utf-8")
    except OSError as e:
        return f"Ошибка чтения: {e}"


def list_files(temp: bool = False) -> str:
    """Список файлов в хранилище или во временной папке (рекурсивно)."""
    root = get_temp_root() if temp else get_storage_root()
    if not root.exists():
        return "Папка не существует."
    lines = []
    for f in sorted(root.rglob("*")):
        if f.is_file():
            rel = f.relative_to(root)
            lines.append(rel.as_posix())
    return "\n".join(lines) if lines else "Файлов нет."


def clean_temp() -> str:
    """Удаляет все файлы и пустые подпапки во временной папке."""
    root = get_temp_root()
    if not root.exists():
        return "Временная папка не существует."
    removed = 0
    for f in sorted(root.rglob("*"), reverse=True):
        if f.is_file():
            try:
                f.unlink()
                removed += 1
            except OSError:
                pass
    for d in sorted(root.rglob("*"), reverse=True):
        if d.is_dir() and d != root:
            try:
                d.rmdir()
            except OSError:
                pass
    return f"Удалено файлов во временной папке: {removed}"
