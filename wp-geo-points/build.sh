#!/usr/bin/env bash
# Собирает архив плагина для загрузки в WordPress.
set -euo pipefail
cd "$(dirname "$0")"

php tests/run.php

rm -f geo-points.zip
zip -rq geo-points.zip geo-points -x '*.DS_Store' '*/.*'
echo "Готово: $(pwd)/geo-points.zip"
