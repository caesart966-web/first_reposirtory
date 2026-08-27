#!/usr/bin/env python3
"""Заглушки под четыре тематических изображения (ЧАСТЬ 4 ТЗ).

Настоящих файлов ещё нет, но вёрстка должна быть готова: слоты, пропорции,
width/height и вес — всё как у боевых картинок. Заглушки нарочно подписаны,
чтобы их нельзя было принять за финальную графику и случайно выкатить.

Цвета — те же, что в дуотоне из T29: от accent-900 #1E2A75 к accent-100 #E6ECFF.

Запуск: python3 scripts/make-image-placeholders.py  (из sro-site/)
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path("public/img")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

DARK = (30, 42, 117)  # accent-900
LIGHT = (230, 236, 255)  # accent-100

SLOTS = [
    ("design.webp", 1200, 900, "Проектирование", "архивный чертёж: план, разрез, штамп"),
    ("construction.webp", 2000, 700, "Стройка", "башенные краны на чистом небе, без людей"),
    ("survey.webp", 1200, 900, "Инженерные изыскания", "тахеометр, буровая, керны, вешки"),
    ("legal.webp", 1200, 800, "Юридическая часть", "гравюра: весы, печать, документ"),
]


def duotone_gradient(w: int, h: int) -> Image.Image:
    """Диагональная растяжка между двумя фирменными цветами."""
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(0, w, 4):
            t = (x / w * 0.65 + y / h * 0.35)
            c = tuple(round(DARK[i] + (LIGHT[i] - DARK[i]) * t) for i in range(3))
            for dx in range(4):
                if x + dx < w:
                    px[x + dx, y] = c
    return img


def draw(name: str, w: int, h: int, title: str, hint: str) -> None:
    img = duotone_gradient(w, h)
    d = ImageDraw.Draw(img, "RGBA")

    # Диагональная штриховка — сразу видно, что это не фотография
    step = max(28, w // 40)
    for x in range(-h, w + h, step):
        d.line([(x, 0), (x + h, h)], fill=(255, 255, 255, 26), width=max(2, w // 600))

    pad = max(16, w // 60)
    d.rectangle([pad, pad, w - pad, h - pad], outline=(255, 255, 255, 90), width=max(2, w // 500))

    big = ImageFont.truetype(FONT_BOLD, max(30, w // 22))
    small = ImageFont.truetype(FONT, max(17, w // 46))
    tiny = ImageFont.truetype(FONT, max(15, w // 60))

    lines = [
        (f"ЗАГЛУШКА · {title}", big, (255, 255, 255, 245)),
        (hint, small, (255, 255, 255, 205)),
        (f"{name} · {w}×{h}", tiny, (255, 255, 255, 165)),
    ]
    heights = [d.textbbox((0, 0), t, font=f)[3] for t, f, _ in lines]
    gap = max(10, h // 45)
    total = sum(heights) + gap * (len(lines) - 1)
    y = (h - total) / 2
    for (text, font, fill), th in zip(lines, heights):
        tw = d.textbbox((0, 0), text, font=font)[2]
        d.text(((w - tw) / 2, y), text, font=font, fill=fill)
        y += th + gap

    img.save(OUT / name, "WEBP", quality=80, method=6)
    img.save(OUT / name.replace(".webp", ".avif"), "AVIF", quality=55)
    kb = (OUT / name).stat().st_size / 1024
    kb_avif = (OUT / name.replace(".webp", ".avif")).stat().st_size / 1024
    print(f"{name}: {w}×{h}, webp {kb:.0f} КБ, avif {kb_avif:.0f} КБ")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for slot in SLOTS:
        draw(*slot)


if __name__ == "__main__":
    main()
