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
from .context_builder import ContextResult, build_context
from .docx_engine import TemplateError, fill_template, scan_placeholders
from .company_parser import split_company_name
from .models import (ENTREPRENEUR_DEFAULTS, FIELD_BY_KEY,  # noqa: E402
                     CompanyData)
from .quality_control import (QualityReport, check_document, lookup_variable,
                              required_variables_for)
from .sro_registry import DocumentSpec, SroError, SroProfile, discover, find

WINDOWS_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class GeneratorError(Exception):
    """Ошибка формирования документов с текстом для пользователя."""


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
    """Пути, общие настройки и ВЫБРАННАЯ саморегулируемая организация.

    Всё, что зависит от СРО (бланки, документы, доверенное лицо, умолчания),
    берётся из профиля `self.sro`. Всё общее (карта переменных, папка вывода)
    — из config/app.json. Смена СРО делается методом `use_sro()`.
    """

    def __init__(self, root: Path | str | None = None,
                 sro: str | SroProfile | None = None) -> None:
        self.root = Path(root) if root else Path(__file__).resolve().parent.parent
        self.config_dir = self.root / "config"
        self.logs_dir = self.root / "logs"

        self.app_config = self._load_json("app.json", required=False)
        self.variables = self._load_json("variables.json").get("variables", {})
        self.output_root = self.root / self.app_config.get("output_root", "output")

        self.all_sro: list[SroProfile] = discover(self.root)
        self.sro: SroProfile = self._choose(sro)

    # ------------------------------------------------------------------ СРО
    def _choose(self, wanted: str | SroProfile | None) -> SroProfile:
        """Какую СРО использовать.

        Если СРО названа явно, а такой нет — это ОШИБКА, а не повод молча
        взять запомненную: иначе документы уедут не в ту СРО.
        Запомненный выбор используется, только когда явного нет.
        """
        if isinstance(wanted, SroProfile):
            return wanted

        if wanted:
            found = find(self.all_sro, str(wanted))
            if found is not None:
                return found
            names = ", ".join(f"«{p.short_name}»" for p in self.all_sro)
            raise GeneratorError(
                f"СРО «{wanted}» не найдена.\n"
                f"Доступны: {names}"
            )

        remembered = self.app_config.get("last_sro")
        if remembered:
            found = find(self.all_sro, str(remembered))
            if found is not None:
                return found
        return self.all_sro[0]

    def use_sro(self, wanted: str | SroProfile, remember: bool = True) -> SroProfile:
        """Переключиться на другую СРО.

        `remember=False` — временное переключение без записи в настройки
        (нужно служебным скриптам, которые обходят все СРО подряд).
        """
        self.sro = self._choose(wanted)
        if remember:
            self.remember_sro()
        return self.sro

    def remember_sro(self) -> None:
        """Записать выбранную СРО в config/app.json — чтобы не выбирать каждый раз."""
        path = self.config_dir / "app.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            data["last_sro"] = self.sro.key
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except (OSError, json.JSONDecodeError) as exc:
            # Не смертельно: в следующий раз просто спросим заново.
            app_logging.get().warning("Не удалось запомнить выбор СРО: %s", exc)

    # ---------------------------------------------------- свойства выбранной СРО
    @property
    def templates_dir(self) -> Path:
        return self.sro.templates_dir

    @property
    def defaults(self) -> dict[str, str]:
        return self.sro.defaults

    @property
    def auto_fill(self) -> dict[str, str]:
        return self.sro.auto_fill

    @property
    def documents(self) -> list[DocumentSpec]:
        return self.sro.documents

    # ------------------------------------------------------------------
    def _load_json(self, name: str, required: bool = True) -> dict:
        path = self.config_dir / name
        if not path.exists():
            if not required:
                return {}
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

    def new_company(self) -> CompanyData:
        """Пустая карточка компании со значениями по умолчанию из настроек.

        Здесь и только здесь появляются умолчания вроде «№ б/н» у доверенности.
        Если пользователь потом очистит поле, оно останется пустым: умолчания
        применяются к НОВОЙ карточке, а не при каждой проверке.
        """
        company = CompanyData()
        for key, value in self.defaults.items():
            company.set(key, value)
        if not company.doc_date:
            company.doc_date = date.today().strftime("%d.%m.%Y")
        return company

    def apply_applicant_defaults(self, company: CompanyData) -> list[str]:
        """Подставить умолчания, зависящие от типа заявителя.

        У предпринимателя должность подписанта и основание полномочий
        всегда одни и те же — «Индивидуальный предприниматель» и «Лист
        записи ЕГРИП». Это подсказка в форме: заполненное поле не трогаем,
        и человек всегда может вписать своё.
        """
        if not company.is_entrepreneur:
            return []
        notes: list[str] = []
        for key, value in ENTREPRENEUR_DEFAULTS.items():
            if company.get(key):
                continue
            company.set(key, value)
            spec = FIELD_BY_KEY.get(key)
            notes.append(
                f"{company.label_for(key) if spec else key}: подставлено "
                f"«{value}» — как обычно у предпринимателя. Если у вас иначе, "
                f"впишите своё."
            )
        # Предприниматель подписывает документы сам.
        if not company.director_full_name and company.full_name:
            _, _, bare = split_company_name(company.full_name)
            if bare and len(bare.split()) >= 2:
                company.set("director_full_name", bare)
                notes.append(
                    f"ФИО подписанта взято из наименования: «{bare}». "
                    f"Предприниматель подписывает документы сам."
                )
        return notes

    def apply_auto_fill(self, company: CompanyData) -> list[str]:
        """Заполнить пустые поля из других полей по правилам config/auto_fill.

        Сейчас правило одно: фактический адрес берётся из юридического —
        у компаний они совпадают. Заполненное поле НЕ перезаписывается,
        поэтому редкий случай «адреса разные» решается простым вводом
        фактического адреса вручную.

        Возвращает понятные пояснения о том, что было подставлено.
        """
        notes: list[str] = []
        for target, source in self.auto_fill.items():
            if company.get(target) or not company.get(source):
                continue
            company.set(target, company.get(source))
            target_field = FIELD_BY_KEY.get(target)
            source_field = FIELD_BY_KEY.get(source)
            notes.append(
                f"{target_field.label if target_field else target} подставлен "
                f"из поля «{source_field.label if source_field else source}». "
                f"Если у этой компании он другой — впишите свой."
            )
        return notes

    def enabled_documents(self) -> list[DocumentSpec]:
        return [d for d in self.documents if d.enabled]

    def template_path(self, spec: DocumentSpec) -> Path:
        return self.templates_dir / spec.template

    def placeholders(self, spec: DocumentSpec) -> list[str]:
        path = self.template_path(spec)
        if not path.exists():
            raise GeneratorError(
                f"Не найден шаблон «{spec.template}» для документа «{spec.title}»\n"
                f"СРО «{self.sro.short_name}».\n"
                f"Положите файл в папку: {self.templates_dir}"
            )
        try:
            return scan_placeholders(path)
        except TemplateError as exc:
            raise GeneratorError(str(exc)) from exc

    def attorney(self) -> dict[str, str]:
        try:
            return self.sro.attorney()
        except SroError as exc:
            raise GeneratorError(str(exc)) from exc


# ---------------------------------------------------------------- готовность
def check_readiness(project: Project, company: CompanyData,
                    documents: list[DocumentSpec] | None = None) -> list[Readiness]:
    """Каких обязательных данных не хватает для каждого документа."""
    documents = documents if documents is not None else project.enabled_documents()
    results: list[Readiness] = []
    if not documents:
        return results

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
            # Переменная не для этого заявителя: у предпринимателя нет КПП,
            # и требовать его — значит просить придумать несуществующее.
            only_for = info.get("only_for")
            if only_for and only_for != company.applicant_kind:
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


def safe_folder_name(name: str, fallback: str = "Без названия") -> str:
    """Имя папки, безопасное для Windows."""
    name = (name or "").replace("«", "").replace("»", "").replace('"', "")
    name = WINDOWS_FORBIDDEN.sub(" ", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:120] or fallback


def company_folder_name(company: CompanyData) -> str:
    """«9701329181_ООО ТЭС» — папка компании."""
    name = safe_folder_name(company.short_name or company.full_name)
    inn = re.sub(r"\D", "", company.inn) or "без_ИНН"
    return f"{inn}_{name}".strip("_ ")[:120] or "Без названия"


def output_folder(project: "Project", company: CompanyData) -> Path:
    """Папка результата: output / компания / СРО.

    Компания сверху, потому что одну и ту же компанию нередко подают
    в несколько СРО — так все её документы лежат рядом.
    """
    return (project.output_root
            / company_folder_name(company)
            / safe_folder_name(project.sro.short_name, "СРО"))


def _check_levels(project: "Project", company: CompanyData) -> None:
    """Выбранный уровень ответственности должен существовать у ЭТОЙ СРО.

    У строительных СРО уровней пять, у проектировщиков и изыскателей — четыре.
    Без проверки программа молча оставила бы таблицу без отметки, и документ
    ушёл бы в СРО с незаявленным уровнем.
    """
    checks = (
        ("harm_fund_level", project.sro.harm_levels,
         "компенсационный фонд возмещения вреда", True),
        ("contract_fund_level", project.sro.contract_levels,
         "компенсационный фонд обеспечения договорных обязательств", False),
    )
    for field_name, levels, what in ((c[0], c[1], c[2]) for c in checks):
        chosen = company.get(field_name)
        if not chosen:
            continue
        if not levels:
            continue
        if chosen not in [item.key for item in levels]:
            available = "\n".join(f"  {item.key} — {item.label}" for item in levels)
            raise GeneratorError(
                f"У СРО «{project.sro.short_name}» нет уровня №{chosen} "
                f"({what}).\n\nДоступные уровни:\n{available}\n\n"
                f"Выберите уровень из этого списка."
            )


# ---------------------------------------------------------------- генерация
def generate(project: Project, company_input: CompanyData,
             documents: list[DocumentSpec] | None = None,
             make_pdf: bool = True,
             today: date | None = None) -> GenerationResult:
    """Сформировать документы для ОДНОЙ компании."""
    log = app_logging.get()

    # Работаем с копией: исходный объект никто по пути не изменит.
    company = company_input.copy()
    result_notes = project.apply_applicant_defaults(company)
    result_notes += project.apply_auto_fill(company)
    documents = documents if documents is not None else project.enabled_documents()
    note = project.sro.readiness_note()
    if note:
        raise GeneratorError(note)
    if not documents:
        raise GeneratorError(
            f"У СРО «{project.sro.short_name}» не включён ни один документ.")

    _check_levels(project, company)

    result = GenerationResult()
    result.notes.extend(result_notes)

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

    context: ContextResult = build_context(company, project.attorney(),
                                       today=today, sro=project.sro)
    result.notes.extend(context.notes)
    log.info("Формирование документов для СРО «%s»: %s",
             project.sro.short_name, app_logging.safe_company(company))
    log.debug("Переменные: %s", app_logging.safe_values(context.values))

    folder = output_folder(project, company)
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
            required_variables_for(placeholders, project.variables,
                                   company.applicant_kind),
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
