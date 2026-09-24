<?php
/* =========================================================================
   Приём заявок с сайта на обычном хостинге с PHP (Timeweb и похожие).
   Принимает заявку из формы и пересылает её в Telegram.

   Токен бота и chat_id в этом файле НЕ хранятся. Они лежат в отдельном
   файле zayavki-config.php, который кладётся на хостинге ВЫШЕ публичной
   папки сайта (рядом с public_html, а не внутри неё): по адресу в браузере
   его не открыть, а в git и в сборку сайта он не попадает никогда.
   Образец — server/zayavki-config.example.php, инструкция — README, раздел 9.

   Заявка нигде на сервере не сохраняется: принята, отправлена, забыта.
   Так и написано в политике обработки персональных данных.

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

// ---------- Настройки: файл выше публичной папки ---------------------------
// Ищем в двух местах: рядом с public_html (основной вариант) и уровнем выше
// (если сайт лежит в подпапке). Первый найденный побеждает.
$config = null;
$candidates = array(
    dirname(__DIR__, 2) . '/zayavki-config.php',
    dirname(__DIR__, 3) . '/zayavki-config.php',
);
foreach ($candidates as $path) {
    if (is_file($path)) {
        $config = include $path;
        break;
    }
}
if (!is_array($config) || empty($config['bot_token']) || empty($config['chat_id'])) {
    error_log('zayavka.php: не найден или не заполнен zayavki-config.php');
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
// Защита от забивания Telegram мусором. На диске лежит только хеш адреса
// и время последних отправок, без имени и телефона; старые записи удаляются.
$dir = rtrim(sys_get_temp_dir(), '/') . '/zayavki-limit';
if (!is_dir($dir)) {
    @mkdir($dir, 0700, true);
}
if (is_dir($dir) && is_writable($dir)) {
    $now = time();
    $window = 600;
    $salt = (string) $config['bot_token'];
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

$name = clean($data['name'] ?? '', 100);
$phone = clean($data['phone'] ?? '', 40);
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

// ---------- Отправка в Telegram --------------------------------------------
$payload = json_encode(array(
    'chat_id' => (string) $config['chat_id'],
    'text' => implode("\n", $lines),
    'disable_web_page_preview' => true,
), JSON_UNESCAPED_UNICODE);
$url = 'https://api.telegram.org/bot' . $config['bot_token'] . '/sendMessage';

// Проверка без отправки: в zayavki-config.php 'dry_run' => true, и заявка
// не уходит в Telegram, а возвращается в ответе. Нужна только для проверки.
if (!empty($config['dry_run'])) {
    reply(200, array('ok' => true, 'dry_run' => true, 'text' => implode("\n", $lines)));
}

$code = 0;
if (function_exists('curl_init')) {
    $ch = curl_init($url);
    curl_setopt_array($ch, array(
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => $payload,
        CURLOPT_HTTPHEADER => array('Content-Type: application/json'),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 15,
    ));
    curl_exec($ch);
    $code = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
} else {
    $ctx = stream_context_create(array('http' => array(
        'method' => 'POST',
        'header' => "Content-Type: application/json\r\n",
        'content' => $payload,
        'timeout' => 15,
        'ignore_errors' => true,
    )));
    @file_get_contents($url, false, $ctx);
    if (isset($http_response_header[0]) && preg_match('/\s(\d{3})\s/', $http_response_header[0], $m)) {
        $code = (int) $m[1];
    }
}

if ($code !== 200) {
    error_log('zayavka.php: Telegram ответил ' . $code);
    reply(502, array('ok' => false, 'error' => 'telegram'));
}

reply(200, array('ok' => true));
