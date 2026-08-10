"""Простой GUI на Tkinter: выбор файла, галочки источников, прогресс-бар с ETA,
счётчики «обработано / найдено / ошибок», кнопки «Пауза» и «Продолжить».

Пайплайн выполняется в фоновом потоке со своим asyncio-циклом; управление
паузой — через loop.call_soon_threadsafe.
"""
from __future__ import annotations

import asyncio
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from connectors import CONNECTOR_REGISTRY
from core.config import Config
from core.orchestrator import Orchestrator, Progress
from storage.db import Database
from utils.io_input import read_companies, write_errors_xlsx
from utils.io_output import export_results
from utils.logging_setup import setup_logging


class FinderGui:
    """Окно приложения."""

    def __init__(self) -> None:
        self.config = Config.load()
        setup_logging(self.config.resolve_path(self.config.get("output.logs_dir", "logs")))
        self.root = tk.Tk()
        self.root.title("Контакты юрлиц РФ — сбор по открытым источникам")
        self.root.geometry("640x560")

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(Path.cwd() / "result.xlsx"))
        self.depth_var = tk.StringVar(value=str(self.config.get("depth", "full")))
        self.status_var = tk.StringVar(value="Готов к запуску")
        self.counter_var = tk.StringVar(value="обработано 0 / найдено 0 / ошибок 0")
        self.source_vars: dict[str, tk.BooleanVar] = {}

        self._msg_queue: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._orchestrator: Optional[Orchestrator] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._paused = False

        self._build_layout()
        self.root.after(200, self._poll_queue)

    # ------------------------------------------------------------------ #

    def _build_layout(self) -> None:
        pad = {"padx": 8, "pady": 4}

        file_frame = ttk.LabelFrame(self.root, text="Файлы")
        file_frame.pack(fill="x", **pad)
        ttk.Label(file_frame, text="Входной файл:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(file_frame, textvariable=self.input_var, width=52).grid(row=0, column=1, **pad)
        ttk.Button(file_frame, text="Обзор…", command=self._pick_input).grid(row=0, column=2, **pad)
        ttk.Label(file_frame, text="Итоговый XLSX:").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(file_frame, textvariable=self.output_var, width=52).grid(row=1, column=1, **pad)
        ttk.Button(file_frame, text="Обзор…", command=self._pick_output).grid(row=1, column=2, **pad)

        source_frame = ttk.LabelFrame(self.root, text="Источники")
        source_frame.pack(fill="x", **pad)
        for idx, (name, cls) in enumerate(sorted(
                CONNECTOR_REGISTRY.items(), key=lambda kv: kv[1].default_priority)):
            var = tk.BooleanVar(value=self.config.source_enabled(name))
            self.source_vars[name] = var
            ttk.Checkbutton(
                source_frame, variable=var,
                text=f"{cls.title} (уровень {cls.level.value})",
            ).grid(row=idx // 2, column=idx % 2, sticky="w", padx=12, pady=2)

        options_frame = ttk.Frame(self.root)
        options_frame.pack(fill="x", **pad)
        ttk.Label(options_frame, text="Глубина поиска:").pack(side="left", padx=8)
        ttk.Radiobutton(options_frame, text="искать всё", value="full",
                        variable=self.depth_var).pack(side="left")
        ttk.Radiobutton(options_frame, text="до первого e-mail", value="first_email",
                        variable=self.depth_var).pack(side="left", padx=8)

        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill="x", **pad)
        self.start_btn = ttk.Button(control_frame, text="Старт", command=self._start)
        self.start_btn.pack(side="left", padx=8)
        self.pause_btn = ttk.Button(control_frame, text="Пауза",
                                    command=self._toggle_pause, state="disabled")
        self.pause_btn.pack(side="left", padx=8)
        self.stop_btn = ttk.Button(control_frame, text="Стоп",
                                   command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=8)

        self.progressbar = ttk.Progressbar(self.root, mode="determinate")
        self.progressbar.pack(fill="x", padx=16, pady=8)
        ttk.Label(self.root, textvariable=self.counter_var).pack()
        ttk.Label(self.root, textvariable=self.status_var).pack()

        self.log_widget = tk.Text(self.root, height=10, state="disabled", wrap="none")
        self.log_widget.pack(fill="both", expand=True, padx=8, pady=8)

    # ------------------------------------------------------------------ #

    def _pick_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Входной файл",
            filetypes=[("Таблицы и списки", "*.xlsx *.csv *.txt"), ("Все файлы", "*.*")])
        if path:
            self.input_var.set(path)

    def _pick_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Куда сохранить результат", defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")])
        if path:
            self.output_var.set(path)

    def _append_log(self, line: str) -> None:
        self.log_widget.configure(state="normal")
        self.log_widget.insert("end", line + "\n")
        self.log_widget.see("end")
        self.log_widget.configure(state="disabled")

    # ------------------------------------------------------------------ #

    def _start(self) -> None:
        input_path = self.input_var.get().strip()
        if not input_path:
            messagebox.showerror("Нет входного файла", "Выберите файл со списком компаний")
            return
        selected = {name for name, var in self.source_vars.items() if var.get()}
        if not selected:
            messagebox.showerror("Нет источников", "Отметьте хотя бы один источник")
            return
        self.start_btn.configure(state="disabled")
        self.pause_btn.configure(state="normal", text="Пауза")
        self.stop_btn.configure(state="normal")
        self._paused = False
        self.status_var.set("Запуск…")

        self._worker = threading.Thread(
            target=self._run_pipeline,
            args=(input_path, self.output_var.get().strip(), selected,
                  self.depth_var.get()),
            daemon=True,
        )
        self._worker.start()

    def _toggle_pause(self) -> None:
        if self._orchestrator is None or self._loop is None:
            return
        event = self._orchestrator.pause_event
        if self._paused:
            self._loop.call_soon_threadsafe(event.set)
            self._paused = False
            self.pause_btn.configure(text="Пауза")
            self.status_var.set("Продолжаем…")
        else:
            self._loop.call_soon_threadsafe(event.clear)
            self._paused = True
            self.pause_btn.configure(text="Продолжить")
            self.status_var.set("Пауза (текущие запросы завершатся и встанут)")

    def _stop(self) -> None:
        if self._orchestrator is not None and self._loop is not None:
            self._loop.call_soon_threadsafe(self._orchestrator.request_stop)
            self.status_var.set("Останавливаемся… прогресс сохранён")

    # ------------------------------------------------------------------ #

    def _run_pipeline(self, input_path: str, output_path: str,
                      sources: set[str], depth: str) -> None:
        """Фоновый поток: чтение входа, прогон, экспорт."""
        try:
            db = Database(self.config.db_path)
            parsed = read_companies(input_path)
            for company in parsed.companies:
                db.upsert_company_input(company)
            if parsed.errors:
                errors_path = str(Path(output_path).with_name("errors.xlsx"))
                write_errors_xlsx(parsed.errors, errors_path)
                self._msg_queue.put(("log", f"Брак входа: {len(parsed.errors)} строк -> {errors_path}"))

            orchestrator = Orchestrator(self.config, db, only_sources=sources, depth=depth)
            self._orchestrator = orchestrator
            orchestrator.on_progress(
                lambda progress, message: self._msg_queue.put(("progress", (progress, message))))

            loop = asyncio.new_event_loop()
            self._loop = loop
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(orchestrator.run())
            finally:
                loop.close()

            stats = export_results(db, output_path)
            db.close()
            self._msg_queue.put(("done", stats))
        except Exception as exc:  # noqa: BLE001 — показываем ошибку пользователю
            self._msg_queue.put(("error", f"{exc.__class__.__name__}: {exc}"))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self._msg_queue.get_nowait()
                if kind == "progress":
                    progress, message = payload  # type: ignore[misc]
                    self._show_progress(progress, message)
                elif kind == "log":
                    self._append_log(str(payload))
                elif kind == "done":
                    stats = payload  # type: ignore[assignment]
                    self.status_var.set(
                        f"Готово: всего {stats['total']}, полностью {stats['full']}, "
                        f"частично {stats['partial']}, не найдено {stats['none']}")
                    self._append_log(f"Результат сохранён: {self.output_var.get()}")
                    self._reset_buttons()
                elif kind == "error":
                    messagebox.showerror("Ошибка", str(payload))
                    self.status_var.set("Ошибка — подробности в logs/finder.log")
                    self._reset_buttons()
        except queue.Empty:
            pass
        self.root.after(200, self._poll_queue)

    def _show_progress(self, progress: Progress, message: str) -> None:
        if progress.total:
            self.progressbar.configure(maximum=progress.total, value=progress.processed)
        eta = progress.eta_seconds
        eta_text = f", осталось ~{int(eta // 60)} мин {int(eta % 60)} c" if eta else ""
        self.counter_var.set(
            f"обработано {progress.processed}/{progress.total} / "
            f"найдено e-mail {progress.found_email}, тел. {progress.found_phone} / "
            f"ошибок {progress.errors}{eta_text}")
        if message:
            self._append_log(message)

    def _reset_buttons(self) -> None:
        self.start_btn.configure(state="normal")
        self.pause_btn.configure(state="disabled", text="Пауза")
        self.stop_btn.configure(state="disabled")
        self._orchestrator = None
        self._loop = None

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    FinderGui().run()


if __name__ == "__main__":
    main()
