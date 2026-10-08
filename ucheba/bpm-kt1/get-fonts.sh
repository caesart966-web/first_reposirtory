#!/bin/sh
# Шрифт схем ARIS — Arial (обычный и жирный). Файлы Microsoft берутся из пакета
# corefonts (arial32.exe с зеркала SourceForge, как у winetricks) и кладутся
# в build/fonts (в git не попадают). Нужны curl и cabextract.
set -e
dir="$(cd "$(dirname "$0")" && pwd)/build/fonts"
mkdir -p "$dir"
cd "$dir"
if [ -f arial.ttf ] && [ -f arialbd.ttf ]; then echo "Arial уже есть: $dir"; exit 0; fi
curl -fsSL -o arial32.exe https://downloads.sourceforge.net/corefonts/arial32.exe
cabextract -q -F 'Arial*.TTF' arial32.exe
mv Arial.TTF arial.ttf
mv Arialbd.TTF arialbd.ttf
rm -f arial32.exe Arial*.TTF
ls -l "$dir"
