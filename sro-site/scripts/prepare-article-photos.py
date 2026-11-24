#!/usr/bin/env python3
"""Кадры для шапок статей (16.10.2026).

Снимки прислал заказчик, источник не указан (см. public/img/CREDITS.md,
«Шапки статей 16.10.2026»). Обработка общая для сайта — тёплый монохром
(scripts/monotone.py), ширина как у шапок услуг.

  article-dogovor  — подпись договора за тёмным столом, «Нужна ли СРО,
                     если договор до 10 млн». Исходник — регистрация брака
                     (букет, невеста), поэтому кадр обрезан до рук, ручки,
                     листа и папки: ни лиц, ни букета, ни кольца в углу.
                     Отражён: лист стоял слева, под самой плотной плёнкой
                     шапки, а справа был пустой стол. Букв в кадре нет,
                     отражение не видно.
  article-proverka — человек читает договор с ручкой в руке, лица нет,
                     «Как проверить СРО перед вступлением».
  article-stoimost — два башенных крана на фоне неба (Unsplash),
                     «Сколько стоит вступление в СРО».
  article-region   — старинный глобус, Россия от Москвы и Ростова до
                     Сибири, «В СРО какого региона вступать». Обрезан
                     до России и Казахстана: нижняя половина — Ближний
                     Восток и Индия, у левого края был кусок соседней
                     страны, а справа Китай — на компьютере правый край
                     шапки светлее всего, и там стояла бы Маньчжурия. Крыма в кадре нет — он за левым краем
                     снимка, вопроса о границах на карте не возникает.

    python3 scripts/prepare-article-photos.py      # из sro-site/
    python3 scripts/prepare-article-photos.py article-vyhod   # один кадр
"""
import sys
from pathlib import Path

from PIL import Image, ImageFilter

from monotone import monotone

SRC = Path("assets-src")
OUT = Path("public/img")
WIDTH = 1600
WEBP_QUALITY, AVIF_QUALITY = 72, 50
WEBP_LIMIT_KB, AVIF_LIMIT_KB = 190, 120
# Глобус весь в мелких подписях и не влезал в бюджет при общем качестве;
# под плёнкой шапки разницы не видно.
QUALITY = {"article-region": (66, 46)}
# Мелкие исходники увеличиваются до этой ширины (Lanczos и лёгкая резкость):
# браузер растягивал бы их сам и мягче. Нейросеть здесь не нужна — кадр
# лежит под плёнкой шапки.
UPSCALE = {"article-dve-sro": 1320}

# (исходник, имя, обрезка в пикселях исходника (left, top, right, bottom) или None,
#  отразить по горизонтали, уровни)
PHOTOS = [
    ("article-dogovor-src.jpg", "article-dogovor", (860, 400, 1880, 1333), True, (0.02, 0.82, 0.75)),
    ("article-proverka-src.jpg", "article-proverka", None, False, (0.04, 0.96, 0.85)),
    ("article-region-src.jpg", "article-region", (70, 0, 1080, 1320), False, (0.03, 0.88, 0.8)),
    # 22.10.2026 — «Сколько стоит вступление в СРО»: два башенных крана
    # (Kouji Tsuru, Unsplash License — CREDITS.md), запасной исходник
    # 1320×462, лежал в assets-src с 27.08.2026. Целиком.
    ("cranes-crop-spare.jpg", "article-stoimost", None, False, (0.02, 0.9, 0.85)),
    # 02.11.2026 — свободных снимков нет (стоки из среды закрыты, кадры
    # заказчика стоят в шапках услуг), поэтому две статьи получили другие
    # куски тех же снимков, без повтора кадра услуги целиком.
    # «Выход из СРО»: ключи на простом плане помещения — из desk-src
    # (целиком он в шапке «Вступления в СРО»), без каски и уровня.
    ("desk-src.jpg", "article-vyhod", (842, 1205, 3970, 2972), False, (0.03, 0.95, 0.85)),
    # «Уведомления о договорах»: руки, бумаги и ноутбук на столе
    # переговоров — из quiz-2-src (целиком в шапке «Сопровождения
    # проверок»), обрезан ниже подбородков: лиц в кадре нет.
    ("quiz-2-src.jpg", "article-uvedomleniya", (1044, 2375, 5958, 3604), False, (0.03, 0.95, 0.85)),
    # 11.11.2026 — исходники, которые на сайте сейчас не стоят нигде.
    # «Нужна ли СРО субподрядчику»: GNSS-приёмник на штативе, за ним башенный
    # кран (Valerie V, Unsplash License — CREDITS.md, «survey»), целиком.
    # Исходник — бывшая синяя плашка, яркость в узкой полосе 0,25–0,79:
    # уровни растянуты по ней, иначе кадр выходил серой дымкой.
    ("survey-card-src.png", "article-subpodryad", None, False, (0.24, 0.80, 1.1)),
    # «Нужна ли СРО техническому заказчику»: план этажа, ручка и свёрнутые
    # чертежи — прежний кадр слайда проектировщиков (с 28.09.2026 там другой
    # план). Обрезан сверху до листа с планом.
    ("slide-design-src.jpg", "article-tehzakazchik", (0, 120, 960, 1200), False, (0.03, 0.95, 0.85)),
    # 18.11.2026 — тоже исходники, которых на сайте нет.
    # «Две СРО, если в договоре изыскания и проект»: силуэты двух изыскателей
    # на закате — прибор на штативе, рулон чертежей, ноутбук; прежний слайд
    # изыскателей (с 28.09.2026 там геодезист), 820×334 — увеличен (UPSCALE).
    ("slide-survey-src.jpg", "article-dve-sro", None, False, (0.03, 0.92, 0.9)),
    # «СРО исключили из реестра»: стопка папок с подшитыми документами
    # (Beatriz Pérez Moya, Unsplash License — CREDITS.md, «documents»),
    # правая часть с папками; белое на белом — уровни круче, как в 2026-08.
    ("folders-src.jpg", "article-isklyuchili", (760, 0, 2000, 1086), False, (0.35, 0.98, 1.6)),
    # 24.11.2026 — снова куски снимков, которые целиком стоят на других
    # страницах: свободных исходников не осталось.
    # «СРО для монтажа пожарной сигнализации»: каска и уровень на бетонном
    # полу — верх desk-src (целиком он в шапке «Вступления в СРО», ключи
    # из него — в «Выходе из СРО»), без планов и ключей.
    ("desk-src.jpg", "article-pozharka", (1500, 0, 4700, 1500), False, (0.03, 0.95, 0.85)),
    # «СРО для рабочей документации»: план с размерными цепочками — низ
    # design-plan-src (целиком он на странице проектировщиков), без рулетки
    # и трафаретов.
    ("design-plan-src.webp", "article-rabochaya", (0, 640, 1200, 1500), False, (0.04, 0.96, 0.9)),
]


def main() -> None:
    # Имена кадров аргументами — собрать только их: прочие файлы не
    # пересобираются, и их отпечатки ?v= на сайте не меняются.
    only = set(sys.argv[1:])
    for source, name, box, mirror, levels in PHOTOS:
        if only and name not in only:
            continue
        img = Image.open(SRC / source).convert("RGB")
        if box:
            img = img.crop(box)
        if mirror:
            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if img.width > WIDTH:
            img = img.resize((WIDTH, round(img.height * WIDTH / img.width)), Image.LANCZOS)
        if name in UPSCALE and img.width < UPSCALE[name]:
            w = UPSCALE[name]
            img = img.resize((w, round(img.height * w / img.width)), Image.LANCZOS)
            img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
        img = monotone(img, *levels)
        webp, avif = OUT / f"{name}.webp", OUT / f"{name}.avif"
        webp_q, avif_q = QUALITY.get(name, (WEBP_QUALITY, AVIF_QUALITY))
        img.save(webp, "WEBP", quality=webp_q, method=6)
        img.save(avif, "AVIF", quality=avif_q)
        for path, limit in ((webp, WEBP_LIMIT_KB), (avif, AVIF_LIMIT_KB)):
            kb = path.stat().st_size / 1024
            mark = "ok" if kb <= limit else f"ПРЕВЫШЕН бюджет {limit} КБ"
            print(f"{path}: {img.width}×{img.height}, {kb:.0f} КБ — {mark}")


if __name__ == "__main__":
    main()
