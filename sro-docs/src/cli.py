# -*- coding: utf-8 -*-
"""Консольный режим: то же самое, что в окне программы, но из командной строки.

Нужен для проверки и для тех случаев, когда окно не открывается.

    python -m src.cli --sro-list                       # какие СРО настроены
    python -m src.cli --sro СССС --card Карточка.docx
    python -m src.cli --text "ООО «Ромашка» ИНН 7812345678 ..."
    python -m src.cli --card input/Карточка.docx --set actual_address="г. СПб, ..."
    python -m src.cli --map            # карта соответствия полей и переменных
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):  # запуск как «python src/cli.py»
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "src"

from . import app_logging  # noqa: E402
from .company_parser import parse_card, parse_text  # noqa: E402
from .context_builder import build_context  # noqa: E402
from .document_generator import (GeneratorError, Project, check_readiness,  # noqa: E402
                                 generate)
from .models import DOC_PARAM_FIELDS, FIELD_SPECS, CompanyData  # noqa: E402
from .quality_control import lookup_variable  # noqa: E402
from .readers import ReadError, read_card  # noqa: E402
from .sro_registry import SroError  # noqa: E402
from .validators import validate_company  # noqa: E402


def print_card(company: CompanyData) -> None:
    print()
    print("=" * 62)
    print("РЕКВИЗИТЫ КОМПАНИИ")
    print("=" * 62)
    group = None
    for spec in FIELD_SPECS:
        value = company.get(spec.key)
        if not value and not spec.used_by_templates:
            continue
        if spec.group != group:
            group = spec.group
            print(f"\n-- {group} --")
        mark = " " if value else "!"
        print(f" {mark} {spec.label + ':':<32} {value or '(не заполнено)'}")
    print()


def print_readiness(project: Project, company: CompanyData) -> bool:
    ready = True
    print("=" * 62)
    print("ГОТОВНОСТЬ ДОКУМЕНТОВ")
    print("=" * 62)
    for item in check_readiness(project, company):
        print(f"\n### {item.spec.title}")
        if item.ok:
            print("    Все обязательные поля заполнены.")
        else:
            ready = False
            for label in item.missing:
                print(f"    отсутствует: {label}")
            for name in item.unknown_variables:
                print(f"    переменная {{{{{name}}}}} не описана в config/variables.json")
    print()
    return ready


def print_sro_list(project: Project) -> None:
    print("НАСТРОЕННЫЕ САМОРЕГУЛИРУЕМЫЕ ОРГАНИЗАЦИИ\n")
    for profile in project.all_sro:
        mark = "→" if profile.key == project.sro.key else " "
        print(f" {mark} {profile.short_name:<12} {profile.name}")
        if profile.city:
            print(f"      город: {profile.city}")
        print(f"      папка: sro/{profile.key}")
        for spec in profile.enabled_documents():
            print(f"      документ: {spec.title}  ({spec.template})")
        if profile.note:
            print(f"      примечание: {profile.note}")
        print()
    print("«→» — СРО, выбранная сейчас. Сменить: --sro <название>")


def print_field_map(project: Project) -> None:
    print(f"КАРТА СООТВЕТСТВИЯ — СРО «{project.sro.short_name}»")
    print("поле данных → переменная → документ → место\n")
    rows: list[tuple[str, str, str, str]] = []
    for spec in project.enabled_documents():
        for name in project.placeholders(spec):
            info = lookup_variable(name, project.variables) or {}
            rows.append((info.get("field") or "—", "{{%s}}" % name,
                         spec.title, info.get("where", "")))
    width = max(len(r[0]) for r in rows) + 2
    for source, variable, document, where in rows:
        print(f"{source:<{width}} {variable:<32} {document:<28} {where}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Заполнение документов на вступление в СРО")
    parser.add_argument("--sro", help="в какую СРО подаём (название или папка)")
    parser.add_argument("--sro-list", action="store_true",
                        help="показать список настроенных СРО")
    parser.add_argument("--card", help="файл карточки компании (DOCX/XLSX/PDF/TXT)")
    parser.add_argument("--text", help="реквизиты обычным текстом")
    parser.add_argument("--set", action="append", default=[], metavar="ПОЛЕ=ЗНАЧЕНИЕ",
                        help="задать или исправить поле вручную")
    parser.add_argument("--no-pdf", action="store_true", help="не создавать PDF")
    parser.add_argument("--dry-run", action="store_true",
                        help="только показать карточку и готовность")
    parser.add_argument("--map", action="store_true",
                        help="показать карту соответствия полей и переменных")
    parser.add_argument("--verbose", action="store_true", help="подробный вывод")
    args = parser.parse_args(argv)

    try:
        project = Project(sro=args.sro)
    except (GeneratorError, SroError) as exc:
        print(f"\n{exc}\n", file=sys.stderr)
        return 2
    app_logging.setup(project.logs_dir, verbose=args.verbose)

    if args.sro_list:
        print_sro_list(project)
        return 0
    if args.map:
        print_field_map(project)
        return 0

    if not args.card and not args.text and not args.set:
        parser.error("укажите --card, --text или хотя бы одно --set")

    print()
    print(f"СРО: {project.sro.name}")
    if project.sro.note:
        print(f"     {project.sro.note}")

    company = project.new_company()
    notes: list[str] = []
    derived: dict[str, str] = {}

    try:
        parsed = None
        if args.card:
            parsed = parse_card(read_card(args.card))
        elif args.text:
            parsed = parse_text(args.text)
        if parsed is not None:
            defaults = company           # умолчания, полученные из настроек
            company = parsed.company
            for key in DOC_PARAM_FIELDS:
                company.set(key, defaults.get(key))
            notes += parsed.notes
            derived.update(parsed.derived)
    except ReadError as exc:
        print(f"\nНе удалось прочитать карточку:\n{exc}\n", file=sys.stderr)
        return 2

    for item in args.set:
        if "=" not in item:
            parser.error(f"неверный формат --set {item!r}, нужно ПОЛЕ=ЗНАЧЕНИЕ")
        key, value = item.split("=", 1)
        key = key.strip()
        if key.startswith("override:"):
            company.overrides[key.split(":", 1)[1]] = value.strip()
        elif hasattr(company, key):
            company.set(key, value)
        else:
            parser.error(f"неизвестное поле {key!r}")

    notes += project.apply_auto_fill(company)

    print_card(company)

    for key, note in derived.items():
        print(f"  ВНИМАНИЕ ({key}): {note}")
    for note in notes:
        print(f"  ПРИМЕЧАНИЕ: {note}")
    if derived or notes:
        print()

    problems = validate_company(company)
    if problems:
        print("-" * 62)
        print("ЗАМЕЧАНИЯ К РЕКВИЗИТАМ")
        print("-" * 62)
        for issue in problems:
            print(f"  [{'ошибка' if issue.is_error else 'внимание'}] {issue.text}")
        print()

    ready = print_readiness(project, company)

    context = build_context(company, project.attorney(), sro=project.sro)
    for note in context.notes:
        print(f"  ПРИМЕЧАНИЕ: {note}")
    if context.confirmations:
        print("-" * 62)
        print("ТРЕБУЕТСЯ ПОДТВЕРЖДЕНИЕ")
        print("-" * 62)
        for item in context.confirmations:
            print(f"  {item.label}")
            print(f"      программа предлагает: «{item.suggestion}»")
            print(f"      причина проверки: {item.reason}")
            print(f"      подтвердить: --set override:{item.key}=«ваш вариант»")
        print()

    if args.dry_run:
        return 0
    if any(issue.is_error for issue in problems):
        print("Формирование остановлено: сначала исправьте ошибки в реквизитах.\n")
        return 3
    if not ready:
        print("Формирование остановлено: не хватает обязательных данных.\n")
        return 3

    try:
        result = generate(project, company, make_pdf=not args.no_pdf)
    except GeneratorError as exc:
        print(f"\n{exc}\n", file=sys.stderr)
        return 3

    print("=" * 62)
    print("РЕЗУЛЬТАТ")
    print("=" * 62)
    print(f"Папка: {result.folder}")
    for path in result.created:
        print(f"  создан: {path.name}")
    for path in result.pdf:
        print(f"  создан: {path.name}")
    for report in result.quality:
        status = "проверен" if report.ok else "НЕ ГОТОВ"
        print(f"  [{status}] {report.document}")
        for problem in report.problems:
            print(f"      проблема: {problem}")
        for warning in report.warnings:
            print(f"      внимание: {warning}")
    for note in result.notes:
        print(f"  примечание: {note}")
    print()
    return 0 if result.ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
