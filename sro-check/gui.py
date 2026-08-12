#!/usr/bin/env python3
"""Оконная версия проверки СРО — то же самое, что check_sro.py, но с кнопками.

Запуск из исходников:
    python gui.py

Из собранной программы — просто двойной клик по «Проверка СРО.exe».

Вся логика проверки живёт в check_sro.py и sro/*; здесь только интерфейс:
выбор файла, кнопки, индикатор прогресса и журнал. Долгая работа идёт
в отдельном потоке, а сообщения из него передаются в окно через очередь —
трогать виджеты Tk из чужого потока нельзя.
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
from tkinter import filedialog, font as tkfont, messagebox, ttk

import check_sro

APP_TITLE = "Проверка СРО — НОСТРОЙ и НОПРИЗ"
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
        super().__init__(master, padding=12)
        self.master = master
        self.grid(row=0, column=0, sticky="nsew")
        master.rowconfigure(0, weight=1)
        master.columnconfigure(0, weight=1)

        self.messages: queue.Queue = queue.Queue()
        self.cancel: threading.Event | None = None
        self.worker: threading.Thread | None = None
        self.output_path = ""
        self.closing = False
        self.has_browser = playwright_available()

        self._build()
        self._drain()

        master.protocol("WM_DELETE_WINDOW", self._on_close)

        self._say("Программа проверяет компании по ИНН в реестрах НОСТРОЙ и НОПРИЗ.")
        self._say("")
        self._say("1. Выберите файл Excel со списком компаний.")
        self._say("2. Нажмите «Проверить связь» — убедиться, что реестры отвечают.")
        self._say("3. Нажмите «Начать проверку».")
        self._say("")
        if not self.has_browser:
            self._say(
                "Примечание: запасная проверка через браузер в этой сборке недоступна — "
                "работает только прямой запрос к реестрам."
            )
            self._say("")

    # ------------------------------------------------------------------
    # Интерфейс
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        row = 0

        # --- выбор файла ---
        ttk.Label(self, text="Файл Excel со списком компаний:").grid(
            row=row, column=0, sticky="w"
        )
        row += 1

        picker = ttk.Frame(self)
        picker.grid(row=row, column=0, sticky="ew", pady=(2, 8))
        picker.columnconfigure(0, weight=1)
        self.path_var = tk.StringVar()
        ttk.Entry(picker, textvariable=self.path_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(picker, text="Выбрать…", command=self._choose_file).grid(
            row=0, column=1, padx=(6, 0)
        )
        row += 1

        # --- лист и режим ---
        options = ttk.Frame(self)
        options.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(options, text="Лист:").grid(row=0, column=0, sticky="w")
        self.sheet_var = tk.StringVar(value="Лиды по приоритету")
        ttk.Entry(options, textvariable=self.sheet_var, width=26).grid(
            row=0, column=1, sticky="w", padx=(6, 16)
        )
        self.retry_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options,
            text="только строки «не удалось проверить»",
            variable=self.retry_var,
        ).grid(row=0, column=2, sticky="w")
        row += 1

        ttk.Separator(self, orient="horizontal").grid(row=row, column=0, sticky="ew", pady=6)
        row += 1

        # --- проверка связи ---
        probe = ttk.Frame(self)
        probe.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(probe, text="ИНН компании, которая точно в СРО:").grid(
            row=0, column=0, sticky="w"
        )
        self.probe_var = tk.StringVar()
        ttk.Entry(probe, textvariable=self.probe_var, width=16).grid(
            row=0, column=1, sticky="w", padx=(6, 6)
        )
        self.probe_button = ttk.Button(
            probe, text="Проверить связь", command=self._start_probe
        )
        self.probe_button.grid(row=0, column=2, sticky="w")
        row += 1

        # --- основные кнопки ---
        actions = ttk.Frame(self)
        actions.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        self.start_button = ttk.Button(
            actions, text="▶  Начать проверку", command=self._start_run
        )
        self.start_button.grid(row=0, column=0, sticky="w")
        self.stop_button = ttk.Button(
            actions, text="■  Остановить", command=self._stop, state="disabled"
        )
        self.stop_button.grid(row=0, column=1, sticky="w", padx=(8, 16))
        self.advanced_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            actions,
            text="дополнительные настройки",
            variable=self.advanced_var,
            command=self._toggle_advanced,
        ).grid(row=0, column=2, sticky="w")
        row += 1

        # --- дополнительные настройки (скрыты по умолчанию) ---
        self.advanced = ttk.Labelframe(self, text="Дополнительно", padding=8)
        self.advanced_row = row
        self._build_advanced()
        row += 1

        # --- прогресс ---
        self.progress = ttk.Progressbar(self, mode="determinate", maximum=100)
        self.progress.grid(row=row, column=0, sticky="ew")
        row += 1

        self.status_var = tk.StringVar(value="Готово к работе")
        ttk.Label(self, textvariable=self.status_var).grid(
            row=row, column=0, sticky="w", pady=(4, 8)
        )
        row += 1

        # --- журнал ---
        log_frame = ttk.Frame(self)
        log_frame.grid(row=row, column=0, sticky="nsew")
        self.rowconfigure(row, weight=1)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        mono = tkfont.nametofont("TkFixedFont").copy()
        mono.configure(size=max(9, mono.cget("size") - 1))
        self.log = tk.Text(log_frame, height=16, wrap="none", font=mono, state="disabled")
        self.log.grid(row=0, column=0, sticky="nsew")
        scroll_y = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x = ttk.Scrollbar(log_frame, orient="horizontal", command=self.log.xview)
        scroll_x.grid(row=1, column=0, sticky="ew")
        self.log.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        row += 1

        # --- нижние кнопки ---
        bottom = ttk.Frame(self)
        bottom.grid(row=row, column=0, sticky="ew", pady=(8, 0))
        self.open_file_button = ttk.Button(
            bottom, text="Открыть результат", command=self._open_result, state="disabled"
        )
        self.open_file_button.grid(row=0, column=0, sticky="w")
        self.open_folder_button = ttk.Button(
            bottom, text="Открыть папку", command=self._open_folder, state="disabled"
        )
        self.open_folder_button.grid(row=0, column=1, sticky="w", padx=(8, 0))

    def _build_advanced(self) -> None:
        frame = self.advanced
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)

        ttk.Label(frame, text="Пауза между запросами, с: от").grid(row=0, column=0, sticky="w")
        self.delay_min_var = tk.StringVar(value="1.0")
        ttk.Spinbox(
            frame, from_=0, to=60, increment=0.5, width=6, textvariable=self.delay_min_var
        ).grid(row=0, column=1, sticky="w", padx=(6, 6))
        ttk.Label(frame, text="до").grid(row=0, column=2, sticky="e")
        self.delay_max_var = tk.StringVar(value="2.0")
        ttk.Spinbox(
            frame, from_=0, to=60, increment=0.5, width=6, textvariable=self.delay_max_var
        ).grid(row=0, column=3, sticky="w", padx=(6, 0))

        self.basis_var = tk.StringVar(value="active")
        ttk.Label(frame, text="Считать «да»:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        basis = ttk.Frame(frame)
        basis.grid(row=1, column=1, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Radiobutton(
            basis,
            text="только действующее членство",
            value="active",
            variable=self.basis_var,
        ).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            basis,
            text="любая запись в реестре",
            value="found",
            variable=self.basis_var,
        ).grid(row=0, column=1, sticky="w", padx=(12, 0))

        self.check_all_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="опрашивать оба реестра, даже если компания уже найдена",
            variable=self.check_all_var,
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(8, 0))

        self.recheck_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="не использовать сохранённые результаты (проверить всё заново)",
            variable=self.recheck_var,
        ).grid(row=3, column=0, columnspan=4, sticky="w")

        ttk.Label(frame, text="Адрес API НОСТРОЙ:").grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.nostroy_url_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.nostroy_url_var).grid(
            row=4, column=1, columnspan=3, sticky="ew", pady=(8, 0)
        )
        ttk.Label(frame, text="Адрес API НОПРИЗ:").grid(row=5, column=0, sticky="w")
        self.nopriz_url_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.nopriz_url_var).grid(
            row=5, column=1, columnspan=3, sticky="ew"
        )

        self.browser_var = tk.StringVar(value="auto" if self.has_browser else "never")
        ttk.Label(frame, text="Проверка через браузер:").grid(row=6, column=0, sticky="w", pady=(8, 0))
        combo = ttk.Combobox(
            frame,
            textvariable=self.browser_var,
            values=("never", "auto", "always"),
            state="readonly" if self.has_browser else "disabled",
            width=10,
        )
        combo.grid(row=6, column=1, sticky="w", pady=(8, 0))

    def _toggle_advanced(self) -> None:
        if self.advanced_var.get():
            self.advanced.grid(row=self.advanced_row, column=0, sticky="ew", pady=(0, 8))
        else:
            self.advanced.grid_forget()

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
            self.status_var.set("Останавливаю… уже проверенное будет сохранено")
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
            self.status_var.set("Останавливаю и сохраняю…")
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
                elif kind == "done":
                    self._finish(payload)
        except queue.Empty:
            pass
        self.after(120, self._drain)

    def _show_progress(self, processed: int, total: int, counters: dict) -> None:
        if self.progress["mode"] != "determinate":
            self.progress.stop()
            self.progress.configure(mode="determinate")
        self.progress.configure(maximum=max(1, total), value=processed)
        self.status_var.set(
            f"Проверено {processed} из {total}   ·   "
            f"да: {counters['yes']}   нет: {counters['no']}   "
            f"не удалось: {counters['unknown']}"
        )

    def _finish(self, code: int) -> None:
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self._set_running(False)
        self.worker = None

        if self.closing:
            self.master.destroy()
            return

        if self.output_path:
            # Программа могла сохранить результат под другим именем, если файл
            # был занят Excel — тогда точный путь ищем в журнале.
            exists = os.path.exists(self.output_path)
            self.open_folder_button.configure(state="normal")
            self.open_file_button.configure(state="normal" if exists else "disabled")

        if code == 0:
            self.status_var.set("Готово")
        elif code == 130:
            self.status_var.set("Остановлено. Проверенное сохранено — можно продолжить позже")
        else:
            self.status_var.set("Завершено с замечаниями — посмотрите журнал")

    def _set_running(self, running: bool, probe: bool = False) -> None:
        state = "disabled" if running else "normal"
        self.start_button.configure(state=state)
        self.probe_button.configure(state=state)
        self.stop_button.configure(state="normal" if running else "disabled")
        if running:
            self.progress.configure(mode="indeterminate")
            self.progress.start(15)
            self.status_var.set(
                "Проверяю связь с реестрами…" if probe else "Идёт проверка…"
            )

    # ------------------------------------------------------------------
    # Журнал
    # ------------------------------------------------------------------

    def _say(self, message: str = "") -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")


def main() -> int:
    # На Windows без этого окно выглядит размытым на экранах с масштабированием.
    if sys.platform.startswith("win"):
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[attr-defined]
        except Exception:
            pass

    root = tk.Tk()
    root.title(APP_TITLE)
    root.minsize(760, 620)
    try:
        root.call("tk", "scaling", 1.3)
    except tk.TclError:
        pass
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
