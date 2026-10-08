#!/bin/sh
# Шрифт ARIS Express — Tahoma. Файлы Microsoft берутся из того же пакета,
# что и у winetricks (IELPKTH.CAB с зеркала corefonts), и кладутся в build/fonts
# (в git не попадают). Нужны curl и cabextract.
set -e
dir="$(cd "$(dirname "$0")" && pwd)/build/fonts"
mkdir -p "$dir"
cd "$dir"
if [ -f tahoma.ttf ] && [ -f tahomabd.ttf ]; then echo "Tahoma уже есть: $dir"; exit 0; fi
curl -fsSL -o IELPKTH.CAB https://downloads.sourceforge.net/corefonts/OldFiles/IELPKTH.CAB
cabextract -q -F 'tahoma*.ttf' IELPKTH.CAB
rm -f IELPKTH.CAB
ls -l "$dir"
