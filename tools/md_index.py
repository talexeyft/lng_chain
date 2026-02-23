#!/usr/bin/env python3
"""
Индексация Markdown-файлов в JSON-манифест.
По умолчанию читает MD_DOCUMENTS_PATH из .env и сохраняет в ai_data/md_manifest.json.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from tqdm import tqdm


def _extract_headings(lines: list[str], max_headings: int) -> list[str]:
    headings: list[str] = []
    for line in lines:
        if line.startswith("#"):
            headings.append(line.lstrip("#").strip())
            if len(headings) >= max_headings:
                break
    return headings


def build_manifest(
    root: Path,
    *,
    max_headings: int = 20,
) -> dict[str, Any]:
    files = sorted(root.rglob("*.md"))
    items: list[dict[str, Any]] = []

    for path in tqdm(files, desc="Индексация .md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        headings = _extract_headings(lines, max_headings=max_headings)
        title = headings[0] if headings else ""
        rel_path = str(path.relative_to(root))

        items.append(
            {
                "path": rel_path,
                "absolute_path": str(path),
                "size_bytes": path.stat().st_size,
                "line_count": len(lines),
                "title": title,
                "headings": headings,
            }
        )

    return {
        "root": str(root),
        "file_count": len(items),
        "files": items,
    }


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Индексация Markdown-файлов в JSON-манифест")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Папка с .md файлами (по умолчанию MD_DOCUMENTS_PATH из .env)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("ai_data/md_manifest.json"),
        help="Путь к JSON-манифесту",
    )
    parser.add_argument(
        "--max-headings",
        type=int,
        default=20,
        help="Максимум заголовков на файл",
    )
    args = parser.parse_args()

    root = args.root or Path(os.environ.get("MD_DOCUMENTS_PATH", "")).expanduser()
    root = root.resolve()
    if not root.exists():
        parser.error(f"Папка с Markdown не найдена: {root}")

    manifest = build_manifest(root, max_headings=args.max_headings)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Готово: {args.output} ({manifest['file_count']} файлов)")


if __name__ == "__main__":
    main()
