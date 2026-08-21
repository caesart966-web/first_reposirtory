#!/usr/bin/env python3
"""
Достаёт картинки из презентации ООО «МАСТЕР» и готовит их для сайта.

Запуск:
    python3 tools/extract-images.py path/to/presentation.pdf

Нужны пакеты: pymupdf, pillow, fonttools[woff] (последний - только для og-обложки).
Скрипт нужен разработчику. Для работы сайта он не требуется, на хостинг
папку tools/ загружать не нужно.
"""
import io
import os
import sys

import pymupdf
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "assets", "img")
OBJ = os.path.join(IMG, "objects")
FONTS = os.path.join(ROOT, "assets", "fonts")

GRAPHITE = (31, 33, 36)
BRASS = (201, 162, 39)
CONCRETE = (237, 239, 240)

# xref изображения в PDF -> что это. Проверено вручную по слайдам.
LOGO = (9, 10)          # логотип: изображение + маска прозрачности
HERO = 8                # слайд 1, стеклянный фасад в цвете
CTA = 97                # слайд 15, стеклянный фасад ч/б
ABOUT = (25, 26)        # слайд 2, стройплощадка с башенными кранами
AWARD = [93, 94]        # слайд 14, медаль НОСТРОЙ

GALLERY = {
    "pgtu": [62, 63, 64, 65],            # слайд 9
    "houses": [68, 69, 70, 71],          # слайд 10
    "kindergarten": [74, 75, 76, 77],    # слайд 11
    "school": [81, 82, 84, 87, 89, 90],  # слайды 12-13
}

# Мусор, который на сайт не идёт:
#   xref 6, 21 - водяной знак SetlGroup из чужого шаблона PowerPoint
#   xref 29    - стоковый коллаж «человек в костюме и логистика» со слайда 3
#   xref 31-38 - иконки-эмодзи из того же шаблона
#   xref 52,53 - QR-коды на телефоны, номера на сайте даны текстом
SKIP = {6, 7, 21, 22, 29, 31, 33, 34, 36, 38, 52, 53}

WEBP_Q = 78
JPEG_Q = 76


def rgba(doc, xref, smask):
    """Картинка вместе с маской прозрачности из PDF."""
    base = Image.open(io.BytesIO(doc.extract_image(xref)["image"])).convert("RGB")
    mask = Image.open(io.BytesIO(doc.extract_image(smask)["image"])).convert("L")
    base.putalpha(mask.resize(base.size, Image.LANCZOS))
    return base


def rgb(doc, xref):
    return Image.open(io.BytesIO(doc.extract_image(xref)["image"])).convert("RGB")


def variants(im, path_noext, widths, fmt_jpeg=True):
    """Сохраняет webp и jpg в нескольких ширинах. Вверх не растягиваем."""
    made = []
    for w in widths:
        if w > im.width:
            w = im.width
        if any(m[1] == w for m in made):
            continue
        h = round(im.height * w / im.width)
        r = im.resize((w, h), Image.LANCZOS)
        r.save(f"{path_noext}-{w}.webp", "WEBP", quality=WEBP_Q, method=6)
        if fmt_jpeg:
            r.save(f"{path_noext}-{w}.jpg", "JPEG", quality=JPEG_Q,
                   optimize=True, progressive=True)
        made.append((r, w, h))
    for _, w, h in made:
        print(f"    {os.path.basename(path_noext)}-{w}  {w}x{h}")
    return made


def load_font(name, size):
    """Наши woff2 -> временный ttf, чтобы Pillow смог ими рисовать."""
    from fontTools.ttLib import TTFont
    src = os.path.join(FONTS, name)
    tmp = os.path.join("/tmp", name.replace(".woff2", ".ttf"))
    if not os.path.exists(tmp):
        f = TTFont(src)
        f.flavor = None
        f.save(tmp)
    return ImageFont.truetype(tmp, size)


def build_og(hero, mark):
    """Картинка для соцсетей: фасад, затемнение, знак и название."""
    card = hero.resize((1200, round(hero.height * 1200 / hero.width)), Image.LANCZOS)
    top = max(0, (card.height - 630) // 2)
    card = card.crop((0, top, 1200, top + 630)).convert("RGB")
    shade = Image.new("RGB", card.size, GRAPHITE)
    card = Image.blend(card, shade, 0.62)

    m = mark.copy()
    m.thumbnail((150, 150), Image.LANCZOS)
    card.paste(m, (80, 150), m)

    d = ImageDraw.Draw(card)
    try:
        f_name = load_font("onest-cyrillic.woff2", 74)
        f_lat = load_font("onest-latin.woff2", 74)
        f_sub = load_font("onest-cyrillic.woff2", 25)
        f_slog = load_font("literata-cyrillic.woff2", 40)
        # Кириллица и кавычки-ёлочки лежат в разных файлах шрифта,
        # поэтому строку рисуем по кускам.
        x = 80
        for part, fnt in (("ООО ", f_name), ("«", f_lat), ("МАСТЕР", f_name), ("»", f_lat)):
            d.text((x, 330), part, font=fnt, fill=(244, 246, 247))
            x += d.textlength(part, font=fnt)
        d.text((84, 424), "С Т Р О И Т Е Л Ь Н А Я   К О М П А Н И Я",
               font=f_sub, fill=(180, 184, 188))
        d.line([(84, 476), (240, 476)], fill=BRASS, width=3)
        d.text((80, 500), "Строим в ритме города", font=f_slog, fill=BRASS)
    except Exception as exc:                                   # pragma: no cover
        print("    ! шрифты для og-обложки не подхватились:", exc)
    card.save(os.path.join(IMG, "og-cover.jpg"), "JPEG", quality=86, optimize=True)
    print("    og-cover.jpg  1200x630")


def build_icons(mark):
    """Фавиконки: знак на графитовом квадрате."""
    for size, name in [(32, "icon-32.png"), (180, "apple-touch-icon.png"),
                       (192, "icon-192.png"), (512, "icon-512.png")]:
        pad = round(size * 0.16)
        canvas = Image.new("RGBA", (size, size), GRAPHITE + (255,))
        m = mark.copy()
        m.thumbnail((size - pad * 2, size - pad * 2), Image.LANCZOS)
        canvas.paste(m, ((size - m.width) // 2, (size - m.height) // 2), m)
        canvas.convert("RGB").save(os.path.join(IMG, name), "PNG", optimize=True)
        print(f"    {name}  {size}x{size}")
    # maskable: знак поменьше, safe zone по спецификации PWA
    size = 512
    canvas = Image.new("RGBA", (size, size), GRAPHITE + (255,))
    m = mark.copy()
    m.thumbnail((round(size * 0.52), round(size * 0.52)), Image.LANCZOS)
    canvas.paste(m, ((size - m.width) // 2, (size - m.height) // 2), m)
    canvas.convert("RGB").save(os.path.join(IMG, "icon-maskable-512.png"), "PNG", optimize=True)
    ico = Image.new("RGBA", (64, 64), GRAPHITE + (255,))
    m = mark.copy()
    m.thumbnail((48, 48), Image.LANCZOS)
    ico.paste(m, ((64 - m.width) // 2, (64 - m.height) // 2), m)
    ico.convert("RGB").save(os.path.join(ROOT, "favicon.ico"),
                            sizes=[(16, 16), (32, 32), (48, 48)])
    print("    icon-maskable-512.png, favicon.ico")


def main(pdf_path):
    os.makedirs(OBJ, exist_ok=True)
    doc = pymupdf.open(pdf_path)

    print("Логотип")
    logo = rgba(doc, *LOGO)
    logo.save(os.path.join(IMG, "logo-full.png"), optimize=True)
    # В исходном логотипе знак сверху, под ним чёрная подпись «МАСТЕР /
    # строительная компания». На тёмном фоне сайта такая подпись пропадает,
    # поэтому берём только знак, а название набираем текстом.
    mark = logo.crop((133, 118, 367, 289))
    for w in (120, 240):
        h = round(mark.height * w / mark.width)
        r = mark.resize((w, h), Image.LANCZOS)
        r.save(os.path.join(IMG, f"logo-mark-{w}.png"), optimize=True)
        r.save(os.path.join(IMG, f"logo-mark-{w}.webp"), "WEBP", quality=92, method=6)
        print(f"    logo-mark-{w}  {w}x{h}")

    print("Первый экран")
    hero = rgb(doc, HERO)
    variants(hero, os.path.join(IMG, "hero-facade"), (960, 1440, 2000))

    print("Блок «Приглашаем к сотрудничеству»")
    variants(rgb(doc, CTA), os.path.join(IMG, "cta-facade"), (960, 1536))

    print("Блок «О компании»")
    about = rgba(doc, *ABOUT).convert("RGB")
    # Вокруг фото рамка из PowerPoint и отражение снизу - срезаем.
    variants(about.crop((18, 18, 483, 320)), os.path.join(IMG, "about-site"), (465, 930))

    print("Медаль")
    for i, xref in enumerate(AWARD, start=1):
        variants(rgb(doc, xref), os.path.join(IMG, f"award-{i}"), (560, 1120))

    print("Объекты")
    for group, xrefs in GALLERY.items():
        for i, xref in enumerate(xrefs, start=1):
            variants(rgb(doc, xref), os.path.join(OBJ, f"{group}-{i}"), (640, 1280))

    print("Обложка для соцсетей")
    build_og(hero, mark)

    print("Фавиконки")
    build_icons(mark)

    total = 0
    for base, _, files in os.walk(IMG):
        total += sum(os.path.getsize(os.path.join(base, f)) for f in files)
    print(f"\nГотово. assets/img весит {total / 1024 / 1024:.1f} МБ")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Укажите путь к PDF презентации")
    main(sys.argv[1])
