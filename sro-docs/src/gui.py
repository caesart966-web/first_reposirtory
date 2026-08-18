# -*- coding: utf-8 -*-
"""Окно программы: загрузка карточки → проверка реквизитов → документы.

Интерфейс на Tkinter — он входит в стандартную поставку Python для Windows,
поэтому ничего дополнительно ставить не нужно.

Перетаскивание файла мышью работает, если установлена библиотека
tkinterdnd2. Без неё всё то же самое доступно кнопкой «Выбрать файл».
"""

from __future__ import annotations

import os
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
from .context_builder import (CONTRACT_LEVELS, HARM_LEVELS, OBJECT_KINDS,  # noqa: E402
                              build_context)
from .document_generator import (GeneratorError, Project, check_readiness,  # noqa: E402
                                 generate)
from .models import FIELD_SPECS, CompanyData  # noqa: E402
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


class ConfirmDialog(tk.Toplevel):
    """Подтверждение склонений, в которых программа не уверена."""

    def __init__(self, master, confirmations) -> None:
        super().__init__(master)
        self.title("Проверьте склонение")
        self.transient(master)
        self.grab_set()
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
        self.wait_window(self)

    def _accept(self) -> None:
        self.result = {key: entry.get().strip() for key, entry in self._entries.items()}
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class SroDialog(tk.Toplevel):
    """Окно выбора саморегулируемой организации."""

    def __init__(self, master, profiles, current=None) -> None:
        super().__init__(master)
        self.title("Выбор СРО")
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)
        self.result = None
        self._profiles = list(profiles)

        ttk.Label(self, text="В какую СРО подаём документы?",
                  font=("Segoe UI", 11, "bold")).pack(
            anchor="w", padx=PAD * 2, pady=(PAD * 2, 0))
        ttk.Label(self, wraplength=560, justify=LEFT, foreground="#40474f",
                  text="Выбор запоминается — в следующий раз программа откроется сразу с ним.").pack(
            anchor="w", padx=PAD * 2, pady=(2, PAD))

        body = ttk.Frame(self)
        body.pack(fill=BOTH, expand=True, padx=PAD * 2)

        self._choice = tk.StringVar(value=(current.key if current else
                                           self._profiles[0].key))
        for profile in self._profiles:
            row = ttk.Frame(body)
            row.pack(fill=X, pady=3)
            ttk.Radiobutton(row, text=profile.short_name, value=profile.key,
                            variable=self._choice, width=24).pack(side=LEFT, anchor="n")
            details = ttk.Frame(row)
            details.pack(side=LEFT, fill=X, expand=True)
            title = profile.name if profile.name != profile.short_name else ""
            if title:
                ttk.Label(details, text=title, wraplength=380,
                          justify=LEFT).pack(anchor="w")
            if profile.is_ready:
                count = len(profile.enabled_documents())
                ttk.Label(details, text=f"бланки загружены, документов: {count}",
                          foreground="#1c6b1c").pack(anchor="w")
            else:
                ttk.Label(details, text="бланки ещё не загружены",
                          foreground="#8a5a00").pack(anchor="w")

        buttons = ttk.Frame(self)
        buttons.pack(fill=X, padx=PAD * 2, pady=PAD * 2)
        ttk.Button(buttons, text="Отмена", command=self._cancel).pack(side=RIGHT)
        ttk.Button(buttons, text="Выбрать", command=self._accept).pack(
            side=RIGHT, padx=PAD)

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.wait_window(self)

    def _accept(self) -> None:
        key = self._choice.get()
        self.result = next((p for p in self._profiles if p.key == key), None)
        self.destroy()

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

        self.pack(fill=BOTH, expand=True)
        self._build()
        self._show_sro()

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
                ttk.Entry(block, textvariable=variable).grid(
                    row=row, column=1, sticky="we", padx=PAD, pady=3)

            hint = (spec.hint + mark).strip()
            if hint:
                ttk.Label(block, text=hint, foreground="#6b7480",
                          wraplength=320, justify=LEFT).grid(
                    row=row, column=2, sticky="w", padx=PAD)
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

        block = ttk.LabelFrame(
            frame, text=" Заявление, п.8 — компенсационный фонд возмещения вреда ")
        block.pack(fill=X, padx=PAD, pady=PAD)
        self.vars["harm_fund_level"] = tk.StringVar(value="1")
        for level, title in HARM_LEVELS.items():
            ttk.Radiobutton(block, text=title, value=level,
                            variable=self.vars["harm_fund_level"]).pack(
                anchor="w", padx=PAD, pady=1)

        block = ttk.LabelFrame(
            frame,
            text=" Заявление, п.9 — компенсационный фонд обеспечения договорных обязательств ")
        block.pack(fill=X, padx=PAD, pady=PAD)
        self.vars["contract_fund_level"] = tk.StringVar(value="")
        for level, title in CONTRACT_LEVELS.items():
            ttk.Radiobutton(block, text=title, value=level,
                            variable=self.vars["contract_fund_level"]).pack(
                anchor="w", padx=PAD, pady=1)

        return frame

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
        for key, variable in self.vars.items():
            self.company.set(key, variable.get())
        for key, widget in self.texts.items():
            self.company.set(key, widget.get("1.0", END).strip())

    def _write_form(self) -> None:
        for key, variable in self.vars.items():
            variable.set(self.company.get(key))
        for key, widget in self.texts.items():
            widget.delete("1.0", END)
            widget.insert("1.0", self.company.get(key))

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
        keep = {
            "doc_date": self.company.doc_date,
            "power_number": self.company.power_number,
            "object_kind": self.company.object_kind,
            "harm_fund_level": self.company.harm_fund_level,
            "contract_fund_level": self.company.contract_fund_level,
        }
        self.company = parsed.company           # новый объект: чужих данных не остаётся
        for key, value in keep.items():
            self.company.set(key, value)
        auto_filled = self.project.apply_auto_fill(self.company)
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
        """Обновить строку с текущей СРО."""
        profile = self.project.sro
        if profile.is_ready:
            self.sro_label.configure(text=profile.label, foreground="black")
        else:
            self.sro_label.configure(text=f"{profile.label} — бланки не загружены",
                                     foreground="#8a5a00")

    def on_change_sro(self) -> None:
        dialog = SroDialog(self.master, self.project.all_sro, self.project.sro)
        if dialog.result is None or dialog.result.key == self.project.sro.key:
            return
        self.project.use_sro(dialog.result)
        self._show_sro()

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
        auto_filled = self.project.apply_auto_fill(self.company)
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

        context = build_context(self.company, self.project.attorney())
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

        context = build_context(self.company, self.project.attorney())
        if context.confirmations:
            dialog = ConfirmDialog(self.master, context.confirmations)
            if dialog.result is None:
                self._set_status("Формирование отменено.", "#8a5a00")
                return
            self.company.overrides.update(dialog.result)

        try:
            result = generate(self.project, self.company, make_pdf=True)
        except GeneratorError as exc:
            messagebox.showerror(TITLE, str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            app_logging.get().exception("Сбой формирования документов")
            messagebox.showerror(
                TITLE, "Не удалось сформировать документы.\n\n"
                       "Подробности записаны в файл logs/app.log.\n\n"
                       f"Причина: {exc}")
            return

        lines = ["РЕЗУЛЬТАТ", "=" * 60,
                 f"Компания: {self.company.identity()}",
                 f"Папка: {result.folder}", ""]
        for path in result.created:
            lines.append(f"  создан: {path.name}")
        for path in result.pdf:
            lines.append(f"  создан: {path.name}")
        lines.append("")
        lines.append("КОНТРОЛЬ КАЧЕСТВА")
        lines.append("-" * 60)
        for report in result.quality:
            lines.append(f"{'ПРОВЕРЕН' if report.ok else 'НЕ ГОТОВ'}: {report.document}")
            for problem in report.problems:
                lines.append(f"    проблема: {problem}")
            for warning in report.warnings:
                lines.append(f"    внимание: {warning}")
        if result.notes:
            lines.append("")
            lines.append("ПРИМЕЧАНИЯ")
            lines.append("-" * 60)
            lines.extend(result.notes)

        self._show_report(lines)
        self.last_folder = result.folder
        self.open_button.configure(state="normal")

        if result.ok:
            self._set_status("Документы сформированы и проверены.", "#1c6b1c")
            if messagebox.askyesno(
                    TITLE,
                    f"Документы готовы ({len(result.created)} шт.).\n\n"
                    f"Папка: {result.folder}\n\nОткрыть папку?"):
                open_in_explorer(result.folder)
        else:
            self._set_status("Документы НЕ прошли контроль качества.", "#b00020")
            messagebox.showerror(
                TITLE,
                "Документы сформированы, но не прошли контроль качества "
                "и использовать их нельзя.\n\nПодробности — на вкладке «Результат».")


def main() -> int:
    try:
        project = Project()
    except (GeneratorError, SroError) as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(TITLE, str(exc))
        return 1

    app_logging.setup(project.logs_dir)

    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    except Exception:  # noqa: BLE001
        root = tk.Tk()

    root.title(TITLE)
    root.geometry("1060x760")
    root.minsize(880, 600)
    try:
        ttk.Style().theme_use("vista" if sys.platform.startswith("win") else "clam")
    except tk.TclError:
        pass

    # Настроена одна СРО — спрашивать не о чем.
    if len(project.all_sro) > 1:
        root.withdraw()
        chosen = SroDialog(root, project.all_sro, project.sro).result
        root.deiconify()
        if chosen is None:
            root.destroy()
            return 0
        project.use_sro(chosen)

    application = Application(root, project)
    note = project.sro.readiness_note()
    if note:
        messagebox.showwarning(TITLE, note)
        application._set_status(
            f"СРО «{project.sro.short_name}»: бланки не загружены.", "#8a5a00")

    root.mainloop()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        try:
            import tkinter.messagebox as mb
            mb.showerror(TITLE, "Программа завершилась с ошибкой.\n\n"
                                "Подробности — в файле logs/app.log.")
        except Exception:  # noqa: BLE001
            pass
        raise SystemExit(1)
