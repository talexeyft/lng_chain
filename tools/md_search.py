#!/usr/bin/env python3
"""
Поиск по Markdown-документам:
- полнотекстовый;
- семантический (локальные эмбеддинги через Ollama).
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from tqdm import tqdm


def _create_ollama_embeddings(model_name: str):
    try:
        from langchain_ollama import OllamaEmbeddings
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Для семантического поиска установите зависимость: pip install langchain-ollama"
        ) from exc
    return OllamaEmbeddings(model=model_name)


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def list_md_files(root: Path, manifest_path: Path | None = None) -> list[Path]:
    if manifest_path and manifest_path.exists():
        manifest = load_manifest(manifest_path)
        return [Path(item["absolute_path"]) for item in manifest.get("files", [])]
    return sorted(root.rglob("*.md"))


def search_fulltext(
    query: str,
    *,
    root: Path,
    manifest_path: Path | None = None,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    query_norm = query.casefold()
    results: list[dict[str, Any]] = []
    files = list_md_files(root, manifest_path)

    for path in files:
        if len(results) >= max_results:
            break
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue

        for line_no, line in enumerate(lines, start=1):
            if query_norm in line.casefold():
                results.append(
                    {
                        "path": str(path),
                        "line": line_no,
                        "snippet": line.strip(),
                    }
                )
                if len(results) >= max_results:
                    break

    return results


def _split_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    clean = text.strip()
    if not clean:
        return []
    if len(clean) <= chunk_size:
        return [clean]

    chunks: list[str] = []
    step = max(1, chunk_size - overlap)
    start = 0
    while start < len(clean):
        end = start + chunk_size
        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(clean):
            break
        start += step
    return chunks


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    den_a = math.sqrt(sum(x * x for x in a))
    den_b = math.sqrt(sum(y * y for y in b))
    if den_a == 0.0 or den_b == 0.0:
        return 0.0
    return num / (den_a * den_b)


def build_semantic_index(
    *,
    root: Path,
    manifest_path: Path | None,
    output_path: Path,
    model_name: str,
    chunk_size: int,
    overlap: int,
    batch_size: int,
) -> int:
    files = list_md_files(root, manifest_path)
    embedding_model = _create_ollama_embeddings(model_name)

    rows: list[dict[str, Any]] = []
    chunk_payloads: list[tuple[Path, int, str]] = []

    for path in tqdm(files, desc="Подготовка чанков"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        chunks = _split_chunks(text, chunk_size=chunk_size, overlap=overlap)
        for idx, chunk in enumerate(chunks):
            chunk_payloads.append((path, idx, chunk))

    if not chunk_payloads:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("", encoding="utf-8")
        return 0

    for batch_start in tqdm(range(0, len(chunk_payloads), batch_size), desc="Эмбеддинги"):
        batch = chunk_payloads[batch_start : batch_start + batch_size]
        batch_texts = [item[2] for item in batch]
        vectors = embedding_model.embed_documents(batch_texts)
        for (path, idx, chunk), vector in zip(batch, vectors):
            rows.append(
                {
                    "path": str(path),
                    "chunk_id": idx,
                    "text": chunk,
                    "embedding": vector,
                }
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return len(rows)


def search_semantic(
    query: str,
    *,
    semantic_index_path: Path,
    model_name: str,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    if not semantic_index_path.exists():
        return []

    embedding_model = _create_ollama_embeddings(model_name)
    query_vec = embedding_model.embed_query(query)

    scored: list[dict[str, Any]] = []
    with semantic_index_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            score = _cosine_similarity(query_vec, row["embedding"])
            scored.append(
                {
                    "score": score,
                    "path": row["path"],
                    "chunk_id": row["chunk_id"],
                    "snippet": row["text"][:280].replace("\n", " "),
                }
            )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:max_results]


def _resolve_root(root_arg: Path | None) -> Path:
    load_dotenv()
    root = root_arg or Path(os.environ.get("MD_DOCUMENTS_PATH", "")).expanduser()
    return root.resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Полнотекстовый и семантический поиск по .md")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fulltext_parser = subparsers.add_parser("fulltext", help="Полнотекстовый поиск")
    fulltext_parser.add_argument("query", type=str, help="Поисковая строка")
    fulltext_parser.add_argument("--root", type=Path, default=None, help="Папка с .md")
    fulltext_parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("ai_data/md_manifest.json"),
        help="Путь к манифесту",
    )
    fulltext_parser.add_argument("--max-results", type=int, default=20, help="Лимит результатов")

    index_parser = subparsers.add_parser("semantic-index", help="Построить семантический индекс")
    index_parser.add_argument("--root", type=Path, default=None, help="Папка с .md")
    index_parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("ai_data/md_manifest.json"),
        help="Путь к манифесту",
    )
    index_parser.add_argument(
        "--output",
        type=Path,
        default=Path("ai_data/md_semantic_index.jsonl"),
        help="Файл семантического индекса",
    )
    index_parser.add_argument(
        "--model",
        type=str,
        default="qwen3-embedding:4b",
        help="Модель эмбеддингов в Ollama",
    )
    index_parser.add_argument("--chunk-size", type=int, default=1200, help="Размер чанка")
    index_parser.add_argument("--overlap", type=int, default=200, help="Перекрытие чанков")
    index_parser.add_argument("--batch-size", type=int, default=16, help="Размер батча")

    semantic_parser = subparsers.add_parser("semantic-search", help="Семантический поиск")
    semantic_parser.add_argument("query", type=str, help="Поисковая строка")
    semantic_parser.add_argument(
        "--index",
        type=Path,
        default=Path("ai_data/md_semantic_index.jsonl"),
        help="Файл семантического индекса",
    )
    semantic_parser.add_argument(
        "--model",
        type=str,
        default="qwen3-embedding:4b",
        help="Модель эмбеддингов в Ollama",
    )
    semantic_parser.add_argument("--max-results", type=int, default=10, help="Лимит результатов")

    args = parser.parse_args()

    if args.command == "fulltext":
        root = _resolve_root(args.root)
        if not root.exists():
            parser.error(f"Папка с Markdown не найдена: {root}")
        manifest_path = args.manifest if args.manifest.exists() else None
        results = search_fulltext(
            args.query,
            root=root,
            manifest_path=manifest_path,
            max_results=args.max_results,
        )
        if not results:
            print("Ничего не найдено.")
            return
        for item in results:
            print(f"{item['path']}:{item['line']}: {item['snippet']}")
        return

    if args.command == "semantic-index":
        root = _resolve_root(args.root)
        if not root.exists():
            parser.error(f"Папка с Markdown не найдена: {root}")
        manifest_path = args.manifest if args.manifest.exists() else None
        chunk_count = build_semantic_index(
            root=root,
            manifest_path=manifest_path,
            output_path=args.output,
            model_name=args.model,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
            batch_size=args.batch_size,
        )
        print(f"Готово: {args.output} ({chunk_count} чанков)")
        return

    results = search_semantic(
        args.query,
        semantic_index_path=args.index,
        model_name=args.model,
        max_results=args.max_results,
    )
    if not results:
        print("Ничего не найдено.")
        return
    for item in results:
        print(f"{item['score']:.4f} | {item['path']}#{item['chunk_id']} | {item['snippet']}")


if __name__ == "__main__":
    main()
