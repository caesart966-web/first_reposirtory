#!/usr/bin/env python3
"""
Генератор сайта.

Что делает: берёт тексты из папки data/, каркас страницы из templates/base.html
и собирает готовый сайт в папку dist/. Папка dist/ — это и есть сайт: её
содержимое заливается на хостинг или отдаётся GitHub Pages.

Запуск:
    python3 build.py                 собрать сайт
    python3 build.py --serve         собрать и открыть локально на http://localhost:8000
    python3 build.py --regen-media   перерисовать картинки-заглушки заново

Ничего устанавливать не нужно: только Python 3.8 или новее.

Как устроен файл:
    1.  Загрузка данных и мелкие помощники
    2.  Блоки страницы (шапка списка услуг, форма, вопросы и т.д.)
    3.  Разметка для поисковиков (Schema.org)
    4.  Сборка страниц
    5.  sitemap.xml, robots.txt, копирование файлов
    6.  Точка входа
"""

import argparse
import html
import json
import re
import math
import shutil
import struct
import subprocess
from datetime import date
from pathlib import Path

import genmedia

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
TPL_DIR = ROOT / "templates"
ASSETS_DIR = ROOT / "assets"
DIST_DIR = ROOT / "dist"

# Знак вставляется в страницу целиком, а не картинкой: только так он может
# наследовать цвет текста и оставаться читаемым на тёмном фоне.
LOGO_SVG = re.sub(r"<!--.*?-->", "",
                  (ASSETS_DIR / "img" / "logo.svg").read_text(encoding="utf-8"),
                  flags=re.S).strip()


# =========================================================================
# 1. Загрузка данных и помощники
# =========================================================================

def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def esc(text) -> str:
    """Экранирует текст, чтобы кавычки и угловые скобки не ломали вёрстку."""
    return html.escape(str(text), quote=True)


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", str(text))


class Site:
    """Всё, что нужно знать странице о сайте в целом."""

    def __init__(self, site: dict, services: list, legal: dict = None,
                 geo: dict = None):
        self.raw = site
        self.services = services
        self.legal = legal or {}
        self.geo = geo or {}
        self.by_slug = {s["slug"]: s for s in services}
        self.company = site["company"]
        self.contacts = site["contacts"]
        self.base_url = site["base_url"].rstrip("/")
        self.base_path = site.get("base_path", "").rstrip("/")
        self.groups = site["groups"]

        seen = set()
        for s in services:
            if s["slug"] in seen:
                raise SystemExit(f"Ошибка в data/services.json: адрес '{s['slug']}' повторяется дважды")
            seen.add(s["slug"])
            if s["group"] not in {g["id"] for g in self.groups}:
                raise SystemExit(f"Ошибка: услуга '{s['slug']}' ссылается на несуществующую группу '{s['group']}'")

    # --- адреса --------------------------------------------------------
    def url(self, path: str) -> str:
        """Внутренняя ссылка с учётом base_path (нужно для GitHub Pages)."""
        return (self.base_path + path) or "/"

    def abs_url(self, path: str) -> str:
        """Полный адрес — для canonical, sitemap и Open Graph."""
        return self.base_url + self.base_path + path

    def service_url(self, slug: str, city: str = "") -> str:
        return f"/uslugi/{slug}/{city + '/' if city else ''}"

    def services_in_group(self, group_id: str) -> list:
        return [s for s in self.services if s["group"] == group_id]


# =========================================================================
# 2. Блоки страницы
# =========================================================================

def asset_exists(rel: str) -> bool:
    """Есть ли файл в папке assets/. Путь вида /assets/media/hero.mp4."""
    if not rel:
        return False
    return (ASSETS_DIR / rel.lstrip("/").removeprefix("assets/")).exists()


def resolve_media(configured: str, fallbacks: list) -> str:
    """Берёт первый существующий файл: сначала указанный в данных, потом
    привычные имена с другими расширениями. Нужно, чтобы постер, полученный
    из видео скриптом tools/prepare-hero-video.sh, подхватился сам —
    без правки data/site.json."""
    for rel in [configured] + fallbacks:
        if asset_exists(rel):
            return rel
    return configured or fallbacks[-1]


def image_size(rel: str):
    """Ширина и высота картинки, прочитанные из заголовка файла.

    Без сторонних библиотек: у png, webp и jpeg размеры лежат в первых
    байтах. Нужны, чтобы браузер знал пропорции до загрузки и не дёргал
    вёрстку, и чтобы правильно описать варианты в srcset.
    Не смог прочитать — вернём None, страница соберётся и без размеров."""
    path = ASSETS_DIR / rel.lstrip("/").removeprefix("assets/")
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        kind = data[12:16]
        if kind == b"VP8X":
            return (int.from_bytes(data[24:27], "little") + 1,
                    int.from_bytes(data[27:30], "little") + 1)
        if kind == b"VP8 ":
            return (int.from_bytes(data[26:28], "little") & 0x3FFF,
                    int.from_bytes(data[28:30], "little") & 0x3FFF)
        if kind == b"VP8L":
            bits = int.from_bytes(data[21:25], "little")
            return ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
    if data[:2] == b"\xff\xd8":                      # jpeg: идём по сегментам
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                break
            marker, length = data[i + 1], int.from_bytes(data[i + 2:i + 4], "big")
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                return (int.from_bytes(data[i + 7:i + 9], "big"),
                        int.from_bytes(data[i + 5:i + 7], "big"))
            i += 2 + length
    return None


# Ширины уменьшенных копий, которые делает tools/make-thumbs.py
THUMB_WIDTHS = (480, 960)


def photo_img(site: Site, rel: str, alt: str, sizes: str, css: str = "") -> str:
    """Фотография с уменьшенными копиями и отложенной загрузкой.

    Браузер сам берёт вариант под ширину экрана: телефону уходит копия
    на 480 точек вместо снимка на 1600. Форматов два: сначала предлагается
    AVIF (легче примерно на четверть), а кто его не понимает — берёт webp.
    Копий нет — отдаём оригинал, вёрстка от этого не зависит."""
    base, _, ext = rel.rpartition(".")
    size = image_size(rel)

    def row(fmt: str):
        """Строка вариантов одного формата: «файл 480w, файл 960w»."""
        got = [(w, f"{base}-{w}.{fmt}") for w in THUMB_WIDTHS
               if asset_exists(f"{base}-{w}.{fmt}")]
        if fmt == "webp" and size and (not got or size[0] > got[-1][0]):
            got.append((size[0], rel))      # оригинал — самый крупный вариант
        return got

    webp = row("webp")
    avif = row("avif")
    src = site.url(webp[-1][1] if webp else rel)
    dims = f' width="{size[0]}" height="{size[1]}"' if size else ""
    cls = f' class="{css}"' if css else ""
    pairs = lambda got: ", ".join(f"{site.url(p)} {w}w" for w, p in got)
    srcset = f' srcset="{pairs(webp)}" sizes="{sizes}"' if len(webp) > 1 else ""
    img = (f'<img{cls} src="{src}"{srcset}{dims} alt="{esc(alt)}"'
           f' loading="lazy" decoding="async">')
    if len(avif) > 1:
        return ('<picture>'
                f'<source type="image/avif" srcset="{pairs(avif)}" sizes="{sizes}">'
                f'{img}</picture>')
    return img


def poster_img(site: Site, rel: str, css: str) -> str:
    """Кадр под видео — тегом picture, а не фоном в стилях.

    Так браузер скачивает ровно один файл: понимает avif — берёт его
    (он вдвое легче), не понимает — берёт webp. С фоном в стилях
    приходилось писать两 строки, и Chrome качал обе картинки."""
    avif = rel.rsplit(".", 1)[0] + ".avif"
    source = (f'<source type="image/avif" srcset="{site.url(avif)}">'
              if asset_exists(avif) else "")
    size = image_size(rel)
    dims = f' width="{size[0]}" height="{size[1]}"' if size else ""
    return (f'<picture>{source}<img class="{css}" src="{site.url(rel)}"{dims}'
            f' alt="" fetchpriority="high" decoding="async"></picture>')


def block_media(site: Site, cfg: dict) -> str:
    """Широкая видео-полоса. Ведёт себя как первый экран: постер виден сразу,
    видео подключается скриптом после загрузки страницы. Если файлов видео нет,
    остаётся постер — блок не ломается."""
    if not cfg:
        return ""
    poster_rel = resolve_media(cfg.get("poster"), [])
    poster = site.url(poster_rel)
    sources = "|".join(site.url(cfg[k]) for k in ("webm", "mp4") if asset_exists(cfg.get(k)))
    mobile = "/assets/media/about-mobile.mp4"
    mob_attr = f' data-src-mobile="{site.url(mobile)}"' if asset_exists(mobile) else ""
    video = (f'''<video class="media-band__video js-video" autoplay muted loop playsinline
             preload="none" data-src="{sources}"{mob_attr}
             aria-hidden="true" tabindex="-1"></video>''' if sources else "")
    caption = (f'<figcaption class="media-band__caption">{esc(cfg["caption"])}</figcaption>'
               if cfg.get("caption") else "")
    return f'''  <section class="section section--tight">
    <div class="container">
      <figure class="media-band">{poster_img(site, poster_rel, "media-band__img")}
        {video}
        {caption}
      </figure>
    </div>
  </section>'''


def map_point(site: Site, lon: float, lat: float):
    """Широта и долгота — в координаты карты. Проекция та же, по которой
    построен контур (Альберс, параллели 52° и 64°, меридиан 100° в. д.),
    поэтому метка не может разойтись с картой: числа в единицах карты
    руками нигде не пишутся."""
    p = site.geo["projection"]
    n = (math.sin(math.radians(p["lat1"])) + math.sin(math.radians(p["lat2"]))) / 2
    c = math.cos(math.radians(p["lat1"])) ** 2 + 2 * n * math.sin(math.radians(p["lat1"]))
    rho0 = math.sqrt(c - 2 * n * math.sin(math.radians(p["lat0"]))) / n
    if lon < 0:
        lon += 360
    rho = math.sqrt(max(c - 2 * n * math.sin(math.radians(lat)), 0.0)) / n
    theta = math.radians(n * (lon - p["lon0"]))
    px, py = rho * math.sin(theta), rho0 - rho * math.cos(theta)
    return ((px - p["minx"]) * p["scale"] + p["pad"],
            (p["maxy"] - py) * p["scale"] + p["pad"])


def block_geo(site: Site) -> str:
    """Карта «Географические зоны наших объектов».

    Города и число объектов берутся из списка объектов, а не пишутся здесь:
    иначе карта и карточки разойдутся ровно в тот день, когда объект добавят
    или уберут. Координаты — в data/site.json → geo_map.cities.

    Карта нарисована SVG, а не картинкой: она резкая на любом экране,
    весит меньше фотографии и перекрашивается вместе с темой сайта."""
    cfg = site.raw.get("geo_map")
    if not cfg or not site.geo:
        return ""
    items = site.raw["portfolio"]["items"]
    counted = {}
    for o in items:
        counted[o["city"]] = counted.get(o["city"], 0) + 1

    unknown = [c for c in counted if c not in cfg["cities"]]
    if unknown:
        # Город без координат молча пропал бы с карты, а карточка осталась.
        print(f"  ВНИМАНИЕ: нет координат для города на карте: {', '.join(unknown)}"
              f"\n  впишите их в data/site.json -> geo_map.cities")

    marks, legend = [], []
    for city, count in sorted(counted.items(), key=lambda kv: -kv[1]):
        point = cfg["cities"].get(city)
        if not point:
            continue
        x, y = map_point(site, point["lon"], point["lat"])
        word = "объект" if count % 10 == 1 and count % 100 != 11 else (
               "объекта" if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14)
               else "объектов")
        # Подпись — справа от точки. Сдвиг и сторону можно задать в настройках
        # города (label_dx, label_dy, label_anchor: "end" — подпись слева):
        # Тверь, Завидово и Москва на карте страны стоят почти в одной точке,
        # и без разноса их подписи наезжают друг на друга.
        dx = point.get("label_dx", 11)
        dy = point.get("label_dy", 4)
        marks.append(
            f'<g class="geo__mark"><circle class="geo__halo" cx="{x:.1f}" cy="{y:.1f}" r="13"/>'
            f'<circle class="geo__dot" cx="{x:.1f}" cy="{y:.1f}" r="5"/>'
            f'<text class="geo__label" x="{x + dx:.1f}" y="{y + dy:.1f}"'
            f' text-anchor="{point.get("label_anchor", "start")}">{esc(city)}</text>'
            f'<title>{esc(city)} — {count} {word}</title></g>')
        legend.append(
            f'<li class="geo__item"><span class="geo__city">{esc(city)}</span>'
            f'<span class="geo__dots"></span>'
            f'<span class="geo__count">{count} {word}</span></li>')

    grid = "".join(f'<path d="{g}"/>' for g in site.geo.get("grid", []))
    return f'''  <section class="section section--dark geo" id="geografiya">
    <div class="container">
      <div class="section__head">
        <span class="section__tag">География</span>
        <h2>{esc(cfg["title"])}</h2>
        <p class="lead">{esc(cfg["lead"])}</p>
      </div>
      <div class="geo__grid">
        <div class="geo__map">
          <svg viewBox="{esc(site.geo["view_box"])}" role="img"
               aria-label="Карта России: города, в которых стоят объекты"
               preserveAspectRatio="xMidYMid meet">
            <g class="geo__lines">{grid}</g>
            <path class="geo__land" d="{site.geo["country"]}"/>
            {"".join(marks)}
          </svg>
        </div>
        <ul class="geo__legend">
          {"".join(legend)}
        </ul>
      </div>
    </div>
  </section>'''


def block_recommendations(site: Site, cfg: dict) -> str:
    """Рекомендательные письма и награды. У карточки без поля file ссылки нет —
    так документ можно показать текстом, не выкладывая сам файл.

    Подписи строк можно переопределить (role_label, object_label, link_label):
    у письма от компании это «Роль» и «Объект», а у благодарности от ведомства —
    «Кому» и «Подписал». Одна вёрстка, разные подписи."""
    if not cfg or not cfg.get("items"):
        return ""
    cards = []
    for r in cfg["items"]:
        # Письмо открывается картинкой во всплывающем окне. Ссылка на исходный
        # PDF остаётся внутри окна — для тех, кому нужен сам документ.
        link = ""
        thumb = ""
        if r.get("image") and asset_exists(r["image"]):
            pdf = (f' data-pdf="{site.url(r["file"])}"'
                   if r.get("file") and asset_exists(r["file"]) else "")
            opens = (f' data-lightbox="{site.url(r["image"])}"'
                     f' data-caption="{esc(r["company"])} · {esc(r["city"])}, {esc(r["date"])}"'
                     f'{pdf}')
            link = (f'<button class="rec__link" type="button"{opens}>'
                    f'{esc(r.get("link_label", "Посмотреть письмо"))}</button>')
            # Превьюшка самого документа: видно, что это настоящее письмо
            # с печатью и подписью, ещё до того как его открыли.
            thumb = (f'<button class="rec__thumb" type="button"{opens}'
                     f' aria-label="Открыть документ: {esc(r["company"])}">'
                     + photo_img(site, r["image"], f'Документ: {r["company"]}',
                                 "(max-width: 720px) 96px, 132px", "rec__thumb-img")
                     + '</button>')
        cards.append(f'''        <article class="card rec{" rec--doc" if thumb else ""}">
          {thumb}
          <div class="rec__body">
          <div class="rec__head">
            <h3>{esc(r["company"])}</h3>
            <span class="rec__meta">{esc(r["city"])} · {esc(r["date"])}</span>
          </div>
          <blockquote class="rec__quote">{esc(r["quote"])}</blockquote>
          <div class="spec">
            <div class="spec__row"><span class="spec__key">{esc(r.get("role_label", "Роль"))}</span>
              <span class="spec__dots"></span><span class="spec__val">{esc(r["role"])}</span></div>
            <div class="spec__row"><span class="spec__key">{esc(r.get("object_label", "Объект"))}</span>
              <span class="spec__dots"></span><span class="spec__val">{esc(r["object"])}</span></div>
          </div>
          <p class="rec__scope">{esc(r["scope"])}</p>
          {link}
          </div>
        </article>''')

    head = f'<h2>{esc(cfg["title"])}</h2>'
    if cfg.get("lead"):
        head += f'<p>{esc(cfg["lead"])}</p>'
    return f'''  <section class="section">
    <div class="container">
      <div class="section__head">{head}</div>
      <div class="grid grid--2">
{chr(10).join(cards)}
      </div>
    </div>
  </section>'''


def block_objects(site: Site, items, limit: int = 0, level: str = "h3") -> str:
    """Карточки объектов. Фотография необязательна: без неё выводится
    фирменная заставка с чертёжной сеткой, вёрстка не ломается.

    level — уровень заголовка карточки. На главной блок стоит под своим h2,
    поэтому карточки идут h3. На странице «Объекты» промежуточного h2 нет,
    и карточки должны быть h2: иначе уровни перескакивают через один, а это
    сбивает и экранные дикторы, и поисковых роботов."""
    if not items:
        return ""
    shown = items[:limit] if limit else items
    # Ритм страницы: первая карточка — во всю ширину, с фотографией слева.
    # Если после неё в последнем ряду остаётся одна штука, широкой делается
    # и она: ряд из одной узкой карточки выглядит обрывком.
    wide = set()
    if not limit and len(shown) >= 4:
        wide.add(0)
        if (len(shown) - 1) % 3 == 1:
            wide.add(len(shown) - 1)
    cards = []
    for n, o in enumerate(shown, start=1):
        # Фотографии ищутся по имени: <slug>.webp — главная, <slug>-2.webp,
        # <slug>-3.webp и далее — дополнительные. Достаточно положить файлы
        # с нужными именами, данные править не нужно.
        photos = []
        if o.get("photo") and asset_exists(o["photo"]):
            photos.append(o["photo"])
        if o.get("slug"):
            for n_photo in range(1, 13):
                suffix = "" if n_photo == 1 else f"-{n_photo}"
                for ext in (".webp", ".jpg", ".jpeg", ".png"):
                    candidate = f'/assets/img/objects/{o["slug"]}{suffix}{ext}'
                    if asset_exists(candidate) and candidate not in photos:
                        photos.append(candidate)
                        break

        # Ширина карточки: во всю ширину экрана на телефоне, половина на
        # планшете, треть на компьютере. По ней браузер выбирает копию.
        sizes = ("(max-width: 720px) calc(100vw - 2.5rem), (max-width: 1020px) 46vw, 31vw"
                 if (n - 1) not in wide else
                 "(max-width: 720px) calc(100vw - 2.5rem), 56vw")
        alt = f'{o["name"]}, {o["city"]}'
        if not photos:
            media = '<div class="object__media object__media--empty"></div>'
        elif len(photos) == 1:
            media = ('<div class="object__media">'
                     + photo_img(site, photos[0], alt, sizes, "object__img")
                     + '</div>')
        else:
            # Несколько фотографий — плитка становится кнопкой, открывающей галерею.
            # Полные снимки грузятся только при открытии, в карточке — уменьшенная копия.
            gallery = json.dumps([site.url(x) for x in photos], ensure_ascii=False)
            media = (f'<button class="object__media object__media--more" type="button"'
                     f' data-gallery="{esc(gallery)}"'
                     f' data-caption="{esc(o["name"])} · {esc(o["city"])}">'
                     + photo_img(site, photos[0], alt, sizes, "object__img")
                     + f'<span class="object__count">{len(photos)} фото</span></button>')
        scope = f'<p class="object__scope">{esc(o["scope"])}</p>' if o.get("scope") else ""

        # Нижняя часть карточки — паспорт объекта: разделы документации,
        # застройщик и наш заказчик. Одинаковый на главной и на странице
        # «Объекты». Раньше на главной стоял сокращённый вид (описание
        # в четыре строки, из паспорта только заказчик), и заказчик
        # принял его за старые описания: одна и та же карточка в двух
        # местах сайта обязана выглядеть одинаково.
        rows = []
        clients = o.get("clients") or ([o["client"]] if o.get("client") else [])
        if o.get("sections"):
            rows.append(("Разделы", o["sections"]))
        if o.get("developer"):
            rows.append(("Застройщик", o["developer"]))
        # «Наш заказчик» — только там, где заказчик это подтвердил в новом
        # формате (поле clients). У объекта со старым полем client роль
        # компании неизвестна: там стоит просто «Заказчик», чтобы сайт
        # не приписал ей роль, которой у неё, возможно, не было.
        first_label = "Наш заказчик" if o.get("clients") else "Заказчик"
        for i, c in enumerate(clients):
            # Подпись не повторяется у второго заказчика: два одинаковых
            # слова подряд читаются как ошибка вёрстки, а не как список.
            rows.append((first_label if i == 0 else "", c))
        spec = "".join(
            f'<div class="spec__row spec__row--cont">'
            f'<span class="spec__val">{esc(val)}</span></div>'
            if not key else
            f'<div class="spec__row"><span class="spec__key">{esc(key)}</span>'
            f'<span class="spec__dots"></span>'
            f'<span class="spec__val">{esc(val)}</span></div>'
            for key, val in rows)
        spec = f'<div class="spec">{spec}</div>' if spec else ""

        css = "object object--wide" if (n - 1) in wide else "object"
        cards.append(f'''        <article class="{css}">
          {media}
          <div class="object__body">
            <span class="object__num">{n:02d}</span>
            <{level} class="object__name">{esc(o["name"])}</{level}>
            <span class="object__city">{esc(o["city"])}</span>
            {scope}
            {spec}
          </div>
        </article>''')
    return f'''      <div class="object-grid">
{chr(10).join(cards)}
      </div>'''


def paragraphs(text, css="") -> str:
    """Текст в абзацы. В данных можно писать как одной строкой, так и списком
    строк — тогда каждая строка станет отдельным абзацем."""
    items = text if isinstance(text, list) else [text]
    cls = f' class="{css}"' if css else ""
    return "\n".join(f"<p{cls}>{esc(t)}</p>" for t in items if str(t).strip())


def li_list(items, css="ticks") -> str:
    body = "\n".join(f"      <li>{esc(i)}</li>" for i in items)
    return f'<ul class="{css}">\n{body}\n    </ul>'


def block_services_by_group(site: Site, level: str = "h3") -> str:
    """Четыре группы услуг со ссылками — используется на главной и в /uslugi/.

    level — уровень заголовка группы: под общим h2 (главная) это h3,
    а на странице «Услуги», где промежуточного h2 нет, — h2."""
    parts = []
    for n, group in enumerate(site.groups, start=1):
        items = []
        for s in site.services_in_group(group["id"]):
            items.append(
                f'''        <a class="service-item" href="{site.url(site.service_url(s["slug"]))}">
          <span class="service-item__title">{esc(s["nav_title"])}</span>
          <span class="service-item__text">{esc(s["short"])}</span>
        </a>'''
            )
        total = len(site.groups)
        parts.append(f'''    <div class="group">
      <div class="group__head" data-index="{n:02d}">
        <span class="group__num">Группа {n:02d} / {total:02d}</span>
        <{level} class="group__title">{esc(group["title"])}</{level}>
        <p class="group__subtitle">{esc(group["subtitle"])}</p>
      </div>
      <div class="service-list">
{chr(10).join(items)}
      </div>
    </div>''')
    return "\n".join(parts)


def block_faq(items, title="Частые вопросы", dark=False) -> str:
    """Блок вопросов и ответов. Разметка FAQPage добавляется отдельно, в head."""
    rows = []
    for it in items:
        rows.append(f'''      <details class="faq__item">
        <summary class="faq__q">{esc(it["q"])}</summary>
        <div class="faq__a"><p>{esc(it["a"])}</p></div>
      </details>''')
    css = "section section--alt" if not dark else "section section--dark"
    return f'''  <section class="{css}">
    <div class="container">
      <div class="section__head"><h2>{esc(title)}</h2></div>
      <div class="faq">
{chr(10).join(rows)}
      </div>
    </div>
  </section>'''


def block_steps(steps, title, text="", columns=3, dark=False) -> str:
    cards = []
    for st in steps:
        cards.append(f'''        <div class="step">
          <h3>{esc(st["title"])}</h3>
          <p>{esc(st["text"])}</p>
        </div>''')
    head = f"<h2>{esc(title)}</h2>"
    if text:
        head += f"<p>{esc(text)}</p>"
    css = "section section--dark" if dark else "section"
    return f'''  <section class="{css}">
    <div class="container">
      <div class="section__head">{head}</div>
      <div class="steps steps--{columns}">
{chr(10).join(cards)}
      </div>
    </div>
  </section>'''


def block_form(site: Site, preselect: str = "") -> str:
    """Форма заявки. Стоит на каждой странице, якорь #zayavka."""
    form_cfg = site.raw["form"]
    c = site.contacts
    consent_url = site.legal.get("policy", {}).get("slug", "/politika/")

    options = ['<option value="">— не важно / несколько услуг —</option>']
    for s in site.services:
        sel = " selected" if s["nav_title"] == preselect else ""
        options.append(f'<option value="{esc(s["nav_title"])}"{sel}>{esc(s["nav_title"])}</option>')

    max_line = ""
    if c.get("max_url"):
        max_line = (f'''<div class="contact-line">
              <span class="contact-line__label">MAX</span>
              <a class="contact-line__value" href="{esc(c["max_url"])}" rel="nofollow noopener" target="_blank">{esc(c.get("max_display", "Канал"))}</a>
            </div>''')

    return f'''  <section class="section form-block" id="zayavka">
    <div class="container">
      <div class="form-grid">
        <div class="section__head" style="max-width:none;margin-bottom:0">
          <h2>{esc(form_cfg["title"])}</h2>
          <p class="lead">{esc(form_cfg["text"])}</p>
          <div class="contact-lines">
            <div class="contact-line">
              <span class="contact-line__label">Телефон</span>
              <a class="contact-line__value" href="tel:{esc(c["phone_href"])}">{esc(c["phone_display"])}</a>
            </div>
            <div class="contact-line">
              <span class="contact-line__label">Почта</span>
              <a class="contact-line__value" href="mailto:{esc(c["email"])}">{esc(c["email"])}</a>
            </div>
            <div class="contact-line">
              <span class="contact-line__label">Telegram</span>
              <a class="contact-line__value" href="{esc(c["telegram_url"])}" rel="nofollow noopener" target="_blank">{esc(c["telegram_display"])}</a>
            </div>
            {max_line}
            <div class="contact-line">
              <span class="contact-line__label">Режим работы</span>
              <span class="contact-line__value" style="font-size:1rem;font-weight:500">{esc(c["work_hours"])}</span>
            </div>
          </div>
        </div>

        <form class="form" data-form="lead" novalidate
              data-success="{esc(form_cfg["success"])}"
              data-error="{esc(form_cfg["error"])}"
              data-mail="{esc(site.contacts["email"])}"
              data-tel="{esc(site.contacts["phone_href"])}"
              data-tel-display="{esc(site.contacts["phone_display"])}"
              data-tg="{esc(site.contacts["telegram_url"])}">
          <div class="field">
            <label for="f-name">Как к вам обращаться <span class="req">*</span></label>
            <input id="f-name" name="name" type="text" autocomplete="name" required>
            <span class="field__error"></span>
          </div>
          <div class="field">
            <label for="f-phone">Телефон <span class="req">*</span></label>
            <input id="f-phone" name="phone" type="tel" inputmode="tel" autocomplete="tel" required
                   placeholder="+7 ___ ___-__-__">
            <span class="field__error"></span>
          </div>
          <div class="field">
            <label for="f-service">Услуга или тип объекта</label>
            <select id="f-service" name="service">
              {chr(10).join("              " + o for o in options).strip()}
            </select>
          </div>
          <div class="field">
            <label for="f-comment">Коротко о задаче</label>
            <textarea id="f-comment" name="comment" rows="3"
                      placeholder="Объект, что нужно сделать, к какой дате"></textarea>
          </div>
          <div class="hp" aria-hidden="true">
            <label for="f-company">Не заполняйте это поле</label>
            <input id="f-company" name="company" type="text" tabindex="-1" autocomplete="off">
          </div>
          <div class="field field--consent">
            <label class="consent">
              <input id="f-consent" name="consent" type="checkbox" required>
              <span class="consent__box" aria-hidden="true"></span>
              <span class="consent__text">{esc(form_cfg["consent"])}
                <a href="{site.url(consent_url)}#soglasie" target="_blank" rel="noopener">{esc(form_cfg["consent_link"])}</a>.</span>
            </label>
            <span class="field__error"></span>
          </div>
          <div class="form__status" role="status"></div>
          <button class="btn btn--primary btn--block" type="submit">Отправить заявку</button>
          <p class="form__note">{esc(form_cfg["note"])}</p>
        </form>
      </div>
    </div>
  </section>'''


# Значки для карточек контактов. Рисуем линиями в один цвет (currentColor),
# поэтому они сами перекрашиваются при наведении и в тёмной теме.
ICONS = {
    "phone": '<path d="M4 3h3l1.6 4-2 1.4a12 12 0 0 0 5 5L13 11.4 17 13v3a1.6 1.6 0 0 1-1.8 1.6A14.4 14.4 0 0 1 2.4 4.8 1.6 1.6 0 0 1 4 3z"/>',
    "mail": '<rect x="2.2" y="4.2" width="15.6" height="11.6" rx="1.6"/><path d="m2.8 5.4 7.2 5.2 7.2-5.2"/>',
    "chat": '<path d="M17 11.2A3.8 3.8 0 0 1 13.2 15H7l-4 2.6V5.2A3.8 3.8 0 0 1 6.8 1.4h6.4A3.8 3.8 0 0 1 17 5.2z" transform="translate(0 1)"/>',
    "link": '<path d="M8.4 11.6a3.4 3.4 0 0 0 5 .3l2.4-2.4a3.4 3.4 0 0 0-4.8-4.8l-1.3 1.3"/><path d="M11.6 8.4a3.4 3.4 0 0 0-5-.3L4.2 10.5a3.4 3.4 0 0 0 4.8 4.8l1.3-1.3"/>',
}


def icon(name: str) -> str:
    return (f'<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


def contact_cards(site: Site) -> str:
    """Четыре способа связи карточками — на странице контактов."""
    c = site.contacts
    notes = site.raw["contacts_page"].get("notes", {})
    ext = ' rel="nofollow noopener" target="_blank"'
    rows = [
        ("phone", "Телефон", c["phone_display"], f'tel:{c["phone_href"]}', "", " contact-card--phone"),
        ("mail", "Почта", c["email"], f'mailto:{c["email"]}', "", ""),
        ("chat", "Telegram", c["telegram_display"], c["telegram_url"], ext, ""),
        ("link", "MAX", c.get("max_display", "Канал"), c["max_url"], ext, ""),
    ]
    keys = ["phone", "email", "telegram", "max"]
    cards = []
    for (ic, label, value, href, attrs, extra), key in zip(rows, keys):
        note = notes.get(key, "")
        cards.append(f'''        <a class="contact-card{extra}" href="{esc(href)}"{attrs}>
          <span class="contact-card__icon">{icon(ic)}</span>
          <span class="contact-card__label">{esc(label)}</span>
          <span class="contact-card__value">{esc(value)}</span>
          {f'<span class="contact-card__note">{esc(note)}</span>' if note else ''}
        </a>''')
    return f'''      <div class="contact-grid">
{chr(10).join(cards)}
      </div>'''


def block_related(site: Site, service: dict) -> str:
    cards = []
    for slug in service.get("related", []):
        rel = site.by_slug.get(slug)
        if not rel:
            raise SystemExit(f"Ошибка: услуга '{service['slug']}' ссылается на несуществующую '{slug}'")
        cards.append(f'''        <a class="card card--link card--compact" href="{site.url(site.service_url(slug))}">
          <h3>{esc(rel["nav_title"])}</h3>
          <p>{esc(rel["short"])}</p>
        </a>''')
    if not cards:
        return ""
    return f'''  <section class="section">
    <div class="container">
      <div class="section__head"><h2>Смежные услуги</h2></div>
      <div class="grid grid--{min(len(cards), 4)}">
{chr(10).join(cards)}
      </div>
    </div>
  </section>'''


# =========================================================================
# 3. Разметка для поисковиков (Schema.org)
# =========================================================================

def jsonld(obj) -> str:
    return ('<script type="application/ld+json">'
            + json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            + "</script>")


def sro_logo(site: Site) -> str:
    """Логотип СРО, если файл положили в assets/img/ под именем sro-logo
    (svg, png или webp). Нет файла — вместо логотипа рисуется печать
    с сокращением, и это не ошибка: так значок работает до того, как
    логотип прислали."""
    for ext in ("svg", "webp", "png"):
        rel = f"/assets/img/sro-logo.{ext}"
        if asset_exists(rel):
            return rel
    return ""


def hero_sro(site: Site) -> str:
    """Значок членства в СРО на первом экране главной.

    Первый экран — единственное место, которое видят все посетители,
    и для подрядчика членство в СРО — главный довод «с ним можно
    работать». Значок короткий: знак, одна строка и реестровый номер;
    полное название и вид СРО — по ссылке, в блоке на странице
    «О компании». Нет данных в настройках — значка нет вовсе."""
    sro = site.company.get("sro")
    if not sro or not sro.get("name"):
        return ""
    short = esc(sro.get("short", ""))
    kind = {"проектирование": "проектировщиков", "строительство": "строителей",
            "изыскания": "изыскателей"}.get(sro.get("kind", ""), "")
    title = f"Член СРО {kind} «{short}»".replace("  ", " ")
    # Номер целиком в неразрывном блоке: разорванный на «СРО-П-116-»
    # и «18012010» он перестаёт читаться как номер, а по нему ищут в реестре.
    reg = (f'<span class="hero-sro__reg">рег. № <span class="nowrap">{esc(sro["reg"])}</span></span>'
           if sro.get("reg") else "")
    logo = sro_logo(site)
    if logo:
        # Настоящий логотип СРО — на белой плашке: он нарисован под светлый
        # фон, и на тёмном первом экране без подложки его золото тонет.
        mark = (f'<span class="hero-sro__logo" aria-hidden="true">'
                f'<img src="{site.url(logo)}" alt="" width="96" height="56" decoding="async"></span>')
    else:
        # Пока файла логотипа нет — круглая печать с сокращением.
        mark = (f'<span class="hero-sro__seal" aria-hidden="true">'
                f'<svg viewBox="0 0 64 64"><circle class="hero-sro__ring" cx="32" cy="32" r="29"/></svg>'
                f'<span>{short}</span></span>')
    return f'''        <a class="hero-sro" href="{site.url('/o-kompanii/')}#sro"
           aria-label="{esc(title)}. Подробнее о членстве в СРО">
          {mark}
          <span class="hero-sro__text">
            <span class="hero-sro__title">{esc(title)}</span>
            {reg}
          </span>
          <svg class="hero-sro__arrow" viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10h11M11 5.5 15.5 10 11 14.5"/></svg>
        </a>'''


def sro_block(site: Site, dark: bool = True) -> str:
    """Членство в СРО. Не строчка мелким шрифтом внизу, а отдельная панель
    со знаком: для подрядчика это допуск к работе, и заказчик ищет его
    первым делом. Номер — регистрационный номер самой СРО в государственном
    реестре: по нему организацию можно найти и проверить, и это единственная
    причина, по которой номер вообще стоит на сайте.
    Нет данных в настройках — блока нет вовсе."""
    sro = site.company.get("sro")
    if not sro or not sro.get("name"):
        return ""
    short = esc(sro.get("short", ""))
    reg = (f'''<div class="sro__row">
          <span class="sro__key">Реестровый номер</span>
          <span class="sro__num">{esc(sro["reg"])}</span>
        </div>''' if sro.get("reg") else "")
    kind = (f'''<div class="sro__row">
          <span class="sro__key">Вид</span>
          <span class="sro__kind">{esc(sro.get("kind", ""))}{", " + esc(sro["city"]) if sro.get("city") else ""}</span>
        </div>''' if sro.get("kind") else "")
    anchor = "" if dark else ' id="sro"'
    logo = sro_logo(site)
    mark = (f'<div class="sro__logo" aria-hidden="true">'
            f'<img src="{site.url(logo)}" alt="" width="120" height="70" loading="lazy" decoding="async"></div>'
            if logo else
            f'<div class="sro__seal" aria-hidden="true"><span>{short}</span></div>')
    return f'''<div class="sro{' sro--dark' if dark else ''}"{anchor}>
      {mark}
      <div class="sro__body">
        <span class="sro__label">Член саморегулируемой организации</span>
        <p class="sro__name">{esc(sro["name"])}</p>
        {reg}
        {kind}
      </div>
    </div>'''


def cookie_bar(site: Site) -> str:
    """Полоса про cookie — и одновременно единственный выключатель Метрики.

    Счётчик подключается ИЗ этого скрипта после нажатия «Принять», а не
    стоит в разметке: до выбора посетителя к Яндексу не уходит ни одного
    запроса. Полоса показывается, только когда счётчик вообще настроен —
    без него сайт не ставит ни одного файла cookie, и полоса «сайт
    использует cookie» была бы ровно тем враньём мелким шрифтом, против
    которого написана вся политика.

    Выбор хранится в localStorage, а не в cookie: хранить согласие
    на cookie в cookie до получения согласия — замкнутый круг."""
    mid = site.raw.get("seo", {}).get("metrika_id", "").strip()
    if not mid:
        return ""
    policy = site.url(site.legal.get("policy", {}).get("slug", "/politika/"))
    return f'''<div class="cookie" id="cookie-bar" hidden data-metrika="{esc(mid)}">
  <p class="cookie__text">Мы считаем посещения страниц, чтобы понимать, какие из них
    полезны. Для этого нужны файлы cookie. Подробности —
    <a href="{policy}#razdel-15">в политике обработки данных</a>.</p>
  <div class="cookie__row">
    <button class="btn btn--primary btn--sm" type="button" data-cookie="all">Принять</button>
    <button class="btn btn--ghost btn--sm" type="button" data-cookie="none">Только необходимые</button>
  </div>
</div>'''


# Короткие слова, после которых строка обрываться не должна. Предлог
# или союз, повисший в конце строки, — самая заметная разница между
# «набрано» и «свёрстано».
#
# В списке ТОЛЬКО предлоги, союзы и частицы. Местоимения и вопросительные
# слова («их», «это», «как», «что») сюда не входят нарочно: они полноценные
# слова, и связывать их с соседним значит делать длинные неразрывные куски,
# которые на экране в 360 px вылезают за край. Список закрытый — гнать
# неразрывный пробел после любого короткого слова нельзя.
SHORT_WORDS = (
    "а и о у в к с я не ни но да же ли бы во со ко об от до из за на по "
    "для при над под без про или меж"
).split()
_SHORT_RE = re.compile(
    r"(?<![\w\u0400-\u04FF])(" + "|".join(SHORT_WORDS) + r") +(?=[\w\u0400-\u04FF«(])",
    re.IGNORECASE)
# Сокращение с точкой перед числом: «ст. 18.1», «д. 7», «№ 152»
_ABBR_RE = re.compile(r"(\b[а-яё]{1,4}\.|№) +(?=[\d«])", re.IGNORECASE)
# Число и то, что к нему относится: «1200 ₽», «14 КБ», «5 лет»
_UNIT_RE = re.compile(r"(\d) +(?=[%‰₽°]|[а-яё]{1,4}[.,)]?(?![\w\u0400-\u04FF]))")
_NBSP = "\u00a0"


def typo_ru(page: str) -> str:
    """Русская типографика: неразрывные пробелы там, где перенос строки
    выглядит ошибкой набора.

    Работает по готовой странице и трогает ТОЛЬКО текст между тегами:
    внутрь самих тегов не заглядывает вовсе, поэтому не может испортить
    ни адрес ссылки, ни имя класса. Содержимое <script>, <style> и <pre>
    пропускается целиком — там пробелы значащие."""
    out = []
    skip = 0
    for chunk in re.split(r"(<[^>]*>)", page):
        if chunk.startswith("<"):
            name = re.match(r"</?\s*(script|style|pre|textarea)\b", chunk, re.I)
            if name:
                skip += 1 if not chunk.startswith("</") else -1
                skip = max(skip, 0)
            out.append(chunk)
            continue
        if skip or not chunk.strip():
            out.append(chunk)
            continue
        text = chunk
        text = _SHORT_RE.sub(lambda m: m.group(1) + _NBSP, text)
        text = _ABBR_RE.sub(lambda m: m.group(1) + _NBSP, text)
        text = _UNIT_RE.sub(lambda m: m.group(1) + _NBSP, text)
        # Тире не должно начинать строку: оно остаётся с предыдущим словом.
        text = text.replace(" —", _NBSP + "—")
        out.append(text)
    return "".join(out)


def og_for(path: str) -> str:
    """Своя обложка страницы для соцсетей, если она нарисована
    инструментом tools/make-og.py. Имя файла повторяет адрес страницы:
    /uslugi/geodeziya/ -> uslugi-geodeziya.jpg. Нет файла — страница
    возьмёт общую картинку, и это не ошибка."""
    name = "-".join(p for p in path.strip("/").split("/") if p) or "home"
    if name.endswith(".html"):
        return ""
    rel = f"/assets/img/og/{name}.jpg"
    return rel if asset_exists(rel) else ""


def verification_tags(site: Site) -> str:
    """Коды подтверждения прав на сайт в Яндекс.Вебмастере и Google.
    Пустая строка = не подключено, и тега нет вовсе: пустой content
    Вебмастер считает неверным кодом и подтверждение не проходит."""
    seo = site.raw.get("seo", {})
    out = []
    if seo.get("yandex_verification"):
        out.append(f'<meta name="yandex-verification" content="{esc(seo["yandex_verification"])}">')
    if seo.get("google_verification"):
        out.append(f'<meta name="google-site-verification" content="{esc(seo["google_verification"])}">')
    return "\n".join(out)


def schema_organization(site: Site) -> dict:
    c = site.contacts
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "@id": site.abs_url("/") + "#organization",
        "name": site.company["name"],
        "legalName": site.company.get("legal_name", site.company["name"]),
        "description": site.company["about_short"],
        "url": site.abs_url("/"),
        "logo": site.abs_url("/assets/img/logo.svg"),
        "image": site.abs_url(site.raw.get("og_image", "/assets/img/og-default.jpg")),
        # sameAs — официальные страницы компании в других сервисах. По ним
        # поисковик связывает сайт, канал в Telegram и канал в MAX в одну
        # карточку организации.
        "sameAs": [u for u in (c.get("telegram_url"), c.get("max_url")) if u],
        "email": c["email"],
        "telephone": c["phone_href"],
        "taxID": site.company.get("inn", ""),
        "areaServed": {"@type": "Country", "name": "Россия"},
        # Основатель — реальный человек с проверяемыми реквизитами ИП.
        # Поисковик связывает карточку компании с её владельцем.
        "founder": {
            "@type": "Person",
            "name": site.legal.get("responsible", site.company.get("legal_name", "")),
        },
        # knowsAbout — темы, в которых компания разбирается. По ним
        # поисковик понимает, к каким запросам относить сайт.
        "knowsAbout": [s["nav_title"] for s in site.services],
        "contactPoint": [{
            "@type": "ContactPoint",
            "telephone": c["phone_href"],
            "email": c["email"],
            "contactType": "sales",
            "areaServed": "RU",
            "availableLanguage": "Russian",
        }],
    }


def schema_website(site: Site) -> dict:
    """Узел «сайт». Связывает все страницы в одно целое и указывает,
    кто издатель — без него каждая страница живёт сама по себе."""
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "@id": site.abs_url("/") + "#website",
        "url": site.abs_url("/"),
        "name": site.company["name"],
        "description": site.company["about_short"],
        "inLanguage": "ru-RU",
        "publisher": {"@id": site.abs_url("/") + "#organization"},
    }


def schema_webpage(site: Site, path: str, title: str, description: str) -> dict:
    """Узел конкретной страницы: что это за страница, чьей частью является
    и о ком она. Через @id к нему привязываются крошки и разметка услуги."""
    return {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": site.abs_url(path) + "#webpage",
        "url": site.abs_url(path),
        "name": title,
        "description": description,
        "inLanguage": "ru-RU",
        "isPartOf": {"@id": site.abs_url("/") + "#website"},
        "about": {"@id": site.abs_url("/") + "#organization"},
    }


def schema_faq(items) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [{
            "@type": "Question",
            "name": it["q"],
            "acceptedAnswer": {"@type": "Answer", "text": it["a"]},
        } for it in items],
    }


def schema_service(site: Site, service: dict, url_path: str, name: str, description: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": name,
        "description": description,
        "serviceType": service["nav_title"],
        "url": site.abs_url(url_path),
        "provider": {"@id": site.abs_url("/") + "#organization"},
        "areaServed": {"@type": "Country", "name": "Россия"},
        "hasOfferCatalog": {
            "@type": "OfferCatalog",
            "name": "Что входит в работу",
            "itemListElement": [{
                "@type": "Offer",
                "itemOffered": {"@type": "Service", "name": item},
            } for item in service["includes"]],
        },
    }


def schema_breadcrumbs(site: Site, crumbs) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [{
            "@type": "ListItem",
            "position": i,
            "name": name,
            "item": site.abs_url(path),
        } for i, (name, path) in enumerate(crumbs, start=1)],
    }


# =========================================================================
# 4. Сборка страниц
# =========================================================================

class Renderer:
    def __init__(self, site: Site, template: str, noindex: bool = False):
        self.site = site
        self.template = template
        self.noindex = noindex   # для превью-сборок: закрыть от поисковиков
        self.pages = []          # (путь, приоритет)

    def nav_links(self, current: str) -> str:
        out = []
        for item in self.site.raw["nav"]:
            active = ' aria-current="page"' if current.startswith(item["url"]) and item["url"] != "/" else ""
            out.append(f'        <li><a class="nav__link" href="{self.site.url(item["url"])}"{active}>{esc(item["title"])}</a></li>')
        return "\n".join(out)

    def footer_services(self):
        """Список услуг в подвале, разбитый на две колонки."""
        links = [
            f'          <li><a href="{self.site.url(self.site.service_url(s["slug"]))}">{esc(s["nav_title"])}</a></li>'
            for s in self.site.services
        ]
        half = (len(links) + 1) // 2
        return "\n".join(links[:half]), "\n".join(links[half:])

    def render(self, *, path: str, title: str, description: str, body: str,
               head_extra: str = "", og_type: str = "website", og_title: str = "",
               in_sitemap: bool = True, priority: str = "0.7",
               robots: str = "index, follow",
               og_image: str = "", og_image_alt: str = "") -> None:
        if self.noindex:
            robots = "noindex, nofollow"
        site = self.site
        c = site.contacts
        f1, f2 = self.footer_services()

        # Узлы «сайт» и «страница» собираются здесь, а не в каждой
        # странице по отдельности: так ни одна не останется без них.
        head_extra = "\n".join([
            jsonld(schema_website(site)),
            jsonld(schema_webpage(site, path, title, description)),
            head_extra,
        ])

        ctx = {
            "title": esc(title),
            "description": esc(description),
            "canonical": site.abs_url(path),
            "og_type": og_type,
            "og_title": esc(og_title or title),
            "og_image": site.abs_url(og_image or og_for(path) or
                                     site.raw.get("og_image", "/assets/img/og-default.jpg")),
            "og_image_alt": esc(og_image_alt or title),
            "verification": verification_tags(site),
            "robots": robots,
            "head_extra": head_extra,
            "base": site.base_path,
            "body": body,
            "nav_links": self.nav_links(path),
            "footer_services_1": f1,
            "footer_services_2": f2,
            "logo_svg": LOGO_SVG,
            "company_name": esc(site.company["name"]),
            "legal_name": esc(site.company.get("legal_name", site.company["name"])),
            "requisites": esc(site.company.get("requisites", site.company.get("legal_name", ""))),
            "company_tagline": esc(site.company["tagline"]),
            "company_about_short": esc(site.company["about_short"]),
            "phone_display": esc(c["phone_display"]),
            "phone_href": esc(c["phone_href"]),
            "email": esc(c["email"]),
            "telegram_url": esc(c["telegram_url"]),
            "telegram_display": esc(c["telegram_display"]),
            "max_url": esc(c.get("max_url", "")),
            "max_display": esc(c.get("max_display", "")),
            "work_hours": esc(c["work_hours"]),
            "geo": esc(c["geo"]),
            "year": str(date.today().year),
            "cookie_bar": cookie_bar(site),
            "sro_line": sro_block(site),
        }

        def sub(m):
            key = m.group(1)
            if key not in ctx:
                raise SystemExit(f"В templates/base.html есть {{{{{key}}}}}, но генератор его не знает")
            return ctx[key]

        page = re.sub(r"\{\{(\w+)\}\}", sub, self.template)
        page = typo_ru(page)

        out = DIST_DIR / path.strip("/") / "index.html" if path != "/" else DIST_DIR / "index.html"
        if path.endswith(".html"):
            out = DIST_DIR / path.strip("/")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")

        if in_sitemap:
            self.pages.append((path, priority))


# ---------- главная -------------------------------------------------------

def page_home(r: Renderer) -> None:
    site = r.site
    h = site.raw["hero"]
    offer = site.raw["offer"]
    why = site.raw["why"]
    process = site.raw["process"]
    faq = site.raw["faq"]

    points = "\n".join(f"          <li>{esc(p)}</li>" for p in h["points"])

    # Ключевые цифры вынесены в первый экран — сразу под текстом,
    # как строка характеристик в паспорте изделия.
    spec = []
    for st in offer["stats"]:
        unit = f'<span class="hero__spec-unit">{esc(st["unit"])}</span>' if st.get("unit") else ""
        # {услуг} считается по списку услуг, а не пишется руками. Однажды
        # услуг стало четырнадцать, а на первом экране осталось тринадцать:
        # такую ошибку не ловит ни одна проверка — она не противоречит
        # ничему, кроме действительности.
        value = str(st["value"]).replace("{услуг}", str(len(site.services)))
        spec.append(f'''          <div class="hero__spec-item">
            <div class="hero__spec-value">{esc(value)}{unit}</div>
            <div class="hero__spec-label">{esc(st["label"])}</div>
          </div>''')

    why_cards = "\n".join(f'''        <div class="card">
          <h3>{esc(w["title"])}</h3>
          <p>{esc(w["text"])}</p>
        </div>''' for w in why["items"])

    # Постер — статичный кадр. Он показывается сразу, пока грузится видео,
    # и остаётся вместо видео на телефонах. Видео подключает app.js.
    poster_rel = resolve_media(h.get("poster"), [
        "/assets/media/hero-poster.webp",
        "/assets/media/hero-poster.jpg",
        "/assets/media/hero-poster.png",
        "/assets/media/hero-poster-placeholder.png",
    ])
    poster = site.url(poster_rel)
    # Тег видео вставляем, только если файл действительно лежит в assets/.
    # Иначе браузер зря дёргал бы несуществующий файл — а на экране всё равно
    # остаётся постер. Положите hero.mp4 в assets/media/, и видео появится само.
    sources = "|".join(site.url(h[k]) for k in ("video_webm", "video_mp4")
                       if asset_exists(h.get(k)))
    # Отдельный лёгкий файл для телефонов: тот же ролик, но 720 точек в ширину
    # и 400 КБ вместо 1,2 МБ. Кладётся рядом как hero-mobile.mp4 — если файла
    # нет, телефон получит обычный, ничего не сломается.
    mobile = "/assets/media/hero-mobile.mp4"
    mob_attr = f' data-src-mobile="{site.url(mobile)}"' if asset_exists(mobile) else ""
    video_tag = (f'''<video class="hero__video js-video" autoplay muted loop playsinline preload="none"
           data-src="{sources}"{mob_attr} aria-hidden="true" tabindex="-1"></video>'''
                 if sources else "")

    # Анонс объектов на главной: три штуки и ссылка на полный список
    pf = site.raw.get("portfolio")
    objects_teaser = ""
    if pf and pf.get("items"):
        objects_teaser = f'''  <section class="section section--alt">
    <div class="container">
      <div class="section__head">
        <span class="eyebrow">Объекты</span>
        <h2>Где мы уже работали</h2>
        <p>{esc(pf["lead"])}</p>
      </div>
{block_objects(site, pf["items"], limit=3)}
      <div class="btn-row mt-6">
        <a class="btn btn--ghost" href="{site.url("/obekty/")}">Все объекты</a>
      </div>
    </div>
  </section>'''

    hero = f'''  <section class="hero">
    <div class="hero__media" aria-hidden="true">{poster_img(site, poster_rel, "hero__media-img")}</div>
    {video_tag}
    <div class="hero__scan" aria-hidden="true"></div>
    <div class="hero__frame" aria-hidden="true"></div>
    <div class="container">
      <div class="hero__inner">
        <span class="eyebrow">{esc(h["eyebrow"])}</span>
        <h1>{esc(h["h1"])}</h1>
        <p class="hero__lead">{esc(h["lead"])}</p>
        <ul class="hero__points">
{points}
        </ul>
        <div class="btn-row">
          <a class="btn btn--primary" href="#zayavka">{esc(h["cta_primary"])}</a>
          <a class="btn btn--on-dark" href="{site.url('/uslugi/')}">{esc(h["cta_secondary"])}</a>
        </div>
        <div class="hero__spec">
{chr(10).join(spec)}
        </div>
{hero_sro(site)}
      </div>
    </div>
  </section>'''

    body = f'''{hero}

  <section class="section section--surface">
    <div class="container">
      <div class="offer-grid">
        <div class="section__head" style="margin-bottom:0">
          <span class="eyebrow">Коротко</span>
          <h2>{esc(offer["title"])}</h2>
          {paragraphs(offer["text"], "lead")}
        </div>
        <aside class="panel panel--accent offer-card">
          <h3>Условия работы</h3>
          <div class="spec">
{chr(10).join(f"""            <div class="spec__row">
              <span class="spec__key">{esc(s["key"])}</span>
              <span class="spec__dots"></span>
              <span class="spec__val">{esc(s["value"])}</span>
            </div>""" for s in site.raw.get("service_spec", []))}
          </div>
          <div class="btn-row" style="margin-top:1.5rem">
            <a class="btn btn--primary btn--block" href="#zayavka">Оценить объём и сроки</a>
          </div>
        </aside>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="container">
      <div class="section__head">
        <h2>Услуги</h2>
        <p>Четыре направления. Можно взять одну задачу, можно передать документальное сопровождение объекта целиком.</p>
      </div>
{block_services_by_group(site)}
      <div class="btn-row mt-6">
        <a class="btn btn--ghost" href="{site.url('/uslugi/')}">Все услуги списком</a>
      </div>
    </div>
  </section>

{objects_teaser}

  <section class="section section--dark">
    <div class="container">
      <div class="section__head"><h2>{esc(why["title"])}</h2></div>
      <div class="grid grid--2">
{why_cards}
      </div>
    </div>
  </section>

{block_steps(process["steps"], process["title"], columns=3)}

{block_faq(faq["items"])}

{block_form(site)}'''

    # Кадр первого экрана — самая крупная картинка страницы. Просим браузер
    # начать качать её сразу, не дожидаясь разбора стилей: экран появляется
    # заметно раньше.
    head = "\n".join([
        (f'<link rel="preload" as="image" type="image/avif" fetchpriority="high"'
         f' href="{site.url(poster_rel.rsplit(".", 1)[0] + ".avif")}">'
         if asset_exists(poster_rel.rsplit(".", 1)[0] + ".avif") else
         f'<link rel="preload" as="image" href="{poster}" fetchpriority="high">'),
        jsonld(schema_organization(site)),
        # Узел «сайт» ставит render() на каждой странице — здесь он
        # был бы вторым и разошёлся бы с ним по составу полей.
        jsonld(schema_faq(faq["items"])),
    ])

    r.render(
        path="/",
        title=f'{site.company["name"]} — документальное сопровождение строительства по всей России',
        description=("Проектирование, исполнительная документация, сметы, ППР, геодезия, защита объёмов "
                     "КС-2 и КС-3, Ростехнадзор и ЗОС. Работаем удалённо по всей России, сдаём без возвратов."),
        body=body,
        head_extra=head,
        priority="1.0",
    )


# ---------- список услуг --------------------------------------------------

def page_services_index(r: Renderer) -> None:
    site = r.site
    cfg = site.raw["services_index"]

    body = f'''  <section class="page-head">
    <div class="container">
      <ul class="breadcrumbs">
        <li><a href="{site.url('/')}">Главная</a></li>
        <li>Услуги</li>
      </ul>
      <h1>{esc(cfg["h1"])}</h1>
      <p class="lead">{esc(cfg["lead"])}</p>
    </div>
  </section>

  <section class="section">
    <div class="container">
{block_services_by_group(site, level='h2')}
    </div>
  </section>

{block_form(site)}'''

    head = "\n".join([
        jsonld(schema_organization(site)),
        jsonld(schema_breadcrumbs(site, [("Главная", "/"), ("Услуги", "/uslugi/")])),
        jsonld({
            "@context": "https://schema.org",
            "@type": "ItemList",
            "itemListElement": [{
                "@type": "ListItem",
                "position": i,
                "name": s["nav_title"],
                "url": site.abs_url(site.service_url(s["slug"])),
            } for i, s in enumerate(site.services, start=1)],
        }),
    ])

    r.render(path="/uslugi/", title=cfg["title"], description=cfg["description"],
             body=body, head_extra=head, priority="0.9")


# ---------- страница услуги ----------------------------------------------

def page_service(r: Renderer, service: dict, city: dict = None) -> None:
    """Одна страница услуги. Если передан city — та же услуга под город."""
    site = r.site
    group = next(g for g in site.groups if g["id"] == service["group"])
    slug_city = city["slug"] if city else ""
    path = site.service_url(service["slug"], slug_city)

    if city:
        h1 = city.get("h1") or f'{service["h1"]} {city["case_in"]}'
        title = city.get("title") or f'{h1} — {site.company["name"]}'
        description = city.get("description") or f'{service["description"]} {city["case_in"]}.'
        lead = city.get("lead") or service["lead"]
    else:
        h1, title, description, lead = service["h1"], service["title"], service["description"], service["lead"]

    crumbs = [("Главная", "/"), ("Услуги", "/uslugi/"), (service["nav_title"], site.service_url(service["slug"]))]
    crumb_html = [f'<li><a href="{site.url("/")}">Главная</a></li>',
                  f'<li><a href="{site.url("/uslugi/")}">Услуги</a></li>']
    if city:
        crumbs.append((city["name"], path))
        crumb_html.append(f'<li><a href="{site.url(site.service_url(service["slug"]))}">{esc(service["nav_title"])}</a></li>')
        crumb_html.append(f'<li>{esc(city["name"])}</li>')
    else:
        crumb_html.append(f'<li>{esc(service["nav_title"])}</li>')

    body = f'''  <section class="page-head">
    <div class="container">
      <ul class="breadcrumbs">
        {chr(10).join("        " + c for c in crumb_html).strip()}
      </ul>
      <span class="eyebrow">{esc(group["title"])}</span>
      <h1>{esc(h1)}</h1>
      <p class="lead">{esc(lead)}</p>
    </div>
  </section>

  <section class="section">
    <div class="container split">
      <div>
        <h2>Когда нужна эта услуга</h2>
        {li_list(service["when"], "dashes")}

        <h2 style="margin-top:2.5rem">Что входит в работу</h2>
        {li_list(service["includes"], "ticks")}

        <h2 style="margin-top:2.5rem">Для кого</h2>
        {li_list(service["audience"], "dashes")}
      </div>

      <aside>
        <div class="sticky-box">
          <div class="panel panel--accent">
            <h3>Оценим объём и сроки</h3>
            <p style="color:var(--ink-muted)">Опишите объект — скажем, что реально успеть к вашей дате сдачи. Ответ в течение рабочего дня.</p>
            <div class="btn-row" style="margin-top:1.25rem">
              <a class="btn btn--primary btn--block" href="#zayavka">Оставить заявку</a>
              <a class="btn btn--ghost btn--block" href="tel:{esc(site.contacts["phone_href"])}">{esc(site.contacts["phone_display"])}</a>
            </div>
            <div class="spec">
{chr(10).join(f"""              <div class="spec__row">
                <span class="spec__key">{esc(s["key"])}</span>
                <span class="spec__dots"></span>
                <span class="spec__val">{esc(s["value"])}</span>
              </div>""" for s in site.raw.get("service_spec", []))}
            </div>
          </div>
        </div>
      </aside>
    </div>
  </section>

{block_steps(service["steps"], "Как проходит работа", columns=3, dark=True)}

{block_faq(service["faq"])}

{block_related(site, service)}

{block_form(site, preselect=service["nav_title"])}'''

    head = "\n".join([
        jsonld(schema_organization(site)),
        jsonld(schema_service(site, service, path, h1, description)),
        jsonld(schema_faq(service["faq"])),
        jsonld(schema_breadcrumbs(site, crumbs)),
    ])

    r.render(path=path, title=title, description=description, body=body,
             head_extra=head, og_type="article", priority="0.8")


# ---------- объекты -------------------------------------------------------

def page_objects(r: Renderer) -> None:
    site = r.site
    cfg = site.raw.get("portfolio")
    if not cfg:
        return

    body = f'''  <section class="page-head">
    <div class="container">
      <ul class="breadcrumbs">
        <li><a href="{site.url('/')}">Главная</a></li>
        <li>Объекты</li>
      </ul>
      <h1>{esc(cfg["h1"])}</h1>
      <p class="lead">{esc(cfg["lead"])}</p>
    </div>
  </section>

  <section class="section">
    <div class="container">
{block_objects(site, cfg["items"], level="h2")}
    </div>
  </section>

{block_geo(site)}

  <section class="section section--alt">
    <div class="container">
      <div class="section__head"><h2>Что делаем на таких объектах</h2></div>
{block_services_by_group(site)}
    </div>
  </section>

{block_form(site)}'''

    head = "\n".join([
        jsonld(schema_organization(site)),
        jsonld(schema_breadcrumbs(site, [("Главная", "/"), ("Объекты", "/obekty/")])),
        jsonld({
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": "Объекты",
            "itemListElement": [{
                "@type": "ListItem",
                "position": i,
                "name": f'{o["name"]}, {o["city"]}',
            } for i, o in enumerate(cfg["items"], start=1)],
        }),
    ])
    r.render(path="/obekty/", title=cfg["title"], description=cfg["description"],
             body=body, head_extra=head, priority="0.8")


# ---------- о компании ----------------------------------------------------

def page_about(r: Renderer) -> None:
    site = r.site
    cfg = site.raw["about"]
    why = site.raw["why"]

    blocks = "\n".join(f'''        <div class="card">
          <h2>{esc(b["title"])}</h2>
          <p>{esc(b["text"])}</p>
        </div>''' for b in cfg["blocks"])

    why_cards = "\n".join(f'''        <div class="card">
          <h3>{esc(w["title"])}</h3>
          <p>{esc(w["text"])}</p>
        </div>''' for w in why["items"])

    body = f'''  <section class="page-head">
    <div class="container">
      <ul class="breadcrumbs">
        <li><a href="{site.url('/')}">Главная</a></li>
        <li>О компании</li>
      </ul>
      <h1>{esc(cfg["h1"])}</h1>
      <p class="lead">{esc(cfg["lead"])}</p>
    </div>
  </section>

{block_media(site, cfg.get("video"))}

  <section class="section">
    <div class="container">
      <div class="grid grid--2">
{blocks}
      </div>
    </div>
  </section>

  <section class="section section--alt">
    <div class="container">
{sro_block(site, dark=False)}
    </div>
  </section>

{block_recommendations(site, site.raw.get("recommendations"))}

  <section class="section section--dark">
    <div class="container">
      <div class="section__head"><h2>{esc(why["title"])}</h2></div>
      <div class="grid grid--2">
{why_cards}
      </div>
    </div>
  </section>

  <section class="section section--alt">
    <div class="container">
      <div class="section__head"><h2>Чем занимаемся</h2></div>
{block_services_by_group(site)}
    </div>
  </section>

{block_form(site)}'''

    head = "\n".join([
        jsonld(schema_organization(site)),
        jsonld(schema_breadcrumbs(site, [("Главная", "/"), ("О компании", "/o-kompanii/")])),
    ])
    r.render(path="/o-kompanii/", title=cfg["title"], description=cfg["description"],
             body=body, head_extra=head, priority="0.6")


# ---------- контакты ------------------------------------------------------

def page_contacts(r: Renderer) -> None:
    site = r.site
    cfg = site.raw["contacts_page"]
    c = site.contacts
    chk = cfg["checklist"]

    body = f'''  <section class="page-head">
    <div class="container">
      <ul class="breadcrumbs">
        <li><a href="{site.url('/')}">Главная</a></li>
        <li>Контакты</li>
      </ul>
      <h1>{esc(cfg["h1"])}</h1>
      <p class="lead">{esc(cfg["lead"])}</p>
    </div>
  </section>

  <section class="section section--surface">
    <div class="container">
{contact_cards(site)}
      <div class="offer-grid mt-6">
        <div>
          <p class="lead lead--tight">{esc(c["work_hours"])}. {esc(c["geo"])}. Договор, счёт и закрывающие документы — в электронном виде, при необходимости отправляем оригиналы почтой.</p>
        </div>
        <aside class="panel panel--accent">
          <h2>{esc(chk["title"])}</h2>
          <p style="color:var(--ink-muted);font-size:0.9375rem">{esc(chk["text"])}</p>
          {li_list(chk["items"], "ticks")}
        </aside>
      </div>
    </div>
  </section>

{block_form(site)}'''

    head = "\n".join([
        jsonld(schema_organization(site)),
        jsonld(schema_breadcrumbs(site, [("Главная", "/"), ("Контакты", "/kontakty/")])),
        jsonld({
            "@context": "https://schema.org",
            "@type": "ContactPage",
            "url": site.abs_url("/kontakty/"),
            "about": {"@id": site.abs_url("/") + "#organization"},
        }),
    ])
    r.render(path="/kontakty/", title=cfg["title"], description=cfg["description"],
             body=body, head_extra=head, priority="0.6")


# ---------- политика обработки персональных данных ------------------------

def legal_tokens(site: Site) -> dict:
    """Подстановки для юридических текстов. Реквизиты пишутся один раз
    в site.json и legal.json — на странице они не дублируются руками,
    иначе редакции неизбежно разойдутся."""
    c, co, lg = site.contacts, site.company, site.legal
    address = (lg.get("address") or "").strip()
    return {
        "{оператор}": co.get("legal_name", co["name"]),
        "{инн}": co.get("inn", ""),
        "{огрнип}": co.get("ogrnip", ""),
        "{почта}": c["email"],
        "{телефон}": c["phone_display"],
        "{сайт}": site.abs_url("/"),
        "{адрес_политики}": site.abs_url(lg["policy"]["slug"]),
        "{ответственный}": lg.get("responsible", co.get("legal_name", "")),
        # Адреса может не быть — тогда фраза о нём не выводится вовсе,
        # а не показывается посетителю незаполненной скобкой.
        "{адрес_фраза}": f" Почтовый адрес: {address}." if address else "",
        "{адрес_запроса}": f" либо почтой по адресу {address}" if address else "",
    }


def legal_text(text: str, tokens: dict) -> str:
    out = esc(text)
    for key, value in tokens.items():
        out = out.replace(key, esc(value))
    return out


def legal_section(sec: dict, tokens: dict, site: Site) -> str:
    """Один раздел документа: заголовок, абзацы, списки, таблица."""
    parts = [f'      <h2 class="legal__h">{legal_text(sec["h"], tokens)}</h2>']
    for key in ("p", "ul", "dl", "table", "p2"):
        if key not in sec:
            continue
        if key in ("p", "p2"):
            parts += [f'      <p>{legal_text(t, tokens)}</p>' for t in sec[key]]
        elif key == "ul":
            items = "".join(f"<li>{legal_text(t, tokens)}</li>" for t in sec[key])
            parts.append(f'      <ul class="legal__list">{items}</ul>')
        elif key == "dl":
            rows = "".join(
                f'<div class="legal__term"><dt>{legal_text(t, tokens)}</dt>'
                f'<dd>{legal_text(d, tokens)}</dd></div>' for t, d in sec[key])
            parts.append(f'      <dl class="legal__terms">{rows}</dl>')
        elif key == "table":
            head = "".join(f"<th scope=\"col\">{esc(h)}</th>" for h in sec[key]["head"])
            cols = sec[key]["head"]
            rows = "".join(
                "<tr>" + "".join(
                    f'<td data-label="{esc(cols[i])}">{esc(v)}</td>'
                    for i, v in enumerate((pr["name"], pr["what"], pr["where"])))
                + "</tr>" for pr in site.legal.get("processors", []))
            parts.append('      <div class="legal__table-wrap">'
                         f'<table class="legal__table"><thead><tr>{head}</tr></thead>'
                         f"<tbody>{rows}</tbody></table></div>")
    return "\n".join(parts)


def page_policy(r: Renderer) -> None:
    site = r.site
    lg = site.legal
    pol = lg["policy"]
    tokens = legal_tokens(site)

    # Раздел про cookie появляется в документе только тогда, когда счётчик
    # действительно подключён. Пока его нет, сайт не ставит ни одного файла
    # cookie, и политика, обещающая обратное, была бы неправдой.
    parts = list(pol["sections"])
    if site.raw.get("seo", {}).get("metrika_id") and lg.get("cookie_section"):
        parts.append(lg["cookie_section"])
    pol = dict(pol, sections=parts)

    toc = "".join(
        f'<li><a href="#razdel-{i}">{esc(sec["h"])}</a></li>'
        for i, sec in enumerate(pol["sections"], start=1))
    toc += '<li><a href="#soglasie">' + esc(lg["consent"]["h"]) + "</a></li>"

    sections = "\n".join(
        f'    <section class="legal__section" id="razdel-{i}">\n'
        f"{legal_section(sec, tokens, site)}\n    </section>"
        for i, sec in enumerate(pol["sections"], start=1))

    consent = lg["consent"]
    consent_html = "\n".join(
        f"      <p>{legal_text(t, tokens)}</p>" for t in consent["p"])

    body = f'''  <section class="page-head">
    <div class="container">
      <ul class="breadcrumbs">
        <li><a href="{site.url('/')}">Главная</a></li>
        <li>Персональные данные</li>
      </ul>
      <h1>{esc(pol["h1"])}</h1>
      <p class="lead">{esc(pol["lead"])}</p>
    </div>
  </section>

  <section class="section section--surface">
    <div class="container legal">
      <div class="legal__meta">
        <div class="legal__meta-item">
          <span class="legal__meta-label">Оператор</span>
          <span class="legal__meta-value">{esc(tokens["{оператор}"])}</span>
        </div>
        <div class="legal__meta-item">
          <span class="legal__meta-label">Редакция</span>
          <span class="legal__meta-value">№ {esc(lg.get("version", "1.0"))} от {esc(lg.get("approved", ""))}</span>
        </div>
        <div class="legal__meta-item">
          <span class="legal__meta-label">Основание</span>
          <span class="legal__meta-value">ст. 18.1 Федерального закона № 152-ФЗ</span>
        </div>
      </div>

      <nav class="legal__toc" aria-label="Содержание документа">
        <p class="legal__toc-title">Содержание</p>
        <ol class="legal__toc-list">{toc}</ol>
      </nav>

{sections}

    <section class="legal__section legal__section--consent" id="soglasie">
      <h2 class="legal__h legal__h--big">{esc(consent["h"])}</h2>
      <p class="legal__note">{esc(consent["lead"])}</p>
{consent_html}
    </section>
    </div>
  </section>

{block_form(site)}'''

    head = "\n".join([
        jsonld(schema_organization(site)),
        jsonld(schema_breadcrumbs(site, [("Главная", "/"), ("Персональные данные", pol["slug"])])),
    ])
    r.render(path=pol["slug"], title=pol["title"], description=pol["description"],
             body=body, head_extra=head, priority="0.3")


# ---------- 404 -----------------------------------------------------------

def page_404(r: Renderer) -> None:
    site = r.site
    body = f'''  <section class="page-head">
    <div class="container">
      <h1>Страница не найдена</h1>
      <p class="lead">Возможно, адрес набран с ошибкой или страница переехала.</p>
      <div class="btn-row" style="margin-top:1.5rem">
        <a class="btn btn--primary" href="{site.url('/uslugi/')}">Все услуги</a>
        <a class="btn btn--on-dark" href="{site.url('/')}">На главную</a>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="container">
{block_services_by_group(site, level='h2')}
    </div>
  </section>'''
    r.render(path="/404.html", title="Страница не найдена — " + site.company["name"],
             description="Такой страницы нет. Перейдите к списку услуг или на главную.",
             body=body, head_extra=jsonld(schema_organization(site)),
             in_sitemap=False, robots="noindex, follow")


# =========================================================================
# 5. sitemap.xml, robots.txt, файлы
# =========================================================================

def source_date(*files) -> str:
    """Дата последнего изменения исходника — из истории git, а не из часов
    сборщика. Дата сборки означала бы «на каждой публикации изменились все
    страницы разом», и за такой lastmod поисковики перестают его учитывать
    вовсе. Нет git (архив, чужая машина) — берём дату файла."""
    best = ""
    for f in files:
        rel = str(Path(f).relative_to(ROOT)) if Path(f).is_absolute() else str(f)
        got = ""
        try:
            out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", rel],
                                 cwd=ROOT, capture_output=True, text=True, timeout=10)
            got = out.stdout.strip()
        except Exception:
            got = ""
        if not got:
            path = ROOT / rel
            if path.exists():
                got = date.fromtimestamp(path.stat().st_mtime).isoformat()
        best = max(best, got)
    return best or date.today().isoformat()


def write_sitemap(site: Site, pages) -> None:
    # Что меняет страницу: услуги приходят из services.json, остальные
    # страницы — из site.json, политика — ещё и из legal.json.
    d_site = source_date(DATA_DIR / "site.json", TPL_DIR / "base.html")
    d_serv = source_date(DATA_DIR / "services.json", TPL_DIR / "base.html")
    d_legal = source_date(DATA_DIR / "legal.json", TPL_DIR / "base.html")

    def lastmod(path: str) -> str:
        if path.startswith("/uslugi/"):
            return d_serv
        if path.startswith("/politika"):
            return d_legal
        return d_site

    rows = "\n".join(
        f"  <url>\n    <loc>{site.abs_url(path)}</loc>\n"
        f"    <lastmod>{lastmod(path)}</lastmod>\n    <priority>{priority}</priority>\n  </url>"
        for path, priority in pages
    )
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f"{rows}\n</urlset>\n")
    (DIST_DIR / "sitemap.xml").write_text(xml, encoding="utf-8")


def write_manifest(site: Site) -> None:
    """Файл для «добавить на домашний экран»: название, иконки и цвета.
    Без него телефон подписывает ярлык адресом сайта."""
    data = {
        "name": site.company["name"] + " — " + site.company["tagline"],
        "short_name": site.company["name"],
        "start_url": site.url("/"),
        "display": "standalone",
        "background_color": "#0a1420",
        "theme_color": "#0a1420",
        "lang": "ru",
        "icons": [
            {"src": site.url("/assets/img/apple-touch-icon.png"),
             "sizes": "180x180", "type": "image/png"},
            {"src": site.url("/assets/img/favicon.svg"),
             "sizes": "any", "type": "image/svg+xml"},
        ],
    }
    (DIST_DIR / "site.webmanifest").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_robots(site: Site, noindex: bool = False) -> None:
    if noindex:
        # Превью для показа заказчику: в поиск попадать не должно
        text = "User-agent: *\nDisallow: /\n"
    else:
        text = ("User-agent: *\n"
                "Allow: /\n"
                # Настройки приёма заявок — не для индексации.
                "Disallow: /assets/config.js\n"
                # Служебная страница с кадрами для сторис: она для нас,
                # а не для посетителей, и в поиске ей делать нечего.
                "Disallow: /assets/promo/\n"
                "Disallow: /api/\n\n"
                f"Sitemap: {site.abs_url('/sitemap.xml')}\n")
    (DIST_DIR / "robots.txt").write_text(text, encoding="utf-8")


def write_photo_hint(site: Site) -> None:
    """Памятка «как добавить фотографию объекта» — собирается по списку
    объектов, а не пишется руками. Раньше имена были перечислены в файле
    вручную, и после удаления объекта в памятке остался несуществующий:
    такую ошибку не ловит ни одна проверка, она не противоречит ничему,
    кроме действительности."""
    rows = "\n".join(
        f"    {it['slug']}.jpg".ljust(36) + f"{it['name']}, {it['city']}"
        for it in site.raw["portfolio"]["items"])
    text = f"""КАК ДОБАВИТЬ ФОТОГРАФИЮ ОБЪЕКТА
================================

Этот файл создаётся сборкой сам по списку объектов из data/site.json.
Править его руками не нужно: при следующей сборке правка потеряется.

Положите сюда файл с нужным именем — и фотография сама появится
в карточке объекта на сайте. Ничего больше настраивать не надо.

Имена файлов (расширение .jpg, .webp или .png — любое):

{rows}

После добавления файлов выполните пересборку:

    python3 build.py

Чтобы фотографии стали лёгкими (копии под размер экрана и формат AVIF):

    python3 tools/make-thumbs.py && python3 build.py

Если фотографии нет — в карточке выводится фирменная заставка,
вёрстка не ломается.
"""
    (ASSETS_DIR / "img" / "objects" / "КАК-ДОБАВИТЬ-ФОТО.txt").write_text(
        text, encoding="utf-8")


def write_llms(site: Site) -> None:
    """Оглавление сайта для ИИ-помощников (llms.txt). Люди всё чаще
    спрашивают не поисковик, а чат; файл даёт ему короткое и точное
    описание вместо того, чтобы он собирал его из вёрстки сам.
    Собирается из тех же данных, что и страницы: ни одного факта,
    написанного здесь руками, — иначе заведётся вторая точка правды."""
    c = site.contacts
    lines = [
        f"# {site.company['name']} — {site.company['tagline']}",
        "",
        f"> {site.company['about_short']} {c['geo']}.",
        "",
        f"Исполнитель: {site.company.get('legal_name', '')}, "
        f"ИНН {site.company.get('inn', '')}, ОГРНИП {site.company.get('ogrnip', '')}.",
        f"Телефон: {c['phone_display']}. Почта: {c['email']}. Telegram: {c['telegram_display']}.",
        f"Режим работы: {c['work_hours']}.",
        "",
        "## Услуги",
        "",
    ]
    for group in site.groups:
        items = site.services_in_group(group["id"])
        if not items:
            continue
        lines.append(f"### {group['title']}")
        lines.append("")
        for srv in items:
            url = site.abs_url(site.service_url(srv["slug"]))
            lines.append(f"- [{srv['nav_title']}]({url}): {strip_tags(srv['short'])}")
        lines.append("")
    lines += [
        "## Разделы сайта",
        "",
        f"- [Все услуги]({site.abs_url('/uslugi/')}): список из "
        f"{len(site.services)} направлений документации.",
        f"- [Объекты]({site.abs_url('/obekty/')}): объекты, на которых велась документация.",
        f"- [О компании]({site.abs_url('/o-kompanii/')}): как устроена работа.",
        f"- [Контакты]({site.abs_url('/kontakty/')}): телефон, почта, мессенджеры.",
        f"- [Персональные данные]({site.abs_url('/politika/')}): политика обработки "
        "персональных данных и текст согласия.",
        "",
    ]
    (DIST_DIR / "llms.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def minify_css(text: str) -> str:
    """Убирает из стилей комментарии и лишние пробелы.

    Исходник assets/style.css остаётся как есть — с комментариями, по нему
    сайт и правят. Сжимается только копия в dist/, которую качает браузер."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)          # комментарии
    text = re.sub(r"\s+", " ", text)                            # переносы строк
    text = re.sub(r"\s*([{}:;,>~])\s*", r"\1", text)            # пробелы у знаков
    text = re.sub(r";}", "}", text)                             # лишняя точка с запятой
    return text.strip()


def minify_js(text: str) -> str:
    """Осторожное сжатие скрипта: убираются только строки-комментарии
    и отступы в начале строк.

    Настоящие минификаторы разбирают код целиком; здесь это лишнее и рискованно:
    выражение вроде 'https://' внутри строки регулярка легко примет за начало
    комментария и сломает сайт. Поэтому трогаем только то, что заведомо
    безопасно — от этого файл худеет примерно на треть."""
    out = []
    in_block = False
    for line in text.split("\n"):
        stripped = line.strip()
        if in_block:
            if "*/" in stripped:
                in_block = False
                tail = stripped.split("*/", 1)[1].strip()
                if tail:
                    out.append(tail)
            continue
        if stripped.startswith("/*"):
            if "*/" not in stripped:
                in_block = True
            continue
        if stripped.startswith("//"):
            continue
        if stripped:
            out.append(stripped)
    return "\n".join(out)


def minify_html(text: str) -> str:
    """Убирает html-комментарии и отступы между тегами.

    Содержимое тегов не трогаем: внутри может быть текст, где пробелы важны."""
    text = re.sub(r"<!--(?!\[if).*?-->", "", text, flags=re.S)
    text = re.sub(r"^[ \t]+", "", text, flags=re.M)
    text = re.sub(r"\n{2,}", "\n", text)
    return text


def shrink_dist() -> None:
    """Сжимает то, что уезжает к посетителю: стили, скрипт и страницы.

    Работает только с папкой dist/. Исходники не меняются — их читают люди."""
    before = after = 0
    for path in list(DIST_DIR.rglob("*.css")) + list(DIST_DIR.rglob("*.js")) \
            + list(DIST_DIR.rglob("*.html")):
        if path.name == "config.js":        # настройки заказчика не трогаем
            continue
        text = path.read_text(encoding="utf-8")
        before += len(text.encode())
        if path.suffix == ".css":
            text = minify_css(text)
        elif path.suffix == ".js":
            text = minify_js(text)
        else:
            text = minify_html(text)
        path.write_text(text, encoding="utf-8")
        after += len(text.encode())
    if before:
        print(f"Сжатие: {before // 1024} КБ -> {after // 1024} КБ "
              f"(минус {round((1 - after / before) * 100)}%)")


def copy_server_config() -> None:
    """Кладёт настройки веб-сервера в корень сайта (server/.htaccess).

    Это кеширование, сжатие и заголовки безопасности для обычного хостинга.
    На GitHub Pages файл не действует и не мешает."""
    src = ROOT / "server" / ".htaccess"
    if src.exists():
        shutil.copy2(src, DIST_DIR / ".htaccess")


def copy_assets() -> None:
    dst = DIST_DIR / "assets"
    shutil.copytree(ASSETS_DIR, dst)
    # На сайт уезжает только рабочий config.js. Образец там не нужен.
    example = dst / "config.example.js"
    if example.exists():
        example.unlink()
    if not (dst / "config.js").exists():
        # Заглушка, чтобы не было ошибки 404 при незаполненных настройках
        (dst / "config.js").write_text(
            "/* Настройки не заданы. Скопируйте assets/config.example.js "
            "в assets/config.js и заполните — иначе форма не отправит заявку. */\n"
            "window.SITE_CONFIG = {};\n",
            encoding="utf-8",
        )


# =========================================================================
# 6. Точка входа
# =========================================================================

def build(regen_media: bool = False, base_path: str = None,
          base_url: str = None, noindex: bool = False) -> Site:
    site_data = load_json(DATA_DIR / "site.json")
    services = load_json(DATA_DIR / "services.json")
    legal = load_json(DATA_DIR / "legal.json")
    geo = load_json(DATA_DIR / "map.json")
    site = Site(site_data, services, legal, geo)

    # Превью-сборка: адрес и подпапку задаём из командной строки,
    # чтобы боевые настройки в data/site.json остались нетронутыми.
    if base_path is not None:
        site.base_path = base_path.rstrip("/")
    if base_url is not None:
        site.base_url = base_url.rstrip("/")

    created = genmedia.ensure_media(ASSETS_DIR, force=regen_media)
    for path in created:
        print(f"  картинка-заглушка: {path.relative_to(ROOT)}")

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)

    template = (TPL_DIR / "base.html").read_text(encoding="utf-8")
    r = Renderer(site, template, noindex=noindex)

    page_home(r)
    page_services_index(r)
    for service in services:
        page_service(r, service)
        for city in service.get("cities", []):
            page_service(r, service, city)
    page_objects(r)
    page_about(r)
    page_contacts(r)
    page_policy(r)
    page_404(r)

    copy_assets()
    write_sitemap(site, r.pages)
    write_robots(site, noindex=noindex)
    write_llms(site)
    write_photo_hint(site)
    write_manifest(site)
    copy_server_config()

    # Проверка, что заголовки нигде не повторяются
    check_unique(r)

    # Последним шагом сжимаем то, что уедет к посетителю
    shrink_dist()

    print(f"\nГотово. Собрано страниц: {len(r.pages) + 1} (включая 404).")
    print(f"Сайт лежит в: {DIST_DIR}")
    launch_checklist(site)
    return site


def launch_checklist(site: Site) -> None:
    """Что ещё не заполнено перед запуском на боевом домене.

    Каждый пункт — то, что нельзя вычислить из кода и что должен
    сообщить владелец сайта. Пока пункт не закрыт, сайт работает,
    но часть его возможностей выключена — и молчать об этом нельзя:
    забытая мелочь вроде адреса в политике обходится дороже всего."""
    seo = site.raw.get("seo", {})
    todo = []

    if "example.com" in site.base_url:
        todo.append("АДРЕС САЙТА. В data/site.json → base_url всё ещё example.com. "
                    "Пока он там, в canonical, карте сайта и картинках для соцсетей "
                    "стоит несуществующий адрес, и поисковик их не примет.")
    if not (ASSETS_DIR / "config.js").exists():
        todo.append("ПРИЁМ ЗАЯВОК. Нет файла assets/config.js — форма никуда не "
                    "отправляет заявки и показывает запасные кнопки. Образец: "
                    "assets/config.example.js, порядок — в README.")
    if not site.legal.get("address"):
        todo.append("АДРЕС ОПЕРАТОРА в data/legal.json → address. Это адрес, по "
                    "которому вы готовы принимать письменные запросы об обработке "
                    "персональных данных; он же нужен для уведомления в Роскомнадзор. "
                    "Пока пусто — строка с адресом на страницу политики не выводится.")
    if not seo.get("metrika_id"):
        todo.append("ЯНДЕКС.МЕТРИКА в data/site.json → seo.metrika_id. Без неё "
                    "не видно, сколько людей пришло и откуда.")
    if not seo.get("yandex_verification"):
        todo.append("ПОДТВЕРЖДЕНИЕ ПРАВ в Яндекс.Вебмастере: "
                    "data/site.json → seo.yandex_verification.")
    if not (ASSETS_DIR / "img" / "og").exists():
        todo.append("ОБЛОЖКИ ДЛЯ СОЦСЕТЕЙ не нарисованы: python3 tools/make-og.py, "
                    "затем пересобрать сайт.")

    if not todo:
        print("\nК запуску готово: все настройки заполнены.")
        return
    print("\n" + "─" * 66)
    print(f"ЕЩЁ НЕ ЗАПОЛНЕНО ({len(todo)}) — сайт работает, но не в полную силу:")
    for i, item in enumerate(todo, start=1):
        print(f"\n{i}. {item}")
    print("─" * 66)


def check_unique(r: Renderer) -> None:
    """Одинаковые title или description — прямая потеря позиций в поиске."""
    titles, descriptions = {}, {}
    for path, _ in r.pages:
        file = DIST_DIR / (path.strip("/") + "/index.html" if path != "/" else "index.html")
        text = file.read_text(encoding="utf-8")
        title = re.search(r"<title>(.*?)</title>", text, re.S)
        desc = re.search(r'<meta name="description" content="(.*?)"', text, re.S)
        if title:
            titles.setdefault(title.group(1), []).append(path)
        if desc:
            descriptions.setdefault(desc.group(1), []).append(path)

    for label, store in (("title", titles), ("description", descriptions)):
        for value, paths in store.items():
            if len(paths) > 1:
                print(f"  ВНИМАНИЕ: одинаковый {label} на страницах: {', '.join(paths)}")


def serve() -> None:
    import http.server
    import socketserver
    import functools

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST_DIR))
    with socketserver.TCPServer(("", 8000), handler) as httpd:
        print("\nОткройте в браузере:  http://localhost:8000")
        print("Остановить: Ctrl+C")
        httpd.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Сборка сайта")
    parser.add_argument("--serve", action="store_true", help="собрать и открыть локально")
    parser.add_argument("--regen-media", action="store_true", help="перерисовать картинки-заглушки")
    parser.add_argument("--base-path", metavar="/подпапка",
                        help="если сайт лежит не в корне домена (для превью)")
    parser.add_argument("--base-url", metavar="https://...",
                        help="адрес сайта, если отличается от указанного в site.json")
    parser.add_argument("--noindex", action="store_true",
                        help="закрыть сборку от поисковиков (для показа заказчику)")
    args = parser.parse_args()

    build(regen_media=args.regen_media, base_path=args.base_path,
          base_url=args.base_url, noindex=args.noindex)
    if args.serve:
        serve()
