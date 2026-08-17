# -*- coding: utf-8 -*-
"""Формирование пакета документов для одной компании.

Порядок работы жёстко зафиксирован:

    реквизиты → проверка обязательных полей → сборка значений
    → заполнение шаблонов → контроль качества → результат

Документы объявляются готовыми только после контроля качества.
Любой сбой на любом шаге останавливает выпуск этого документа.

Защита от подмешивания чужих данных:
  * генерация работает с КОПИЕЙ объекта компании, сделанной на входе;
  * значения переменных собираются заново при каждом запуске;
  * готовые файлы проверяются на присутствие реквизитов ИМЕННО этой компании
    и на отсутствие чужих.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import app_logging
from .context_builder import ContextResult, build_context, load_attorney
from .docx_engine import TemplateError, fill_template, scan_placeholders
from .models import FIELD_BY_KEY, CompanyData
from .quality_control import (QualityReport, check_document, lookup_variable,
                              required_variables_for)

WINDOWS_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class GeneratorError(Exception):
    """Ошибка формирования документов с текстом для пользователя."""


@dataclass
class DocumentSpec:
    """Описание документа из config/documents.json."""

    id: str
    title: str
    template: str
    output_name: str
    enabled: bool = True


@dataclass
class Readiness:
    """Готовность одного документа к формированию."""

    spec: DocumentSpec
    missing: list[str] = field(default_factory=list)       # понятные названия полей
    missing_keys: list[str] = field(default_factory=list)  # ключи полей
    unknown_variables: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing and not self.unknown_variables


@dataclass
class GenerationResult:
    """Итог формирования пакета документов."""

    folder: Path | None = None
    created: list[Path] = field(default_factory=list)
    pdf: list[Path] = field(default_factory=list)
    quality: list[QualityReport] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.created) and all(report.ok for report in self.quality)


class Project:
    """Пути, настройки и шаблоны проекта."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root else Path(__file__).resolve().parent.parent
        self.config_dir = self.root / "config"
        self.templates_dir = self.root / "templates"
        self.logs_dir = self.root / "logs"

        self.documents_config = self._load_json("documents.json")
        self.variables = self._load_json("variables.json").get("variables", {})
        self.output_root = self.root / self.documents_config.get("output_root", "output")

        self.documents: list[DocumentSpec] = []
        for item in self.documents_config.get("documents", []):
            self.documents.append(DocumentSpec(
                id=item["id"],
                title=item["title"],
                template=item["template"],
                output_name=item.get("output_name", item["template"]),
                enabled=bool(item.get("enabled", True)),
            ))

    # ------------------------------------------------------------------
    def _load_json(self, name: str) -> dict:
        path = self.config_dir / name
        if not path.exists():
            raise GeneratorError(
                f"Не найден файл настроек «{name}» в папке config.\n"
                f"Восстановите его из архива программы."
            )
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise GeneratorError(
                f"Файл настроек «{name}» повреждён (строка {exc.lineno}): {exc.msg}.\n"
                f"Проверьте, что при правке не потерялись запятые или кавычки."
            ) from exc

    def enabled_documents(self) -> list[DocumentSpec]:
        return [d for d in self.documents if d.enabled]

    def template_path(self, spec: DocumentSpec) -> Path:
        return self.templates_dir / spec.template

    def placeholders(self, spec: DocumentSpec) -> list[str]:
        path = self.template_path(spec)
        if not path.exists():
            raise GeneratorError(
                f"Не найден шаблон «{spec.template}» для документа «{spec.title}».\n"
                f"Положите файл в папку: {self.templates_dir}"
            )
        try:
            return scan_placeholders(path)
        except TemplateError as exc:
            raise GeneratorError(str(exc)) from exc

    def attorney(self) -> dict[str, str]:
        return load_attorney(self.config_dir)


# ---------------------------------------------------------------- готовность
def check_readiness(project: Project, company: CompanyData,
                    documents: list[DocumentSpec] | None = None) -> list[Readiness]:
    """Каких обязательных данных не хватает для каждого документа."""
    documents = documents if documents is not None else project.enabled_documents()
    results: list[Readiness] = []

    for spec in documents:
        readiness = Readiness(spec)
        for name in project.placeholders(spec):
            info = lookup_variable(name, project.variables)
            if info is None:
                readiness.unknown_variables.append(name)
                continue
            source = info.get("field")
            if not source or not info.get("required"):
                continue
            if company.get(source):
                continue
            if source in readiness.missing_keys:
                continue
            readiness.missing_keys.append(source)
            spec_field = FIELD_BY_KEY.get(source)
            readiness.missing.append(spec_field.label if spec_field else source)
        results.append(readiness)

    return results


def company_folder_name(company: CompanyData) -> str:
    """«9701329181_ООО ТЭС» — имя папки, безопасное для Windows."""
    name = company.short_name or company.full_name or "Без названия"
    name = name.replace("«", "").replace("»", "").replace('"', "")
    name = WINDOWS_FORBIDDEN.sub(" ", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    inn = re.sub(r"\D", "", company.inn) or "без_ИНН"
    folder = f"{inn}_{name}".strip("_ ")
    return folder[:120] or "Без названия"


# ---------------------------------------------------------------- генерация
def generate(project: Project, company_input: CompanyData,
             documents: list[DocumentSpec] | None = None,
             make_pdf: bool = True,
             today: date | None = None) -> GenerationResult:
    """Сформировать документы для ОДНОЙ компании."""
    log = app_logging.get()

    # Работаем с копией: исходный объект никто по пути не изменит.
    company = company_input.copy()
    documents = documents if documents is not None else project.enabled_documents()
    if not documents:
        raise GeneratorError("В настройках не включён ни один документ.")

    result = GenerationResult()

    readiness = check_readiness(project, company, documents)
    blocked = [r for r in readiness if not r.ok]
    if blocked:
        lines = ["Для формирования документов не хватает следующих данных:", ""]
        number = 1
        seen: set[str] = set()
        for item in blocked:
            for label in item.missing:
                if label in seen:
                    continue
                seen.add(label)
                lines.append(f"{number}. {label}")
                number += 1
        for item in blocked:
            for name in item.unknown_variables:
                lines.append(
                    f"{number}. Переменная {{{{{name}}}}} из шаблона «{item.spec.template}» "
                    f"не описана в config/variables.json"
                )
                number += 1
        lines.append("")
        lines.append("Заполните недостающие поля и повторите.")
        raise GeneratorError("\n".join(lines))

    context: ContextResult = build_context(company, project.attorney(), today=today)
    result.notes.extend(context.notes)
    log.info("Формирование документов: %s", app_logging.safe_company(company))
    log.debug("Переменные: %s", app_logging.safe_values(context.values))

    folder = project.output_root / company_folder_name(company)
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise GeneratorError(
            f"Не удалось создать папку для документов:\n{folder}\n\n"
            f"Проверьте, что диск доступен и на нём есть свободное место.\n"
            f"Техническая причина: {exc}"
        ) from exc
    result.folder = folder

    for spec in documents:
        template = project.template_path(spec)
        target = folder / spec.output_name
        placeholders = project.placeholders(spec)

        try:
            report = fill_template(template, target, context.values)
        except TemplateError as exc:
            log.error("Ошибка заполнения «%s»: %s", spec.template, exc)
            raise GeneratorError(str(exc)) from exc

        if report.unknown:
            log.warning("Шаблон «%s»: неизвестные переменные %s",
                        spec.template, ", ".join(report.unknown))
            result.notes.append(
                f"«{spec.title}»: в шаблоне есть переменные, для которых нет данных: "
                + ", ".join("{{%s}}" % name for name in report.unknown)
            )

        quality = check_document(
            target, spec.title, company, context.values,
            required_variables_for(placeholders, project.variables),
            placeholders,
        )
        result.quality.append(quality)

        if quality.ok:
            result.created.append(target)
            log.info("Готов документ «%s» (%d подстановок)", spec.title, report.total)
        else:
            log.error("Документ «%s» не прошёл контроль: %s",
                      spec.title, "; ".join(quality.problems))

    # PDF — только для документов, прошедших контроль.
    if make_pdf and result.created:
        from .pdf_export import convert_many
        pdfs, pdf_note = convert_many(result.created)
        result.pdf.extend(pdfs)
        if pdf_note:
            result.notes.append(pdf_note)

    return result
