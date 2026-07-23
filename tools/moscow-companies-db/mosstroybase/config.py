"""Настройки по умолчанию: регион, коды ОКВЭД, адреса источников."""

# Код региона ФНС для Москвы
MOSCOW_REGION_CODE = "77"

# Строительство, проектирование и инженерные изыскания (ОКВЭД-2):
#   41    — строительство зданий
#   42    — строительство инженерных сооружений
#   43    — работы строительные специализированные
#   71.11 — деятельность в области архитектуры
#   71.12 — инженерные изыскания и инженерно-техническое проектирование
# Сопоставление — по строковому префиксу кода ("71.1" накроет и 71.11, и 71.12).
DEFAULT_OKVED_PREFIXES = ("41", "42", "43", "71.11", "71.12")

# Открытые данные ФНС «Единый реестр субъектов МСП»
RSMP_META_URL = "https://www.nalog.gov.ru/opendata/7707329152-rsmp/meta.csv"
RSMP_PASSPORT_URL = "https://www.nalog.gov.ru/opendata/7707329152-rsmp/"

# Бесплатное JSON-зеркало ЕГРЮЛ
EGRUL_JSON_URL = "https://egrul.itsoft.ru/{inn}.json"

# Checko API (нужен бесплатный ключ: https://checko.ru/integration/api)
CHECKO_COMPANY_URL = "https://api.checko.ru/v2/company"
CHECKO_API_KEY_ENV = "CHECKO_API_KEY"

DEFAULT_DB_PATH = "mosstroybase.sqlite3"

# Представляемся честно: сборщик открытых данных
USER_AGENT = "mosstroybase/0.1 (+open-data harvester)"

# Паузы между запросами к внешним сервисам, сек
DEFAULT_DELAY_EGRUL = 0.6
DEFAULT_DELAY_CHECKO = 1.0
DEFAULT_DELAY_WEBSITE = 1.0
