# -*- coding: utf-8 -*-
"""Реестр саморегулируемых организаций.

Каждая СРО — отдельная папка в `sro/`:

    sro/
      СССС/
        sro.json          название, документы, умолчания
        attorney.json     доверенное лицо (персональные данные)
        templates/        бланки именно этой СРО
      НОСТРОЙ-Регион/
        ...

Программа находит их сама: сколько папок — столько СРО в списке выбора.
Добавление новой СРО не требует правки кода.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

SRO_DIR_NAME = "sro"
PROFILE_FILE = "sro.json"
ATTORNEY_FILE = "attorney.json"
TEMPLATES_DIR = "templates"


class SroError(Exception):
    """Ошибка настроек СРО с текстом, понятным пользователю."""


@dataclass
class DocumentSpec:
    """Описание одного документа СРО."""

    id: str
    title: str
    template: str
    output_name: str
    enabled: bool = True


@dataclass
class SroProfile:
    """Одна саморегулируемая организация."""

    folder: Path
    name: str
    short_name: str
    city: str = ""
    note: str = ""
    defaults: dict[str, str] = field(default_factory=dict)
    auto_fill: dict[str, str] = field(default_factory=dict)
    documents: list[DocumentSpec] = field(default_factory=list)

    @property
    def key(self) -> str:
        """Устойчивый идентификатор — имя папки."""
        return self.folder.name

    @property
    def templates_dir(self) -> Path:
        return self.folder / TEMPLATES_DIR

    @property
    def attorney_path(self) -> Path:
        return self.folder / ATTORNEY_FILE

    @property
    def label(self) -> str:
        """Как показывать в списке выбора."""
        if self.city:
            return f"{self.name} — {self.city}"
        return self.name

    def enabled_documents(self) -> list[DocumentSpec]:
        return [d for d in self.documents if d.enabled]

    def missing_templates(self) -> list[str]:
        """Документы, описанные в настройках, но без файла бланка."""
        return [d.template for d in self.enabled_documents()
                if not (self.templates_dir / d.template).exists()]

    @property
    def is_ready(self) -> bool:
        """Можно ли уже формировать документы этой СРО."""
        return bool(self.enabled_documents()) and not self.missing_templates()

    def readiness_note(self) -> str:
        """Чего не хватает, обычными словами. Пусто — если всё на месте."""
        if not self.enabled_documents():
            return (f"Бланки СРО «{self.short_name}» ещё не загружены.\n\n"
                    f"Что нужно сделать:\n"
                    f"  1. Положить DOCX-бланки в папку:\n     {self.templates_dir}\n"
                    f"  2. Вписать в них переменные вида {{{{inn}}}}\n"
                    f"     (список — в ИНСТРУКЦИЯ.md, раздел 7).\n"
                    f"  3. Описать документы в файле:\n     {self.folder / PROFILE_FILE}")
        missing = self.missing_templates()
        if missing:
            files = "\n".join(f"     {name}" for name in missing)
            return (f"У СРО «{self.short_name}» описаны документы, "
                    f"но самих файлов бланков нет:\n{files}\n\n"
                    f"Ожидаются в папке:\n     {self.templates_dir}")
        return ""

    def attorney(self) -> dict[str, str]:
        """Данные доверенного лица. Пусто, если файла нет — он нужен не всем."""
        if not self.attorney_path.exists():
            return {}
        try:
            data = json.loads(self.attorney_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SroError(
                f"Файл «{self.attorney_path.name}» СРО «{self.short_name}» повреждён "
                f"(строка {exc.lineno}): {exc.msg}.\n"
                f"Проверьте, что при правке не потерялись запятые или кавычки."
            ) from exc
        return {k: str(v) for k, v in data.items() if not k.startswith("_")}


# ------------------------------------------------------------------ загрузка
def _load_json(path: Path, what: str) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SroError(
            f"{what} повреждён (строка {exc.lineno}): {exc.msg}.\n"
            f"Проверьте, что при правке не потерялись запятые или кавычки.\n"
            f"Файл: {path}"
        ) from exc
    except OSError as exc:
        raise SroError(f"Не удалось прочитать {what}.\nФайл: {path}\nПричина: {exc}") from exc


def load_profile(folder: Path) -> SroProfile:
    """Прочитать одну СРО из её папки."""
    folder = Path(folder)
    profile_path = folder / PROFILE_FILE
    if not profile_path.exists():
        raise SroError(
            f"В папке «{folder.name}» нет файла {PROFILE_FILE} — "
            f"программа не понимает, что это за СРО."
        )
    data = _load_json(profile_path, f"файл настроек СРО «{folder.name}»")

    documents: list[DocumentSpec] = []
    for item in data.get("documents", []):
        try:
            documents.append(DocumentSpec(
                id=item["id"],
                title=item["title"],
                template=item["template"],
                output_name=item.get("output_name", item["template"]),
                enabled=bool(item.get("enabled", True)),
            ))
        except KeyError as exc:
            raise SroError(
                f"В описании документов СРО «{folder.name}» не хватает поля {exc}.\n"
                f"У каждого документа должны быть id, title и template.\n"
                f"Файл: {profile_path}"
            ) from exc

    def clean(section: str) -> dict[str, str]:
        return {k: str(v) for k, v in data.get(section, {}).items()
                if not k.startswith("_")}

    return SroProfile(
        folder=folder,
        name=str(data.get("name") or folder.name),
        short_name=str(data.get("short_name") or folder.name),
        city=str(data.get("city", "")),
        note=str(data.get("note", "")),
        defaults=clean("defaults"),
        auto_fill=clean("auto_fill"),
        documents=documents,
    )


def discover(root: Path | None = None) -> list[SroProfile]:
    """Все СРО, найденные в папке sro/. Порядок — по имени папки."""
    base = Path(root) if root else Path(__file__).resolve().parent.parent
    sro_dir = base / SRO_DIR_NAME
    if not sro_dir.exists():
        raise SroError(
            f"Не найдена папка «{SRO_DIR_NAME}» с настройками СРО.\n"
            f"Ожидалась здесь: {sro_dir}\n"
            f"Распакуйте архив программы заново."
        )

    profiles: list[SroProfile] = []
    problems: list[str] = []
    for folder in sorted(p for p in sro_dir.iterdir() if p.is_dir()):
        if folder.name.startswith((".", "_")):
            continue
        try:
            profiles.append(load_profile(folder))
        except SroError as exc:
            problems.append(str(exc))

    if not profiles:
        message = f"В папке «{SRO_DIR_NAME}» не найдено ни одной настроенной СРО."
        if problems:
            message += "\n\n" + "\n\n".join(problems)
        raise SroError(message)
    return profiles


def find(profiles: list[SroProfile], wanted: str) -> SroProfile | None:
    """Найти СРО по имени папки, сокращённому или полному названию."""
    needle = (wanted or "").strip().casefold()
    if not needle:
        return None
    for profile in profiles:
        candidates = (profile.key, profile.short_name, profile.name)
        if any(needle == str(c).casefold() for c in candidates):
            return profile
    for profile in profiles:
        if needle in profile.name.casefold():
            return profile
    return None
