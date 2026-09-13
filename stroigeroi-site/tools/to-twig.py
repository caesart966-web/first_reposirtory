#!/usr/bin/env python3
"""
Перенос страницы макета в шаблон темы OpenCart.

Делает только механическую часть, одинаковую для всех страниц:

  - вырезает содержимое <main> (шапка и подвал живут в общих шаблонах);
  - переписывает пути к картинкам и стилям на путь темы;
  - переводит ссылки между страницами макета в адреса движка;
  - выбрасывает блоки data-notice - это пометки заказчику про недостающие
    данные, на живой сайт они не идут;
  - оборачивает результат в {{ header }} и {{ footer }}.

Чего он НЕ делает и делать не должен: превращать карточки товара в циклы
по products. Это у каждой страницы своё, и подстановка вслепую дала бы
разметку, которая выглядит правильной и не работает.

Про ссылки, которым не нашлось соответствия, скрипт СООБЩАЕТ и оставляет
их как есть - чтобы битая ссылка не уехала в тему молча.

    python3 tools/to-twig.py index.html common/home.twig
"""
import re
import sys
import pathlib

THEME = 'stroigeroi2026'

# Соответствие страниц макета адресам движка. Пустая строка означает
# "адрес зависит от данных страницы" - такие скрипт перечислит отдельно.
ROUTES = {
    'index.html':       'index.php?route=common/home',
    'catalog.html':     'index.php?route=information/sitemap',
    'calculator.html':  'index.php?route=information/calculator',
    'contacts.html':    'index.php?route=information/contact',
    'cart.html':        'index.php?route=checkout/cart',
    'checkout.html':    'index.php?route=checkout/checkout',
    'order-done.html':  'index.php?route=checkout/success',
    'login.html':       'index.php?route=account/login',
    'favourites.html':  'index.php?route=account/wishlist',
    'compare.html':     'index.php?route=product/compare',
    'product.html':     '',   # адрес берётся из карточки товара
    'delivery.html':    '',   # текстовая страница, номер узнаём в админке
    'policy.html':      '',   # то же
    'terms.html':       '',   # то же
    '404.html':         '',   # страницу 404 движок открывает сам
}


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2

    src = pathlib.Path(sys.argv[1])
    dst = pathlib.Path('opencart-theme/catalog/view/theme') / THEME / 'template' / sys.argv[2]

    html = src.read_text(encoding='utf-8')

    body = re.search(r'<main id="main">(.*?)</main>', html, re.S)
    if not body:
        print(f'{src}: не нашёл <main id="main">')
        return 1
    s = body.group(1)

    notices = len(re.findall(r'<div class="data-notice">', s))
    s = re.sub(r'<div class="data-notice">.*?</div>\s*', '', s, flags=re.S)

    s = s.replace('assets/', f'catalog/view/theme/{THEME}/image/')
    s = s.replace(f'catalog/view/theme/{THEME}/image/app.js',
                  f'catalog/view/theme/{THEME}/javascript/app.js')
    s = s.replace(f'catalog/view/theme/{THEME}/image/style.css',
                  f'catalog/view/theme/{THEME}/stylesheet/style.css')

    unresolved = {}
    for page, route in ROUTES.items():
        found = len(re.findall(r'href="' + re.escape(page), s))
        if not found:
            continue
        if route:
            s = s.replace(f'href="{page}"', f'href="{route}"')
            s = re.sub(r'href="' + re.escape(page) + r'#', f'href="{route}#', s)
        else:
            unresolved[page] = found

    left = re.findall(r'href="([^"]*\.html[^"]*)"', s)

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text('{{ header }}\n' + s.strip('\n') + '\n{{ footer }}\n', encoding='utf-8')

    print(f'{src.name} -> {dst.relative_to("opencart-theme")}  ({len(s.splitlines())} строк)')
    if notices:
        print(f'  выброшено пометок заказчику: {notices}')
    if unresolved:
        print('  ССЫЛКИ, КОТОРЫЕ НАДО РАЗОБРАТЬ РУКАМИ:')
        for page, n in sorted(unresolved.items()):
            print(f'    {page}: {n} шт.')
    if left:
        print(f'  осталось адресов с .html: {len(left)} (перечислены выше)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
