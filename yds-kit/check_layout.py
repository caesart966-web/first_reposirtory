#!/usr/bin/env python3
"""Basılmış kitapçığın sayfa düzenini denetler.

check_output.py her şeyin basıldığına bakar; bu betik nasıl basıldığına bakar.
Soru sayfalarında (kapaktan sonra, SORU AÇIKLAMALARI'ndan önce):

  * her sayfanın ve her sütunun ilk satırı bir sorunun, yönergenin, bölüm
    başlığının ya da okuma parçasının başı olmalı; başka bir şeyle başlıyorsa
    önceki sütundaki kutu bölünmüştür;
  * yönerge kutusu ilk sorusuyla, bölüm başlığı yönergesiyle aynı sayfada olmalı.

    python3 check_layout.py kits/ara-kit-02.json

Sorun bir bölümün başında çıkıyorsa (sayfa dibinde açılan iki sütunlu bölümde
yönerge sol sütunda kalıyor, ilk soru sağ sütunda sayfadan taşıyor), o bölümün
ilk soru numarası kit JSON'undaki "break_before" listesine yazılır ve kit
yeniden derlenir. Ana kitler (1-14) öğrenciye verildiği için yeniden dizilmez.

LibreOffice (soffice) ve pymupdf gerektirir; ikisi de yoksa betik atlanır.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_kit as bk  # noqa: E402
from check_output import render_pdf  # noqa: E402

#: Bir sütunun meşru başlangıcı: soru numarası, yönerge ya da büyük harfli başlık.
START = re.compile(r"^(\d+\.|\d+-\d+:|[A-ZÇĞİÖŞÜ ]{6,}$)")


def _spans(page, wide_only: bool):
    """Gövdedeki metin parçaları (bbox, metin). Üst ve alt bilgi atlanır."""
    import pymupdf

    mid = page.rect.width / 2
    wide = [pymupdf.Rect(d["rect"]) for d in page.get_drawings()
            if d["rect"].width > mid * 1.2 and d["rect"].height > 12]
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                text = span["text"].strip()
                box = pymupdf.Rect(span["bbox"])
                if not text or not 35 < box.y0 < page.rect.height - 50:
                    continue
                inside = any(r.contains(pymupdf.Point((box.x0 + box.x1) / 2,
                                                       (box.y0 + box.y1) / 2)) for r in wide)
                # Tam genişlik kutular (parça, diyalog, başlık) sütun denetimine girmez.
                if inside == wide_only:
                    out.append((box, text))
    return out


def _first(spans):
    top = min(box.y0 for box, _ in spans)
    return min((s for s in spans if s[0].y0 <= top + 3), key=lambda s: s[0].x0)[1]


def problems(pdf: Path, kit: dict) -> tuple[int, list[tuple[int, str, str]]]:
    import pymupdf

    starts = [p["text"][:25] for p in kit["passages"]]
    found: list[tuple[int, str, str]] = []
    with pymupdf.open(pdf) as doc:
        pages = doc.page_count
        last = next((i for i, pg in enumerate(doc) if "SORU AÇIKLAMALARI" in pg.get_text()),
                    pages)
        for i in range(1, last):
            page = doc[i]
            mid = page.rect.width / 2
            text = page.get_text()

            body = _spans(page, wide_only=False) + _spans(page, wide_only=True)
            if body:
                head = _first(body)
                if not (START.match(head) or any(s.startswith(head[:20]) for s in starts)):
                    found.append((i + 1, "sayfa başı", head[:50]))

            narrow = _spans(page, wide_only=False)
            for side, inside in (("sol sütun", lambda b: b.x0 < mid - 20),
                                 ("sağ sütun", lambda b: b.x0 >= mid - 5)):
                column = [s for s in narrow if inside(s[0])]
                if column and not START.match(_first(column)):
                    found.append((i + 1, side, _first(column)[:50]))

            for first, last_q in re.findall(r"(\d\d)-(\d\d): ", text):
                if not re.search(rf"(^|\n){first}\.", text):
                    found.append((i + 1, "yönerge", f"{first}-{last_q} ilk sorusundan kopuk"))
            for sec in bk.SECTIONS:
                if sec["tr"] in text and not re.search(rf"\b{sec['first']}-\d\d: ", text):
                    found.append((i + 1, "başlık", f"{sec['tr']} yönergesinden kopuk"))
    # Aynı bölünme hem sayfa başında hem sütun başında görünebilir.
    unique = []
    for item in found:
        if not any(u[0] == item[0] and u[2] == item[2] for u in unique):
            unique.append(item)
    return pages, unique


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Basılan kitapçığın sayfa düzenini denetler.")
    parser.add_argument("kit", type=Path, help="kit JSON dosyası")
    parser.add_argument("--docx", type=Path, help="denetlenecek .docx (varsayılan: dist/)")
    args = parser.parse_args(argv)

    kit = json.loads(args.kit.read_text(encoding="utf-8"))
    docx = args.docx or (Path(__file__).parent / "dist" / bk.kit_label(kit)["file"])
    if not docx.exists():
        print(f"{docx} yok; önce build_kit.py çalıştırın.", file=sys.stderr)
        return 1
    if shutil.which("soffice") is None:
        print("soffice bulunamadı; sayfa denetimi atlandı.", file=sys.stderr)
        return 0
    try:
        import pymupdf  # noqa: F401
    except ImportError:
        print("pymupdf bulunamadı; sayfa denetimi atlandı.", file=sys.stderr)
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        pages, found = problems(render_pdf(docx, Path(tmp)), kit)

    print(f"{docx.name}: {pages} sayfa")
    if not found:
        print("  bölünen kutu, sayfa dibinde kalan başlık ya da yönerge yok.")
        return 0
    for page, where, text in found:
        print(f"  s. {page}, {where}: {text}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
