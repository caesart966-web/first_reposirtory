"""Запускатор настольной версии: один .exe, двойной щелчок — и работает.

Что делает: находит папку для данных, поднимает сервер приложения внутри себя,
открывает окно с интерфейсом (встроенный браузер Windows — WebView2; если его
нет — обычный браузер плюс маленькое окно состояния). Закрыли окно — сервер
остановлен. Никаких команд, адресов и Python на компьютере коллеги.
"""
from __future__ import annotations

import os
import shutil
import socket
import sys
import threading
import time
import urllib.request

APP_TITLE = "ОДО-проверка"
FROZEN = getattr(sys, "frozen", False)
BUNDLE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def app_root() -> str:
    """Папка, где лежит .exe (или odo-app/ при запуске из исходников)."""
    return os.path.dirname(sys.executable) if FROZEN else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pick_data_dir() -> str:
    """Данные рядом с .exe (удобно копировать), а если туда нельзя писать — в профиле пользователя."""
    cand = os.path.join(app_root(), "ОДО-данные")
    try:
        os.makedirs(cand, exist_ok=True)
        probe = os.path.join(cand, ".w")
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
        return cand
    except OSError:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        d = os.path.join(base, "ODO-proverka")
        os.makedirs(d, exist_ok=True)
        return d


def engine_dir() -> str:
    if FROZEN:
        return os.path.join(BUNDLE, "engine")
    return os.path.abspath(os.path.join(app_root(), "..", ".claude", "skills", "sro-odo"))


def seed_cases(data_dir: str, eng: str) -> str:
    """Прецеденты живут в данных (в .exe они только для чтения); при первом запуске — копия из сборки."""
    dst = os.path.join(data_dir, "cases")
    src = os.path.join(eng, "cases")
    if not os.path.exists(os.path.join(dst, "index.jsonl")) and os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)
    os.makedirs(dst, exist_ok=True)
    return dst


def free_port(start: int = 8765) -> int:
    for p in range(start, start + 50):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return start


def main() -> int:
    data = os.environ.get("ODO_DATA_DIR") or pick_data_dir()
    eng = engine_dir()
    os.environ["ODO_DATA_DIR"] = data
    os.environ["ODO_ENGINE_DIR"] = eng
    if not os.environ.get("ODO_REPORTS_DIR"):
        rep = os.path.join(os.path.dirname(data), "ОДО-отчёты") if os.path.basename(data) == "ОДО-данные" else os.path.join(data, "отчёты")
        os.makedirs(rep, exist_ok=True)
        os.environ["ODO_REPORTS_DIR"] = rep
    os.environ.setdefault("ODO_CASES_DIR", seed_cases(data, eng))
    tess = os.path.join(BUNDLE, "tesseract", "tesseract.exe")
    if FROZEN and os.path.exists(tess):
        os.environ.setdefault("ODO_TESSERACT", tess)
        os.environ.setdefault("TESSDATA_PREFIX", os.path.join(BUNDLE, "tesseract", "tessdata"))
    port = free_port(int(os.environ.get("ODO_PORT", "8765")))
    os.environ["ODO_PORT"] = str(port)
    os.environ["ODO_HOST"] = "127.0.0.1"
    url = f"http://127.0.0.1:{port}/"

    if not FROZEN:
        sys.path.insert(0, app_root())
    log_path = os.path.join(data, "server.log")
    smoke = bool(os.environ.get("ODO_SMOKE"))
    # у оконного .exe нет консоли: sys.stdout/sys.stderr = None, а uvicorn спрашивает у них isatty()
    if sys.stdout is None:
        sys.stdout = open(os.path.join(data, "stdout.log"), "a", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.path.join(data, "stderr.log"), "a", encoding="utf-8")
    try:
        import uvicorn
        from server.main import app  # noqa: E402  (после установки окружения)
    except Exception:
        import traceback
        tb = traceback.format_exc()
        with open(os.path.join(data, "start-error.txt"), "w", encoding="utf-8") as f:
            f.write(tb)
        if smoke:
            return 2
        _fatal("Не удалось загрузить приложение. Подробности в файле:\n" + os.path.join(data, "start-error.txt"))
        return 2

    log_cfg = uvicorn.config.LOGGING_CONFIG
    for fmt in log_cfg["formatters"].values():
        fmt["use_colors"] = False
    for h in log_cfg["handlers"].values():
        h.pop("stream", None)
        h["class"] = "logging.FileHandler"
        h["filename"] = log_path
        h["encoding"] = "utf-8"
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_config=log_cfg, log_level="info")
    server = uvicorn.Server(config)

    def run_server():
        try:
            server.run()
        except Exception:
            import traceback
            with open(os.path.join(data, "start-error.txt"), "w", encoding="utf-8") as f:
                f.write(traceback.format_exc())

    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    ok = False
    for _ in range(60 if smoke else 200):
        try:
            with urllib.request.urlopen(url + "health", timeout=1) as r:
                ok = r.status == 200
                if ok:
                    break
        except Exception:
            time.sleep(0.1)
    if not ok:
        if smoke:
            return 1
        _fatal(f"Сервер не запустился. Подробности в файлах:\n{log_path}\n{os.path.join(data, 'start-error.txt')}")
        return 1

    if smoke:
        # у оконного .exe нет консоли: результат проверки — файлом
        with open(os.path.join(data, "smoke.ok"), "w", encoding="utf-8") as f:
            f.write(f"smoke ok {url} {data}\n")
        server.should_exit = True
        t.join(timeout=10)
        return 0

    try:
        import webview
        webview.create_window(APP_TITLE, url, width=1280, height=860, min_size=(900, 600), text_select=True)
        webview.start()
    except Exception:
        _browser_fallback(url, data)
    server.should_exit = True
    t.join(timeout=10)
    return 0


def _browser_fallback(url: str, data: str):
    import webbrowser
    webbrowser.open(url)
    try:
        import tkinter as tk
    except Exception:
        while True:  # без tkinter окна не будет — просто держим сервер
            time.sleep(3600)
    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry("460x200")
    root.resizable(False, False)
    tk.Label(root, text="ОДО-проверка работает.", font=("Segoe UI", 13, "bold")).pack(pady=(18, 4))
    tk.Label(root, text=f"Интерфейс открыт в браузере: {url}\nДанные: {data}", font=("Segoe UI", 9), justify="center").pack()
    tk.Button(root, text="Открыть ещё раз", command=lambda: webbrowser.open(url), width=22).pack(pady=(12, 4))
    tk.Label(root, text="Закройте это окно, чтобы остановить программу.", font=("Segoe UI", 9), fg="#666").pack()
    root.mainloop()


def _fatal(msg: str):
    try:
        import tkinter as tk
        from tkinter import messagebox
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror(APP_TITLE, msg)
    except Exception:
        print(msg, file=sys.stderr)


def _guarded_main() -> int:
    """Любая неожиданная ошибка — в файл: у оконного .exe консоли нет, а окно PyInstaller с ошибкой на сборочной машине ждёт вечно."""
    try:
        return main()
    except BaseException:  # noqa: BLE001
        import tempfile
        import traceback
        tb = traceback.format_exc()
        d = os.environ.get("ODO_DATA_DIR") or tempfile.gettempdir()
        try:
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "start-error.txt"), "a", encoding="utf-8") as f:
                f.write(tb)
        except OSError:
            pass
        if sys.stderr:
            sys.stderr.write(tb)
        if not os.environ.get("ODO_SMOKE"):
            _fatal("Ошибка при запуске. Подробности в файле start-error.txt в папке данных.")
        return 3


if __name__ == "__main__":
    sys.exit(_guarded_main())
