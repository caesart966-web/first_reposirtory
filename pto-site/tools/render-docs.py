#!/usr/bin/env python3
"""
Делает картинки из PDF-документов: рекомендательных писем, благодарностей,
сертификатов. Картинка нужна, чтобы документ открывался во всплывающем окне
прямо на сайте, а не скачивался отдельным файлом.

Как пользоваться:

    1. Положите PDF в assets/docs/ с понятным именем латиницей,
       например  blagodarnost-minstroy-tatarstan.pdf
    2. Запустите:

           python3 tools/render-docs.py

    3. Рядом появится blagodarnost-minstroy-tatarstan.webp
    4. Пропишите оба пути в data/site.json, блок recommendations

Скрипт не трогает картинки, которые уже есть. Чтобы перерисовать заново:

    python3 tools/render-docs.py --force

Нужна одна библиотека (ставится один раз):

    pip install pymupdf
"""

import argparse
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "assets" / "docs"
WIDTH = 1400      # ширины 1400px хватает, чтобы читать текст письма на экране
QUALITY = 82


def main() -> int:
    parser = argparse.ArgumentParser(description="PDF -> картинка для всплывающего окна")
    parser.add_argument("--force", action="store_true", help="перерисовать уже существующие")
    args = parser.parse_args()

    try:
        import pymupdf
    except ImportError:
        print("Не установлена библиотека pymupdf. Установите командой:\n"
              "    pip install pymupdf")
        return 1

    if not DOCS.exists():
        print(f"Нет папки {DOCS}")
        return 1

    pdfs = sorted(DOCS.glob("*.pdf"))
    if not pdfs:
        print(f"В {DOCS} нет ни одного PDF.")
        return 0

    made = 0
    for pdf in pdfs:
        out = pdf.with_suffix(".webp")
        if out.exists() and not args.force:
            print(f"  пропуск (уже есть): {out.name}")
            continue

        doc = pymupdf.open(pdf)
        page = doc[0]
        if len(doc) > 1:
            print(f"  ВНИМАНИЕ: в {pdf.name} страниц {len(doc)}, "
                  f"картинка делается только с первой")
        zoom = WIDTH / page.rect.width
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        pix.pil_save(out, format="WEBP", quality=QUALITY, method=6)
        print(f"  готово: {out.name}  {pix.width}x{pix.height}  {out.stat().st_size // 1024} КБ")
        made += 1

    print(f"\nСоздано картинок: {made}. Не забудьте прописать их в data/site.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
