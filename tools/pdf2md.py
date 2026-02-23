#!/usr/bin/env python3
"""
Утилита конвертации PDF в Markdown.
Использует pymupdf4llm для извлечения текста с сохранением структуры (заголовки, списки, таблицы).
"""
import argparse
from pathlib import Path

import pymupdf4llm


def pdf_to_md(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    write_images: bool = False,
    pages: list[int] | None = None,
) -> str:
    """
    Конвертирует PDF в Markdown.

    :param input_path: путь к PDF-файлу
    :param output_path: путь для .md файла (если None — подставляется то же имя с расширением .md)
    :param write_images: сохранять ли изображения в отдельные файлы
    :param pages: номера страниц (1-based), None — все страницы
    :return: текст в формате Markdown
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Файл не найден: {input_path}")

    # pymupdf4llm принимает 0-based индексы
    pages_0based = [p - 1 for p in pages] if pages else None

    md_text = pymupdf4llm.to_markdown(
        str(input_path),
        write_images=write_images,
        pages=pages_0based,
    )

    out = Path(output_path) if output_path else input_path.with_suffix(".md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md_text, encoding="utf-8")
    return md_text


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Конвертация PDF в Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Путь к PDF-файлу",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Путь к выходному .md файлу (по умолчанию — рядом с PDF, то же имя с расширением .md)",
    )
    parser.add_argument(
        "--images",
        action="store_true",
        help="Извлекать изображения в отдельные файлы",
    )
    parser.add_argument(
        "--pages",
        type=str,
        default=None,
        help="Страницы через запятую, например: 1,3,5-7 (по умолчанию — все)",
    )
    args = parser.parse_args()

    pages = None
    if args.pages:
        pages = []
        for part in args.pages.replace(" ", "").split(","):
            if "-" in part:
                a, b = part.split("-", 1)
                pages.extend(range(int(a), int(b) + 1))
            else:
                pages.append(int(part))

    pdf_to_md(
        args.input,
        output_path=args.output,
        write_images=args.images,
        pages=pages,
    )
    out = args.output or args.input.with_suffix(".md")
    print(f"Готово: {out}")


if __name__ == "__main__":
    main()
