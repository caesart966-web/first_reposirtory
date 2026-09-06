#!/usr/bin/env python3
"""Basılmış kitapçığı içerikle karşılaştırır.

Doğrulayıcı (build_kit.py) JSON'un kurallara uygunluğuna bakar; bu betik ise
üretilmiş .docx dosyasının gerçekten her şeyi bastığını denetler. Gerekçesi
somut: bir soru kutusu sütun sonuna denk geldiğinde LibreOffice onu sonraki
sütuna taşımak yerine kırpabiliyordu ve 72. sorunun B-E seçenekleri kitapçıkta
hiç görünmüyordu. Bu, JSON tarafında hiçbir kural ihlali üretmez.

    python3 check_output.py kits/kit-01.json

LibreOffice (soffice) ve pymupdf gerektirir; ikisi de yoksa betik atlanır.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_kit as bk  # noqa: E402

#: Kısa parçalar yanlış eşleşme üretir; bu uzunlukta bir başlangıç yeterlidir.
PROBE = 45

#: Sayfa altı ve üstü, bir cümlenin ortasına girip eşleşmeyi bozar; çıkarılır.
NOISE = (
    r"Go on to the next page\.\s*\d+\s*Kit \d+ / \d+",
    r"TEST BİTTİ\.\s*\d+\s*Kit \d+ / \d+",
    r"YDS DENEME — KIT \d+\s*ENGLISH",
)

#: PDF'te satır sonu tirenin ardından gelebilir ("eight-hundred- thousand-year").
HYPHENS = {"\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-"}


def flatten(text: str) -> str:
    for source, target in HYPHENS.items():
        text = text.replace(source, target)
    return re.sub(r"\s+", " ", text).strip()


def printed_text(pdf_text: str) -> str:
    """Kolon ve sayfa kırılmalarından arındırılmış, aranabilir metin."""
    text = flatten(pdf_text)
    for pattern in NOISE:
        text = re.sub(pattern, " ", text)
    text = re.sub(r"-\s+", "-", text)  # tireden bölünmüş sözcükleri birleştir
    return re.sub(r"\s+", " ", text)


def expected_fragments(kit: dict) -> list[tuple[str, str]]:
    """(nerede, basılması beklenen metin) çiftleri."""
    items: list[tuple[str, str]] = []
    for p in kit["passages"]:
        items.append((f"parça {p['first']}-{p['last']}", p["text"]))
    for q in kit["questions"]:
        where = f"soru {q['no']}"
        if q.get("stem"):
            items.append((where, q["stem"]))
        for sentence in q.get("sentences", []) or []:
            items.append((where, sentence))
        for _who, line in q.get("dialogue") or []:
            if line != "----":
                items.append((where, line))
        for text in (q.get("options") or {}).values():
            items.append((where, text))
        items.append((f"{where} açıklaması", q["why"]))
        items.append((f"{where} tuzağı", q["trap_note"]))
    for en, tr in kit["vocabulary"]:
        items.append(("kelime röntgeni", en))
        items.append(("kelime röntgeni", tr))
    return items


def render_pdf(docx: Path, out_dir: Path) -> Path:
    subprocess.run(
        ["soffice", "--headless", "--norestore", "--convert-to", "pdf",
         "--outdir", str(out_dir), str(docx)],
        check=True, capture_output=True, timeout=600,
    )
    return out_dir / (docx.stem + ".pdf")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Basılan kitapçığı içerikle karşılaştırır.")
    parser.add_argument("kit", type=Path, help="kit JSON dosyası")
    parser.add_argument("--docx", type=Path, help="denetlenecek .docx (varsayılan: dist/)")
    args = parser.parse_args(argv)

    kit = json.loads(args.kit.read_text(encoding="utf-8"))
    docx = args.docx or (Path(__file__).parent / "dist" /
                         f"YDS-DENEME-Kit-{kit['kit']:02d}.docx")
    if not docx.exists():
        print(f"{docx} yok; önce build_kit.py çalıştırın.", file=sys.stderr)
        return 1

    if shutil.which("soffice") is None:
        print("soffice bulunamadı; sayfa denetimi atlandı.", file=sys.stderr)
        return 0
    try:
        import pymupdf
    except ImportError:
        print("pymupdf bulunamadı; sayfa denetimi atlandı.", file=sys.stderr)
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        pdf = render_pdf(docx, Path(tmp))
        with pymupdf.open(pdf) as doc:
            pages = doc.page_count
            printed = printed_text("\n".join(page.get_text() for page in doc))

    missing = []
    for where, text in expected_fragments(kit):
        probe = re.sub(r"-\s+", "-", flatten(text))[:PROBE]
        if probe not in printed:
            missing.append((where, probe))

    answers_missing = [q["no"] for q in kit["questions"]
                       if f"{q['no']}-{bk.answer_letter(q)}" not in printed]

    print(f"{docx.name}: {pages} sayfa")
    if missing:
        print(f"  {len(missing)} parça basılmamış:", file=sys.stderr)
        for where, text in missing[:20]:
            print(f"  - {where}: {text}...", file=sys.stderr)
        return 1
    if answers_missing:
        print(f"  cevap anahtarında eksik: {answers_missing}", file=sys.stderr)
        return 1
    print("  tüm sorular, seçenekler, açıklamalar, kelimeler ve cevaplar basılmış.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
