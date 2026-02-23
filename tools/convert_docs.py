#!/usr/bin/env python3
"""
Пакетная конвертация документов из SRC_DOCUMENTS_PATH в MD_DOCUMENTS_PATH.
Конвертирует все PDF из папки-источника в Markdown в папку-назначение с сохранением структуры подпапок.
"""
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

from pdf2md import pdf_to_md


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Конвертация всех PDF из SRC_DOCUMENTS_PATH в MD_DOCUMENTS_PATH",
    )
    parser.add_argument(
        "--src",
        type=Path,
        default=None,
        help="Папка с исходными документами (по умолчанию SRC_DOCUMENTS_PATH из .env)",
    )
    parser.add_argument(
        "--dst",
        type=Path,
        default=None,
        help="Папка для .md файлов (по умолчанию MD_DOCUMENTS_PATH из .env)",
    )
    parser.add_argument(
        "--images",
        action="store_true",
        help="Извлекать изображения в отдельные файлы",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только показать список файлов, не конвертировать",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Пропускать PDF, для которых уже есть .md в папке назначения",
    )
    args = parser.parse_args()

    src_root = args.src or Path(os.environ.get("SRC_DOCUMENTS_PATH", "")).expanduser().resolve()
    dst_root = args.dst or Path(os.environ.get("MD_DOCUMENTS_PATH", "")).expanduser().resolve()

    if not src_root or not src_root.exists():
        parser.error(f"Папка-источник не задана или не существует: {src_root}")
    if not args.dry_run and (not dst_root or not dst_root.as_posix().strip()):
        parser.error("Задайте MD_DOCUMENTS_PATH в .env или укажите --dst")

    pdf_files = list(src_root.rglob("*.pdf"))
    if not pdf_files:
        print(f"PDF не найдены в {src_root}")
        return

    total_pdf = len(pdf_files)
    if args.skip_existing:
        pdf_files = [
            p for p in pdf_files
            if not (dst_root / p.relative_to(src_root).with_suffix(".md")).exists()
        ]
        if not pdf_files:
            print("Все файлы уже сконвертированы.")
            return
        print(f"К конвертации: {len(pdf_files)} из {total_pdf}")

    if args.dry_run:
        for p in pdf_files:
            rel = p.relative_to(src_root)
            print(rel.with_suffix(".md"))
        print(f"\nВсего: {len(pdf_files)} файлов")
        return

    dst_root.mkdir(parents=True, exist_ok=True)
    failed = []

    for pdf_path in tqdm(pdf_files, desc="Конвертация"):
        rel = pdf_path.relative_to(src_root)
        out_path = dst_root / rel.with_suffix(".md")
        if args.skip_existing and out_path.exists():
            continue
        try:
            pdf_to_md(
                pdf_path,
                output_path=out_path,
                write_images=args.images,
            )
        except Exception as e:
            failed.append((pdf_path, e))

    if failed:
        print(f"\nОшибки ({len(failed)}):")
        for path, err in failed:
            print(f"  {path}: {err}")
    else:
        print(f"\nГотово: {len(pdf_files)} файлов → {dst_root}")


if __name__ == "__main__":
    main()
