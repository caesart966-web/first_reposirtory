"""
nostroy_checko — автономный парсер реестра НОСТРОЙ + обогащение контактами с checko.ru.

Пакет разбит на независимые модули:

* :mod:`nostroy_checko.config`          — настройки запуска и константы;
* :mod:`nostroy_checko.logging_setup`   — настройка логирования;
* :mod:`nostroy_checko.textutils`       — нормализация текста, ИНН, дат, телефонов, email;
* :mod:`nostroy_checko.models`          — модели данных (записи реестра, контакты checko);
* :mod:`nostroy_checko.archives`        — распаковка .rar/.zip (в т.ч. вложенных архивов);
* :mod:`nostroy_checko.excel_reader`    — чтение всех листов всех Excel-файлов;
* :mod:`nostroy_checko.column_mapper`   — определение строки заголовков и ролей колонок;
* :mod:`nostroy_checko.registry_parser` — сборка записей членов СРО из «сырых» строк;
* :mod:`nostroy_checko.quota`           — суточная квота запросов к checko.ru;
* :mod:`nostroy_checko.state`           — сохранение прогресса между запусками (по дням);
* :mod:`nostroy_checko.checko_client`   — HTTP-клиент и разбор карточки checko.ru;
* :mod:`nostroy_checko.pipeline`        — оркестрация всего процесса;
* :mod:`nostroy_checko.report`          — итоговый Excel-отчёт с тремя вкладками.
"""

__version__ = "1.0.0"
__all__ = ["__version__"]
