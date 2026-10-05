#!/usr/bin/env python3
"""QR-код для отзыва на Яндекс Картах — из картинки, которую выдал Яндекс Бизнес.

Запуск (из norma-site):
    pip install pillow zxing-cpp
    python3 scripts/prepare-review-qr.py

Исходник — assets-src/otzyv-qr.png, как его прислал заказчик 05.10.2026
(тот же код, что Яндекс Бизнес даёт для визиток и табличек). Результат —
src/config/review-qr.json: строки модулей ('#' — тёмный, '.' — светлый)
и текст, который код несёт. Рисует его ReviewQr.astro векторной картинкой
прямо в разметке страницы.

Почему не сама картинка. PNG 2000×2000 без белого поля вокруг: на странице
он весил бы в двадцать раз больше разметки, а без поля камера телефона
читает код хуже. Модули снимаются с центров клеток, поле в четыре модуля
добавляет компонент, как требует стандарт QR.

Почему код распознаётся здесь, а не просто перерисовывается. Скрипт читает
QR тем же способом, что телефон, и сверяет текст с SITE.reviewLink
в site.ts: ссылка в коде и ссылка рядом с кодом обязаны совпадать.
Сборка сайта проверяет то же самое (ReviewQr.astro падает, если ссылки
разошлись), так что поменять ссылку в site.ts и забыть про код нельзя.
"""
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageOps

try:
    import zxingcpp
except ImportError:
    sys.exit('Нужен распознаватель QR: pip install zxing-cpp')

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'assets-src' / 'otzyv-qr.png'
OUT = ROOT / 'src' / 'config' / 'review-qr.json'
SITE_TS = ROOT / 'src' / 'config' / 'site.ts'


def gray(path):
    im = Image.open(path).convert('RGBA')
    bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    return bg.convert('L')


def modules(img):
    """Сетка модулей: размер модуля — по ширине левого верхнего поискового
    узора (у QR он всегда семь модулей), значение — по центру клетки."""
    w, h = img.size
    if w != h:
        sys.exit(f'Картинка не квадратная: {w}×{h} — обрежьте поле так, чтобы код стоял от края до края')
    first_light = next((x for x in range(w) if img.getpixel((x, 0)) > 128), None)
    if not first_light:
        sys.exit('Не найден поисковый узор в левом верхнем углу — нужен код без белого поля по краям')
    m = first_light / 7
    n = round(w / m)
    if (n - 17) % 4 or abs(n * m - w) > m / 4:
        sys.exit(f'Не похоже на QR без поля: {n} модулей по {m:.1f} px')
    rows = []
    for r in range(n):
        row = ''
        for c in range(n):
            # Клетка должна быть одного цвета целиком, иначе сетка снята криво.
            box = [img.getpixel((int((c + fx) * m), int((r + fy) * m))) < 128
                   for fx in (0.25, 0.5, 0.75) for fy in (0.25, 0.5, 0.75)]
            if len(set(box)) > 1:
                sys.exit(f'Модуль {r},{c} не одного цвета — картинка размыта или масштабирована')
            row += '#' if box[0] else '.'
        rows.append(row)
    return rows


def decode(img):
    padded = ImageOps.expand(img, border=img.size[0] // 8, fill=255)
    found = [r.text for r in zxingcpp.read_barcodes(padded) if r.format == zxingcpp.BarcodeFormat.QRCode]
    if len(found) != 1:
        sys.exit(f'QR не распознан (найдено: {found})')
    return found[0]


def rows_image(rows, scale=8, quiet=4):
    n = len(rows)
    size = (n + 2 * quiet) * scale
    im = Image.new('L', (size, size), 255)
    for r, row in enumerate(rows):
        for c, v in enumerate(row):
            if v == '#':
                x, y = (c + quiet) * scale, (r + quiet) * scale
                im.paste(0, (x, y, x + scale, y + scale))
    return im


img = gray(SRC)
text = decode(img)
rows = modules(img)

# Сетка, снятая с картинки, обязана читаться так же, как сама картинка:
# иначе на сайт ушёл бы код, который ведёт неизвестно куда.
again = [r.text for r in zxingcpp.read_barcodes(rows_image(rows))]
if again != [text]:
    sys.exit(f'Перерисованный код читается иначе: {again} вместо {text!r}')

link = re.search(r"reviewLink:\s*'([^']*)'", SITE_TS.read_text(encoding='utf-8'))
if not link:
    sys.exit('В site.ts нет SITE.reviewLink')
if link.group(1) != text:
    sys.exit(f'QR ведёт на {text}, а в site.ts SITE.reviewLink = {link.group(1)} — исправьте одно из двух')

OUT.write_text(json.dumps({'text': text, 'rows': rows}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'{OUT.relative_to(ROOT)}: {len(rows)}×{len(rows)} модулей, ведёт на {text}')
