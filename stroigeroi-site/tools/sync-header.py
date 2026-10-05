#!/usr/bin/env python3
"""
Переносит шапку из index.html во все страницы макета.

Шапка физически повторяется в каждом html-файле (в теме OpenCart это один
header.twig). Правится она в index.html, а этот скрипт копирует блок
<header class="site-header" …>…</header> в остальные страницы — иначе
какая-нибудь из пятнадцати отстанет на пункт меню.

    python3 tools/sync-header.py           переписать страницы
    python3 tools/sync-header.py --check   только проверить (код 1 — разошлись)
"""

import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent.parent
PAGES = ['index', 'catalog', 'product', 'cart', 'calculator', 'delivery', 'contacts',
         'checkout', 'order-done', 'favourites', 'compare', 'login', 'policy', 'terms', '404']
START, END = '<header class="site-header"', '</header>'


def block(html):
    a = html.index(START)
    b = html.index(END, a) + len(END)
    return a, b


def main():
    check = '--check' in sys.argv
    src = (DIR / 'index.html').read_text(encoding='utf-8')
    a, b = block(src)
    header = src[a:b]
    stale = []
    for name in PAGES[1:]:
        f = DIR / f'{name}.html'
        html = f.read_text(encoding='utf-8')
        x, y = block(html)
        if html[x:y] == header:
            continue
        stale.append(name)
        if not check:
            f.write_text(html[:x] + header + html[y:], encoding='utf-8')
    if check and stale:
        print('Шапка разошлась с index.html:', ', '.join(stale))
        sys.exit(1)
    print('Шапка одинаковая на всех страницах' if not stale else f'Переписано страниц: {len(stale)}')


if __name__ == '__main__':
    main()
