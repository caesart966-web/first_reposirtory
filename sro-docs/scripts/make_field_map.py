# -*- coding: utf-8 -*-
"""Пересобрать карту соответствия config/field_map.md по текущим шаблонам.

    python scripts/make_field_map.py

Запускайте после добавления нового шаблона — карта обновится сама.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.document_generator import Project  # noqa: E402
from src.models import FIELD_BY_KEY  # noqa: E402
from src.quality_control import lookup_variable  # noqa: E402

HEADER = """# Карта соответствия

Файл создаётся автоматически: `python scripts/make_field_map.py`.
Править вручную не нужно.

Читается так: **поле данных → переменная шаблона → документ → место использования**.

"""


def main() -> int:
    project = Project(ROOT)
    lines = [HEADER]

    for spec in project.enabled_documents():
        lines.append(f"## {spec.title}\n")
        lines.append(f"Шаблон: `templates/{spec.template}`\n")
        lines.append("| Поле данных | Переменная | Место использования |")
        lines.append("| --- | --- | --- |")

        for name in project.placeholders(spec):
            info = lookup_variable(name, project.variables) or {}
            source = info.get("field")
            if source:
                field = FIELD_BY_KEY.get(source)
                label = f"`{source}` — {field.label}" if field else f"`{source}`"
            else:
                label = "*не реквизит компании*"
            lines.append(f"| {label} | `{{{{{name}}}}}` | {info.get('where', '')} |")
        lines.append("")

    used: set[str] = set()
    for spec in project.enabled_documents():
        for name in project.placeholders(spec):
            info = lookup_variable(name, project.variables) or {}
            if info.get("field"):
                used.add(info["field"])

    lines.append("## Поля, которые текущим шаблонам не нужны\n")
    lines.append("Программа их читает и хранит — пригодятся будущим документам СРО, —")
    lines.append("но никогда не требует для формирования заявления и доверенности.\n")
    lines.append("| Поле | Название |")
    lines.append("| --- | --- |")
    for key, field in FIELD_BY_KEY.items():
        if key not in used:
            lines.append(f"| `{key}` | {field.label} |")
    lines.append("")

    target = ROOT / "config" / "field_map.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    print(f"Карта соответствия обновлена: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
