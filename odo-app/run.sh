#!/usr/bin/env bash
# Запуск на Linux/macOS. Первый раз: pip install -r requirements.txt
cd "$(dirname "$0")"
exec python3 -m server
