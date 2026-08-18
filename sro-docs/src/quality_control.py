# -*- coding: utf-8 -*-
"""Контроль качества готового документа.

Документ считается готовым, только если он прошёл ВСЕ проверки:
  1. файл существует и открывается как документ Word;
  2. в тексте не осталось {{переменных}};
  3. все обязательные переменные документа заполнены;
  4. ключевые реквизиты компании реально присутствуют в тексте;
  5. в документе нет реквизитов другой компании (в том числе оставшихся
     от образца, по которому делался бланк).

Пятая проверка — главная защита от ситуации «данные компании А попали
в документы компании Б».
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .docx_engine import PLACEHOLDER_RE, extract_all_text, extract_package_text
from .models import CompanyData

EMAIL_IN_TEXT_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


@dataclass
class QualityReport:
    """Результат проверки одного документа."""

    document: str
    path: Path
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def check_document(path: Path, title: str, company: CompanyData,
                   values: dict[str, str], required_variables: set[str],
                   placeholders: list[str],
                   allowed_emails: set[str] | None = None) -> QualityReport:
    """Проверить один сформированный документ."""
    report = QualityReport(title, Path(path))

    # 1. Файл на месте и не повреждён.
    if not path.exists():
        report.problems.append("файл не создан")
        return report
    if path.stat().st_size == 0:
        report.problems.append("файл пустой (0 байт)")
        return report
    try:
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                report.problems.append("файл повреждён")
                return report
            if "word/document.xml" not in archive.namelist():
                report.problems.append("файл не открывается как документ Word")
                return report
    except zipfile.BadZipFile:
        report.problems.append("файл повреждён и не открывается как документ Word")
        return report

    text = extract_all_text(path)
    package_text = extract_package_text(path)

    # 2. Не осталось незаполненных переменных.
    leftovers = sorted({m.group(1) for m in PLACEHOLDER_RE.finditer(package_text)})
    if leftovers:
        report.problems.append(
            "в документе остались незаполненные переменные: "
            + ", ".join("{{%s}}" % name for name in leftovers)
        )

    # 3. Обязательные переменные документа не пустые.
    empty = sorted(name for name in required_variables if not (values.get(name) or "").strip())
    if empty:
        report.problems.append(
            "не заполнены обязательные данные: " + ", ".join(empty))

    # 4. Реквизиты текущей компании действительно в документе.
    #    Проверяем только то, что этот шаблон вообще использует.
    used = set(placeholders)
    all_digits = _digits(text)

    if company.inn and any(name == "inn" or name.startswith("inn_d") for name in used):
        if _digits(company.inn) not in all_digits:
            report.problems.append(f"в документе не найден ИНН {company.inn}")
    if company.ogrn and any(name == "ogrn" or name.startswith("ogrn_d") for name in used):
        if _digits(company.ogrn) not in all_digits:
            report.problems.append(f"в документе не найден ОГРН {company.ogrn}")

    for variable in ("short_name_bare", "company_name_bare"):
        value = values.get(variable, "")
        if variable in used and value and value not in text:
            report.problems.append(f"в документе не найдено наименование «{value}»")

    surname = (company.director_full_name or "").split()
    if surname and any(name.startswith("director_") for name in used):
        expected = [values.get(name, "") for name in
                    ("director_short_name", "director_full_name",
                     "director_full_name_genitive")
                    if name in used]
        expected = [value for value in expected if value]
        if expected and not any(value in text for value in expected):
            report.problems.append(
                f"в документе не найдена фамилия руководителя ({surname[0]})")

    # 5. Чужих реквизитов быть не должно.
    allowed = {e.lower() for e in (allowed_emails or set()) if e}
    if company.email:
        allowed.add(company.email.lower())
    found_emails = {m.group(0).lower() for m in EMAIL_IN_TEXT_RE.finditer(package_text)}
    foreign_emails = sorted(found_emails - allowed)
    if foreign_emails:
        report.problems.append(
            "в документе найден чужой адрес электронной почты: "
            + ", ".join(foreign_emails)
            + " — это остаток от другого документа, документ использовать нельзя"
        )

    own_ids = {_digits(company.inn), _digits(company.ogrn)}
    own_ids.discard("")
    for match in re.finditer(r"(?<!\d)\d{13}(?!\d)", text):
        if match.group(0) not in own_ids:
            report.warnings.append(
                f"в тексте есть 13-значное число {match.group(0)}, "
                f"не совпадающее с ОГРН компании — проверьте документ"
            )

    return report


def required_variables_for(placeholders: list[str], variable_map: dict) -> set[str]:
    """Какие переменные шаблона обязаны быть заполнены В ГОТОВОМ ДОКУМЕНТЕ.

    Не то же самое, что обязательные поля карточки: клетки под отдельные
    цифры ИНН и ОГРН помечены `may_be_empty`. У юрлица ИНН 10 знаков,
    а клеток в бланке бывает 12 — две последние законно пустые.
    """
    required = set()
    for name in placeholders:
        spec = lookup_variable(name, variable_map)
        if spec and spec.get("required") and not spec.get("may_be_empty"):
            required.add(name)
    return required


def lookup_variable(name: str, variable_map: dict) -> dict | None:
    """Найти описание переменной, учитывая ключи с * (например inn_d*)."""
    if name in variable_map:
        return variable_map[name]
    best: tuple[int, dict] | None = None
    for pattern, spec in variable_map.items():
        if not pattern.endswith("*"):
            continue
        prefix = pattern[:-1]
        if name.startswith(prefix):
            if best is None or len(prefix) > best[0]:
                best = (len(prefix), spec)
    return best[1] if best else None
