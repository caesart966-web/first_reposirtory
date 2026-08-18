#!/usr/bin/env bash
# Пробный запуск: только 3 компании — проверить ключ API и качество данных,
# не расходуя суточный лимит.
export EXTRA_ARGS="--max-companies 3 --with-diagnostics"
exec "$(dirname "$0")/run.sh" "$@"
