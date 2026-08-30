#!/usr/bin/env python3
"""Единая обработка тематических фотографий (T29) и контроль веса (T30).

В ТЗ путь записан командами ImageMagick:

    magick input.jpg -colorspace Gray \
      \( -size 256x1 gradient:'#1E2A75-#E6ECFF' \) -clut \
      -resize 1200x -quality 82 public/img/documents.webp
    magick public/img/documents.webp -quality 55 public/img/documents.avif

Здесь то же самое на Pillow, чтобы обработку можно было повторить без
установки magick. Смысл: разные кадры из разных источников выглядят как
четыре разных сайта; перевод в дуотон на фирменном синем сводит их в одну
серию и заодно прячет «стоковость».

Один кадр из четырёх может остаться в цвете как акцент — для этого --color.

Примеры:
    python3 scripts/prepare-photo.py ~/downloads/blueprint.jpg design --width 1200
    python3 scripts/prepare-photo.py ~/downloads/cranes.jpg construction --width 2000 --color

Бюджет T30 проверяется после сохранения: WebP <= 180 КБ, AVIF <= 120 КБ.
"""

import argparse
import sys
from pathlib import Path

from PIL import Image

OUT = Path("public/img")
DARK = (0x1E, 0x2A, 0x75)  # accent-900
LIGHT = (0xE6, 0xEC, 0xFF)  # accent-100
WEBP_LIMIT_KB, AVIF_LIMIT_KB = 180, 120


# Нижние точки дуотона. По умолчанию accent-900; для кадров со сплошным тёмным
# фоном (синька) есть светлее — иначе кадр читается тяжёлым прямоугольником
# рядом с воздушными соседями.
DARK_POINTS = {
    "900": (0x1E, 0x2A, 0x75),
    "800": (0x20, 0x2F, 0x93),
    "700": (0x24, 0x39, 0xB8),
    "600": (0x2F, 0x4B, 0xDE),
}


def duotone(img: Image.Image, stretch: bool = False, dark: tuple = DARK, gamma: float = 1.0) -> Image.Image:
    """Обесцвечиваем и раскладываем яркость по градиенту dark -> LIGHT."""
    gray = img.convert("L")
    if stretch:
        gray = normalize(gray)
    if gamma != 1.0:
        gray = apply_gamma(gray, gamma)
    lut = []
    for channel in range(3):
        lut += [round(dark[channel] + (LIGHT[channel] - dark[channel]) * v / 255) for v in range(256)]
    return Image.merge("RGB", (gray, gray, gray)).point(lut)


def normalize(gray: Image.Image) -> Image.Image:
    """Растягиваем гистограмму, отбрасывая по 0.5% с краёв (аналог -normalize).

    Нужно для малоконтрастных исходников вроде цианотипных синек: там весь
    диапазон сидит в середине, и дуотон без растяжки даёт вялое сиреневое
    пятно вместо чертежа.
    """
    hist = gray.histogram()
    cut = sum(hist) * 0.005
    acc, low = 0, 0
    for value, count in enumerate(hist):
        acc += count
        if acc > cut:
            low = value
            break
    acc, high = 0, 255
    for value in range(255, -1, -1):
        acc += hist[value]
        if acc > cut:
            high = value
            break
    if high <= low:
        return gray
    scale = 255.0 / (high - low)
    return gray.point(lambda v: min(255, max(0, int((v - low) * scale))))


def apply_gamma(gray: Image.Image, gamma: float) -> Image.Image:
    """Гнём кривую яркости: gamma > 1 темнит, gamma < 1 высветляет.

    Растяжка гистограммы выравнивает ДИАПАЗОН, но не РАСПРЕДЕЛЕНИЕ. Кадры,
    у которых сюжет занимает меньшую часть площади (лес белых папок на белом,
    геодезический прибор на пасмурном небе), после растяжки всё равно остаются светлым
    пятном: их гистограмма прижата к правому краю. Рядом с кадрами поплотнее
    такой снимок в серии читается как незагрузившийся.

    Гамма правит именно это — сдвигает середину, не трогая крайние точки,
    поэтому белое остаётся белым, чёрное чёрным, а средняя яркость приходит
    к общей для серии.
    """
    return gray.point(lambda v: round(255 * (v / 255) ** gamma))


CUTOUT_BLACK, CUTOUT_WHITE = 50, 230


def cutout(img: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Восстанавливает прозрачность штриховой графики по яркости.

    Вырезанные PNG часто приходят с УЖЕ ЗАПЕЧЁННОЙ в пиксели шашечкой: экспорт
    или скриншот сплющил альфу в серо-белую клетку. Дуотон такого файла даёт
    двухцветную сетку вместо чистого объекта.

    Для чёрного штриха на светлом фоне это лечится: светлое — фон, тёмное —
    объект. Строим альфу из яркости и заливаем сам объект фирменным тёмным
    цветом, чтобы по краям не лезла серая кайма от сглаживания.

    Работает только для контрастной штриховой графики. Для фотографии не
    годится и не предназначено.
    """
    gray = img.convert("L")
    span = CUTOUT_WHITE - CUTOUT_BLACK
    alpha = gray.point(
        lambda v: 255 if v <= CUTOUT_BLACK else (0 if v >= CUTOUT_WHITE else round(255 * (CUTOUT_WHITE - v) / span))
    )
    return Image.new("RGB", img.size, DARK), alpha


def split_alpha(img: Image.Image) -> tuple[Image.Image, Image.Image | None]:
    """Отделяем прозрачность, если она есть.

    Вырезанные PNG (весы, печати с rawpixel) приходят с альфой. Простой
    convert("RGB") залил бы прозрачные пиксели чёрным, и вместо аккуратного
    объекта получился бы чёрный прямоугольник. Поэтому альфу снимаем заранее,
    обрабатываем только цвет и возвращаем её на место в конце.
    """
    if img.mode in ("RGBA", "LA") or "transparency" in img.info:
        rgba = img.convert("RGBA")
        return rgba.convert("RGB"), rgba.getchannel("A")
    return img.convert("RGB"), None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path, help="исходный файл (jpg/png/webp)")
    ap.add_argument("name", help="имя без расширения: design | construction | survey | legal")
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--color", action="store_true", help="оставить в цвете (акцентный кадр)")
    ap.add_argument(
        "--dark",
        choices=sorted(DARK_POINTS),
        default="900",
        help="нижняя точка дуотона (оттенок accent-N); светлее — для кадров со сплошным тёмным фоном",
    )
    ap.add_argument(
        "--cutout",
        action="store_true",
        help="штриховая графика: восстановить прозрачность из яркости и залить объект accent-900",
    )
    ap.add_argument(
        "--normalize",
        action="store_true",
        help="растянуть гистограмму перед дуотоном (для малоконтрастных исходников)",
    )
    ap.add_argument(
        "--gamma",
        type=float,
        default=1.0,
        help="кривая яркости после растяжки: >1 темнит, <1 высветляет; нужна, чтобы свести кадры серии к общей плотности",
    )
    ap.add_argument(
        "--flatten",
        action="store_true",
        help="положить прозрачный объект на белый фон вместо сохранения альфы",
    )
    ap.add_argument("--webp-quality", type=int, default=82)
    ap.add_argument("--avif-quality", type=int, default=55)
    args = ap.parse_args()

    if args.gamma != 1.0 and (args.color or args.cutout):
        print(
            "--gamma действует только на дуотон: с --color и --cutout яркость не трогаем.",
            file=sys.stderr,
        )
        return 1

    img, alpha = split_alpha(Image.open(args.source))
    if args.cutout:
        if alpha is not None:
            # Настоящая альфа есть — восстанавливать нечего, только зальём тон
            img = Image.new("RGB", img.size, DARK)
        else:
            img, alpha = cutout(img)
    elif not args.color:
        img = duotone(img, stretch=args.normalize, dark=DARK_POINTS[args.dark], gamma=args.gamma)
    if img.width != args.width:
        height = round(img.height * args.width / img.width)
        img = img.resize((args.width, height), Image.LANCZOS)
        if alpha is not None:
            alpha = alpha.resize((args.width, height), Image.LANCZOS)
    if alpha is not None:
        if args.flatten:
            # Кладём объект на белый: так он ведёт себя как обычная фотография.
            white = Image.new("RGB", img.size, (255, 255, 255))
            white.paste(img, mask=alpha)
            img = white
        else:
            img = img.convert("RGBA")
            img.putalpha(alpha)

    OUT.mkdir(parents=True, exist_ok=True)
    webp, avif = OUT / f"{args.name}.webp", OUT / f"{args.name}.avif"
    img.save(webp, "WEBP", quality=args.webp_quality, method=6)
    img.save(avif, "AVIF", quality=args.avif_quality)

    # Средняя яркость — рабочий показатель, а не украшение отчёта: кадры одной
    # серии должны сойтись по нему, иначе рядом они читаются разнобоем.
    #
    # У вырезанного объекта прозрачные пиксели в среднюю яркость не входят:
    # convert("L") подставил бы им чёрный, и число получилось бы про размер
    # выреза, а не про плотность самого объекта.
    gray = img.convert("RGB").convert("L") if alpha is None else img.convert("RGBA").convert("L")
    mean = sum(v * c for v, c in enumerate(gray.histogram())) / (gray.width * gray.height)
    print(f"средняя яркость: {mean:.0f}")

    over = False
    for path, limit in ((webp, WEBP_LIMIT_KB), (avif, AVIF_LIMIT_KB)):
        kb = path.stat().st_size / 1024
        mark = "ок" if kb <= limit else f"ПРЕВЫШЕН бюджет {limit} КБ"
        over |= kb > limit
        print(f"{path}: {img.width}×{img.height}, {kb:.0f} КБ — {mark}")
    if over:
        print("Снизьте качество или ширину — бюджет T30 не выполнен.", file=sys.stderr)
        return 1
    print(f"Не забудьте вписать источник и лицензию в {OUT / 'CREDITS.md'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
