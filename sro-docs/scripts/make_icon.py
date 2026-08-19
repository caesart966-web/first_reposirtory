# -*- coding: utf-8 -*-
"""Нарисовать значок программы.

Значок делается кодом, чтобы его можно было пересобрать в любой момент и не
хранить «магическую» картинку неизвестного происхождения. Рисуется простой
узнаваемый знак: синий скруглённый квадрат, белый лист документа с строками
и зелёная галочка «готово».

Результат:
  assets/icon.ico  — для .exe и окна на Windows (несколько размеров внутри);
  assets/icon.png  — 256×256, для окна программы на любой системе.

Нужен Pillow: pip install pillow
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

BLUE = (31, 106, 176)          # фон
BLUE_DARK = (23, 82, 137)      # обводка листа
PAPER = (255, 255, 255)
LINE = (176, 196, 214)
GREEN = (28, 150, 70)


def _rounded(size: int, radius_ratio: float, fill) -> Image.Image:
    """Скруглённый квадрат нужного цвета на прозрачном фоне."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    radius = int(size * radius_ratio)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=fill)
    return image


def draw_icon(size: int) -> Image.Image:
    """Значок целиком в заданном размере."""
    scale = size / 256.0

    def px(value: float) -> int:
        return int(round(value * scale))

    image = _rounded(size, 0.22, BLUE)
    draw = ImageDraw.Draw(image)

    # Лист документа.
    left, top, right, bottom = px(70), px(48), px(186), px(208)
    corner = px(10)
    draw.rounded_rectangle((left, top, right, bottom), radius=corner,
                           fill=PAPER, outline=BLUE_DARK, width=max(1, px(3)))

    # Строки текста на листе.
    line_x0, line_x1 = px(88), px(168)
    line_w = max(1, px(7))
    for i, y in enumerate((px(78), px(100), px(122), px(144))):
        x1 = line_x1 if i % 2 == 0 else px(150)
        draw.line((line_x0, y, x1, y), fill=LINE, width=line_w)

    # Зелёная галочка «готово».
    check_w = max(2, px(16))
    draw.line((px(96), px(170), px(116), px(190)), fill=GREEN, width=check_w)
    draw.line((px(116), px(190), px(158), px(150)), fill=GREEN, width=check_w)
    return image


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    master = draw_icon(256)
    master.save(ASSETS / "icon.png")

    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [draw_icon(s) for s in sizes]
    # .ico хранит несколько размеров; берём отрисованные под каждый размер,
    # чтобы мелкие значки не мылились.
    frames[-1].save(ASSETS / "icon.ico", format="ICO",
                    sizes=[(s, s) for s in sizes],
                    append_images=frames[:-1])
    print("Готово:", ASSETS / "icon.ico", "и", ASSETS / "icon.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
