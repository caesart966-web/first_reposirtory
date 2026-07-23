#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автоматическая пакетная генерация стикеров 512×512 PNG в едином стиле:
персонаж-супергерой + подпись капсом снизу (золотой градиент, синяя
обводка, белый кант).

Пайплайн для каждой картинки из input/:
  1) удаление серого водяного знака слева внизу (cv2.inpaint)
  2) вырезание белого фона в прозрачность (floodfill от всех границ;
     белое ВНУТРИ персонажа сохраняется)
  3) цветокоррекция (насыщенность ×1.18, яркость ×1.04)
  4) белая обводка вокруг персонажа
  5) вписывание персонажа во весь кадр 512×512
  6) подпись капсом поверх нижней части персонажа
  7) сохранение 512×512 PNG с прозрачным фоном

Все параметры стиля — в config.json. Подписи — в captions.csv
(filename,caption); если подписи нет — берётся имя файла без расширения.

Запуск:  python main.py   (на Windows — run.bat)
"""

import csv
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
FONTS_DIR = BASE_DIR / "fonts"
FONT_PATH = FONTS_DIR / "RussoOne-Regular.ttf"
FONT_URL = ("https://github.com/google/fonts/raw/main/ofl/"
            "russoone/RussoOne-Regular.ttf")
CONFIG_PATH = BASE_DIR / "config.json"
CAPTIONS_PATH = BASE_DIR / "captions.csv"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# Запасные системные шрифты на случай отсутствия сети при первом запуске
FALLBACK_FONTS = [
    r"C:\Windows\Fonts\impact.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]

# Значения по умолчанию — на случай отсутствия/неполноты config.json
DEFAULT_CONFIG = {
    "canvas": 512,
    "supersample": 4,
    "gold_top": [248, 218, 124],
    "gold_bot": [208, 152, 40],
    "navy": [20, 35, 70],
    "cap_target": 50,
    "outline_ratio": 0.21,
    "white_ratio": 0.13,
    "max_line_width": 476,
    "line_gap_ratio": 0.34,
    "char_fill_margin": 6,
    "text_bottom_margin": 16,
    "char_white_outline": 4,
    "enhance_color": 1.18,
    "enhance_brightness": 1.04,
    "watermark_inpaint_radius": 3,
}


def ensure_dependencies() -> None:
    """При первом запуске доустанавливает Pillow/OpenCV/numpy, если их нет."""
    try:
        import cv2  # noqa: F401
        import numpy  # noqa: F401
        import PIL  # noqa: F401
    except ImportError:
        print("Не хватает библиотек — устанавливаю зависимости...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r",
             str(BASE_DIR / "requirements.txt")]
        )


ensure_dependencies()

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageEnhance, ImageFont  # noqa: E402


# ----------------------------------------------------------------------------
# Подготовка окружения
# ----------------------------------------------------------------------------

def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    return cfg


def ensure_font() -> Path:
    """Возвращает путь к Russo One, при необходимости скачав его с Google Fonts."""
    if FONT_PATH.exists():
        return FONT_PATH
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    print("Скачиваю шрифт Russo One...")
    try:
        urllib.request.urlretrieve(FONT_URL, FONT_PATH)
        return FONT_PATH
    except Exception as exc:  # нет сети — берём системный шрифт
        for cand in FALLBACK_FONTS:
            if Path(cand).exists():
                print(f"  не удалось скачать ({exc}); использую {cand}")
                return Path(cand)
        raise RuntimeError(
            f"Не удалось скачать шрифт ({exc}) и не найден системный запасной. "
            f"Положите RussoOne-Regular.ttf в {FONTS_DIR}"
        ) from exc


def load_captions() -> dict:
    """Читает captions.csv → {имя файла: подпись}."""
    caps: dict[str, str] = {}
    if not CAPTIONS_PATH.exists():
        return caps
    with open(CAPTIONS_PATH, encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            name = row[0].strip()
            caption = ",".join(row[1:]).strip()
            if not name or name.lower() == "filename":
                continue
            caps[name] = caption
    return caps


def load_bgr(path: Path) -> np.ndarray:
    """Читает картинку в BGR (np.fromfile — ради кириллицы в путях на Windows)."""
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError("не удалось прочитать изображение")
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.shape[2] == 4:
        # PNG с прозрачностью кладём на белый фон — дальше фон снова вырежется
        alpha = img[:, :, 3:4].astype(np.float32) / 255.0
        img = (img[:, :, :3].astype(np.float32) * alpha
               + 255.0 * (1.0 - alpha)).astype(np.uint8)
    return img


# ----------------------------------------------------------------------------
# Шаги обработки персонажа
# ----------------------------------------------------------------------------

def remove_watermark(bgr: np.ndarray, cfg: dict) -> np.ndarray:
    """Затирает серый водяной знак в левом нижнем углу через inpaint.

    Зона поиска: нижние ~12% высоты и левые ~55% ширины. Серым считаем
    пиксель с насыщенностью (max−min каналов) < 45 и яркостью 135–236.
    """
    h, w = bgr.shape[:2]
    y0, x1 = int(h * 0.88), int(w * 0.55)
    roi = bgr[y0:, :x1]
    if roi.size == 0:
        return bgr
    mx = roi.max(axis=2).astype(np.int16)
    mn = roi.min(axis=2).astype(np.int16)
    mean = roi.mean(axis=2)
    gray = (mx - mn < 45) & (mean >= 135) & (mean <= 236)
    if not gray.any():
        return bgr
    mask = np.zeros((h, w), np.uint8)
    mask[y0:, :x1] = gray.astype(np.uint8) * 255
    # чуть расширяем маску, чтобы не остались контуры букв
    mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    return cv2.inpaint(bgr, mask, cfg["watermark_inpaint_radius"],
                       cv2.INPAINT_TELEA)


def cut_background(bgr: np.ndarray, cfg: dict) -> np.ndarray:
    """Возвращает RGBA: почти белый фон, достижимый от границ, → прозрачность.

    Прозрачным становится только белое (min(R,G,B) > 236), связанное с
    границами кадра, — аналог floodfill со всех четырёх сторон. Белые области
    внутри персонажа (глаза, зубы, логотип) не задеваются. Из непрозрачного
    остаётся только самая большая связная компонента — тело персонажа.
    """
    white = (bgr.min(axis=2) > 236).astype(np.uint8)
    _, labels = cv2.connectedComponents(white, connectivity=8)
    border = np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])
    bg_ids = np.unique(border)
    bg_ids = bg_ids[bg_ids != 0]  # метка 0 — не-белые пиксели
    background = np.isin(labels, bg_ids)
    alpha = np.where(background, 0, 255).astype(np.uint8)

    n, comp, stats, _ = cv2.connectedComponentsWithStats(
        (alpha > 0).astype(np.uint8), connectivity=8)
    if n <= 1:
        raise ValueError("персонаж не найден (кадр целиком белый)")
    if n > 2:
        biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        alpha[comp != biggest] = 0

    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)  # анти-алиасинг края

    rgba = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGBA)
    rgba[:, :, 3] = alpha
    return rgba


def enhance(rgba: np.ndarray, cfg: dict) -> Image.Image:
    """Повышает насыщенность и яркость, не трогая альфа-канал."""
    img = Image.fromarray(rgba, "RGBA")
    r, g, b, a = img.split()
    rgb = Image.merge("RGB", (r, g, b))
    rgb = ImageEnhance.Color(rgb).enhance(cfg["enhance_color"])
    rgb = ImageEnhance.Brightness(rgb).enhance(cfg["enhance_brightness"])
    return Image.merge("RGBA", (*rgb.split(), a))


def fit_to_canvas(img: Image.Image, cfg: dict) -> Image.Image:
    """Вписывает персонажа во весь холст canvas×canvas с полями char_fill_margin."""
    canvas, margin = cfg["canvas"], cfg["char_fill_margin"]
    bbox = img.split()[3].getbbox()
    if bbox is None:
        raise ValueError("пустой альфа-канал")
    img = img.crop(bbox)
    avail = canvas - 2 * margin
    scale = min(avail / img.width, avail / img.height)
    nw = max(1, round(img.width * scale))
    nh = max(1, round(img.height * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    out = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    out.paste(img, ((canvas - nw) // 2, (canvas - nh) // 2))
    return out


def add_char_outline(img: Image.Image, cfg: dict) -> Image.Image:
    """Белая обводка вокруг альфа-силуэта: dilate(alpha) − alpha = кольцо.

    Накладывается уже на холсте 512×512, чтобы толщина всегда была ровно
    char_white_outline пикселей независимо от размера исходной картинки.
    """
    t = int(cfg["char_white_outline"])
    if t <= 0:
        return img
    alpha = np.array(img.split()[3])
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * t + 1, 2 * t + 1))
    dilated = cv2.dilate(alpha, kernel)
    white = Image.new("RGBA", img.size, (255, 255, 255, 0))
    white.putalpha(Image.fromarray(dilated))
    return Image.alpha_composite(white, img)


# ----------------------------------------------------------------------------
# Рендер подписи
# ----------------------------------------------------------------------------

def _font_for_cap_height(font_path: Path, cap_px: int) -> ImageFont.FreeTypeFont:
    """Подбирает кегль так, чтобы высота заглавных («ОБВГ») была ≈ cap_px."""
    base = 100
    f = ImageFont.truetype(str(font_path), base)
    left, top, right, bottom = f.getbbox("ОБВГ")
    cap_at_base = max(1, bottom - top)
    size = max(4, round(base * cap_px / cap_at_base))
    return ImageFont.truetype(str(font_path), size)


def _line_width(font: ImageFont.FreeTypeFont, text: str) -> int:
    left, _, right, _ = font.getbbox(text)
    return right - left


def _split_two_lines(words: list, font: ImageFont.FreeTypeFont) -> list:
    """Разбивает слова на 2 строки, балансируя ширины (минимакс)."""
    best, best_w = None, None
    for i in range(1, len(words)):
        l1, l2 = " ".join(words[:i]), " ".join(words[i:])
        w = max(_line_width(font, l1), _line_width(font, l2))
        if best_w is None or w < best_w:
            best, best_w = [l1, l2], w
    return best


def render_caption(text: str, cfg: dict, font_path: Path) -> Image.Image:
    """Рендерит подпись: золотой градиент + синяя обводка + белый кант.

    Рисуется в supersample-кратном разрешении и ужимается LANCZOS'ом для
    гладких краёв. Слои снизу вверх: белый кант → синяя обводка → градиент.
    """
    ss = int(cfg["supersample"])
    cap = int(cfg["cap_target"]) * ss
    max_w = int(cfg["max_line_width"]) * ss

    text = " ".join(text.split()).upper()
    font = _font_for_cap_height(font_path, cap)

    # Перенос: 1 строка → при переполнении 2 строки → при переполнении кегль ниже
    words = text.split()
    if _line_width(font, text) <= max_w or len(words) == 1:
        lines = [text]
    else:
        lines = _split_two_lines(words, font)
    widest = max(_line_width(font, ln) for ln in lines)
    if widest > max_w:
        cap = max(8, int(cap * max_w / widest))
        font = _font_for_cap_height(font_path, cap)

    navy_t = max(1, round(cfg["outline_ratio"] * cap))
    white_t = max(1, round(cfg["white_ratio"] * cap))
    pad = navy_t + white_t
    gap = round(cfg["line_gap_ratio"] * cap)

    # Маска глифов каждой строки
    line_masks = []
    for ln in lines:
        left, top, right, bottom = font.getbbox(ln)
        m = Image.new("L", (max(1, right - left), max(1, bottom - top)), 0)
        ImageDraw.Draw(m).text((-left, -top), ln, font=font, fill=255)
        line_masks.append(m)

    block_w = max(m.width for m in line_masks)
    block_h = sum(m.height for m in line_masks) + gap * (len(line_masks) - 1)
    W, H = block_w + 2 * pad, block_h + 2 * pad

    mask = Image.new("L", (W, H), 0)
    spans = []
    y = pad
    for m in line_masks:
        mask.paste(m, (pad + (block_w - m.width) // 2, y))
        spans.append((y, y + m.height))
        y += m.height + gap
    mask_np = np.array(mask)

    def dilate(arr: np.ndarray, radius: int) -> np.ndarray:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                      (2 * radius + 1, 2 * radius + 1))
        return cv2.dilate(arr, k)

    navy_a = dilate(mask_np, navy_t)            # синий силуэт
    white_a = dilate(mask_np, navy_t + white_t)  # внешний белый силуэт

    # Золотой градиент по вертикали — для каждой строки от gold_top к gold_bot
    top_c = np.array(cfg["gold_top"], np.float32)
    bot_c = np.array(cfg["gold_bot"], np.float32)
    row_color = np.tile(top_c, (H, 1))
    for y0, y1 in spans:
        t = np.linspace(0.0, 1.0, max(1, y1 - y0))[:, None]
        row_color[y0:y1] = top_c * (1 - t) + bot_c * t
        row_color[y1:] = bot_c
    gold_rgb = np.repeat(row_color[:, None, :], W, axis=1).astype(np.uint8)

    def layer(rgb: np.ndarray, alpha: np.ndarray) -> Image.Image:
        return Image.fromarray(np.dstack([rgb, alpha]), "RGBA")

    navy_rgb = np.broadcast_to(np.array(cfg["navy"], np.uint8), (H, W, 3)).copy()
    img = Image.alpha_composite(
        layer(np.full((H, W, 3), 255, np.uint8), white_a),  # белый кант
        layer(navy_rgb, navy_a),                            # синяя обводка
    )
    img = Image.alpha_composite(img, layer(gold_rgb, mask_np))  # золото

    # Против тёмной каймы при ужатии: прозрачным пикселям задаём белый цвет
    arr = np.array(img)
    arr[arr[:, :, 3] == 0, :3] = 255
    img = Image.fromarray(arr, "RGBA")

    return img.resize((max(1, round(W / ss)), max(1, round(H / ss))),
                      Image.LANCZOS)


def compose(char_img: Image.Image, caption_img, cfg: dict) -> Image.Image:
    """Кладёт подпись поверх нижней части персонажа (по центру, к низу)."""
    if caption_img is None:
        return char_img
    canvas = cfg["canvas"]
    x = (canvas - caption_img.width) // 2
    y = canvas - cfg["text_bottom_margin"] - caption_img.height
    text_layer = Image.new("RGBA", char_img.size, (0, 0, 0, 0))
    text_layer.paste(caption_img, (x, max(0, y)))
    return Image.alpha_composite(char_img, text_layer)


# ----------------------------------------------------------------------------
# Пакетный прогон
# ----------------------------------------------------------------------------

def safe_name(caption: str) -> str:
    """Подпись → безопасное имя файла: пробелы в «_», мусорные символы долой."""
    s = caption.strip().replace(" ", "_")
    s = re.sub(r"[?!,%.\u2013\u2014]", "", s)   # ? ! , % . – —
    s = re.sub(r'[\\/:*"<>|]', "", s)           # запрещённые в именах файлов
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "sticker"


def process_one(path: Path, caption: str, index: int, cfg: dict,
                font_path: Path) -> Path:
    """Полный пайплайн одной картинки; возвращает путь к готовому стикеру."""
    bgr = load_bgr(path)
    bgr = remove_watermark(bgr, cfg)
    rgba = cut_background(bgr, cfg)
    img = enhance(rgba, cfg)
    img = fit_to_canvas(img, cfg)
    img = add_char_outline(img, cfg)
    caption_img = render_caption(caption, cfg, font_path) if caption.strip() else None
    img = compose(img, caption_img, cfg)
    out_path = OUTPUT_DIR / f"{index:02d}_{safe_name(caption)}.png"
    img.save(out_path, "PNG")
    return out_path


def run_batch() -> None:
    """Обрабатывает все картинки из input/ без вопросов и подтверждений."""
    cfg = load_config()
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    font_path = ensure_font()
    captions = load_captions()

    files = sorted((p for p in INPUT_DIR.iterdir()
                    if p.suffix.lower() in IMAGE_EXTS),
                   key=lambda p: p.name.lower())
    if not files:
        print(f"В папке {INPUT_DIR} нет картинок (jpg/png/webp/bmp). "
              f"Положите файлы и запустите снова.")
        return

    ok, failed = 0, []
    for i, path in enumerate(files, start=1):
        caption = captions.get(path.name, captions.get(path.stem, path.stem))
        try:
            out = process_one(path, caption, i, cfg, font_path)
            ok += 1
            print(f"Обработано {i}/{len(files)}: {path.name} → "
                  f"{out.relative_to(BASE_DIR)}")
        except Exception as exc:  # одна ошибка не роняет весь прогон
            failed.append((path.name, exc))
            print(f"ОШИБКА {i}/{len(files)}: {path.name} — {exc}")

    print("-" * 50)
    print(f"Готово: успешно {ok}, с ошибкой {len(failed)}")
    for name, exc in failed:
        print(f"  не удалось: {name} — {exc}")


if __name__ == "__main__":
    try:  # кириллица в консоли Windows
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    run_batch()
