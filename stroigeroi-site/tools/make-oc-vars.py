#!/usr/bin/env python3
"""
Пересобирает tools/oc-vars.json - список переменных, которые контроллеры
OpenCart отдают шаблонам.

Зачем это нужно. Twig не сообщает о переменной, которой нет: он молча
подставляет пустоту. Ошибка от этого не видна ни в браузере, ни в журналах -
просто пропадает кусок страницы. Именно так у нас в шапке оказались пустыми
ссылки на сравнение и на товары со скидкой: я взял имена переменных
по памяти, а таких переменных у движка нет.

Скрипт качает исходники движка с GitHub и вытаскивает из них все $data['...'].
Запускается редко - только при смене версии OpenCart.

    python3 tools/make-oc-vars.py

Требует доступа в интернет. Результат коммитится, поэтому сама проверка
(check-vars.py) работает без сети - в том числе на сборочной машине.
"""
import json
import pathlib
import re
import sys
import urllib.request

VERSION = '3.0.3.7'
BASE = f'https://raw.githubusercontent.com/opencart/opencart/{VERSION}/upload/catalog/controller/'

ROUTES = [
    'common/header', 'common/footer', 'common/menu', 'common/cart',
    'common/search', 'common/home',
    'checkout/success', 'checkout/cart', 'checkout/checkout',
    'product/category', 'product/product', 'product/search',
    'product/special', 'product/compare',
    'information/information', 'information/contact', 'information/sitemap',
    'account/login', 'account/wishlist', 'account/account', 'account/order',
    'error/not_found',
    'extension/module/banner', 'extension/module/carousel',
    'extension/module/slideshow', 'extension/module/featured',
    'extension/module/bestseller', 'extension/module/latest',
    'extension/module/special',
]


def main():
    out = {
        '__': f'Переменные, которые контроллеры OpenCart {VERSION} отдают шаблонам. '
              'Снято из исходников движка скриптом, руками не правится. '
              'Пересобрать: tools/make-oc-vars.py',
    }

    for route in ROUTES:
        try:
            with urllib.request.urlopen(BASE + route + '.php', timeout=40) as r:
                php = r.read().decode('utf-8', 'replace')
        except Exception as e:
            print(f'{route}: не скачался — {e}')
            return 1
        out[route] = sorted(set(re.findall(r"\$data\['([a-z_0-9]+)'\]", php)))
        print(f'  {route}: {len(out[route])} переменных')

    path = pathlib.Path('tools/oc-vars.json')
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + '\n',
                    encoding='utf-8')
    print(f'{path}: {len(ROUTES)} маршрутов')
    return 0


if __name__ == '__main__':
    sys.exit(main())
