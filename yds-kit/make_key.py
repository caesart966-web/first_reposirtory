#!/usr/bin/env python3
"""Cevap anahtarı üretir ve kit JSON'una işler.

Harfler hiçbir yerde elle yazılmaz: içerik "o1 = doğru cevap, o2 = tuzak"
varsayımıyla yazılır, anahtar burada üretilir ve `order` dizileri buna göre
kurulur. Amaç yalnızca denge değil, **desensizlik**: kit 6'nın ilk hâlinde
43–62 bloğu C-E-B-D-A diye düzenli tekrar ediyordu ve öğrenci anahtarı
soruları okumadan çıkarabilirdi.

    python3 make_key.py --new 10                  # anahtar üret, ekrana yaz
    python3 make_key.py kits/kit-10.json <anahtar>  # kite işle

Kurallar:
  * dört harf 11, biri 10 kez geçer;
  * yan yana iki aynı harf yok;
  * ABAB gibi dönüşümlü desen yok;
  * 43–62 bloğunda aynı harf, beşin katı konumlarda ikiden çok kez yok
    ("her 5. soru C" izlenimi oluşmasın);
  * ardışık iki beşli blok birbirinin aynısı değil;
  * 76–80 anlam bozan cümle sorularıdır: harf Roma rakamına çevrildiği için
    A (= I.) kullanılmaz; ÖSYM'de de giriş cümlesi neredeyse hiç konu dışı olmaz.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter

LETTERS = "ABCDE"
ROMAN = ["I", "II", "III", "IV", "V"]
N_QUESTIONS = 54
PARAGRAPH_SLICE = slice(16, 36)   # 43-62
ODD_START = 49                    # 76-80


def _allowed(key: list[str], i: int, c: str) -> bool:
    if i and key[-1] == c:
        return False
    if i >= 3 and key[i - 2] == c and key[i - 3] == key[i - 1]:
        return False
    lo, hi = PARAGRAPH_SLICE.start, PARAGRAPH_SLICE.stop
    if lo <= i < hi:
        same_column = [key[j] for j in range(lo, i) if (j - lo) % 5 == (i - lo) % 5]
        if same_column.count(c) >= 2:
            return False
    if i >= 9 and key[i - 4:] + [c] == key[i - 9:i - 4]:
        return False
    if i >= ODD_START and c == "A":
        return False
    return True


def generate(seed: int, n: int = N_QUESTIONS) -> str:
    """Kurallara uyan bir anahtar bulur (geri izleme)."""
    rnd = random.Random(seed)
    scarce = rnd.choice(LETTERS)
    left = {c: (n // 5 if c == scarce else n // 5 + 1) for c in LETTERS}
    key: list[str] = []

    def step(i: int) -> bool:
        if i == n:
            return True
        for c in sorted(LETTERS, key=lambda c: (-left[c], rnd.random())):
            if left[c] and _allowed(key, i, c):
                key.append(c)
                left[c] -= 1
                if step(i + 1):
                    return True
                key.pop()
                left[c] += 1
        return False

    if not step(0):
        raise SystemExit("Kurallara uyan anahtar bulunamadı.")
    return "".join(key)


def apply(path: str, key: str, seed: int) -> None:
    """Anahtarı kite işler; dosya biçimi korunur, yalnızca order/answer değişir."""
    raw = open(path).read()
    kit = json.loads(raw)
    rnd = random.Random(seed)
    questions = kit["questions"]
    if len(key) != len(questions):
        raise SystemExit(f"Anahtar {len(key)} harf, kitte {len(questions)} soru var.")

    for q, letter in zip(questions, key):
        no, idx = q["no"], LETTERS.index(letter)
        start = raw.index(f'"no": {no},')
        nxt = raw.find('"no": ', start + 10)
        end = nxt if nxt != -1 else len(raw)
        seg = raw[start:end]

        if q["group"] == "odd_one_out":
            if q["trap"] == ROMAN[idx]:
                raise SystemExit(f"Soru {no}: tuzak cümle cevapla aynı olamaz.")
            seg, n = re.subn(r'"answer": "[IVX]+"', f'"answer": "{ROMAN[idx]}"', seg, count=1)
        else:
            others = [k for k in sorted(q["options"]) if k not in ("o1", "o2")]
            rnd.shuffle(others)
            slots: list[str | None] = [None] * 5
            slots[idx] = "o1"
            slots[rnd.choice([i for i in range(5) if i != idx])] = "o2"
            for i in range(5):
                if slots[i] is None:
                    slots[i] = others.pop()
            line = '"order": [' + ", ".join(f'"{s}"' for s in slots) + "]"
            seg, n = re.subn(r'"order": \[[^\]]*\]', line, seg, count=1)

        if n != 1:
            raise SystemExit(f"Soru {no}: değiştirilecek satır bulunamadı.")
        raw = raw[:start] + seg + raw[end:]

    open(path, "w").write(raw)
    print(f"  anahtar işlendi: {path}")
    print(f"  dağılım: {dict(sorted(Counter(key).items()))}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kit", nargs="?", help="kit JSON dosyası")
    ap.add_argument("key", nargs="?", help="54 harflik anahtar")
    ap.add_argument("--new", type=int, metavar="SEED", help="yeni anahtar üret ve yazdır")
    args = ap.parse_args()

    if args.new is not None:
        print(generate(args.new))
        return
    if not (args.kit and args.key):
        ap.error("kit ve anahtar birlikte verilmeli (ya da --new kullanın)")
    apply(args.kit, args.key, len(args.key))


if __name__ == "__main__":
    sys.exit(main())
