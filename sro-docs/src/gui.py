# -*- coding: utf-8 -*-
"""Окно программы: загрузка карточки → проверка реквизитов → документы.

Интерфейс на Tkinter — он входит в стандартную поставку Python для Windows,
поэтому ничего дополнительно ставить не нужно.

Перетаскивание файла мышью работает, если установлена библиотека
tkinterdnd2. Без неё всё то же самое доступно кнопкой «Выбрать файл».
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import traceback
from datetime import date
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, WORD, X, Y, filedialog, messagebox
import tkinter as tk
from tkinter import ttk

if __package__ in (None, ""):  # запуск как «python src/gui.py»
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "src"

from . import app_logging  # noqa: E402
from .company_parser import parse_card, parse_text  # noqa: E402
from .context_builder import OBJECT_KINDS, build_context  # noqa: E402
from .document_generator import (GeneratorError, Project, check_readiness,  # noqa: E402
                                 generate_many)
from .models import (APPLICANT_KINDS, COMPANY, DOC_PARAM_FIELDS,  # noqa: E402
                     ENTREPRENEUR, FIELD_SPECS, CompanyData)
from .readers import SUPPORTED_SUFFIXES, ReadError, read_card  # noqa: E402
from .sro_registry import SroError  # noqa: E402
from .validators import validate_company  # noqa: E402

TITLE = "Документы для вступления в СРО"
PAD = 8


def open_in_explorer(path: Path) -> None:
    """Открыть папку в проводнике — на Windows, macOS и Linux."""
    path = Path(path)
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as exc:  # noqa: BLE001
        messagebox.showinfo(
            TITLE, f"Не удалось открыть папку автоматически.\n\nОна находится здесь:\n{path}"
            f"\n\nТехническая причина: {exc}")


def _present_modal(window, master) -> None:
    """Показать модальное окно так, чтобы его было ВИДНО.

    `transient` привязывает окно к родителю. Но если родитель сейчас скрыт
    (на первом запуске главное окно ещё не построено и спрятано `withdraw()`),
    на Windows такое окно тоже становится невидимым: оно есть, но его не видно,
    а программа замирает на `wait_window`. Со стороны выглядит как «не
    запускается». Поэтому к СКРЫТОМУ родителю не привязываемся, а окно
    поднимаем на передний план и захватываем фокус сами.

    К видимому родителю (кнопка «Сменить СРО…», подтверждение склонений во
    время формирования) привязка сохраняется — так окно ведёт себя как
    положено дочернему.
    """
    if master is not None and master.winfo_viewable():
        window.transient(master)
    window.update_idletasks()
    width = window.winfo_width() or window.winfo_reqwidth()
    height = window.winfo_height() or window.winfo_reqheight()
    x = max(0, (window.winfo_screenwidth() - width) // 2)
    y = max(0, (window.winfo_screenheight() - height) // 3)
    window.geometry(f"+{x}+{y}")
    window.deiconify()
    window.lift()
    try:
        window.attributes("-topmost", True)
        window.after(300, lambda: window.attributes("-topmost", False))
    except tk.TclError:
        pass
    window.focus_force()
    try:
        window.grab_set()
    except tk.TclError:
        pass


class ConfirmDialog(tk.Toplevel):
    """Подтверждение склонений, в которых программа не уверена."""

    def __init__(self, master, confirmations) -> None:
        super().__init__(master)
        self.title("Проверьте склонение")
        self.result: dict[str, str] | None = None
        self._entries: dict[str, tk.Entry] = {}

        ttk.Label(
            self, wraplength=620, justify=LEFT,
            text=("Программа не уверена, что склонила эти значения правильно.\n"
                  "Проверьте и при необходимости исправьте — в документ попадёт "
                  "то, что написано в поле."),
        ).pack(fill=X, padx=PAD * 2, pady=PAD)

        body = ttk.Frame(self)
        body.pack(fill=BOTH, expand=True, padx=PAD * 2)
        for row, item in enumerate(confirmations):
            ttk.Label(body, text=item.label, font=("Segoe UI", 9, "bold")).grid(
                row=row * 3, column=0, sticky="w", pady=(PAD, 0))
            ttk.Label(body, text=f"причина проверки: {item.reason}",
                      foreground="#8a5a00", wraplength=600, justify=LEFT).grid(
                row=row * 3 + 1, column=0, sticky="w")
            entry = ttk.Entry(body, width=70)
            entry.insert(0, item.suggestion)
            entry.grid(row=row * 3 + 2, column=0, sticky="we", pady=(2, PAD))
            self._entries[item.key] = entry
        body.columnconfigure(0, weight=1)

        buttons = ttk.Frame(self)
        buttons.pack(fill=X, padx=PAD * 2, pady=PAD)
        ttk.Button(buttons, text="Отмена", command=self._cancel).pack(side=RIGHT)
        ttk.Button(buttons, text="Подтвердить", command=self._accept).pack(
            side=RIGHT, padx=PAD)

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        _present_modal(self, master)
        self.wait_window(self)

    def _accept(self) -> None:
        self.result = {key: entry.get().strip() for key, entry in self._entries.items()}
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class SroDialog(tk.Toplevel):
    """Окно выбора саморегулируемых организаций (можно несколько).

    Возвращает СПИСОК выбранных профилей в `self.result` (или None, если
    пользователь нажал «Отмена»). Отмечено может быть сколько угодно —
    комплекты документов сформируются сразу для всех.
    """

    def __init__(self, master, profiles, current=None) -> None:
        super().__init__(master)
        self.title("Выбор СРО")
        self.resizable(False, False)
        self.result = None
        self._profiles = list(profiles)
        # current — уже выбранные СРО: список профилей. Допускаем и один
        # профиль (для обратной совместимости), тогда оборачиваем в список.
        if current is None:
            current = []
        elif not isinstance(current, (list, tuple, set)):
            current = [current]
        current_keys = {p.key for p in current}
        if not current_keys and self._profiles:
            current_keys = {self._profiles[0].key}

        ttk.Label(self, text="В какие СРО подаём документы?",
                  font=("Segoe UI", 11, "bold")).pack(
            anchor="w", padx=PAD * 2, pady=(PAD * 2, 0))
        ttk.Label(self, wraplength=560, justify=LEFT, foreground="#40474f",
                  text="Отметьте одну или несколько галочками — комплекты "
                       "документов сформируются сразу для всех выбранных. "
                       "Выбор запоминается.").pack(
            anchor="w", padx=PAD * 2, pady=(2, PAD))

        body = ttk.Frame(self)
        body.pack(fill=BOTH, expand=True, padx=PAD * 2)

        self._vars: dict[str, tk.BooleanVar] = {}
        for profile in self._profiles:
            var = tk.BooleanVar(value=(profile.key in current_keys))
            self._vars[profile.key] = var
            row = ttk.Frame(body)
            row.pack(fill=X, pady=3)
            ttk.Checkbutton(row, text=profile.short_name, variable=var,
                            width=24).pack(side=LEFT, anchor="n")
            details = ttk.Frame(row)
            details.pack(side=LEFT, fill=X, expand=True)
            title = profile.name if profile.name != profile.short_name else ""
            if title:
                ttk.Label(details, text=title, wraplength=380,
                          justify=LEFT).pack(anchor="w")
            # «Бланки загружены, документов: N» убрано как лишнее: у готовых
            # СРО ничего не пишем, а вот про НЕзагруженные предупреждаем.
            if not profile.is_ready:
                ttk.Label(details, text="бланки ещё не загружены",
                          foreground="#8a5a00").pack(anchor="w")

        buttons = ttk.Frame(self)
        buttons.pack(fill=X, padx=PAD * 2, pady=PAD * 2)
        ttk.Button(buttons, text="Отмена", command=self._cancel).pack(side=RIGHT)
        ttk.Button(buttons, text="Выбрать", command=self._accept).pack(
            side=RIGHT, padx=PAD)

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        _present_modal(self, master)
        self.wait_window(self)

    def _accept(self) -> None:
        chosen = [p for p in self._profiles if self._vars[p.key].get()]
        if not chosen:
            messagebox.showwarning(
                "Выбор СРО", "Отметьте галочкой хотя бы одну СРО.")
            return
        self.result = chosen
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class SroParamsWizard(tk.Toplevel):
    """Мастер: по очереди задаёт параметры заявления для каждой СРО.

    Реквизиты компании одни на все СРО, а виды работ и уровни ответственности
    (в том числе обеспечения договорных обязательств, ОДО) в разных СРО могут
    быть разными — их и спрашиваем на каждую СРО отдельно.

    В `self.result` возвращается список словарей параметров (по одному на
    СРО, в том же порядке) или None, если пользователь нажал «Отмена».
    """

    def __init__(self, master, profiles, defaults) -> None:
        super().__init__(master)
        self.title("Параметры для каждой СРО")
        self.resizable(False, False)
        self.result = None
        self._profiles = list(profiles)
        self._index = 0
        self._params = [
            {
                "doc_date": defaults.get("doc_date") or "",
                "doc_number": defaults.get("doc_number") or "",
                "object_kind": defaults.get("object_kind") or "ordinary",
                "harm_fund_level": defaults.get("harm_fund_level") or "1",
                "contract_fund_level": defaults.get("contract_fund_level") or "",
            }
            for _ in self._profiles
        ]

        self._heading = ttk.Label(self, font=("Segoe UI", 11, "bold"))
        self._heading.pack(anchor="w", padx=PAD * 2, pady=(PAD * 2, 0))
        self._subhead = ttk.Label(self, foreground="#40474f", wraplength=620,
                                  justify=LEFT)
        self._subhead.pack(anchor="w", padx=PAD * 2, pady=(2, PAD))

        self._body = ttk.Frame(self)
        self._body.pack(fill=BOTH, expand=True, padx=PAD * 2)

        buttons = ttk.Frame(self)
        buttons.pack(fill=X, padx=PAD * 2, pady=PAD * 2)
        ttk.Button(buttons, text="Отмена", command=self._cancel).pack(side=RIGHT)
        self._next_btn = ttk.Button(buttons, text="Далее", command=self._next)
        self._next_btn.pack(side=RIGHT, padx=PAD)
        self._back_btn = ttk.Button(buttons, text="Назад", command=self._back)
        self._back_btn.pack(side=RIGHT)

        self._date_var = tk.StringVar()
        self._number_var = tk.StringVar()
        self._object_var = tk.StringVar()
        self._harm_var = tk.StringVar()
        self._contract_var = tk.StringVar()

        self._render()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        _present_modal(self, master)
        self.wait_window(self)

    def _render(self) -> None:
        profile = self._profiles[self._index]
        params = self._params[self._index]
        self._heading.configure(
            text=f"СРО {self._index + 1} из {len(self._profiles)}: "
                 f"{profile.short_name}")
        self._subhead.configure(
            text="Отметьте виды работ и уровни ответственности именно для этой "
                 "СРО. У следующей можно указать другие.")
        for child in self._body.winfo_children():
            child.destroy()

        self._date_var.set(params["doc_date"])
        self._number_var.set(params["doc_number"])
        self._object_var.set(params["object_kind"])
        self._harm_var.set(params["harm_fund_level"])
        self._contract_var.set(params["contract_fund_level"])

        head = ttk.LabelFrame(self._body, text=" Дата и номер заявления ")
        head.pack(fill=X, pady=(0, PAD))
        head.columnconfigure(1, weight=1)
        ttk.Label(head, text="Дата:").grid(row=0, column=0, sticky="e", padx=PAD, pady=4)
        ttk.Entry(head, textvariable=self._date_var, width=16).grid(
            row=0, column=1, sticky="w", padx=PAD)
        ttk.Label(head, text="в виде ДД.ММ.ГГГГ", foreground="#6b7480").grid(
            row=0, column=2, sticky="w", padx=PAD)
        ttk.Label(head, text="Номер:").grid(row=1, column=0, sticky="e", padx=PAD, pady=4)
        ttk.Entry(head, textvariable=self._number_var, width=16).grid(
            row=1, column=1, sticky="w", padx=PAD)
        ttk.Label(head, text="исходящий номер; по умолчанию «б/н»",
                  foreground="#6b7480").grid(row=1, column=2, sticky="w", padx=PAD)

        obj = ttk.LabelFrame(self._body, text=" Виды объектов ")
        obj.pack(fill=X, pady=(0, PAD))
        for kind, title in OBJECT_KINDS.items():
            ttk.Radiobutton(obj, text=title, value=kind,
                            variable=self._object_var).pack(
                anchor="w", padx=PAD, pady=1)

        self._level_block(" Компенсационный фонд возмещения вреда ",
                          profile.harm_levels, self._harm_var, allow_none=False)
        self._level_block(" Компенсационный фонд обеспечения договорных "
                          "обязательств (ОДО) ",
                          profile.contract_levels, self._contract_var, allow_none=True)

        last = self._index == len(self._profiles) - 1
        self._next_btn.configure(text="Готово" if last else "Далее")
        self._back_btn.configure(state="normal" if self._index else "disabled")

    def _level_block(self, title, levels, variable, allow_none) -> None:
        block = ttk.LabelFrame(self._body, text=title)
        block.pack(fill=X, pady=(0, PAD))
        if not levels:
            ttk.Label(block, foreground="#8a5a00",
                      text="Уровни этой СРО не заданы.").pack(
                anchor="w", padx=PAD, pady=2)
            return
        keys = [x.key for x in levels]
        if allow_none:
            ttk.Radiobutton(block, text="не заявляется (как в бланке)", value="",
                            variable=variable).pack(anchor="w", padx=PAD, pady=1)
            if variable.get() not in keys:
                variable.set("")
        elif variable.get() not in keys:
            variable.set(keys[0])
        for level in levels:
            ttk.Radiobutton(block, text=level.label, value=level.key,
                            variable=variable).pack(anchor="w", padx=PAD, pady=1)

    def _save(self) -> None:
        self._params[self._index] = {
            "doc_date": self._date_var.get().strip(),
            "doc_number": self._number_var.get().strip(),
            "object_kind": self._object_var.get(),
            "harm_fund_level": self._harm_var.get(),
            "contract_fund_level": self._contract_var.get(),
        }

    def _date_ok(self) -> bool:
        """Дата пустая (тогда подставится сегодняшняя) либо ДД.ММ.ГГГГ."""
        text = self._date_var.get().strip()
        if not text:
            return True
        if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", text):
            messagebox.showwarning(
                "Дата", f"Дата «{text}» не в том виде.\n"
                        "Впишите её как ДД.ММ.ГГГГ, например 19.08.2026, "
                        "или оставьте поле пустым.")
            return False
        return True

    def _next(self) -> None:
        if not self._date_ok():
            return
        self._save()
        if self._index == len(self._profiles) - 1:
            self.result = self._params
            self.destroy()
        else:
            self._index += 1
            self._render()

    def _back(self) -> None:
        self._save()
        if self._index:
            self._index -= 1
            self._render()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class Application(tk.Frame):
    def __init__(self, master: tk.Tk, project: Project) -> None:
        super().__init__(master)
        self.project = project
        self.company = project.new_company()
        self.last_folder: Path | None = None

        self.vars: dict[str, tk.StringVar] = {}
        self.texts: dict[str, tk.Text] = {}
        self.labels: dict[str, ttk.Label] = {}
        self.hints: dict[str, tuple] = {}
        self.entries: dict[str, ttk.Entry] = {}

        self.pack(fill=BOTH, expand=True)
        self._build()
        self._show_sro()
        self._show_applicant_kind()

    # ------------------------------------------------------------ разметка
    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill=X, padx=PAD, pady=(PAD, 0))
        ttk.Label(top, text="СРО:", font=("Segoe UI", 9, "bold")).pack(side=LEFT)
        self.sro_label = ttk.Label(top, text="")
        self.sro_label.pack(side=LEFT, padx=(4, PAD))
        ttk.Button(top, text="Сменить СРО…", command=self.on_change_sro).pack(side=LEFT)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=BOTH, expand=True, padx=PAD, pady=PAD)

        self.notebook.add(self._build_load_tab(), text="  1. Загрузка  ")
        self.notebook.add(self._build_fields_tab(), text="  2. Реквизиты  ")
        self.notebook.add(self._build_options_tab(), text="  3. Параметры документов  ")
        self.notebook.add(self._build_result_tab(), text="  4. Результат  ")

        bar = ttk.Frame(self)
        bar.pack(fill=X, padx=PAD, pady=(0, PAD))
        self.status = ttk.Label(bar, text="Загрузите карточку компании или вставьте текст.")
        self.status.pack(side=LEFT)
        ttk.Button(bar, text="Сформировать документы",
                   command=self.on_generate).pack(side=RIGHT)
        ttk.Button(bar, text="Проверить", command=self.on_check).pack(side=RIGHT, padx=PAD)
        self.open_button = ttk.Button(bar, text="Открыть папку с документами",
                                      command=self.on_open_folder, state="disabled")
        self.open_button.pack(side=RIGHT, padx=PAD)

    def _build_load_tab(self) -> ttk.Frame:
        frame = ttk.Frame(self.notebook)

        block = ttk.LabelFrame(frame, text=" Вариант 1. Файл с карточкой компании ")
        block.pack(fill=X, padx=PAD, pady=PAD)
        self.drop_zone = tk.Label(
            block, height=4, relief="ridge", bd=2, bg="#f4f6f8", fg="#40474f",
            text="Перетащите сюда файл карточки\n(DOCX, XLSX, PDF, TXT, изображение)")
        self.drop_zone.pack(fill=X, padx=PAD, pady=PAD)
        ttk.Button(block, text="Выбрать файл…", command=self.on_pick_file).pack(
            anchor="w", padx=PAD, pady=(0, PAD))
        self._enable_drag_and_drop()

        block = ttk.LabelFrame(frame, text=" Вариант 2. Реквизиты обычным текстом ")
        block.pack(fill=BOTH, expand=True, padx=PAD, pady=PAD)
        self.paste_area = tk.Text(block, height=12, wrap=WORD, font=("Consolas", 10))
        self.paste_area.pack(fill=BOTH, expand=True, padx=PAD, pady=PAD)
        self.paste_area.insert("1.0",
                               'ООО "Ромашка"\nИНН 7812345675\nКПП 781201001\n'
                               'ОГРН 1237800000008\nЮридический адрес: ...\n'
                               'Генеральный директор: Иванов Иван Иванович\n'
                               'Действует на основании Устава\nТелефон: ...\nEmail: ...')
        ttk.Button(block, text="Разобрать текст", command=self.on_parse_text).pack(
            anchor="w", padx=PAD, pady=(0, PAD))

        ttk.Label(frame, wraplength=900, justify=LEFT, foreground="#40474f",
                  text=("Вариант 3. Можно ничего не загружать и заполнить все поля "
                        "вручную на вкладке «Реквизиты».")).pack(anchor="w", padx=PAD)
        return frame

    def _enable_drag_and_drop(self) -> None:
        try:
            from tkinterdnd2 import DND_FILES
        except ImportError:
            self.drop_zone.configure(
                text=("Перетаскивание файлов недоступно\n"
                      "(не установлена библиотека tkinterdnd2)\n"
                      "Нажмите «Выбрать файл…»"))
            return
        try:
            self.drop_zone.drop_target_register(DND_FILES)
            self.drop_zone.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:  # noqa: BLE001
            pass

    def _on_drop(self, event) -> None:
        path = event.data.strip().strip("{}")
        self.load_file(Path(path))

    def _build_fields_tab(self) -> ttk.Frame:
        outer = ttk.Frame(self.notebook)
        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-int(e.delta / 120), "units"))

        # --- кто подаёт документы -------------------------------------
        # От этого зависят длина ИНН и ОГРН, наличие КПП и вид наименования,
        # поэтому переключатель стоит первым, до всех полей.
        kind_block = ttk.LabelFrame(inner, text=" Кто подаёт документы ")
        kind_block.pack(fill=X, padx=PAD, pady=PAD // 2)
        self.applicant_kind = tk.StringVar(value=COMPANY)
        for value in (COMPANY, ENTREPRENEUR):
            ttk.Radiobutton(kind_block, text=APPLICANT_KINDS[value], value=value,
                            variable=self.applicant_kind,
                            command=self.on_applicant_kind).pack(
                anchor="w", padx=PAD, pady=2)
        ttk.Label(kind_block, foreground="#6b7480", wraplength=620, justify=LEFT,
                  text="У предпринимателя ИНН из 12 цифр, ОГРНИП из 15 и нет КПП. "
                       "Клетки под цифры в бланках программа расширит сама.").pack(
            anchor="w", padx=PAD, pady=(0, PAD // 2))

        group = None
        block = None
        row = 0
        for spec in FIELD_SPECS:
            if spec.group != group:
                group = spec.group
                block = ttk.LabelFrame(inner, text=f" {group} ")
                block.pack(fill=X, padx=PAD, pady=PAD // 2)
                block.columnconfigure(1, weight=1)
                row = 0

            mark = "" if spec.used_by_templates else "  (в текущих шаблонах не используется)"
            label = ttk.Label(block, text=spec.label + ":")
            label.grid(row=row, column=0, sticky="ne", padx=PAD, pady=3)
            self.labels[spec.key] = label

            if spec.multiline:
                widget = tk.Text(block, height=2, wrap=WORD, font=("Segoe UI", 9))
                widget.grid(row=row, column=1, sticky="we", padx=PAD, pady=3)
                self.texts[spec.key] = widget
            else:
                variable = tk.StringVar()
                self.vars[spec.key] = variable
                entry = ttk.Entry(block, textvariable=variable)
                entry.grid(row=row, column=1, sticky="we", padx=PAD, pady=3)
                self.entries[spec.key] = entry

            hint_label = ttk.Label(block, text=(spec.hint + mark).strip(),
                                   foreground="#6b7480", wraplength=320,
                                   justify=LEFT)
            hint_label.grid(row=row, column=2, sticky="w", padx=PAD)
            self.hints[spec.key] = (hint_label, mark)
            if spec.key == "actual_address":
                ttk.Button(block, text="Ещё раз скопировать из юридического",
                           command=self.on_copy_address).grid(
                    row=row + 1, column=1, sticky="w", padx=PAD, pady=(0, PAD))
                row += 1
            row += 1

        return outer

    def _build_options_tab(self) -> ttk.Frame:
        frame = ttk.Frame(self.notebook)

        block = ttk.LabelFrame(frame, text=" Дата и номер ")
        block.pack(fill=X, padx=PAD, pady=PAD)
        block.columnconfigure(1, weight=1)

        self.vars["doc_date"] = tk.StringVar(value=self.company.doc_date)
        ttk.Label(block, text="Дата документов:").grid(row=0, column=0, sticky="e",
                                                       padx=PAD, pady=4)
        ttk.Entry(block, textvariable=self.vars["doc_date"], width=16).grid(
            row=0, column=1, sticky="w", padx=PAD)
        ttk.Label(block, text="в виде ДД.ММ.ГГГГ", foreground="#6b7480").grid(
            row=0, column=2, sticky="w")

        self.vars["doc_number"] = tk.StringVar(value=self.company.doc_number)
        ttk.Label(block, text="Номер заявления:").grid(row=2, column=0, sticky="e",
                                                       padx=PAD, pady=4)
        ttk.Entry(block, textvariable=self.vars["doc_number"], width=16).grid(
            row=2, column=1, sticky="w", padx=PAD)
        ttk.Label(block, text="исходящий номер письма; по умолчанию «б/н»",
                  foreground="#6b7480").grid(row=2, column=2, sticky="w")

        self.vars["power_number"] = tk.StringVar(value=self.company.power_number)
        ttk.Label(block, text="Номер доверенности:").grid(row=1, column=0, sticky="e",
                                                          padx=PAD, pady=4)
        ttk.Entry(block, textvariable=self.vars["power_number"], width=16).grid(
            row=1, column=1, sticky="w", padx=PAD)
        ttk.Label(block, text="по умолчанию «б/н» — без номера; можно вписать "
                              "настоящий номер, если он нужен",
                  foreground="#6b7480").grid(row=1, column=2, sticky="w")

        block = ttk.LabelFrame(frame, text=" Заявление, п.7 — виды объектов ")
        block.pack(fill=X, padx=PAD, pady=PAD)
        self.vars["object_kind"] = tk.StringVar(value="ordinary")
        for kind, title in OBJECT_KINDS.items():
            ttk.Radiobutton(block, text=title, value=kind,
                            variable=self.vars["object_kind"]).pack(
                anchor="w", padx=PAD, pady=1)

        # Уровни ответственности у каждой СРО свои: у строительных пять,
        # у проектировщиков и изыскателей четыре, и суммы разные.
        # Поэтому список строится по выбранной СРО и пересобирается при смене.
        self.harm_block = ttk.LabelFrame(
            frame, text=" Компенсационный фонд возмещения вреда ")
        self.harm_block.pack(fill=X, padx=PAD, pady=PAD)
        self.vars["harm_fund_level"] = tk.StringVar(value="1")

        self.contract_block = ttk.LabelFrame(
            frame, text=" Компенсационный фонд обеспечения договорных обязательств ")
        self.contract_block.pack(fill=X, padx=PAD, pady=PAD)
        self.vars["contract_fund_level"] = tk.StringVar(value="")

        self._rebuild_levels()
        return frame

    def _rebuild_levels(self) -> None:
        """Перестроить списки уровней под выбранную СРО."""
        for block, levels, variable, allow_none in (
                (self.harm_block, self.project.sro.harm_levels,
                 self.vars["harm_fund_level"], False),
                (self.contract_block, self.project.sro.contract_levels,
                 self.vars["contract_fund_level"], True)):
            for child in block.winfo_children():
                child.destroy()
            if not levels:
                ttk.Label(block, foreground="#8a5a00",
                          text="Уровни этой СРО не заданы — бланк заявления "
                               "ещё не загружен.").pack(anchor="w", padx=PAD, pady=2)
                continue
            if allow_none:
                ttk.Radiobutton(block, text="не заявляется (как в бланке)", value="",
                                variable=variable).pack(anchor="w", padx=PAD, pady=1)
            for level in levels:
                ttk.Radiobutton(block, text=level.label, value=level.key,
                                variable=variable).pack(anchor="w", padx=PAD, pady=1)
            # Если выбранного уровня у новой СРО нет — сбрасываем на первый.
            if variable.get() and variable.get() not in [x.key for x in levels]:
                variable.set(levels[0].key if not allow_none else "")

    def _build_result_tab(self) -> ttk.Frame:
        frame = ttk.Frame(self.notebook)
        self.report = tk.Text(frame, wrap=WORD, font=("Consolas", 10), state="disabled")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.report.yview)
        self.report.configure(yscrollcommand=scrollbar.set)
        self.report.pack(side=LEFT, fill=BOTH, expand=True, padx=(PAD, 0), pady=PAD)
        scrollbar.pack(side=RIGHT, fill=Y, pady=PAD)
        return frame

    # ------------------------------------------------------------ данные
    def _read_form(self) -> None:
        """Перенести всё, что в полях окна, в объект компании."""
        self.company.applicant_kind = self.applicant_kind.get()
        for key, variable in self.vars.items():
            self.company.set(key, variable.get())
        for key, widget in self.texts.items():
            self.company.set(key, widget.get("1.0", END).strip())

    def _write_form(self) -> None:
        self.applicant_kind.set(self.company.applicant_kind)
        for key, variable in self.vars.items():
            variable.set(self.company.get(key))
        for key, widget in self.texts.items():
            widget.delete("1.0", END)
            widget.insert("1.0", self.company.get(key))
        self._show_applicant_kind()

    def _show_applicant_kind(self) -> None:
        """Подписи и подсказки полей — под выбранный тип заявителя.

        Поля, которых у этого заявителя не бывает (КПП у предпринимателя),
        не прячем, а гасим и подписываем почему: так человек видит, что
        программа их не забыла, а сознательно не спрашивает.
        """
        for spec in FIELD_SPECS:
            label = self.labels.get(spec.key)
            if label is None:
                continue
            applicable = not spec.only_for or spec.only_for == self.company.applicant_kind
            label.configure(text=self.company.label_for(spec.key) + ":",
                            foreground="black" if applicable else "#9aa2ac")
            hint_label, mark = self.hints.get(spec.key, (None, ""))
            if hint_label is not None:
                text = ("У индивидуального предпринимателя этого реквизита нет"
                        if not applicable
                        else (self.company.hint_for(spec.key) + mark).strip())
                hint_label.configure(text=text)
            entry = self.entries.get(spec.key)
            if entry is not None:
                entry.configure(state="normal" if applicable else "disabled")

    def on_applicant_kind(self) -> None:
        """Пользователь переключил «юрлицо / предприниматель»."""
        self._read_form()
        notes = self.project.apply_applicant_defaults(self.company)
        self._write_form()
        if notes:
            self._set_status("; ".join(notes)[:200])
        else:
            self._set_status(
                f"Заявитель: {APPLICANT_KINDS[self.company.applicant_kind]}.")

    def _set_status(self, text: str, color: str = "") -> None:
        self.status.configure(text=text, foreground=color or "black")

    def _show_report(self, lines: list[str]) -> None:
        self.report.configure(state="normal")
        self.report.delete("1.0", END)
        self.report.insert("1.0", "\n".join(lines))
        self.report.configure(state="disabled")
        self.notebook.select(3)

    # ------------------------------------------------------------ действия
    def on_pick_file(self) -> None:
        patterns = " ".join(f"*{s}" for s in sorted(SUPPORTED_SUFFIXES))
        path = filedialog.askopenfilename(
            title="Выберите файл карточки компании",
            filetypes=[("Карточка компании", patterns), ("Все файлы", "*.*")])
        if path:
            self.load_file(Path(path))

    def load_file(self, path: Path) -> None:
        try:
            parsed = parse_card(read_card(path))
        except ReadError as exc:
            messagebox.showerror(TITLE, str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            app_logging.get().exception("Ошибка чтения карточки")
            messagebox.showerror(
                TITLE, f"Не удалось прочитать файл «{path.name}».\n\n"
                       f"Подробности записаны в logs/app.log.\n\nПричина: {exc}")
            return
        self._apply_parsed(parsed, f"Загружено из файла: {path.name}")

    def on_parse_text(self) -> None:
        text = self.paste_area.get("1.0", END)
        try:
            parsed = parse_text(text)
        except ReadError as exc:
            messagebox.showerror(TITLE, str(exc))
            return
        self._apply_parsed(parsed, "Реквизиты разобраны из текста")

    def _apply_parsed(self, parsed, source: str) -> None:
        # Дата и параметры документов не относятся к карточке — сохраняем их.
        self._read_form()
        keep = {key: self.company.get(key) for key in DOC_PARAM_FIELDS}
        self.company = parsed.company           # новый объект: чужих данных не остаётся
        for key, value in keep.items():
            self.company.set(key, value)
        auto_filled = self.project.apply_applicant_defaults(self.company)
        auto_filled += self.project.apply_auto_fill(self.company)
        self._write_form()

        messages = [source, ""]
        for note in auto_filled:
            messages.append(f"Подставлено автоматически: {note}")
        for key, note in parsed.derived.items():
            messages.append(f"ВНИМАНИЕ: {note}")
        for note in parsed.notes:
            messages.append(f"Примечание: {note}")
        if len(messages) > 2:
            messagebox.showinfo(TITLE, "\n\n".join(messages))

        self._set_status(source + ". Проверьте реквизиты на вкладке 2.", "#1c6b1c")
        self.notebook.select(1)
        self.on_check(silent=True)

    def _show_sro(self) -> None:
        """Обновить строку с выбранными СРО."""
        profiles = self.project.selected_sros
        names = ", ".join(p.short_name for p in profiles)
        not_ready = [p.short_name for p in profiles if not p.is_ready]
        if not_ready:
            self.sro_label.configure(
                text=f"{names}  (бланки не загружены: {', '.join(not_ready)})",
                foreground="#8a5a00")
        elif len(profiles) > 1:
            self.sro_label.configure(
                text=f"{names}  — комплектов: {len(profiles)}", foreground="black")
        else:
            self.sro_label.configure(text=names, foreground="black")

    def on_change_sro(self) -> None:
        dialog = SroDialog(self.master, self.project.all_sro,
                           self.project.selected_sros)
        if dialog.result is None:
            return
        chosen_keys = {p.key for p in dialog.result}
        if chosen_keys == {p.key for p in self.project.selected_sros}:
            return
        self.project.set_selected(dialog.result)
        self._show_sro()
        self._rebuild_levels()

        # Умолчания у разных СРО могут отличаться — подставляем новые
        # только туда, где пользователь ничего не вводил.
        self._read_form()
        for key, value in self.project.defaults.items():
            if not self.company.get(key):
                self.company.set(key, value)
        self._write_form()

        note = self.project.sro.readiness_note()
        if note:
            messagebox.showwarning(TITLE, note)
            self._set_status(f"СРО «{self.project.sro.short_name}»: "
                             f"бланки не загружены.", "#8a5a00")
            return
        self._set_status(f"Выбрана СРО «{self.project.sro.short_name}». "
                         f"Проверьте реквизиты и формируйте документы.", "#1c6b1c")
        self.on_check(silent=True)

    def on_copy_address(self) -> None:
        self._read_form()
        self.company.set("actual_address", self.company.legal_address)
        self._write_form()

    def on_open_folder(self) -> None:
        if self.last_folder:
            open_in_explorer(self.last_folder)

    # ------------------------------------------------------------ проверка
    def on_check(self, silent: bool = False) -> bool:
        note = self.project.sro.readiness_note()
        if note:
            if not silent:
                messagebox.showwarning(TITLE, note)
            self._set_status(f"СРО «{self.project.sro.short_name}»: "
                             f"бланки не загружены.", "#8a5a00")
            return False

        self._read_form()
        auto_filled = self.project.apply_applicant_defaults(self.company)
        auto_filled += self.project.apply_auto_fill(self.company)
        if auto_filled:
            self._write_form()

        for key, label in self.labels.items():
            label.configure(foreground="black")

        lines: list[str] = [f"СРО: {self.project.sro.name}"]
        if self.project.sro.note:
            lines.append(f"     {self.project.sro.note}")
        lines += ["", "КАРТОЧКА КОМПАНИИ", "=" * 60]
        lines.append(f"Компания: {self.company.short_name or '(не заполнено)'}")
        lines.append(f"Полное наименование: {self.company.full_name or '(не заполнено)'}")
        lines.append(f"ИНН: {self.company.inn or '(не заполнено)'}")
        lines.append(f"КПП: {self.company.kpp or '(не заполнено)'}")
        lines.append(f"ОГРН: {self.company.ogrn or '(не заполнено)'}")
        lines.append(f"Юридический адрес: {self.company.legal_address or '(не заполнено)'}")
        lines.append(f"Фактический адрес: {self.company.actual_address or '(не заполнено)'}")
        lines.append(f"Телефон: {self.company.phone or '(не заполнено)'}")
        lines.append(f"Эл. почта: {self.company.email or '(не заполнено)'}")
        lines.append(f"{self.company.director_position or 'Руководитель'}: "
                     f"{self.company.director_full_name or '(не заполнено)'}")
        lines.append(f"Основание полномочий: {self.company.director_basis or '(не заполнено)'}")
        lines.append(f"Дата документов: {self.company.doc_date}")
        lines.append("")

        if auto_filled:
            lines.append("ПОДСТАВЛЕНО АВТОМАТИЧЕСКИ")
            lines.append("-" * 60)
            lines.extend(auto_filled)
            lines.append("")

        issues = validate_company(self.company)
        errors = [i for i in issues if i.is_error]
        if issues:
            lines.append("ЗАМЕЧАНИЯ К РЕКВИЗИТАМ")
            lines.append("-" * 60)
            for issue in issues:
                prefix = "ОШИБКА " if issue.is_error else "внимание"
                lines.append(f"{prefix}: {issue.text}")
                if issue.field in self.labels:
                    self.labels[issue.field].configure(
                        foreground="#b00020" if issue.is_error else "#8a5a00")
            lines.append("")

        ready = True
        lines.append("ГОТОВНОСТЬ ДОКУМЕНТОВ")
        lines.append("-" * 60)
        try:
            readiness = check_readiness(self.project, self.company)
        except GeneratorError as exc:
            messagebox.showerror(TITLE, str(exc))
            return False
        missing_all: list[str] = []
        for item in readiness:
            lines.append("")
            lines.append(f"### {item.spec.title}")
            if item.ok:
                lines.append("    Все обязательные поля заполнены.")
            else:
                ready = False
                for index, label in enumerate(item.missing, 1):
                    lines.append(f"    {index}. отсутствует: {label}")
                    if label not in missing_all:
                        missing_all.append(label)
                for name in item.unknown_variables:
                    lines.append(f"    переменная {{{{{name}}}}} не описана "
                                 f"в config/variables.json")
                    ready = False
            for key in item.missing_keys:
                if key in self.labels:
                    self.labels[key].configure(foreground="#b00020")
        lines.append("")

        context = build_context(self.company, self.project.attorney(), sro=self.project.sro)
        if context.notes:
            lines.append("ПРИМЕЧАНИЯ")
            lines.append("-" * 60)
            lines.extend(context.notes)
            lines.append("")
        if context.confirmations:
            lines.append("ТРЕБУЕТСЯ ПОДТВЕРЖДЕНИЕ СКЛОНЕНИЯ")
            lines.append("-" * 60)
            for item in context.confirmations:
                lines.append(f"{item.label}: предлагается «{item.suggestion}» "
                             f"({item.reason})")
            lines.append("")

        self._show_report(lines)

        if not silent:
            if missing_all:
                messagebox.showwarning(
                    TITLE,
                    "Для формирования документов не хватает следующих данных:\n\n"
                    + "\n".join(f"{i}. {name}" for i, name in enumerate(missing_all, 1))
                    + "\n\nЗаполните их на вкладке «Реквизиты».")
            elif errors:
                messagebox.showwarning(
                    TITLE, "В реквизитах есть ошибки:\n\n"
                           + "\n\n".join(i.text for i in errors))
            else:
                messagebox.showinfo(TITLE, "Все обязательные поля заполнены. "
                                           "Можно формировать документы.")

        state = "готово к формированию" if (ready and not errors) else "нужно исправить данные"
        self._set_status(f"Проверка выполнена: {state}.",
                         "#1c6b1c" if (ready and not errors) else "#b00020")
        return ready and not errors

    # ------------------------------------------------------------ генерация
    def on_generate(self) -> None:
        if not self.on_check(silent=True):
            self.on_check(silent=False)
            return

        context = build_context(self.company, self.project.attorney(), sro=self.project.sro)
        if context.confirmations:
            dialog = ConfirmDialog(self.master, context.confirmations)
            if dialog.result is None:
                self._set_status("Формирование отменено.", "#8a5a00")
                return
            self.company.overrides.update(dialog.result)

        # Параметры заявления (виды работ, уровни, ОДО) в разных СРО могут
        # быть разными. Реквизиты компании общие, а параметры при нескольких
        # СРО собираем мастером — по очереди на каждую.
        profiles = self.project.selected_sros
        if len(profiles) > 1:
            defaults = {
                "doc_date": self.company.doc_date,
                "doc_number": self.company.doc_number,
                "object_kind": self.company.object_kind,
                "harm_fund_level": self.company.harm_fund_level,
                "contract_fund_level": self.company.contract_fund_level,
            }
            wizard = SroParamsWizard(self.master, profiles, defaults)
            if wizard.result is None:
                self._set_status("Формирование отменено.", "#8a5a00")
                return
            plans = list(zip(profiles, wizard.result))
        else:
            plans = list(profiles)  # одна СРО — параметры со вкладки «Параметры»

        try:
            outcomes = generate_many(self.project, self.company, plans, make_pdf=True)
        except Exception as exc:  # noqa: BLE001
            app_logging.get().exception("Сбой формирования документов")
            messagebox.showerror(
                TITLE, "Не удалось сформировать документы.\n\n"
                       "Подробности записаны в файл logs/app.log.\n\n"
                       f"Причина: {exc}")
            return

        lines = ["РЕЗУЛЬТАТ", "=" * 60,
                 f"Компания: {self.company.identity()}",
                 f"Выбрано СРО: {len(outcomes)}", ""]
        total_created = 0
        failed_sros: list[str] = []
        ok_folders: list[Path] = []
        for outcome in outcomes:
            lines.append(f"### {outcome.sro.short_name}")
            if outcome.error:
                failed_sros.append(outcome.sro.short_name)
                lines.append("    НЕ СФОРМИРОВАНО:")
                for line in outcome.error.splitlines():
                    lines.append(f"      {line}")
                lines.append("")
                continue
            result = outcome.result
            lines.append(f"    папка: {result.folder}")
            for path in result.created:
                lines.append(f"      создан: {path.name}")
            for path in result.pdf:
                lines.append(f"      создан: {path.name}")
            total_created += len(result.created)
            document_failed = False
            for report in result.quality:
                if not report.ok:
                    document_failed = True
                    lines.append(f"      НЕ ГОТОВ: {report.document}")
                    for problem in report.problems:
                        lines.append(f"        проблема: {problem}")
                for warning in report.warnings:
                    lines.append(f"      внимание: {warning}")
            if document_failed:
                failed_sros.append(outcome.sro.short_name)
            elif result.ok:
                ok_folders.append(result.folder)
            for note in result.notes:
                lines.append(f"      примечание: {note}")
            lines.append("")

        self._show_report(lines)

        # Кнопка «Открыть папку»: если одна СРО — её папку, если несколько —
        # общий корень output, где лежат все папки СРО.
        if len(ok_folders) == 1:
            self.last_folder = ok_folders[0]
        elif ok_folders:
            self.last_folder = self.project.output_root
        if self.last_folder:
            self.open_button.configure(state="normal")

        if not failed_sros and ok_folders:
            self._set_status(
                f"Готово: комплектов {len(ok_folders)}, документов "
                f"{total_created}. Все проверены.", "#1c6b1c")
            if self.last_folder and messagebox.askyesno(
                    TITLE,
                    f"Документы готовы: {total_created} шт. "
                    f"в {len(ok_folders)} СРО.\n\n"
                    f"Папка: {self.last_folder}\n\nОткрыть папку?"):
                open_in_explorer(self.last_folder)
        else:
            self._set_status(
                f"Часть СРО не сформирована: {', '.join(failed_sros)}. "
                f"Подробности — на вкладке «Результат».", "#b00020")
            messagebox.showwarning(
                TITLE,
                "Не для всех СРО удалось сформировать документы.\n\n"
                f"С проблемами: {', '.join(failed_sros)}.\n\n"
                "Подробности — на вкладке «Результат».")


def main() -> int:
    try:
        project = Project()
    except (GeneratorError, SroError) as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(TITLE, str(exc))
        return 1

    app_logging.setup(project.logs_dir)
    log = app_logging.get()
    # Отпечаток окружения и шаги запуска — чтобы по журналу было видно,
    # до какого места дошёл запуск, даже если окно так и не появилось.
    log.info("запуск: Python %s, платформа %s",
             sys.version.split()[0], sys.platform)
    log.info("запуск: найдено СРО — %d", len(project.all_sro))

    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    except Exception:  # noqa: BLE001
        root = tk.Tk()
    log.info("запуск: главное окно создано")

    root.title(TITLE)
    root.geometry("1060x760")
    root.minsize(880, 600)
    try:
        ttk.Style().theme_use("vista" if sys.platform.startswith("win") else "clam")
    except tk.TclError:
        pass

    # Настроена одна СРО — спрашивать не о чем.
    if len(project.all_sro) > 1:
        log.info("запуск: показываю окно выбора СРО")
        root.withdraw()
        chosen = SroDialog(root, project.all_sro, project.selected_sros).result
        root.deiconify()
        if chosen is None:
            log.info("запуск: выбор СРО отменён пользователем")
            root.destroy()
            return 0
        log.info("запуск: выбрано СРО — %s",
                 ", ".join(p.short_name for p in chosen))
        project.set_selected(chosen)

    application = Application(root, project)
    log.info("запуск: главное окно построено")
    note = project.sro.readiness_note()
    if note:
        messagebox.showwarning(TITLE, note)
        application._set_status(
            f"СРО «{project.sro.short_name}»: бланки не загружены.", "#8a5a00")

    log.info("запуск: окно открыто, работаем")
    root.mainloop()
    log.info("выход: окно закрыто")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        # Записать причину в журнал: сообщение в окне отсылает к app.log,
        # значит там и должна быть полная расшифровка, а не только в консоли,
        # которую пользователь закроет.
        try:
            app_logging.get().exception("Программа завершилась с ошибкой при запуске")
        except Exception:  # noqa: BLE001
            pass
        try:
            import tkinter.messagebox as mb
            mb.showerror(TITLE, "Программа завершилась с ошибкой.\n\n"
                                "Подробности — в файле logs/app.log.\n\n"
                                "Можно запустить DIAGNOSTIKA.bat — он соберёт "
                                "отчёт и откроет его.")
        except Exception:  # noqa: BLE001
            pass
        raise SystemExit(1)
