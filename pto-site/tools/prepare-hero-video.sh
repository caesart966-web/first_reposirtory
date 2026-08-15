#!/usr/bin/env bash
# =========================================================================
# Подготовка видео для первого экрана — одной командой.
#
# Что делает: обрезает ролик до нужной длины, убирает звук, сжимает
# до веса, пригодного для сайта, делает второй файл в формате webm
# и вытаскивает первый кадр в постер. Всё складывает в assets/media/.
#
# Использование:
#     bash tools/prepare-hero-video.sh ~/Downloads/pexels-video.mp4
#     bash tools/prepare-hero-video.sh ~/Downloads/video.mp4 12   # 12 секунд
#
# Нужен ffmpeg:
#     macOS:    brew install ffmpeg
#     Windows:  winget install ffmpeg   (или скачать с ffmpeg.org)
#     Ubuntu:   sudo apt install ffmpeg
#
# После этого: python3 build.py — и видео на сайте.
# =========================================================================

set -euo pipefail

SRC="${1:-}"
SECONDS_LIMIT="${2:-15}"

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$DIR/assets/media"

if [ -z "$SRC" ]; then
  echo "Укажите файл: bash tools/prepare-hero-video.sh путь/к/видео.mp4"
  exit 1
fi
if [ ! -f "$SRC" ]; then
  echo "Файл не найден: $SRC"
  exit 1
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "Не установлен ffmpeg. Как поставить — в шапке этого файла."
  exit 1
fi

mkdir -p "$OUT"
echo "Исходник: $SRC"
echo "Длительность: ${SECONDS_LIMIT} сек, звук убирается, ширина 1920."
echo

# -an          убрать звук: он всё равно не проигрывается
# -crf 30      степень сжатия; больше число — меньше файл и хуже качество
# scale=1920   больше для фона не нужно, а вес растёт заметно
echo "[1/3] mp4 (основной файл)…"
ffmpeg -y -loglevel error -i "$SRC" -t "$SECONDS_LIMIT" -an \
  -vf "scale=1920:-2" -c:v libx264 -crf 30 -preset slow -pix_fmt yuv420p \
  -movflags +faststart "$OUT/hero.mp4"

echo "[2/3] webm (весит меньше, где поддерживается)…"
ffmpeg -y -loglevel error -i "$SRC" -t "$SECONDS_LIMIT" -an \
  -vf "scale=1920:-2" -c:v libvpx-vp9 -crf 38 -b:v 0 "$OUT/hero.webm" || {
    echo "    webm собрать не удалось — не страшно, mp4 достаточно."
    rm -f "$OUT/hero.webm"
  }

echo "[3/3] постер (первый кадр)…"
ffmpeg -y -loglevel error -i "$OUT/hero.mp4" -vframes 1 -q:v 3 "$OUT/hero-poster.jpg"

echo
echo "Готово. Что получилось:"
ls -lh "$OUT"/hero.* 2>/dev/null | awk '{printf "  %-22s %s\n", $9, $5}'
echo
echo "Дальше:  python3 build.py"
echo

# Предупреждение о весе: 5 МБ — предел, за которым первый экран тормозит
SIZE_MB=$(du -m "$OUT/hero.mp4" | cut -f1)
if [ "$SIZE_MB" -gt 5 ]; then
  echo "ВНИМАНИЕ: hero.mp4 весит ${SIZE_MB} МБ, это много."
  echo "Пережмите сильнее — увеличьте crf, например до 33:"
  echo "  ffmpeg -y -i \"$SRC\" -t $SECONDS_LIMIT -an -vf scale=1920:-2 \\"
  echo "    -c:v libx264 -crf 33 -preset slow -pix_fmt yuv420p \\"
  echo "    -movflags +faststart \"$OUT/hero.mp4\""
fi
