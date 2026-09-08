#!/usr/bin/env python3
"""PDF'te başlıkların hangi sayfada olduğunu bulur (statik içindekiler için).

    python3 tools/pagemap.py booklet.pdf needles.json
"""
import json
import re
import sys

import pymupdf


def flat(text):
    return re.sub(r"\s+", " ", text)


def main():
    pdf, needles_file = sys.argv[1], sys.argv[2]
    needles = json.loads(open(needles_file, encoding="utf-8").read())
    with pymupdf.open(pdf) as doc:
        pages = [flat(page.get_text()) for page in doc]

    # İçindekiler kendisi de başlıkları listeler; aramaya ondan sonra başlanır.
    start = 0
    for i, text in enumerate(pages):
        if "Table of Contents" in text:
            start = i
    while start < len(pages) and "Table of Contents" in pages[start]:
        start += 1

    # Harf aralığı verilmiş başlıklar PDF'te "C H A P T E R  1" gibi çıkar,
    # bu yüzden boşluksuz karşılaştırma da denenir.
    squeezed = [re.sub(r"\s+", "", text) for text in pages]

    result, missing = {}, []
    for item in needles:
        needle = flat(item["needle"])
        tight = re.sub(r"\s+", "", needle)
        for i in range(start, len(pages)):
            if needle in pages[i] or tight in squeezed[i]:
                result[item["key"]] = i + 1
                break
        else:
            missing.append(item["key"])
    print(json.dumps({"pages": result, "missing": missing, "total": len(pages)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
