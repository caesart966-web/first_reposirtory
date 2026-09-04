#!/usr/bin/env python3
"""Быстрые проверки собранного сайта. Ничего устанавливать не нужно.

Запуск (после python3 build.py):
    python3 tests/check_static.py

Что проверяет:
  1. внутренние ссылки ведут на существующие файлы;
  2. у каждой страницы свои title и description, они не пустые и не длиннее нормы;
  3. у каждой картинки есть подпись alt;
  4. уровни заголовков не перескакивают (h1 -> h3 без h2);
  5. в карте сайта нет чужих и битых адресов;
  6. в собранном сайте не осталось незаполненных мест вида {{...}}.

Возвращает код 1, если что-то не так, — поэтому годится для проверки
при выкладке: сломанная сборка не уедет на сайт.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
problems: list[str] = []


def fail(where: str, what: str) -> None:
    problems.append(f"{where}: {what}")


# Страницы сайта. Папка assets/promo — служебная (картинки для сторис),
# к сайту не относится и правил про заголовки на неё не распространяется.
SKIP = ("assets/promo/",)


def pages() -> list[Path]:
    return sorted(p for p in DIST.rglob("*.html")
                  if not any(s in str(p.relative_to(DIST)).replace("\\", "/") for s in SKIP))


def rel(p: Path) -> str:
    return "/" + str(p.relative_to(DIST)).replace("index.html", "")


def check_links(html: str, page: Path) -> None:
    for href in re.findall(r'href="([^"]+)"', html):
        if href.startswith(("http", "mailto:", "tel:", "#", "data:")):
            continue
        clean = href.split("#")[0].split("?")[0]
        if not clean:
            continue
        # Ссылка может быть от корня сайта (/uslugi/) или относительной
        # (photo.jpg) — разбираем оба случая, иначе проверка врёт.
        base = DIST if clean.startswith("/") else page.parent
        target = (base / clean.lstrip("/")).resolve()
        if target.is_dir() or not target.suffix:
            target = target / "index.html"
        if not target.exists():
            fail(rel(page), f"ссылка ведёт в никуда: {href}")


def check_meta(html: str, page: Path, seen: dict) -> None:
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    desc = re.search(r'<meta name="description" content="(.*?)"', html, re.S)
    if not title or not title.group(1).strip():
        fail(rel(page), "нет заголовка страницы (title)")
    else:
        t = title.group(1).strip()
        if len(t) > 70:
            fail(rel(page), f"заголовок длиннее 70 знаков ({len(t)}) — поиск обрежет")
        if t in seen.setdefault("title", {}):
            fail(rel(page), f"заголовок повторяет {seen['title'][t]}")
        seen["title"][t] = rel(page)
    if not desc or not desc.group(1).strip():
        fail(rel(page), "нет описания страницы (description)")
    else:
        d = desc.group(1).strip()
        if len(d) > 200:
            fail(rel(page), f"описание длиннее 200 знаков ({len(d)})")
        if d in seen.setdefault("desc", {}):
            fail(rel(page), f"описание повторяет {seen['desc'][d]}")
        seen["desc"][d] = rel(page)


def check_images(html: str, page: Path) -> None:
    for tag in re.findall(r"<img\b[^>]*>", html):
        if 'alt="' not in tag:
            fail(rel(page), f"у картинки нет подписи alt: {tag[:70]}")


def check_headings(html: str, page: Path) -> None:
    levels = [int(m.group(1)) for m in re.finditer(r"<h([1-4])\b", html)]
    if not levels:
        return
    if levels[0] != 1:
        fail(rel(page), f"страница начинается не с h1, а с h{levels[0]}")
    if levels.count(1) > 1:
        fail(rel(page), f"на странице {levels.count(1)} заголовков h1, должен быть один")
    prev = levels[0]
    for lvl in levels[1:]:
        if lvl > prev + 1:
            fail(rel(page), f"уровень заголовка перескочил: h{prev} -> h{lvl}")
            break
        prev = lvl


def check_placeholders(html: str, page: Path) -> None:
    left = re.findall(r"\{\{\w+\}\}", html)
    if left:
        fail(rel(page), f"осталось незаполненное место: {left[0]}")


def check_sitemap() -> None:
    path = DIST / "sitemap.xml"
    if not path.exists():
        fail("sitemap.xml", "файла нет")
        return
    xml = path.read_text(encoding="utf-8")
    if "http://www.sitemaps.org/schemas/sitemap/0.9" not in xml:
        fail("sitemap.xml", "неверное пространство имён")
    for loc in re.findall(r"<loc>(.*?)</loc>", xml):
        tail = re.sub(r"^https?://[^/]+", "", loc)
        target = DIST / tail.strip("/") / "index.html" if tail.strip("/") else DIST / "index.html"
        if not target.exists():
            fail("sitemap.xml", f"адреса нет на диске: {loc}")


def main() -> int:
    if not DIST.exists():
        print("Сначала соберите сайт: python3 build.py")
        return 1
    seen: dict = {}
    files = pages()
    for page in files:
        html = page.read_text(encoding="utf-8")
        check_links(html, page)
        check_meta(html, page, seen)
        check_images(html, page)
        check_headings(html, page)
        check_placeholders(html, page)
    check_sitemap()

    print(f"Проверено страниц: {len(files)}")
    if problems:
        print(f"\nНайдено проблем: {len(problems)}")
        for p in problems:
            print("  •", p)
        return 1
    print("Проблем не найдено.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
