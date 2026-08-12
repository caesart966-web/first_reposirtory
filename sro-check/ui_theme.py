"""Оформление окна: стили ttk, значок и составные виджеты.

Вынесено из gui.py, чтобы код интерфейса остался про поведение, а не про цвета.
Цвета и разбор строк журнала лежат в ui_palette.py — там нет tkinter, и их
можно проверять тестами. Здесь нет ничего про СРО, только внешний вид.

За основу взята тема «clam»: единственная из встроенных, которую можно
последовательно перекрасить на всех системах. Родные «vista» и «aqua»
выглядят привычнее, но не дают менять цвета кнопок и полей.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont, ttk

from ui_palette import (  # noqa: F401 — пробрасываем дальше, gui.py берёт их отсюда
    ACCENT,
    ACCENT_DIM,
    ACCENT_HOVER,
    BAD,
    BAD_BG,
    BG,
    BORDER,
    CARD,
    LOG_BG,
    LOG_TAGS,
    MUTED,
    OK,
    OK_BG,
    TEXT,
    TROUGH,
    WARN,
    WARN_BG,
    classify,
)

# Иконка окна: скруглённый квадрат с галочкой, 64×64.
ICON_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAEX0lEQVR42uWbX0xTVxzHjwomDAqG"
    "oeus91Yoycg2rFmykaDGKMasmFiRAQMdVdzYHmZIJpvOB41uiT4sg/hvvpAa9cUU12zLlvCghScS"
    "iOkTZqLSQin/ZGtAzIS4/HbO7cq0rO09595bb3t+yefm9MD9nd/3+zv3tAkUIRmRkSOYDcV1jjVb"
    "zjlNNreHUNw0BXpCsN/2krqMFVfceW82t6zMf8uKlEaWsXwrSag3sTSmkMZRC1++MjevoOybtlQV"
    "Hg3ZGWQXyxJPto6w+5a3+OAkpBOF+wZD2eL79oTiCxsGQ+km/nliPhJk26dj55fsBNzg/z0gC947"
    "3VZ8YAJ4gDR6yWnPi/gI+RtbTy4aYNzudFvwJE8UNtwLhT/kZAtmiwNPcojBgg9Eg6XWYXGMA4+s"
    "3tTuROTCqwFidZ8Prd1502NpxBOcgg3oxAaMAa8gnsWHDfgIDzgGFeELz2ADgpBKWD8dg/YfZ2HA"
    "vwAkeu8+lV6z5kNF+/EgRbA2jy0Kjw4yT35OmxOlg/hIdPY8YTFgFFIBIk5OWJuDVHlR0T480Dmd"
    "PXMgN+q/naLKrXsDTl8NAU0wGBAAvdJ6+U8q8TNzf1OvgQobAqBHKr+eANpo75yhXkeXBlQem5C6"
    "SRMufE6wrKU7AzZ8PEotfsA/L93HZkD9COiFDYcCkhgq8b556T7WNRUbsPlwEFp/mJaoPDauKFfv"
    "wF/Uh57SNZGSbnX1L/1wQkSwdMTVPZd08WEDPhwGFuJ1S9qWTQHZuTp+m6U+8Zu/mwLW2p+HyYDW"
    "S9Pyns2mEVVyRQe5Rw3xkgHr8YWWrr4n8g8obEKsPJ/gLtJGx68zwFJzLND6Oj/QQnNYERNKiQlR"
    "OWxHx+jf67sfA0u98WAygBRC+1ZVenD4P/FfBanFE9PVFs9sQN2pceqtGzGBQMZKDFTXgFo8YMDl"
    "ecxkAq14slMk8Yx1JgIb4ANWWEygFW/7MghKakwEUppASxO0Fh82oAYPFKKFCUcuPgI1aksEMtcM"
    "gRq4PLOqiT/lnAa16koEUjOZGiaQHMkSHzbgAzxQESUmSOJVricRSIukrtv0JgwMPYXSRv/LMOAh"
    "aAGNCWHxPtCqlnggczUeaIQcE2bmnoHtSAC0rCMeSOsF4pnwssX/a8AD0JqOX5b+cSMwuYDFj0Ay"
    "1o8HEvElGZR/5ocvzk/C9zf+gNoTo5CsdROBxL14wDHIuP1nr7j3PvAKWrPluodrAwrKLrnFKvyC"
    "Q9btuhNCBoujhVcDSPNRZl6JVawaBB4hzQ//u/y2n7ziHjzJGcsyDXmSAdlilUPAEzyR/85Z5wvf"
    "Glm9+ZpH2HMPeMC0qz+02P1IrMgymU2V/SHBjn8pzckyVthjfFO0wp7u4le9fbwt7ncHXxGqHOGd"
    "8DukGwnFRyIzt8T62la3V9iNb0wDTLa+UMxtHy9y3/j8JLk5lcXnbzzjXJYRdeDRBnksSKLXd9zy"
    "pUK3X333gjunqLFFjvB/AMZCFiMaRvVrAAAAAElFTkSuQmCC"
)


def _first_available(root: tk.Misc, *candidates: str) -> str:
    families = set(tkfont.families(root))
    for name in candidates:
        if name in families:
            return name
    return "TkDefaultFont"


class Fonts:
    """Шрифты подбираются под систему: чужой шрифт выглядит хуже родного."""

    def __init__(self, root: tk.Misc) -> None:
        ui = _first_available(root, "Segoe UI", "SF Pro Text", "Helvetica Neue", "DejaVu Sans")
        mono = _first_available(
            root, "Cascadia Mono", "Consolas", "SF Mono", "Menlo", "DejaVu Sans Mono", "Courier New"
        )
        self.body = (ui, 10)
        self.bold = (ui, 10, "bold")
        self.small = (ui, 9)
        self.section = (ui, 11, "bold")
        self.title = (ui, 17, "bold")
        self.button = (ui, 10)
        self.mono = (mono, 9)
        self.mono_bold = (mono, 9, "bold")


def apply(root: tk.Misc) -> Fonts:
    """Настроить палитру и стили. Возвращает подобранные шрифты."""
    fonts = Fonts(root)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:  # на всякий случай: тема есть везде, но мало ли
        pass

    style.configure(".", background=BG, foreground=TEXT, font=fonts.body)

    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD)
    style.configure("Head.TFrame", background=BG)

    style.configure("TLabel", background=CARD, foreground=TEXT, font=fonts.body)
    style.configure("Bg.TLabel", background=BG, foreground=TEXT)
    style.configure("Title.TLabel", background=BG, foreground=TEXT, font=fonts.title)
    style.configure("Subtitle.TLabel", background=BG, foreground=MUTED, font=fonts.small)
    style.configure("Section.TLabel", background=CARD, foreground=TEXT, font=fonts.section)
    style.configure("Muted.TLabel", background=CARD, foreground=MUTED, font=fonts.small)
    style.configure("Status.TLabel", background=BG, foreground=TEXT, font=fonts.bold)

    style.configure(
        "TEntry",
        fieldbackground=CARD,
        background=CARD,
        foreground=TEXT,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        insertcolor=TEXT,
        padding=6,
    )
    style.map("TEntry", bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)])

    style.configure("TSpinbox", fieldbackground=CARD, bordercolor=BORDER, padding=3, arrowsize=12)
    style.configure("TCombobox", fieldbackground=CARD, bordercolor=BORDER, padding=4)

    for name in ("TCheckbutton", "TRadiobutton"):
        style.configure(
            name,
            background=CARD,
            foreground=TEXT,
            font=fonts.body,
            focuscolor=CARD,
            indicatorcolor=CARD,
        )
        style.map(
            name,
            background=[("active", CARD)],
            indicatorcolor=[("selected", ACCENT), ("pressed", ACCENT)],
        )

    # Кнопки: главная — синяя, второстепенные — светлые с рамкой.
    style.configure(
        "Accent.TButton",
        background=ACCENT,
        foreground="#FFFFFF",
        bordercolor=ACCENT,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
        focuscolor=ACCENT,
        font=fonts.button,
        padding=(16, 9),
        relief="flat",
    )
    style.map(
        "Accent.TButton",
        background=[("pressed", ACCENT_HOVER), ("active", ACCENT_HOVER), ("disabled", ACCENT_DIM)],
        bordercolor=[("disabled", ACCENT_DIM)],
        foreground=[("disabled", "#F2F5FD")],
    )

    style.configure(
        "Ghost.TButton",
        background=CARD,
        foreground=TEXT,
        bordercolor=BORDER,
        lightcolor=CARD,
        darkcolor=CARD,
        focuscolor=CARD,
        font=fonts.button,
        padding=(14, 8),
        relief="flat",
    )
    style.map(
        "Ghost.TButton",
        background=[("pressed", "#E8EDF6"), ("active", "#F3F6FC"), ("disabled", CARD)],
        foreground=[("disabled", "#AEB9C6")],
    )

    # Точка на «Ghost»: «Остановить» — та же светлая кнопка, но красной подписью.
    style.configure("Stop.Ghost.TButton", foreground=BAD)
    style.map("Stop.Ghost.TButton", foreground=[("disabled", "#D9B0B0")])

    # Флажок, стоящий не на карточке, а прямо на фоне окна.
    style.configure("Bg.TCheckbutton", background=BG, focuscolor=BG, indicatorcolor=CARD)
    style.map(
        "Bg.TCheckbutton",
        background=[("active", BG)],
        indicatorcolor=[("selected", ACCENT), ("pressed", ACCENT)],
    )

    style.configure(
        "Accent.Horizontal.TProgressbar",
        troughcolor=TROUGH,
        background=ACCENT,
        bordercolor=TROUGH,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
        thickness=10,
    )

    style.configure("TSeparator", background=BORDER)
    style.configure("Vertical.TScrollbar", background="#CFD8E3", troughcolor=BG,
                    bordercolor=BG, arrowcolor=MUTED)
    style.configure("Horizontal.TScrollbar", background="#CFD8E3", troughcolor=BG,
                    bordercolor=BG, arrowcolor=MUTED)

    return fonts


def set_icon(root: tk.Tk) -> None:
    """Поставить иконку окна. Не критично: не вышло — работаем без неё."""
    try:
        image = tk.PhotoImage(data=ICON_PNG)
        root.iconphoto(True, image)
        root._sro_icon = image  # держим ссылку, иначе картинку соберёт сборщик мусора
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Карточка и «чип» со счётчиком
# ---------------------------------------------------------------------------


class Card(ttk.Frame):
    """Белый блок с заголовком — из таких собрано окно."""

    def __init__(self, master, title: str = "", padding: int = 16, **kwargs) -> None:
        super().__init__(master, style="Card.TFrame", padding=padding, **kwargs)
        if title:
            ttk.Label(self, text=title, style="Section.TLabel").grid(
                row=0, column=0, sticky="w", pady=(0, 10)
            )


class Chip(tk.Canvas):
    """Счётчик в цветной плашке со скруглёнными углами.

    Обычный ttk.Label скругления не умеет, поэтому рисуем сами: три таких
    плашки — «да», «нет», «не удалось» — главный смысловой элемент окна.
    """

    def __init__(
        self, master, fill: str, foreground: str, font, height: int = 26, background: str = CARD
    ) -> None:
        super().__init__(
            master, height=height, highlightthickness=0, bd=0, background=background
        )
        self.fill = fill
        self.foreground = foreground
        self.font = font
        self.height = height
        self._text = ""
        self._measure = tkfont.Font(font=font)

    def set_text(self, text: str) -> None:
        if text == self._text:
            return
        self._text = text
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        padding = 12
        width = self._measure.measure(self._text) + padding * 2
        self.configure(width=width)
        self._rounded(1, 1, width - 1, self.height - 1, radius=(self.height - 2) / 2)
        self.create_text(
            width / 2, self.height / 2, text=self._text, fill=self.foreground, font=self.font
        )

    def _rounded(self, x1: float, y1: float, x2: float, y2: float, radius: float) -> None:
        self.create_oval(x1, y1, x1 + 2 * radius, y2, fill=self.fill, outline=self.fill)
        self.create_oval(x2 - 2 * radius, y1, x2, y2, fill=self.fill, outline=self.fill)
        self.create_rectangle(
            x1 + radius, y1, x2 - radius, y2, fill=self.fill, outline=self.fill
        )


class StatusDot(tk.Canvas):
    """Кружок слева от строки состояния: цвет читается быстрее слов."""

    SIZE = 12

    def __init__(self, master, background: str = CARD) -> None:
        super().__init__(
            master,
            width=self.SIZE,
            height=self.SIZE,
            highlightthickness=0,
            bd=0,
            background=background,
        )
        self.set_color(MUTED)

    def set_color(self, color: str) -> None:
        self.delete("all")
        self.create_oval(1, 1, self.SIZE - 1, self.SIZE - 1, fill=color, outline=color)

