#!/usr/bin/env python3
"""
Классы из шаблонов темы, у которых нет ни одного правила в стилях.

Так на живом сайте оказались голыми: кнопка «Заказать звонок» в подвале
(серая системная кнопка на синем), страница «Заказ принят», шесть пустых
состояний («Корзина пуста», «Ничего не нашлось»...), старая цена при
скидке и таблица характеристик товара. В макете у всего этого оформление
было, но шаблоны темы завели для тех же мест свои имена классов, а стили
остались под старыми. Глазами такое не видно, пока не откроешь нужную
страницу в нужном состоянии, - заказчик нашёл кнопку с телефона.

Проверка собирает классы из всех шаблонов темы и из app.js (className,
classList.add/toggle) и ищет каждый в style.css и opencart.css. Классы,
которые нарочно ничем не оформлены (крючки для разметки, скриптов или
поисковиков), перечислены ниже с причиной; всё остальное - ошибка.

Запуск: python3 tools/check-classes.py
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
THEME = ROOT / 'opencart-theme/catalog/view/theme/stroigeroi2026'

# Класс -> почему у него нет своих стилей. Добавлять сюда только то,
# что действительно не должно выглядеть никак.
HOOKS = {
    'product-hero': 'обёртка карточки товара для разметки schema.org (itemscope)',
    'gallery': 'обёртка галереи; оформлены её части, gallery__main и gallery__thumbs',
    'selection': 'обёртка подборки товаров в модулях; оформлена сетка внутри',
    'footer-brand': 'обёртка названия в подвале; оформлены её части',
    'data': 'метка таблицы сравнения; оформление - у compare-table',
    'done': 'метка страницы «Заказ принят»; оформление - у error-page',
    'empty': 'метка пустого состояния для скриптов; оформление - у empty-state',
    'is-done': 'пройденный шаг оформления заказа; в макете пройденные шаги не выделены',
    'shop-card__now--': 'начало имени, остальное app.js дописывает сам: --open, --closed',
}


def css_classes():
    text = ''.join((THEME / f'stylesheet/{name}').read_text(encoding='utf-8')
                   for name in ('style.css', 'opencart.css'))
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    return set(re.findall(r'\.(-?[_a-zA-Z][\w-]*)', text))


def used_classes():
    used = {}
    for path in sorted((THEME / 'template').rglob('*.twig')):
        src = re.sub(r'\{#.*?#\}', '', path.read_text(encoding='utf-8'), flags=re.S)
        for m in re.finditer(r'class="([^"]*)"', src):
            # Выражения Twig внутри class="..." - не классы, а их источник.
            for cls in re.sub(r'\{\{.*?\}\}|\{%.*?%\}', ' ', m.group(1)).split():
                used.setdefault(cls, set()).add(str(path.relative_to(THEME / 'template')))
    js = (THEME / 'javascript/app.js').read_text(encoding='utf-8')
    for m in re.finditer(r"(?:className\s*=\s*|classList\.(?:add|toggle)\()\s*'([^']+)'", js):
        for cls in m.group(1).split():
            used.setdefault(cls, set()).add('app.js')
    return used


def main():
    styled = css_classes()
    used = used_classes()
    bad = 0
    for cls in sorted(used):
        if cls in styled or cls in HOOKS:
            continue
        print(f'Класс «{cls}» без стилей: {", ".join(sorted(used[cls]))}')
        bad += 1
    for cls in sorted(HOOKS):
        if cls not in used:
            print(f'Класс «{cls}» числится в исключениях, но в шаблонах его больше нет — убрать из HOOKS')
            bad += 1
    print(f'Классов в шаблонах и app.js: {len(used)}'
          + (f', без стилей: {bad}' if bad else ' — у каждого есть стили или причина их не иметь'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
