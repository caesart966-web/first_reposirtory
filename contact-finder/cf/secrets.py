"""Единый заслон от утечки секретов в вывод программы.

Почему так, а не маскировкой URL по месту: ключ попадает в лог не только
через URL, который мы формируем сами. Библиотека requests вкладывает полный
адрес запроса внутрь текста исключения, и печать «{exc}» выносит ключ наружу
в обход любой аккуратности с URL.

Поэтому здесь регистрируются сами значения секретов, а функция scrub()
вырезает их из произвольной строки — независимо от того, каким путём строка
собралась. Логи копируют в переписку, скриншоты и баг-репорты, поэтому
заслон должен стоять на выходе, а не на каждом источнике текста.
"""
from __future__ import annotations

import urllib.parse

_MASK = "***"
_secrets: set[str] = set()


def register(*values: str | None) -> None:
    """Запомнить значения, которые нельзя печатать (API-ключи, токены)."""
    for value in values:
        if value and len(str(value)) >= 6:  # короткие строки — не секреты
            text = str(value)
            _secrets.add(text)
            # Тот же ключ, но в percent-encoding: он встречается в текстах
            # исключений и в собранных библиотеками URL.
            quoted = urllib.parse.quote(text, safe="")
            if quoted != text:
                _secrets.add(quoted)


def scrub(text: object) -> str:
    """Вернуть текст без зарегистрированных секретов."""
    result = str(text)
    for secret in _secrets:
        if secret in result:
            result = result.replace(secret, _MASK)
    return result


def count() -> int:
    """Сколько секретов под защитой — для самопроверки."""
    return len(_secrets)
