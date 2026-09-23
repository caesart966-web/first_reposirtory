#!/usr/bin/env python3
"""
robots.txt боевого сайта — прогон по настоящим адресам.

Ошибка в robots.txt не видна глазами, а цена у неё — весь магазин
в выдаче. Готовые robots.txt для OpenCart почти все советуют строку
«Disallow: /index.php?route=»; на stroigeroi.ru человекопонятные адреса
выключены, каждая страница живёт по index.php?route=..., и эта одна
строка убрала бы из поиска всё. Глазами такое пропускают, потому что
правило выглядит разумным.

Проверка разбирает правила так же, как их читают Яндекс и Google:
у адреса побеждает самое длинное совпавшее правило, при равной длине —
Allow; «*» — любая последовательность, «$» — конец адреса. И прогоняет
через них адреса, снятые с живого сайта 23.09.2026: товар, раздел,
вторая страница раздела, та же страница с сортировкой, корзина,
кабинет, карта сайта, стили с отпечатком.

Запуск: python3 tools/check-robots.py [путь к robots.txt]
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'opencart-theme/robots.txt'

R = '/index.php?route='
# (адрес, должен ли быть открыт, почему)
URLS = [
    ('/', True, 'главная'),
    (R + 'product/product&product_id=154', True, 'карточка товара'),
    (R + 'product/category&path=92', True, 'раздел каталога'),
    (R + 'product/category&path=92&page=2', True, 'вторая страница раздела — на ней другие товары'),
    (R + 'product/special', True, 'товары со скидкой'),
    (R + 'product/manufacturer', True, 'список производителей'),
    (R + 'information/information&information_id=4', True, 'текстовая страница'),
    (R + 'information/contact', True, 'контакты и адреса магазинов'),
    (R + 'information/sitemap', True, 'карта сайта для людей'),
    (R + 'extension/feed/google_sitemap', True, 'карта сайта для поисковиков — сама себя закрыть не должна'),
    # Короткие адреса (ЧПУ). Сняты с живого сайта 23.09.2026: движок открывал
    # их ещё до включения настройки, а после неё ведёт на них сам.
    ('/elektrika-i-svet', True, 'отдел по короткому адресу'),
    ('/elektrika-i-svet/osveschenie', True, 'подраздел внутри отдела'),
    ('/pylesosy-stroitelnye', True, 'раздел из 1С'),
    ('/otvertka-denzel-3-6v-lii-ion-1-3ach-s-aksessuarami-csl-3-6-01', True, 'карточка товара'),
    ('/pylesosy-stroitelnye?page=2', True, 'вторая страница раздела — на ней другие товары'),
    ('/catalog/view/theme/stroigeroi2026/stylesheet/style.css?v=4d04a862', True, 'стили с отпечатком'),
    ('/catalog/view/javascript/jquery/jquery-2.1.1.min.js', True, 'скрипты движка'),
    ('/image/cache/import_files/40/40e63c0a-1000x1000.jpg', True, 'фотография товара'),

    (R + 'product/category&path=92&sort=p.price&order=ASC', False, 'та же страница раздела, другая сортировка'),
    (R + 'product/category&path=92&sort=p.price&order=ASC&page=2', False, 'сортировка + страница: всё равно копия'),
    (R + 'product/category&path=92&limit=100', False, 'та же страница, другое число товаров'),
    ('/pylesosy-stroitelnye?sort=p.price&order=ASC', False, 'короткий адрес, другая сортировка'),
    ('/pylesosy-stroitelnye?sort=p.price&order=ASC&page=2', False, 'короткий адрес, сортировка + страница'),
    ('/pylesosy-stroitelnye?limit=100', False, 'короткий адрес, другое число товаров'),
    (R + 'product/product&manufacturer_id=5&product_id=154', False, 'товар через производителя — копия карточки'),
    (R + 'common/home', False, 'вторая копия главной'),
    (R + 'checkout/cart', False, 'корзина'),
    (R + 'checkout/simplecheckout', False, 'оформление заказа'),
    (R + 'account/login', False, 'вход в кабинет'),
    (R + 'product/search&search=drel', False, 'результаты поиска'),
    (R + 'product/compare', False, 'сравнение'),
    ('/admin/index.php', False, 'админка'),
    ('/system/storage/logs/error.log', False, 'служебные файлы'),
]


def rules_for_all(text):
    """Правила группы User-agent: *."""
    rules, sitemaps, clean = [], [], []
    group = None
    for raw in text.splitlines():
        line = raw.split('#', 1)[0].strip()
        if ':' not in line:
            continue
        key, val = (p.strip() for p in line.split(':', 1))
        key = key.lower()
        if key == 'user-agent':
            group = val
        elif key == 'sitemap':
            sitemaps.append(val)
        elif key == 'clean-param':
            clean.append(val)
        elif key in ('allow', 'disallow') and group == '*' and val:
            rules.append((key, val))
    return rules, sitemaps, clean


def to_regex(pattern):
    end = pattern.endswith('$')
    body = pattern[:-1] if end else pattern
    rx = ''.join('.*' if ch == '*' else re.escape(ch) for ch in body)
    return re.compile('^' + rx + ('$' if end else ''))


def verdict(rules, path):
    """(открыт ли, правило-победитель)."""
    best = None
    for kind, pat in rules:
        if to_regex(pat).match(path):
            length = len(pat)
            if (best is None or length > best[0]
                    or (length == best[0] and kind == 'allow')):
                best = (length, kind, pat)
    if best is None:
        return True, None
    return best[1] == 'allow', f'{best[1].capitalize()}: {best[2]}'


def main():
    text = SRC.read_text(encoding='utf-8')
    rules, sitemaps, clean = rules_for_all(text)
    bad = 0

    for path, want, why in URLS:
        ok, rule = verdict(rules, path)
        if ok != want:
            state = 'ЗАКРЫТ' if not ok else 'ОТКРЫТ'
            print(f'{state}, а должен быть {"открыт" if want else "закрыт"}: {path}')
            print(f'    это {why}; решило правило «{rule or "никакое"}»')
            bad += 1

    if not sitemaps:
        print('Нет строки Sitemap: поисковик не узнает, где карта сайта')
        bad += 1
    for sm in sitemaps:
        path = re.sub(r'^https?://[^/]+', '', sm)
        if not verdict(rules, path)[0]:
            print(f'Карта сайта закрыта этим же файлом: {sm}')
            bad += 1

    for c in clean:
        params = c.split()[0].split('&')
        if 'page' in params:
            print(f'Clean-param с page: «{c}» — вторая страница каталога показывает '
                  f'другие товары, и Яндекс выкинул бы из индекса всё, кроме первых страниц')
            bad += 1

    wide = [p for k, p in rules if k == 'disallow' and p.rstrip('*') in ('/', '/index.php', '/index.php?', '/index.php?route=')]
    for p in wide:
        print(f'Правило «Disallow: {p}» закрывает весь сайт: человекопонятные адреса '
              f'на stroigeroi.ru выключены, каждая страница живёт по index.php?route=...')
        bad += 1

    nonascii = sorted({ch for ch in text if ord(ch) > 127})
    if nonascii:
        print(f'В файле есть не-ASCII символы ({"".join(nonascii[:10])}): сервер отдаёт .txt '
              f'без кодировки, и браузер покажет их кракозябрами')
        bad += 1

    print(f'robots.txt: адресов проверено {len(URLS)}, правил {len(rules)}'
          + (f', ОШИБОК {bad}' if bad else ' — всё сходится'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
