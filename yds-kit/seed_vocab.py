#!/usr/bin/env python3
"""Bir denemenin kelime röntgeninden, kite girmiş sözcükleri çıkarır.

Öğrenci çözdüğü denemenin kelime röntgenini PDF olarak veriyor; bu betik o
listeyi okur ve hazırlanan kitte **gerçekten geçen** maddeleri seçer. Böylece
kitin `vocabulary` alanı uydurulmuş değil, öğrencinin karşılaştığı sınavdan
türetilmiş olur.

    python3 seed_vocab.py kelime-rontgeni.pdf kits/kit-04.json
    python3 seed_vocab.py kelime-rontgeni.pdf kits/kit-04.json --list

PDF, üç sütunlu bir tablo olarak varsayılır: hedef kelime | Türkçe karşılığı |
eş anlamlılar. Sütunlar sayfadaki x konumuna göre ayrılır, çünkü düz metin
çıkarımı satırları birbirine karıştırıyor.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

#: Üç sütunun kabaca başladığı x konumları (A4, 72 dpi kullanıcı birimi).
COLUMN_BOUNDS = (150, 330)
HEADER_HEIGHT = 110
HEADERS = {"Hedef Kelime", "Türkçe Karşılığı", "Eş ve Yakın Anlamları"}


def parse_vocabulary(pdf_path: Path) -> list[dict]:
    try:
        import pymupdf
    except ImportError:
        sys.exit("pymupdf gerekli: pip install pymupdf")

    def column(x: float) -> int:
        return 0 if x < COLUMN_BOUNDS[0] else (1 if x < COLUMN_BOUNDS[1] else 2)

    rows: list[list[str]] = []
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            buckets: dict[int, dict[int, list]] = {}
            for x0, y0, _x1, _y1, word, *_ in page.get_text("words"):
                if y0 < HEADER_HEIGHT:
                    continue
                line = buckets.setdefault(round(y0 / 4), {0: [], 1: [], 2: []})
                line[column(x0)].append((x0, word))
            for key in sorted(buckets):
                rows.append([" ".join(w for _, w in sorted(buckets[key][c])) for c in range(3)])

    entries, seen = [], set()
    for en, tr, _syn in rows:
        en, tr = en.strip(), tr.strip()
        if not en or not tr or en in HEADERS or tr in HEADERS:
            continue
        if not re.match(r"^[A-Za-z][A-Za-z '\-/()]*$", en) or len(en) > 40:
            continue
        # Okuma parçası satırları sütunlara taşar: baş sözcük kısa olmalı
        if len(en.split()) > 3 or len(tr.split()) > 6:
            continue
        if re.search(r"\b(the|and|that|which|with|from|were|was|are)\b", tr, re.I):
            continue
        if en.lower() in seen:
            continue
        seen.add(en.lower())
        entries.append({"en": en, "tr": tr})
    return entries


def kit_text(kit_path: Path) -> str:
    """Kitin basılan tüm metni, biçimlemeden arındırılmış."""
    kit = json.loads(kit_path.read_text(encoding="utf-8"))
    parts = [p.get("text", "") for p in kit.get("passages", [])]
    for q in kit.get("questions", []):
        parts.append(q.get("stem", ""))
        parts.extend(q.get("sentences", []) or [])
        parts.extend(f"{who} {line}" for who, line in (q.get("dialogue") or []))
        parts.extend((q.get("options") or {}).values())
    return re.sub(r"\s+", " ", " ".join(parts)).lower()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Denemenin kelime röntgeninden kite girenleri seçer.")
    parser.add_argument("pdf", type=Path, help="kelime röntgeni PDF'i")
    parser.add_argument("kit", type=Path, help="kit JSON dosyası")
    parser.add_argument("--list", action="store_true", help="JSON yerine okunaklı liste bas")
    args = parser.parse_args(argv)

    vocabulary = parse_vocabulary(args.pdf)
    text = kit_text(args.kit)

    hits = []
    for entry in vocabulary:
        head = entry["en"].lower()
        if len(head) < 4:
            continue
        # çekimli hâlleri de yakalamak için sondaki e düşürülür
        stem = re.escape(head[:-1] if head.endswith("e") else head)
        if re.search(r"\b" + stem, text):
            hits.append([entry["en"], entry["tr"]])

    print(f"{len(vocabulary)} maddelik listeden {len(hits)} tanesi {args.kit.name} içinde geçiyor.",
          file=sys.stderr)
    if args.list:
        for en, tr in hits:
            print(f"{en:<24} {tr}")
    else:
        print(json.dumps(hits, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
