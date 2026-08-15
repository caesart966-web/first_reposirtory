"""
Генератор картинок-заглушек: постер первого экрана и картинка для мессенджеров.

Нужен только чтобы сайт не выглядел пустым до того, как вы поставите настоящие
изображения. Ничего не устанавливает — рисует PNG стандартными средствами Python.

Вызывается автоматически из build.py. Уже существующие файлы НЕ перезаписываются,
поэтому ваши картинки в безопасности. Чтобы перерисовать заглушки заново:

    python3 build.py --regen-media
"""

import struct
import zlib
from pathlib import Path

NAVY_TOP = (11, 25, 40)
NAVY_BOTTOM = (27, 58, 94)
GRID = (255, 255, 255)
ACCENT = (31, 111, 235)
WHITE = (255, 255, 255)


def _write_png(path: Path, width: int, height: int, rows: list) -> None:
    """Собирает PNG из готовых строк пикселей (по три байта на пиксель)."""
    raw = b"".join(b"\x00" + bytes(row) for row in rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def _mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _blend(base, over, alpha):
    return tuple(round(base[i] + (over[i] - base[i]) * alpha) for i in range(3))


def _canvas(width, height, grid_step):
    """Тёмный градиент с технической сеткой — фирменный фон."""
    rows = []
    for y in range(height):
        row = bytearray()
        vy = y / (height - 1)
        for x in range(width):
            vx = x / (width - 1)
            colour = _mix(NAVY_TOP, NAVY_BOTTOM, vx * 0.55 + vy * 0.45)

            # сетка
            if x % grid_step == 0 or y % grid_step == 0:
                colour = _blend(colour, GRID, 0.05)
            # каждая пятая линия чуть заметнее
            if x % (grid_step * 5) == 0 or y % (grid_step * 5) == 0:
                colour = _blend(colour, GRID, 0.06)

            # затемнение по краям, чтобы текст поверх читался
            edge = min(x, width - 1 - x) / width + min(y, height - 1 - y) / height
            if edge < 0.22:
                colour = _blend(colour, (5, 12, 20), (0.22 - edge) * 1.4)

            row += bytes(colour)
        rows.append(row)
    return rows


def _rect(rows, x0, y0, w, h, colour, alpha=1.0):
    height = len(rows)
    width = len(rows[0]) // 3
    for y in range(max(0, y0), min(height, y0 + h)):
        row = rows[y]
        for x in range(max(0, x0), min(width, x0 + w)):
            i = x * 3
            if alpha >= 1.0:
                row[i:i + 3] = bytes(colour)
            else:
                cur = (row[i], row[i + 1], row[i + 2])
                row[i:i + 3] = bytes(_blend(cur, colour, alpha))


def make_poster(path: Path, width: int = 1280, height: int = 720) -> None:
    """Постер первого экрана: он же — картинка вместо видео на телефонах."""
    rows = _canvas(width, height, grid_step=40)
    # горизонтальный акцентный штрих слева, как в вёрстке первого экрана
    _rect(rows, int(width * 0.08), int(height * 0.52), int(width * 0.14), 6, ACCENT)
    _rect(rows, int(width * 0.08), int(height * 0.60), int(width * 0.34), 3, WHITE, 0.18)
    _rect(rows, int(width * 0.08), int(height * 0.66), int(width * 0.26), 3, WHITE, 0.12)
    _write_png(path, width, height, rows)


def make_og(path: Path, width: int = 1200, height: int = 630) -> None:
    """Картинка для ссылок в мессенджерах и соцсетях."""
    rows = _canvas(width, height, grid_step=42)

    # мотив логотипа: стопка документов
    bx, by, bw = 760, 190, 300
    _rect(rows, bx + 30, by + 250, bw - 60, 34, (36, 70, 110))
    _rect(rows, bx + 15, by + 200, bw - 30, 38, (22, 48, 79))
    _rect(rows, bx, by, bw, 190, WHITE)
    _rect(rows, bx + 34, by + 40, 170, 14, (14, 30, 51))
    _rect(rows, bx + 34, by + 82, 220, 12, (195, 207, 221))
    _rect(rows, bx + 34, by + 120, 130, 12, (195, 207, 221))

    # акцентная полоса слева — место, где в макете стоит заголовок
    _rect(rows, 90, 250, 150, 8, ACCENT)
    _rect(rows, 90, 300, 420, 5, WHITE, 0.22)
    _rect(rows, 90, 330, 330, 5, WHITE, 0.16)

    _write_png(path, width, height, rows)


def ensure_media(assets_dir: Path, force: bool = False) -> list:
    """Создаёт заглушки, если их ещё нет. Возвращает список созданных файлов."""
    created = []
    targets = [
        (assets_dir / "media" / "hero-poster.png", make_poster),
        (assets_dir / "img" / "og-default.png", make_og),
    ]
    for path, maker in targets:
        if force or not path.exists():
            maker(path)
            created.append(path)
    return created
