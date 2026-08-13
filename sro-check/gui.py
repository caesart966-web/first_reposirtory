#!/usr/bin/env python3
"""Оконная версия проверки СРО — то же самое, что check_sro.py, но с кнопками.

Запуск из исходников:
    python gui.py

Из собранной программы — просто двойной клик по «Проверка СРО.exe».

Вся логика проверки живёт в check_sro.py и sro/*, оформление — в ui_theme.py;
здесь только поведение окна: выбор файла, кнопки, прогресс и журнал. Долгая
работа идёт в отдельном потоке, а сообщения из него передаются в окно через
очередь — трогать виджеты Tk из чужого потока нельзя.
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import traceback


# У оконной сборки (PyInstaller --windowed) нет консоли, и sys.stdout равен None.
# Любой случайный print() в такой ситуации роняет программу — подставляем заглушку.
class _NullStream:
    def write(self, *_args) -> int:
        return 0

    def flush(self) -> None:
        pass


if sys.stdout is None:
    sys.stdout = _NullStream()
if sys.stderr is None:
    sys.stderr = _NullStream()

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import check_sro
import ui_theme as theme

APP_TITLE = "Проверка СРО"
WINDOW_TITLE = "Проверка СРО — НОСТРОЙ и НОПРИЗ"
EXCEL_TYPES = [("Файлы Excel", "*.xlsx *.xlsm"), ("Все файлы", "*.*")]


def playwright_available() -> bool:
    """Есть ли запасная проверка через браузер.

    В собранную программу Playwright не входит (это ещё ~150 МБ браузера),
    поэтому в .exe этот способ выключен, а в версии из исходников — доступен.
    """
    try:
        import playwright.sync_api  # noqa: F401
    except Exception:
        return False
    return True


def open_in_system(path: str) -> None:
    """Открыть файл или папку средствами операционной системы."""
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


class App(ttk.Frame):
    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master, style="TFrame", padding=(18, 16))
        self.master = master
        self.fonts = theme.apply(master)
        self.grid(row=0, column=0, sticky="nsew")
        master.rowconfigure(0, weight=1)
        master.columnconfigure(0, weight=1)
        master.configure(background=theme.BG)

        self.messages: queue.Queue = queue.Queue()
        self.cancel: threading.Event | None = None
        self.worker: threading.Thread | None = None
        self.output_path = ""
        self.closing = False
        self.has_browser = playwright_available()

        self._build()
        self._drain()
        master.protocol("WM_DELETE_WINDOW", self._on_close)

        self._greet()

    # ------------------------------------------------------------------
    # Сборка окна
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        row = 0

        row = self._build_header(row)
        row = self._build_source_card(row)
        row = self._build_run_card(row)
        row = self._build_advanced_card(row)
        row = self._build_log_card(row)
        self._build_footer(row)

    def _build_header(self, row: int) -> int:
        header = ttk.Frame(self, style="Head.TFrame")
        header.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=APP_TITLE, style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Проверка членства компаний по ИНН в реестрах НОСТРОЙ и НОПРИЗ",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        return row + 1

    def _build_source_card(self, row: int) -> int:
        card = theme.Card(self, title="1. Что проверяем")
        card.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        card.columnconfigure(0, weight=1)

        picker = ttk.Frame(card, style="Card.TFrame")
        picker.grid(row=1, column=0, sticky="ew")
        picker.columnconfigure(0, weight=1)
        self.path_var = tk.StringVar()
        ttk.Entry(picker, textvariable=self.path_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(picker, text="Выбрать файл…", style="Ghost.TButton", command=self._choose_file).grid(
            row=0, column=1, padx=(8, 0)
        )

        options = ttk.Frame(card, style="Card.TFrame")
        options.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(options, text="Лист:").grid(row=0, column=0, sticky="w")
        self.sheet_var = tk.StringVar(value="Лиды по приоритету")
        ttk.Entry(options, textvariable=self.sheet_var, width=24).grid(
            row=0, column=1, sticky="w", padx=(8, 20)
        )
        self.retry_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options,
            text="только строки «не удалось проверить»",
            variable=self.retry_var,
        ).grid(row=0, column=2, sticky="w")
        return row + 1

    def _build_run_card(self, row: int) -> int:
        card = theme.Card(self, title="2. Проверка")
        card.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        card.columnconfigure(0, weight=1)

        # -- связь --
        probe = ttk.Frame(card, style="Card.TFrame")
        probe.grid(row=1, column=0, sticky="ew")
        ttk.Label(probe, text="ИНН компании, которая точно в СРО:").grid(row=0, column=0, sticky="w")
        self.probe_var = tk.StringVar()
        ttk.Entry(probe, textvariable=self.probe_var, width=16).grid(
            row=0, column=1, sticky="w", padx=(8, 8)
        )
        self.probe_button = ttk.Button(
            probe, text="Проверить связь", style="Ghost.TButton", command=self._start_probe
        )
        self.probe_button.grid(row=0, column=2, sticky="w")
        ttk.Label(
            card,
            text="Стоит нажать перед большим прогоном: покажет за полминуты, отвечают ли реестры.",
            style="Muted.TLabel",
        ).grid(row=2, column=0, sticky="w", pady=(6, 14))

        # -- запуск --
        actions = ttk.Frame(card, style="Card.TFrame")
        actions.grid(row=3, column=0, sticky="ew")
        self.start_button = ttk.Button(
            actions, text="Начать проверку", style="Accent.TButton", command=self._start_run
        )
        self.start_button.grid(row=0, column=0, sticky="w")
        self.stop_button = ttk.Button(
            actions,
            text="Остановить",
            style="Stop.Ghost.TButton",
            command=self._stop,
            state="disabled",
        )
        self.stop_button.grid(row=0, column=1, sticky="w", padx=(10, 0))

        # -- прогресс --
        self.progress = ttk.Progressbar(
            card, mode="determinate", maximum=100, style="Accent.Horizontal.TProgressbar"
        )
        self.progress.grid(row=4, column=0, sticky="ew", pady=(14, 8))

        state = ttk.Frame(card, style="Card.TFrame")
        state.grid(row=5, column=0, sticky="ew")
        state.columnconfigure(2, weight=1)
        self.dot = theme.StatusDot(state)
        self.dot.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.status_var = tk.StringVar(value="Готово к работе")
        ttk.Label(state, textvariable=self.status_var, style="TLabel").grid(
            row=0, column=1, sticky="w"
        )

        chips = ttk.Frame(state, style="Card.TFrame")
        chips.grid(row=0, column=3, sticky="e")
        self.chip_yes = theme.Chip(chips, theme.OK_BG, theme.OK, self.fonts.bold)
        self.chip_no = theme.Chip(chips, theme.BAD_BG, theme.BAD, self.fonts.bold)
        self.chip_unknown = theme.Chip(chips, theme.WARN_BG, theme.WARN, self.fonts.bold)
        for index, chip in enumerate((self.chip_yes, self.chip_no, self.chip_unknown)):
            chip.grid(row=0, column=index, padx=(6, 0))
        self._set_chips(0, 0, 0)
        return row + 1

    def _build_advanced_card(self, row: int) -> int:
        toggle = ttk.Frame(self, style="Head.TFrame")
        toggle.grid(row=row, column=0, sticky="w", pady=(0, 8))
        self.advanced_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            toggle,
            text="Дополнительные настройки",
            variable=self.advanced_var,
            command=self._toggle_advanced,
            style="Bg.TCheckbutton",
        ).grid(row=0, column=0, sticky="w")

        self.advanced = theme.Card(self, title="")
        self.advanced_row = row + 1
        self._fill_advanced(self.advanced)
        return row + 2

    def _fill_advanced(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)

        ttk.Label(frame, text="Пауза между запросами, с: от").grid(row=0, column=0, sticky="w")
        self.delay_min_var = tk.StringVar(value="1.0")
        ttk.Spinbox(
            frame, from_=0, to=60, increment=0.5, width=6, textvariable=self.delay_min_var
        ).grid(row=0, column=1, sticky="w", padx=(8, 8))
        ttk.Label(frame, text="до").grid(row=0, column=2, sticky="e")
        self.delay_max_var = tk.StringVar(value="2.0")
        ttk.Spinbox(
            frame, from_=0, to=60, increment=0.5, width=6, textvariable=self.delay_max_var
        ).grid(row=0, column=3, sticky="w", padx=(8, 0))

        ttk.Label(frame, text="Считать «да»:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.basis_var = tk.StringVar(value="active")
        basis = ttk.Frame(frame, style="Card.TFrame")
        basis.grid(row=1, column=1, columnspan=3, sticky="w", pady=(10, 0))
        ttk.Radiobutton(
            basis, text="только действующее членство", value="active", variable=self.basis_var
        ).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            basis, text="любая запись в реестре", value="found", variable=self.basis_var
        ).grid(row=0, column=1, sticky="w", padx=(16, 0))

        self.check_all_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="опрашивать оба реестра, даже если компания уже найдена",
            variable=self.check_all_var,
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(10, 0))

        self.recheck_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="не использовать сохранённые результаты (проверить всё заново)",
            variable=self.recheck_var,
        ).grid(row=3, column=0, columnspan=4, sticky="w", pady=(2, 0))

        ttk.Label(frame, text="Адрес API НОСТРОЙ:").grid(row=4, column=0, sticky="w", pady=(12, 0))
        self.nostroy_url_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.nostroy_url_var).grid(
            row=4, column=1, columnspan=3, sticky="ew", pady=(12, 0)
        )
        ttk.Label(frame, text="Адрес API НОПРИЗ:").grid(row=5, column=0, sticky="w", pady=(6, 0))
        self.nopriz_url_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.nopriz_url_var).grid(
            row=5, column=1, columnspan=3, sticky="ew", pady=(6, 0)
        )
        ttk.Label(
            frame,
            text="Обычно заполнять не нужно: программа сама ищет действующий адрес.",
            style="Muted.TLabel",
        ).grid(row=6, column=0, columnspan=4, sticky="w", pady=(4, 0))

        ttk.Label(frame, text="Проверка через браузер:").grid(row=7, column=0, sticky="w", pady=(12, 0))
        self.browser_var = tk.StringVar(value="auto" if self.has_browser else "never")
        ttk.Combobox(
            frame,
            textvariable=self.browser_var,
            values=("never", "auto", "always"),
            state="readonly" if self.has_browser else "disabled",
            width=10,
        ).grid(row=7, column=1, sticky="w", pady=(12, 0))

    def _build_log_card(self, row: int) -> int:
        card = theme.Card(self, title="Журнал")
        card.grid(row=row, column=0, sticky="nsew")
        self.rowconfigure(row, weight=1)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)

        holder = ttk.Frame(card, style="Card.TFrame")
        holder.grid(row=1, column=0, sticky="nsew")
        holder.rowconfigure(0, weight=1)
        holder.columnconfigure(0, weight=1)

        self.log = tk.Text(
            holder,
            height=13,
            wrap="none",
            font=self.fonts.mono,
            state="disabled",
            background=theme.LOG_BG,
            foreground=theme.TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            highlightcolor=theme.BORDER,
            padx=10,
            pady=8,
            spacing1=1,
            spacing3=1,
        )
        self.log.grid(row=0, column=0, sticky="nsew")
        for name, options in theme.LOG_TAGS.items():
            self.log.tag_configure(name, **options)
        # Полужирным — только заголовки и сбои. Если выделять и «не удалось
        # проверить», выделенной окажется вся простыня и смысл потеряется.
        self.log.tag_configure("head", font=self.fonts.mono_bold)
        self.log.tag_configure("alert", font=self.fonts.mono_bold)

        scroll_y = ttk.Scrollbar(holder, orient="vertical", command=self.log.yview)
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x = ttk.Scrollbar(holder, orient="horizontal", command=self.log.xview)
        scroll_x.grid(row=1, column=0, sticky="ew")
        self.log.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        return row + 1

    def _build_footer(self, row: int) -> None:
        footer = ttk.Frame(self, style="Head.TFrame")
        footer.grid(row=row, column=0, sticky="ew", pady=(12, 0))
        self.open_file_button = ttk.Button(
            footer,
            text="Открыть результат",
            style="Ghost.TButton",
            command=self._open_result,
            state="disabled",
        )
        self.open_file_button.grid(row=0, column=0, sticky="w")
        self.open_folder_button = ttk.Button(
            footer,
            text="Открыть папку",
            style="Ghost.TButton",
            command=self._open_folder,
            state="disabled",
        )
        self.open_folder_button.grid(row=0, column=1, sticky="w", padx=(10, 0))

    def _toggle_advanced(self) -> None:
        if self.advanced_var.get():
            self.advanced.grid(row=self.advanced_row, column=0, sticky="ew", pady=(0, 12))
        else:
            self.advanced.grid_forget()

    def _greet(self) -> None:
        self._say("Программа проверяет компании по ИНН в реестрах НОСТРОЙ и НОПРИЗ.")
        self._say("")
        self._say("1. Выберите файл Excel со списком компаний.")
        self._say("2. Нажмите «Проверить связь» — убедиться, что реестры отвечают.")
        self._say("3. Нажмите «Начать проверку».")
        self._say("")
        self._say("Результат ляжет рядом с исходным файлом, сам файл не изменится.")
        if not self.has_browser:
            self._say(
                "Запасная проверка через браузер в этой сборке недоступна — "
                "работает прямой запрос к реестрам."
            )
        self._say("")

    # ------------------------------------------------------------------
    # Действия пользователя
    # ------------------------------------------------------------------

    def _choose_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Выберите файл со списком компаний", filetypes=EXCEL_TYPES
        )
        if path:
            self.path_var.set(path)

    def _start_run(self) -> None:
        path = self.path_var.get().strip()
        if not path:
            messagebox.showwarning(APP_TITLE, "Сначала выберите файл Excel со списком компаний.")
            return
        if not os.path.exists(path):
            messagebox.showerror(APP_TITLE, f"Файл не найден:\n{path}")
            return
        self._launch(probe_inn="")

    def _start_probe(self) -> None:
        inn = self.probe_var.get().strip()
        if not inn:
            messagebox.showwarning(
                APP_TITLE,
                "Введите ИНН компании, которая точно состоит в СРО.\n\n"
                "Так проверяется, отвечают ли реестры и правильно ли программа\n"
                "понимает их ответ.",
            )
            return
        self._launch(probe_inn=inn)

    def _stop(self) -> None:
        if self.cancel is not None:
            self.cancel.set()
            self._set_status("Останавливаю… уже проверенное будет сохранено", theme.WARN)
            self.stop_button.configure(state="disabled")

    def _open_result(self) -> None:
        if self.output_path and os.path.exists(self.output_path):
            open_in_system(self.output_path)

    def _open_folder(self) -> None:
        if self.output_path:
            folder = os.path.dirname(os.path.abspath(self.output_path))
            if os.path.isdir(folder):
                open_in_system(folder)

    def _on_close(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            if not messagebox.askyesno(
                APP_TITLE, "Проверка ещё идёт. Остановить её и закрыть программу?"
            ):
                return
            self.closing = True
            if self.cancel is not None:
                self.cancel.set()
            self._set_status("Останавливаю и сохраняю…", theme.WARN)
            return
        self.master.destroy()

    # ------------------------------------------------------------------
    # Запуск работы в отдельном потоке
    # ------------------------------------------------------------------

    def _build_argv(self, probe_inn: str) -> list[str]:
        argv: list[str] = []
        path = self.path_var.get().strip()
        if path:
            argv += ["--input", path]
        sheet = self.sheet_var.get().strip()
        if sheet:
            argv += ["--sheet", sheet]

        argv += ["--delay-min", self._float(self.delay_min_var.get(), 1.0)]
        argv += ["--delay-max", self._float(self.delay_max_var.get(), 2.0)]
        argv += ["--verdict-basis", self.basis_var.get()]
        argv += ["--browser", self.browser_var.get()]

        if self.nostroy_url_var.get().strip():
            argv += ["--nostroy-url", self.nostroy_url_var.get().strip()]
        if self.nopriz_url_var.get().strip():
            argv += ["--nopriz-url", self.nopriz_url_var.get().strip()]

        if probe_inn:
            argv += ["--probe", probe_inn]
        else:
            if self.retry_var.get():
                argv.append("--retry-failed")
            if self.check_all_var.get():
                argv.append("--check-all")
            if self.recheck_var.get():
                argv.append("--recheck-all")
        return argv

    @staticmethod
    def _float(raw: str, fallback: float) -> str:
        try:
            return str(max(0.0, float(str(raw).replace(",", "."))))
        except (TypeError, ValueError):
            return str(fallback)

    def _launch(self, probe_inn: str) -> None:
        self.output_path = ""
        self.open_file_button.configure(state="disabled")
        self.open_folder_button.configure(state="disabled")
        self._clear_log()
        self._set_chips(0, 0, 0)

        argv = self._build_argv(probe_inn)
        self.cancel = threading.Event()
        self._set_running(True, probe=bool(probe_inn))
        self.worker = threading.Thread(
            target=self._work, args=(argv, bool(probe_inn)), daemon=True
        )
        self.worker.start()

    def _work(self, argv: list[str], is_probe: bool) -> None:
        """Выполняется в фоновом потоке. В окно пишет только через очередь."""
        code = 1
        log = None
        try:
            args = check_sro.parse_args(argv)
            # Путь результата сообщаем сразу: файл появляется уже на первом
            # промежуточном сохранении, и открыть его должно быть можно, не
            # дожидаясь конца прогона.
            if not is_probe:
                self.messages.put(("output", args.output))
            # Журнал на диск ведём только для настоящего прогона: для диагностики
            # файл не нужен, а папка может оказаться недоступной для записи.
            log_path = "" if is_probe else args.log
            try:
                log = check_sro.Log(log_path, sink=self._emit)
            except OSError:
                log = check_sro.Log(None, sink=self._emit)
                self._emit("(журнал на диск не ведётся: папка недоступна для записи)")

            if is_probe:
                code = check_sro.run_probe(args, log, cancel=self.cancel)
            else:
                code = check_sro.run(
                    args, log, cancel=self.cancel, progress=self._emit_progress
                )
                self.messages.put(("output", args.output))
        except Exception as error:
            self._emit("")
            self._emit(f"СБОЙ: {type(error).__name__}: {error}")
            self._emit(traceback.format_exc())
        finally:
            if log is not None:
                try:
                    log.close()
                except Exception:
                    pass
            self.messages.put(("done", code))

    def _emit(self, message: str = "") -> None:
        self.messages.put(("line", message))

    def _emit_progress(self, processed: int, total: int, counters: dict) -> None:
        self.messages.put(("progress", (processed, total, counters)))

    # ------------------------------------------------------------------
    # Приём сообщений из фонового потока
    # ------------------------------------------------------------------

    def _drain(self) -> None:
        try:
            while True:
                kind, payload = self.messages.get_nowait()
                if kind == "line":
                    self._say(payload)
                elif kind == "progress":
                    self._show_progress(*payload)
                elif kind == "output":
                    self.output_path = payload
                    self._refresh_output_buttons()
                elif kind == "done":
                    self._finish(payload)
                    if self.closing:
                        # Окно уже уничтожено — планировать следующий опрос не на чем.
                        return
        except queue.Empty:
            pass
        except tk.TclError:
            return
        except Exception:
            # Сбой отрисовки одной строки не должен навсегда остановить приём
            # сообщений: иначе окно замрёт с наполовину показанным результатом.
            pass
        self.after(120, self._drain)

    def _refresh_output_buttons(self) -> None:
        """Включить кнопки, как только файл появился на диске.

        Результат сохраняется каждые 20 строк, так что открыть его можно
        задолго до конца прогона.
        """
        if not self.output_path:
            return
        self.open_folder_button.configure(state="normal")
        if os.path.exists(self.output_path):
            self.open_file_button.configure(state="normal")

    def _show_progress(self, processed: int, total: int, counters: dict) -> None:
        if self.progress["mode"] != "determinate":
            self.progress.stop()
            self.progress.configure(mode="determinate")
        self.progress.configure(maximum=max(1, total), value=processed)
        self._set_status(f"Проверено {processed} из {total}", theme.ACCENT)
        self._set_chips(counters["yes"], counters["no"], counters["unknown"])
        # Файл сохраняется каждые 20 строк — примерно с той же частотой и
        # проверяем, не пора ли разблокировать кнопки.
        if processed % 20 == 0:
            self._refresh_output_buttons()

    def _finish(self, code: int) -> None:
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self._set_running(False)
        self.worker = None

        if self.closing:
            self.master.destroy()
            return

        if self.output_path:
            self._refresh_output_buttons()
        else:
            self.progress.configure(value=0)

        if code == 0:
            self._set_status("Готово", theme.OK)
        elif code == 130:
            self._set_status("Остановлено. Проверенное сохранено — можно продолжить позже", theme.WARN)
        else:
            self._set_status("Завершено с замечаниями — посмотрите журнал", theme.BAD)

    def _set_running(self, running: bool, probe: bool = False) -> None:
        state = "disabled" if running else "normal"
        self.start_button.configure(state=state)
        self.probe_button.configure(state=state)
        self.stop_button.configure(state="normal" if running else "disabled")
        if running:
            self.progress.configure(mode="indeterminate")
            self.progress.start(15)
            self._set_status(
                "Проверяю связь с реестрами…" if probe else "Идёт проверка…", theme.ACCENT
            )

    # ------------------------------------------------------------------
    # Состояние и журнал
    # ------------------------------------------------------------------

    def _set_status(self, text: str, color: str = theme.MUTED) -> None:
        self.status_var.set(text)
        self.dot.set_color(color)

    def _set_chips(self, yes: int, no: int, unknown: int) -> None:
        self.chip_yes.set_text(f"да  {yes}")
        self.chip_no.set_text(f"нет  {no}")
        self.chip_unknown.set_text(f"не удалось  {unknown}")

    def _say(self, message: str = "") -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n", theme.classify(message))
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")


def _selftest(root: tk.Tk, app: App) -> int:
    """Проверка сборки: собрать окно, прогнать через него данные и выйти.

    Гоняем и раскраску журнала, и счётчики, и раскрывающийся блок — чтобы
    сборочный конвейер падал на ошибке в отрисовке, а не только на импорте.
    """
    app.advanced_var.set(True)
    app._toggle_advanced()
    for line in (
        "=== НОСТРОЙ ===",
        "Проверено 1 из 3 | ООО «Пример» | ИНН 7702521529 → да | СРО «Строители»",
        "Проверено 2 из 3 | АО «Пример» | ИНН 7707083893 → нет",
        "Проверено 3 из 3 | ООО «Третий» | ИНН 7806479303 → не удалось проверить",
        "ВНИМАНИЕ: в реестре по этому ИНН другая компания",
        "ОШИБКА: файл не найден",
        "  … промежуточный результат сохранён",
        "ИТОГ: рабочий способ проверки есть",
    ):
        app._say(line)
    app._show_progress(2, 3, {"yes": 1, "no": 1, "unknown": 0})
    app._set_status("Готово", theme.OK)
    root.update_idletasks()
    root.update()
    root.destroy()
    return 0


def main() -> int:
    # На Windows без этого окно выглядит размытым на экранах с масштабированием.
    if sys.platform.startswith("win"):
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[attr-defined]
        except Exception:
            pass

    root = tk.Tk()
    root.title(WINDOW_TITLE)
    root.minsize(840, 700)
    root.geometry("960x780")
    theme.set_icon(root)

    app = App(root)

    if "--selftest" in sys.argv[1:]:
        # --require-browser: убедиться, что в сборку попал Playwright. Без него
        # проверка через браузер молча превратится в «недоступно», а это сейчас
        # единственный надёжный способ достучаться до реестров.
        if "--require-browser" in sys.argv[1:] and not app.has_browser:
            root.destroy()
            return 3
        return _selftest(root, app)

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
