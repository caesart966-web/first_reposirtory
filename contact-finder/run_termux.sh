#!/data/data/com.termux/files/usr/bin/bash
# Запуск пробива контактов на Android (Termux).
# Делает всё сам: ставит зависимости, находит список в Загрузках,
# спрашивает ключ Checko, запускает пробив и кладёт результат обратно в Загрузки.
#
#   bash run_termux.sh
#
set -u
cd "$(dirname "$0")"

DL=/sdcard/Download
say() { printf '\n\033[1;36m%s\033[0m\n' "$*"; }
err() { printf '\n\033[1;31m%s\033[0m\n' "$*"; }

# --- 1. доступ к памяти телефона --------------------------------------------
if [ ! -d "$DL" ]; then
  say "Запрашиваю доступ к файлам телефона — нажмите «Разрешить»."
  termux-setup-storage
  sleep 3
fi
[ -d "$DL" ] || { err "Нет доступа к $DL. Дайте Termux разрешение на файлы и запустите снова."; exit 1; }

# --- 2. python и зависимости -------------------------------------------------
if ! command -v python >/dev/null 2>&1; then
  say "Устанавливаю Python…"
  pkg install -y python || { err "Не удалось установить Python."; exit 1; }
fi
say "Проверяю библиотеки (openpyxl, requests)…"
python -m pip install --quiet --upgrade pip >/dev/null 2>&1
python -m pip install --quiet openpyxl requests 2>/dev/null || \
  say "Библиотеки не встали — не страшно, программа умеет работать без них (результат будет в CSV)."

# --- 3. входной список -------------------------------------------------------
IN="${1:-}"
if [ -z "$IN" ]; then
  IN=$(ls -t "$DL"/*.xlsx "$DL"/*.csv 2>/dev/null | head -1)
fi
if [ -z "$IN" ] || [ ! -f "$IN" ]; then
  err "Не нашёл список в $DL"
  echo "Положите файл (1-й столбец — название, 2-й — ИНН) в папку «Загрузки» и запустите снова."
  echo "Либо укажите путь явно:  bash run_termux.sh /sdcard/Download/мой_список.xlsx"
  exit 1
fi
say "Беру список: $IN"

# --- 4. ключ Checko ----------------------------------------------------------
if [ ! -f .env ] || ! grep -q '^CHECKO_API_KEY=.\+' .env 2>/dev/null; then
  echo
  echo "Ключ Checko API (checko.ru -> раздел API)."
  echo "Можно нажать Enter и пропустить — тогда сработают только бесплатные источники."
  printf 'Вставьте ключ: '
  read -r KEY
  if [ -n "$KEY" ]; then
    grep -v '^CHECKO_API_KEY=' .env 2>/dev/null > .env.tmp || true
    echo "CHECKO_API_KEY=$KEY" >> .env.tmp
    mv .env.tmp .env
    say "Ключ сохранён в .env — второй раз спрашивать не буду."
  fi
fi

# --- 5. не даём Android усыпить процесс --------------------------------------
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock

# --- 6. пробив ---------------------------------------------------------------
OUT="contacts_result.xlsx"
PREV=""
[ -f "$DL/Телефоны_компаний_по_ИНН.xlsx" ] && PREV="--only-missing $DL/Телефоны_компаний_по_ИНН.xlsx"

say "Начинаю пробив. Экран можно гасить, но Termux не закрывайте."
# shellcheck disable=SC2086
python find_contacts.py --in "$IN" --out "$OUT" --delay 2 --verbose $PREV
CODE=$?

command -v termux-wake-unlock >/dev/null 2>&1 && termux-wake-unlock

# --- 7. отдать результат в Загрузки ------------------------------------------
RESULT="$OUT"
[ -f "$RESULT" ] || RESULT="${OUT%.xlsx}.csv"
if [ -f "$RESULT" ]; then
  cp "$RESULT" "$DL/" && say "Готово. Файл лежит в «Загрузки»: $(basename "$RESULT")"
  echo "Откройте его в Google Таблицах, Excel или Samsung «Мои файлы»."
else
  err "Результат не создан. Посмотрите сообщения выше."
fi

exit $CODE
