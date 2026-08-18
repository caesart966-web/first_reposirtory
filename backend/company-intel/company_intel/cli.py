"""Командная строка: `company-intel search --name ... --inn ...`."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from .config import KEY_HELP, Config
from .models import Query
from .pipeline import run_pipeline
from .report import to_csv, to_markdown, to_text
from .sources import describe_sources

EPILOG = """\
Примеры:
  company-intel search --name "ООО Ромашка" --city Москва
  company-intel search --inn 7707083893 --format md --out romashka.md
  company-intel search --domain romashka.ru --guess-emails
  company-intel sources          # какие источники готовы и каких ключей не хватает
  company-intel demo             # офлайн-демонстрация на встроенном примере
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="company-intel",
        description="Сбор данных о компании из открытых источников",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--verbose", action="count", default=0, help="подробный лог")
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="искать данные о компании")
    known = search.add_argument_group("что известно о компании")
    known.add_argument("--name", help="наименование, например «ООО Ромашка»")
    known.add_argument("--inn", help="ИНН")
    known.add_argument("--ogrn", help="ОГРН/ОГРНИП")
    known.add_argument("--domain", help="сайт или домен")
    known.add_argument("--email", help="известная почта")
    known.add_argument("--phone", help="известный телефон")
    known.add_argument("--person", help="ФИО руководителя или сотрудника")
    known.add_argument("--city", help="город (уточняет поиск)")
    known.add_argument("--term", action="append", default=[],
                       help="дополнительный поисковый термин (можно несколько раз)")

    out = search.add_argument_group("вывод")
    out.add_argument("--format", choices=("text", "md", "json", "csv"), default="text")
    out.add_argument("--out", help="файл для отчёта (формат определяется по расширению)")
    out.add_argument("--min-confidence", type=float, default=0.25,
                     help="порог уверенности для попадания в отчёт (по умолчанию 0.25)")

    behaviour = search.add_argument_group("поведение сборщика")
    behaviour.add_argument("--sources", help="только эти источники, через запятую")
    behaviour.add_argument("--exclude", help="исключить источники, через запятую")
    behaviour.add_argument("--guess-emails", action="store_true",
                           help="добавить гипотезы адресов по шаблону (помечаются отдельно)")
    behaviour.add_argument("--rounds", type=int, default=3, help="число раундов раскрутки")
    behaviour.add_argument("--delay", type=float, default=1.0,
                           help="пауза между запросами к одному хосту, сек")
    behaviour.add_argument("--concurrency", type=int, default=8)
    behaviour.add_argument("--timeout", type=float, default=20.0)
    behaviour.add_argument("--max-pages", type=int, default=12,
                           help="сколько страниц обходить на сайте компании")
    behaviour.add_argument("--no-cache", action="store_true", help="не использовать HTTP-кэш")
    behaviour.add_argument("--cache", default=".cache/http.sqlite3", help="путь к файлу кэша")
    behaviour.add_argument("--no-follow-search", action="store_true",
                           help="не заходить на страницы из поисковой выдачи")
    behaviour.add_argument(
        "--ignore-robots", action="store_true",
        help="игнорировать robots.txt (только для своих сайтов и с разрешения владельца)",
    )

    sub.add_parser("sources", help="показать источники и статус ключей")
    demo = sub.add_parser("demo", help="офлайн-демонстрация разбора без сети")
    demo.add_argument("--format", choices=("text", "md", "json", "csv"), default="text")
    return parser


def _config_from_args(args) -> Config:
    return Config.from_env(
        per_host_delay=args.delay,
        max_concurrency=args.concurrency,
        timeout=args.timeout,
        respect_robots=not args.ignore_robots,
        cache_path=None if args.no_cache else args.cache,
        max_pages_per_site=args.max_pages,
        max_rounds=max(1, args.rounds),
        enabled_sources=[s.strip() for s in args.sources.split(",")] if args.sources else None,
        disabled_sources=[s.strip() for s in args.exclude.split(",")] if args.exclude else [],
        allow_email_guessing=args.guess_emails,
        fetch_search_results=not args.no_follow_search,
    )


def _render(profile, fmt: str, min_confidence: float) -> str:
    if fmt == "json":
        return profile.to_json()
    if fmt == "md":
        return to_markdown(profile, min_confidence)
    if fmt == "csv":
        return to_csv(profile, min_confidence)
    return to_text(profile, min_confidence)


def _fmt_from_path(path: str, fallback: str) -> str:
    suffix = Path(path).suffix.lower()
    return {".md": "md", ".json": "json", ".csv": "csv", ".txt": "text"}.get(suffix, fallback)


def cmd_search(args) -> int:
    query = Query(
        name=args.name, inn=args.inn, ogrn=args.ogrn, domain=args.domain,
        email=args.email, phone=args.phone, person=args.person, city=args.city,
        extra_terms=list(args.term or []),
    )
    if query.is_empty():
        print("Укажите хотя бы один признак: --name, --inn, --domain, --email, --phone",
              file=sys.stderr)
        return 2
    config = _config_from_args(args)
    profile = asyncio.run(run_pipeline(query, config))

    fmt = _fmt_from_path(args.out, args.format) if args.out else args.format
    text = _render(profile, fmt, args.min_confidence)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        found = sum(len(v) for v in profile.attributes.values())
        print(f"Отчёт сохранён: {args.out} (значений: {found}, "
              f"находок: {profile.stats.get('findings', 0)})")
    else:
        print(text)
    for warning in profile.warnings[:10]:
        print(f"! {warning}", file=sys.stderr)
    return 0


def cmd_sources(args) -> int:
    config = Config.from_env()
    rows = describe_sources(config)
    width = max(len(r["name"]) for r in rows)
    print("Источники:\n")
    for row in rows:
        mark = "✓" if row["ready"] else "·"
        line = f" {mark} {row['name'].ljust(width)}  {row['title']}"
        if not row["ready"]:
            line += f"  — {row['reason']}"
        print(line)
    print("\nКлючи API (переменные окружения или файл .env):\n")
    for name, help_text in KEY_HELP.items():
        status = "задан" if config.key(name) else "не задан"
        print(f"  {name.ljust(18)} [{status}]  {help_text}")
    return 0


def cmd_demo(args) -> int:
    """Разбор встроенного примера страницы — работает без сети и ключей."""
    from .extract import parse_page
    from .merge import apply_relevance, merge_findings
    from .models import Finding, Profile, Provenance, Query as Q

    fixture = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "company_site.html"
    if not fixture.is_file():
        print(f"нет файла примера: {fixture}", file=sys.stderr)
        return 1
    url = "https://romashka-stroy.ru/contacts"
    page = parse_page(fixture.read_text(encoding="utf-8"), url)
    prov = Provenance(source="website", url=url, note="демо-пример")
    findings: list[Finding] = []
    for email in page.emails:
        findings.append(Finding("email", email, prov, 0.78))
    for phone, ext, label in page.phones:
        findings.append(Finding("phone", phone, prov, 0.78, {"extension": ext, "label": label}))
    for kind, values in page.requisites.items():
        for value in values:
            findings.append(Finding(kind, value, prov, 0.88))
    for address in page.addresses:
        findings.append(Finding("address", address, prov, 0.7))
    for fio, position in page.persons:
        findings.append(Finding("person", fio, prov, 0.65, {"position": position}))
    for network, link in page.socials:
        findings.append(Finding("social", link, prov, 0.8, {"network": network}))

    profile = Profile(query=Q(name="ООО «Ромашка-Строй»", domain="romashka-stroy.ru"))
    profile.attributes = merge_findings(findings)
    profile.warnings.extend(apply_relevance(profile.attributes, profile.query))
    profile.stats = {"findings": len(findings), "by_source": {"website": len(findings)},
                     "http": {"requests": 0, "cached": 0}, "rounds": 1}
    profile.finished_at = profile.started_at
    print(_render(profile, args.format, 0.25))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    level = logging.WARNING - min(args.verbose, 2) * 10
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")
    if args.command == "search":
        return cmd_search(args)
    if args.command == "sources":
        return cmd_sources(args)
    if args.command == "demo":
        return cmd_demo(args)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
