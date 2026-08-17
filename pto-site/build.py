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
import shutil
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

    def __init__(self, site: dict, services: list):
        self.raw = site
        self.services = services
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


def block_media(site: Site, cfg: dict) -> str:
    """Широкая видео-полоса. Ведёт себя как первый экран: постер виден сразу,
    видео подключается скриптом после загрузки страницы. Если файлов видео нет,
    остаётся постер — блок не ломается."""
    if not cfg:
        return ""
    poster = site.url(resolve_media(cfg.get("poster"), []))
    sources = "|".join(site.url(cfg[k]) for k in ("webm", "mp4") if asset_exists(cfg.get(k)))
    video = (f'''<video class="media-band__video js-video" autoplay muted loop playsinline
             preload="none" poster="{poster}" data-src="{sources}"
             aria-hidden="true" tabindex="-1"></video>''' if sources else "")
    caption = (f'<figcaption class="media-band__caption">{esc(cfg["caption"])}</figcaption>'
               if cfg.get("caption") else "")
    return f'''  <section class="section section--tight">
    <div class="container">
      <figure class="media-band" style="background-image:url({poster})">
        {video}
        {caption}
      </figure>
    </div>
  </section>'''


def block_recommendations(site: Site, cfg: dict) -> str:
    """Рекомендательные письма. У карточки без поля file ссылки нет —
    так письмо можно показать текстом, не выкладывая сам документ."""
    if not cfg or not cfg.get("items"):
        return ""
    cards = []
    for r in cfg["items"]:
        # Письмо открывается картинкой во всплывающем окне. Ссылка на исходный
        # PDF остаётся внутри окна — для тех, кому нужен сам документ.
        link = ""
        if r.get("image") and asset_exists(r["image"]):
            pdf = (f' data-pdf="{site.url(r["file"])}"'
                   if r.get("file") and asset_exists(r["file"]) else "")
            link = (f'<button class="rec__link" type="button"'
                    f' data-lightbox="{site.url(r["image"])}"'
                    f' data-caption="{esc(r["company"])} · {esc(r["city"])}, {esc(r["date"])}"'
                    f'{pdf}>Посмотреть письмо</button>')
        cards.append(f'''        <article class="card rec">
          <div class="rec__head">
            <h3>{esc(r["company"])}</h3>
            <span class="rec__meta">{esc(r["city"])} · {esc(r["date"])}</span>
          </div>
          <blockquote class="rec__quote">{esc(r["quote"])}</blockquote>
          <div class="spec">
            <div class="spec__row"><span class="spec__key">Роль</span>
              <span class="spec__dots"></span><span class="spec__val">{esc(r["role"])}</span></div>
            <div class="spec__row"><span class="spec__key">Объект</span>
              <span class="spec__dots"></span><span class="spec__val">{esc(r["object"])}</span></div>
          </div>
          <p class="rec__scope">{esc(r["scope"])}</p>
          {link}
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


def block_objects(site: Site, items, limit: int = 0) -> str:
    """Карточки объектов. Фотография необязательна: без неё выводится
    фирменная заставка с чертёжной сеткой, вёрстка не ломается."""
    if not items:
        return ""
    shown = items[:limit] if limit else items
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

        if not photos:
            media = '<div class="object__media object__media--empty"></div>'
        elif len(photos) == 1:
            media = f'<div class="object__media" style="background-image:url({site.url(photos[0])})"></div>'
        else:
            # Несколько фотографий — media становится кнопкой, открывающей галерею
            gallery = json.dumps([site.url(x) for x in photos], ensure_ascii=False)
            media = (f'<button class="object__media object__media--more" type="button"'
                     f' style="background-image:url({site.url(photos[0])})"'
                     f' data-gallery="{esc(gallery)}"'
                     f' data-caption="{esc(o["name"])} · {esc(o["city"])}">'
                     f'<span class="object__count">{len(photos)} фото</span></button>')
        scope = f'<p class="object__scope">{esc(o["scope"])}</p>' if o.get("scope") else ""
        cards.append(f'''        <article class="object">
          {media}
          <div class="object__body">
            <span class="object__num">{n:02d}</span>
            <h3 class="object__name">{esc(o["name"])}</h3>
            <span class="object__city">{esc(o["city"])}</span>
            {scope}
            <div class="spec">
              <div class="spec__row"><span class="spec__key">Заказчик</span>
                <span class="spec__dots"></span><span class="spec__val">{esc(o["client"])}</span></div>
            </div>
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


def block_services_by_group(site: Site) -> str:
    """Четыре группы услуг со ссылками — используется на главной и в /uslugi/."""
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
      <div class="group__head">
        <span class="group__index" aria-hidden="true">{n:02d}</span>
        <span class="group__num">Группа {n:02d} / {total:02d}</span>
        <h3 class="group__title">{esc(group["title"])}</h3>
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
        <div>
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
              data-error="{esc(form_cfg["error"])}">
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
          <div class="form__status" role="status"></div>
          <button class="btn btn--primary btn--block" type="submit">Отправить заявку</button>
          <p class="form__note">{esc(form_cfg["note"])}</p>
        </form>
      </div>
    </div>
  </section>'''


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
        "image": site.abs_url("/assets/img/og-default.png"),
        "email": c["email"],
        "telephone": c["phone_href"],
        "taxID": site.company.get("inn", ""),
        "areaServed": {"@type": "Country", "name": "Россия"},
        "contactPoint": [{
            "@type": "ContactPoint",
            "telephone": c["phone_href"],
            "email": c["email"],
            "contactType": "sales",
            "areaServed": "RU",
            "availableLanguage": "Russian",
        }],
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
               robots: str = "index, follow") -> None:
        if self.noindex:
            robots = "noindex, nofollow"
        site = self.site
        c = site.contacts
        f1, f2 = self.footer_services()

        ctx = {
            "title": esc(title),
            "description": esc(description),
            "canonical": site.abs_url(path),
            "og_type": og_type,
            "og_title": esc(og_title or title),
            "og_image": site.abs_url(site.raw.get("og_image", "/assets/img/og-default.png")),
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
        }

        def sub(m):
            key = m.group(1)
            if key not in ctx:
                raise SystemExit(f"В templates/base.html есть {{{{{key}}}}}, но генератор его не знает")
            return ctx[key]

        page = re.sub(r"\{\{(\w+)\}\}", sub, self.template)

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
        spec.append(f'''          <div class="hero__spec-item">
            <div class="hero__spec-value">{esc(st["value"])}{unit}</div>
            <div class="hero__spec-label">{esc(st["label"])}</div>
          </div>''')

    why_cards = "\n".join(f'''        <div class="card">
          <h3>{esc(w["title"])}</h3>
          <p>{esc(w["text"])}</p>
        </div>''' for w in why["items"])

    # Постер — статичный кадр. Он показывается сразу, пока грузится видео,
    # и остаётся вместо видео на телефонах. Видео подключает app.js.
    poster = site.url(resolve_media(h.get("poster"), [
        "/assets/media/hero-poster.webp",
        "/assets/media/hero-poster.jpg",
        "/assets/media/hero-poster.png",
        "/assets/media/hero-poster-placeholder.png",
    ]))
    # Тег видео вставляем, только если файл действительно лежит в assets/.
    # Иначе браузер зря дёргал бы несуществующий файл — а на экране всё равно
    # остаётся постер. Положите hero.mp4 в assets/media/, и видео появится само.
    sources = "|".join(site.url(h[k]) for k in ("video_webm", "video_mp4")
                       if asset_exists(h.get(k)))
    video_tag = (f'''<video class="hero__video js-video" autoplay muted loop playsinline preload="none"
           poster="{poster}" data-src="{sources}" aria-hidden="true" tabindex="-1"></video>'''
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
    <div class="hero__media" style="background-image:url({poster})"></div>
    {video_tag}
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

    head = "\n".join([
        jsonld(schema_organization(site)),
        jsonld({
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": site.company["name"],
            "url": site.abs_url("/"),
        }),
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
{block_services_by_group(site)}
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
{block_objects(site, cfg["items"])}
    </div>
  </section>

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
          <h3>{esc(b["title"])}</h3>
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
      <div class="grid grid--4">
        <div class="stat">
          <div class="contact-line__label">Телефон</div>
          <a class="contact-line__value" href="tel:{esc(c["phone_href"])}" style="color:var(--navy)">{esc(c["phone_display"])}</a>
        </div>
        <div class="stat">
          <div class="contact-line__label">Почта</div>
          <a class="contact-line__value" href="mailto:{esc(c["email"])}" style="color:var(--navy);font-size:1.0625rem">{esc(c["email"])}</a>
        </div>
        <div class="stat">
          <div class="contact-line__label">Telegram</div>
          <a class="contact-line__value" href="{esc(c["telegram_url"])}" rel="nofollow noopener" target="_blank" style="color:var(--navy);font-size:1.0625rem">{esc(c["telegram_display"])}</a>
        </div>
        <div class="stat">
          <div class="contact-line__label">MAX</div>
          <a class="contact-line__value" href="{esc(c["max_url"])}" rel="nofollow noopener" target="_blank" style="color:var(--navy);font-size:1.0625rem">{esc(c.get("max_display","Канал"))}</a>
        </div>
      </div>
      <p class="lead lead--tight mt-6">{esc(c["work_hours"])}. {esc(c["geo"])}. Договор, счёт и закрывающие документы — в электронном виде, при необходимости отправляем оригиналы почтой.</p>
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
{block_services_by_group(site)}
    </div>
  </section>'''
    r.render(path="/404.html", title="Страница не найдена — " + site.company["name"],
             description="Такой страницы нет. Перейдите к списку услуг или на главную.",
             body=body, head_extra=jsonld(schema_organization(site)),
             in_sitemap=False, robots="noindex, follow")


# =========================================================================
# 5. sitemap.xml, robots.txt, файлы
# =========================================================================

def write_sitemap(site: Site, pages) -> None:
    today = date.today().isoformat()
    rows = "\n".join(
        f"  <url>\n    <loc>{site.abs_url(path)}</loc>\n"
        f"    <lastmod>{today}</lastmod>\n    <priority>{priority}</priority>\n  </url>"
        for path, priority in pages
    )
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f"{rows}\n</urlset>\n")
    (DIST_DIR / "sitemap.xml").write_text(xml, encoding="utf-8")


def write_robots(site: Site, noindex: bool = False) -> None:
    if noindex:
        # Превью для показа заказчику: в поиск попадать не должно
        text = "User-agent: *\nDisallow: /\n"
    else:
        text = ("User-agent: *\n"
                "Allow: /\n"
                "Disallow: /assets/config.js\n\n"
                f"Sitemap: {site.abs_url('/sitemap.xml')}\n")
    (DIST_DIR / "robots.txt").write_text(text, encoding="utf-8")


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
    site = Site(site_data, services)

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
    page_404(r)

    copy_assets()
    write_sitemap(site, r.pages)
    write_robots(site, noindex=noindex)

    # Проверка, что заголовки нигде не повторяются
    check_unique(r)

    print(f"\nГотово. Собрано страниц: {len(r.pages) + 1} (включая 404).")
    print(f"Сайт лежит в: {DIST_DIR}")
    return site


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
