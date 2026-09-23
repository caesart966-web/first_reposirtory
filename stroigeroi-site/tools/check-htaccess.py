#!/usr/bin/env python3
"""
Команда из УСТАНОВКА.md, которая правит .htaccess боевого сайта.

Ошибка в .htaccess роняет сайт целиком, с ошибкой 500, поэтому команда
сама делает копию, после правки открывает главную и при ответе
не 200 возвращает файл как был. Всё это — логика на одной строке shell,
которую человек вставляет в Shell хостинга не читая. Сломать её правкой
легко, а заметить поломку можно только в ту минуту, когда откат
понадобится по-настоящему.

Поэтому команда здесь запускается по-настоящему: на временной папке
вместо корня сайта и на подставном сервере вместо stroigeroi.ru,
который умеет отвечать 200 или 500. Шесть случаев:

  1. .htaccess нет, сайт отвечает — файл создан, в нём ровно наш блок;
  2. повторный запуск — блок не удваивается;
  3. .htaccess был, после правки 500 — файл вернулся как был;
  4. .htaccess не было, после правки 500 — созданный файл убран;
  5. .htaccess был, копию сделать нельзя — остановка, файл не тронут;
  6. .htaccess был, сайт отвечает — старое содержимое цело, блок в конце.

Плюс две сверки: дописанные строки совпадают с htaccess-скорость.txt
(иначе в репозитории лежит одно, а на сервер уходит другое), и в команде
только ASCII — её вставляют в веб-терминал хостинга.

Запуск: python3 tools/check-htaccess.py
"""
import http.server
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading

ROOT = pathlib.Path(__file__).resolve().parent.parent
GUIDE = ROOT / 'opencart-theme/УСТАНОВКА.md'
RULES = ROOT / 'opencart-theme/htaccess-скорость.txt'

SITE_DIR = '/var/www/u2934771/data/www/stroigeroi.ru'
BACKUP = '/var/www/u2934771/data/htaccess-2026-09-23.bak'
SITE_URL = 'https://stroigeroi.ru'
MARKER = 'stroigeroi-webp-avif'
ORIGINAL = 'Options +FollowSymlinks\nRewriteEngine On\n'

errors = []


def check(ok, what):
    print(('  ок    ' if ok else '  ОШИБКА ') + what)
    if not ok:
        errors.append(what)


lines = [l for l in GUIDE.read_text(encoding='utf-8').splitlines()
         if l.startswith('( cd ' + SITE_DIR)]
if len(lines) != 1:
    sys.exit(f'В {GUIDE.name} ожидалась одна строка команды, найдено {len(lines)}')
command = lines[0]

rules = RULES.read_text(encoding='utf-8')
at = rules.find('# ' + MARKER)
if at < 0:
    sys.exit(f'В {RULES.name} нет строки с меткой {MARKER}')
# Команда дописывает пустую строку-отбивку и сам блок от метки до конца.
block = '\n' + rules[at:]

print('Сверки')
check(command.isascii(), 'в команде только ASCII')
check(command.count(SITE_DIR) == 1 and command.count(BACKUP) == 1,
      'папка сайта и путь копии — те, что описаны в УСТАНОВКА.md')
check('max-age=3888000' in block and 3888000 == 45 * 86400,
      'срок в блоке — 45 дней, как у jpg и png от nginx')


class Server(http.server.BaseHTTPRequestHandler):
    """Подставной stroigeroi.ru: отвечает кодом из status, а к webp
    и avif добавляет срок, если в .htaccess есть наш блок, — так, как
    это сделает Apache."""
    status = 200
    htaccess = None

    def log_message(self, *args):
        pass

    def do_GET(self):
        self.send_response(Server.status)
        f = Server.htaccess
        if self.path.endswith(('.webp', '.avif')) and f.exists() and MARKER in f.read_text():
            self.send_header('Cache-Control', 'max-age=3888000')
        self.send_header('Content-Length', '0')
        self.end_headers()


srv = http.server.HTTPServer(('127.0.0.1', 0), Server)
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{srv.server_port}'

tmp = pathlib.Path(tempfile.mkdtemp())
site = tmp / 'site'
backup = tmp / 'htaccess.bak'
htaccess = site / '.htaccess'
Server.htaccess = htaccess


def run(status, backup_path=backup):
    Server.status = status
    cmd = (command.replace(SITE_DIR, str(site))
                  .replace(BACKUP, str(backup_path))
                  .replace(SITE_URL, url))
    r = subprocess.run(['bash', '-c', cmd], capture_output=True, text=True, timeout=60)
    return r.stdout + r.stderr


def fresh(original=None):
    shutil.rmtree(site, ignore_errors=True)
    site.mkdir(parents=True)
    backup.unlink(missing_ok=True)
    if original is not None:
        htaccess.write_text(original)


try:
    print('1. .htaccess нет, сайт отвечает')
    fresh()
    out = run(200)
    check(htaccess.exists() and htaccess.read_text() == block, 'файл создан, в нём ровно блок из htaccess-скорость.txt')
    check(not backup.exists(), 'копии нет — копировать было нечего')
    check(out.lower().count('cache-control: max-age=3888000') == 2, 'показан срок у avif и у webp')
    check('ROLLBACK' not in out, 'отката не было')

    print('2. Повторный запуск')
    run(200)
    check(htaccess.read_text().count(MARKER) == 1, 'блок не удвоился')

    print('3. .htaccess был, после правки 500')
    fresh(ORIGINAL)
    out = run(500)
    check(htaccess.read_text() == ORIGINAL, 'файл вернулся как был')
    check(backup.exists() and backup.read_text() == ORIGINAL, 'копия лежит и совпадает с исходным')
    check('ROLLBACK' in out, 'об откате сказано')

    print('4. .htaccess не было, после правки 500')
    fresh()
    out = run(500)
    check(not htaccess.exists(), 'созданный файл убран')
    check('ROLLBACK' in out, 'об откате сказано')

    print('5. .htaccess был, копию сделать нельзя')
    fresh(ORIGINAL)
    out = run(200, backup_path=tmp / 'no-such-dir' / 'htaccess.bak')
    check(htaccess.read_text() == ORIGINAL, 'файл не тронут')
    check('STOP' in out, 'об остановке сказано')

    print('6. .htaccess был, сайт отвечает')
    fresh(ORIGINAL)
    out = run(200)
    check(htaccess.read_text() == ORIGINAL + block, 'старое содержимое цело, блок дописан в конец')
    check(backup.read_text() == ORIGINAL, 'копия — исходный файл')
    check('ROLLBACK' not in out, 'отката не было')
finally:
    srv.shutdown()
    shutil.rmtree(tmp, ignore_errors=True)

if errors:
    print(f'\nНе прошло: {len(errors)}')
    sys.exit(1)
print('\nКоманда правки .htaccess работает во всех шести случаях.')
