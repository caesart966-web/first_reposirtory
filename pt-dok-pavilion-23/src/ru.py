"""Типографика текста на листах и в документах: запятая в дробях, «...», дефис-минус."""
import re

# перед номером нормы, пункта, таблицы точка остаётся: «СП 485.1311500.2020», «табл. 6.1, 6.2», «п. 4.4»
_KEEP = re.compile(r'(раздел[аеу]?|табл\.|п\.|пп\.|ст\.|прил\.|разд\.|рис\.|ч\.|СП|ГОСТ|ГОСТ Р|№)\s*[\d.,\s]*$')
_NUM = re.compile(r'(?<![\w.])(\d+)\.(\d+)(?![\w.])')


def _num(m, s):
    if _KEEP.search(s[max(0, m.start() - 24):m.start()]):
        return m.group(0)
    return f'{m.group(1)},{m.group(2)}'


def ru(s):
    if not isinstance(s, str) or not s:
        return s
    s = _NUM.sub(lambda m: _num(m, s), s)
    return s.replace('…', '...').replace('−', '-')


def plural(n, one, few, many):
    """496 оросителей, 462 оросителя, 1 ороситель."""
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many
