<?php
/* =========================================================================
   Приём заявок с сайта на обычном хостинге с PHP (Timeweb и похожие).
   Принимает заявку из формы и отправляет её письмом на почту.

   Куда слать: адрес подставляет сборка из data/site.json → contacts.email
   (в строке с $to ниже). Если заявки нужно получать на другой
   ящик, не показывая его на сайте, положите на хостинге ВЫШЕ публичной
   папки (рядом с public_html, а не внутри) файл zayavki-config.php
   с полем 'to' — образец в server/zayavki-config.example.php.

   Заявка нигде на сервере не сохраняется: принята, отправлена, забыта.
   Письмо идёт с хостинга в России на почту в России — так и написано
   в политике обработки персональных данных.

   Синтаксис нарочно простой (PHP 7.4+): на виртуальном хостинге версия
   бывает любой, а файл с незнакомой конструкцией не выполнится вовсе.
   Закрывающего тега PHP в конце файла нет нарочно, и в комментариях его
   писать нельзя: однострочный комментарий на нём обрывается, и всё,
   что после, сервер отдаёт посетителю как текст.
   ========================================================================= */

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex');

function reply($status, $data)
{
    http_response_code($status);
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

function clean($value, $max)
{
    $s = is_scalar($value) ? (string) $value : '';
    $s = str_replace(array('<', '>'), '', $s);
    $s = preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', $s);
    $s = trim((string) $s);
    return function_exists('mb_substr') ? mb_substr($s, 0, $max, 'UTF-8') : substr($s, 0, $max);
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    header('Allow: POST');
    reply(405, array('ok' => false, 'error' => 'method'));
}

// ---------- Настройки ----------------------------------------------------
// Необязательный файл выше публичной папки: рядом с public_html (основной
// вариант) или уровнем выше (если сайт лежит в подпапке).
$config = array();
foreach (array(dirname(__DIR__, 2), dirname(__DIR__, 3)) as $base) {
    if (is_file($base . '/zayavki-config.php')) {
        $loaded = include $base . '/zayavki-config.php';
        if (is_array($loaded)) {
            $config = $loaded;
        }
        break;
    }
}
$to = trim((string) ($config['to'] ?? '{{почта_заявок}}'));
if (!filter_var($to, FILTER_VALIDATE_EMAIL)) {
    error_log('zayavka.php: не задан адрес для заявок');
    reply(500, array('ok' => false, 'error' => 'config'));
}

// ---------- Только со своего сайта -----------------------------------------
// Браузер сам ставит заголовок Origin, подделать его из чужой страницы нельзя.
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
$host = $_SERVER['HTTP_HOST'] ?? '';
if ($origin !== '') {
    $originHost = parse_url($origin, PHP_URL_HOST);
    $bare = preg_replace('/:\d+$/', '', $host);
    if (!$originHost || (strcasecmp($originHost, $bare) !== 0
        && strcasecmp($originHost, 'www.' . $bare) !== 0
        && strcasecmp('www.' . $originHost, $bare) !== 0)) {
        reply(403, array('ok' => false, 'error' => 'origin'));
    }
}

// ---------- Не чаще пяти заявок за десять минут с одного адреса ------------
// Защита от забивания почты мусором. На диске лежит только хеш адреса
// и время последних отправок, без имени и телефона; старые записи удаляются.
$dir = rtrim(sys_get_temp_dir(), '/') . '/zayavki-limit';
if (!is_dir($dir)) {
    @mkdir($dir, 0700, true);
}
if (is_dir($dir) && is_writable($dir)) {
    $now = time();
    $window = 600;
    $salt = __FILE__ . $to;
    $file = $dir . '/' . hash('sha256', ($_SERVER['REMOTE_ADDR'] ?? '') . $salt);
    $stamps = array();
    if (is_file($file)) {
        foreach (explode("\n", (string) @file_get_contents($file)) as $t) {
            if ($t !== '' && (int) $t > $now - $window) {
                $stamps[] = (int) $t;
            }
        }
    }
    if (count($stamps) >= 5) {
        reply(429, array('ok' => false, 'error' => 'rate'));
    }
    $stamps[] = $now;
    @file_put_contents($file, implode("\n", $stamps), LOCK_EX);
    if (mt_rand(1, 50) === 1) {
        foreach ((array) glob($dir . '/*') as $old) {
            if (is_file($old) && filemtime($old) < $now - $window) {
                @unlink($old);
            }
        }
    }
}

// ---------- Разбор заявки -------------------------------------------------
$raw = file_get_contents('php://input', false, null, 0, 20000);
$data = json_decode((string) $raw, true);
if (!is_array($data)) {
    reply(400, array('ok' => false, 'error' => 'json'));
}

// Имя уходит в тему письма, поэтому переносы строк в нём заменяются пробелом.
$name = preg_replace('/\s+/u', ' ', clean($data['name'] ?? '', 100));
$phone = preg_replace('/\s+/u', ' ', clean($data['phone'] ?? '', 40));
if ($name === '' || strlen(preg_replace('/\D/', '', $phone)) < 10) {
    reply(422, array('ok' => false, 'error' => 'invalid'));
}

$lines = array('Заявка с сайта', '', 'Имя: ' . $name, 'Телефон: ' . $phone);
$service = clean($data['service'] ?? '', 200);
$comment = clean($data['comment'] ?? '', 2000);
if ($service !== '') {
    $lines[] = 'Услуга / объект: ' . $service;
}
if ($comment !== '') {
    $lines[] = 'Комментарий: ' . $comment;
}
$lines[] = '';
$lines[] = 'Страница: ' . clean($data['page'] ?? '', 300);

// ---------- Отправка письма ----------------------------------------------
// Отправитель — ящик на домене сайта: хостинг не пропускает письма
// от чужого имени, а почта получателя отправляет такие в спам.
$domain = strtolower(preg_replace('/^www\./i', '', preg_replace('/:\d+$/', '', $host)));
if (!preg_match('/^[a-z0-9.-]+$/', $domain)) {
    $domain = 'localhost';
}
$from = trim((string) ($config['from'] ?? ('noreply@' . $domain)));
$subject = 'Заявка с сайта: ' . $name;
$body = implode("\n", $lines);

// Проверка без отправки: в zayavki-config.php 'dry_run' => true, и письмо
// не уходит, а возвращается в ответе. Нужна только для проверки.
if (!empty($config['dry_run'])) {
    reply(200, array('ok' => true, 'dry_run' => true, 'to' => $to, 'from' => $from,
        'subject' => $subject, 'text' => $body));
}

$headers = implode("\r\n", array(
    'From: =?UTF-8?B?' . base64_encode('Сайт X-PTO') . '?= <' . $from . '>',
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
    'Content-Transfer-Encoding: base64',
));
$sent = mail(
    $to,
    '=?UTF-8?B?' . base64_encode($subject) . '?=',
    chunk_split(base64_encode($body)),
    $headers,
    '-f' . $from
);

if (!$sent) {
    error_log('zayavka.php: письмо не ушло');
    reply(502, array('ok' => false, 'error' => 'mail'));
}

reply(200, array('ok' => true));
