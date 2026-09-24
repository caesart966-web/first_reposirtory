#!/usr/bin/env python3
"""
Проставляет в шаблонах темы номера текстовых страниц OpenCart.

Зачем. Ссылки «Доставка», «Политика конфиденциальности» ведут на страницы,
которые заказчик создаёт в админке сам, и их номера заранее не известны.
В шаблонах они стоят нулями, и пока там ноль, пункт меню или ссылка
не выводятся совсем: ссылка в никуда хуже её отсутствия.

Номера встречаются в нескольких файлах. Проставленные руками, они однажды
разойдутся - поэтому их ставит скрипт, разом во всех.

Где взять номер: админка -> Каталог -> Информация -> открыть страницу
на редактирование; в адресной строке будет information_id=NN.

    python3 tools/set-page-ids.py --delivery 6 --policy 3
    python3 tools/set-page-ids.py --show          # что стоит сейчас
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path('opencart-theme/catalog/view/theme/stroigeroi2026/template')

KNOWN = {
    'delivery': 'страница «Доставка и оплата»',
    'policy': 'страница «Политика обработки персональных данных»',
    'requisites': 'страница «Реквизиты»',
}


def occurrences():
    """Где какие номера стоят: {имя: [(файл, значение), ...]}"""
    found = {}
    for path in sorted(ROOT.rglob('*.twig')):
        text = path.read_text(encoding='utf-8')
        for name, value in re.findall(r'\{%\s*set\s+id_(\w+)\s*=\s*(\d+)\s*%\}', text):
            found.setdefault(name, []).append((path, int(value)))
    return found


def show():
    found = occurrences()
    if not found:
        print('В шаблонах нет ни одной пометки id_*.')
        return 0
    for name in sorted(found):
        title = KNOWN.get(name, 'назначение неизвестно')
        print(f'{name}  ({title})')
        for path, value in found[name]:
            state = 'не задан' if value == 0 else str(value)
            print(f'    {path.relative_to(ROOT)}: {state}')
    return 0


def main():
    parser = argparse.ArgumentParser(add_help=True, description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--show', action='store_true', help='показать текущие значения')
    for name, title in KNOWN.items():
        parser.add_argument(f'--{name}', type=int, metavar='NN', help=title)
    args = parser.parse_args()

    if args.show or not any(getattr(args, name) is not None for name in KNOWN):
        return show()

    found = occurrences()
    changed = 0

    for name in KNOWN:
        value = getattr(args, name)
        if value is None:
            continue
        if value < 1:
            print(f'Номер страницы должен быть больше нуля: --{name} {value}')
            return 1
        if name not in found:
            print(f'ВНИМАНИЕ: пометки id_{name} нет ни в одном шаблоне — нечего проставлять')
            continue
        for path, _ in found[name]:
            text = path.read_text(encoding='utf-8')
            text, n = re.subn(r'(\{%\s*set\s+id_' + name + r'\s*=\s*)\d+(\s*%\})',
                              r'\g<1>' + str(value) + r'\g<2>', text)
            path.write_text(text, encoding='utf-8')
            print(f'  id_{name} = {value}  ->  {path.relative_to(ROOT)} ({n} шт.)')
            changed += n

    print(f'Проставлено значений: {changed}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
