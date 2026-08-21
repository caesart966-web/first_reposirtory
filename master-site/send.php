<?php
/* =============================================================================
   Приём заявок с сайта ООО «МАСТЕР».

   ВСЕ НАСТРОЙКИ - В БЛОКЕ НИЖЕ. Ниже блока настроек ничего менять не нужно.
   Пошаговая инструкция - в README.md, раздел «Куда приходят заявки».
   ========================================================================== */

// --- НАСТРОЙКИ ---------------------------------------------------------------

$CONFIG = [

    // Куда отправлять заявку:
    //   'mail'     - письмом на почту
    //   'telegram' - сообщением в Telegram
    //   'both'     - и туда, и туда
    'mode' => 'mail',

    // --- почта ---------------------------------------------------------------

    // Кому приходят заявки. Можно несколько через запятую.
    'to' => 'ooomaster2022@mail.ru',

    // От чьего имени уходит письмо. Адрес должен быть НА ВАШЕМ ДОМЕНЕ, иначе
    // письма будут падать в спам. Почтовый ящик заводить не обязательно.
    'from' => 'site@example.com',
    'from_name' => 'Сайт ООО МАСТЕР',

    'subject' => 'Заявка с сайта',

    // Как отправлять письмо:
    //   'mail' - встроенной функцией PHP (подходит большинству хостингов)
    //   'smtp' - через SMTP-сервер (если хостинг не отправляет письма сам)
    'mail_transport' => 'mail',

    'smtp' => [
        'host' => 'smtp.example.com',
        'port' => 465,
        'secure' => 'ssl',        // 'ssl' для порта 465, 'tls' для порта 587
        'user' => 'site@example.com',
        'pass' => '',
    ],

    // --- telegram ------------------------------------------------------------

    // Токен бота от @BotFather и id чата, куда слать заявки.
    // Здесь токен лежит на сервере и посетителям сайта не виден.
    'telegram' => [
        'token' => '',
        'chat_id' => '',
    ],

    // --- защита от спама -----------------------------------------------------

    // Минимальное время заполнения формы в секундах. Роботы отправляют мгновенно.
    'min_seconds' => 3,

    // Сколько заявок принимать с одного адреса за час. 0 - без ограничения.
    'per_hour' => 10,
];

// --- ДАЛЬШЕ МЕНЯТЬ НИЧЕГО НЕ НУЖНО -------------------------------------------

mb_internal_encoding('UTF-8');

$isAjax = isset($_POST['ajax'])
    || (isset($_SERVER['HTTP_ACCEPT']) && strpos($_SERVER['HTTP_ACCEPT'], 'application/json') !== false);

/**
 * Ответ посетителю: JSON для формы на сайте, обычная страница - если у
 * посетителя выключен JavaScript.
 */
function respond($ok, $message, $isAjax)
{
    if ($isAjax) {
        header('Content-Type: application/json; charset=utf-8');
        http_response_code($ok ? 200 : 400);
        echo json_encode(
            $ok ? ['ok' => true] : ['ok' => false, 'error' => $message],
            JSON_UNESCAPED_UNICODE
        );
        exit;
    }

    header('Content-Type: text/html; charset=utf-8');
    http_response_code($ok ? 200 : 400);
    $title = $ok ? 'Заявка отправлена' : 'Заявка не отправлена';
    $safe = htmlspecialchars($message, ENT_QUOTES, 'UTF-8');
    echo '<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">'
        . '<meta name="viewport" content="width=device-width,initial-scale=1">'
        . '<meta name="robots" content="noindex">'
        . '<title>' . $title . '</title>'
        . '<style>body{margin:0;min-height:100vh;display:grid;place-items:center;'
        . 'background:#1f2124;color:#f4f6f7;font-family:system-ui,Arial,sans-serif;'
        . 'line-height:1.6;padding:24px}main{max-width:34rem}h1{font-size:1.5rem;'
        . 'margin:0 0 12px}a{color:#c9a227}</style></head><body><main>'
        . '<h1>' . $title . '</h1><p>' . $safe . '</p>'
        . '<p><a href="index.html">Вернуться на сайт</a></p>'
        . '</main></body></html>';
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    respond(false, 'Форма отправляется только методом POST.', $isAjax);
}

/** Убирает переводы строк, чтобы через поле нельзя было подделать заголовки письма. */
function clean($value, $limit)
{
    $value = is_string($value) ? $value : '';
    $value = str_replace(["\r", "\0"], '', $value);
    $value = trim($value);
    return mb_substr($value, 0, $limit);
}

function oneLine($value, $limit)
{
    return clean(str_replace("\n", ' ', $value), $limit);
}

$name    = oneLine($_POST['name']    ?? '', 80);
$phone   = oneLine($_POST['phone']   ?? '', 40);
$email   = oneLine($_POST['email']   ?? '', 120);
$message = clean($_POST['message']   ?? '', 2000);
$consent = !empty($_POST['consent']);
$trap    = oneLine($_POST['company'] ?? '', 100);
$ts      = isset($_POST['ts']) ? (int) $_POST['ts'] : 0;

// Ловушка для роботов: поле скрыто, человек его не заполнит.
// Отвечаем «принято», чтобы робот не подбирал обход.
if ($trap !== '') {
    respond(true, 'Заявка принята.', $isAjax);
}

// Слишком быстрая отправка - тоже признак робота.
if ($ts > 0 && (microtime(true) * 1000 - $ts) < $CONFIG['min_seconds'] * 1000) {
    respond(true, 'Заявка принята.', $isAjax);
}

// --- проверка полей ----------------------------------------------------------

$errors = [];

if ($name === '') {
    $errors[] = 'Напишите, как к вам обращаться.';
} elseif (mb_strlen($name) < 2) {
    $errors[] = 'Имя слишком короткое - нужно хотя бы две буквы.';
}

$digits = preg_replace('/\D+/', '', $phone);
if ($digits === '') {
    $errors[] = 'Оставьте телефон, чтобы мы могли перезвонить.';
} elseif (strlen($digits) !== 11) {
    $errors[] = 'В телефоне должно быть 11 цифр, например +7 (929) 555-50-00.';
}

if ($email !== '' && !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    $errors[] = 'Проверьте адрес почты: нужны знак @ и точка, например name@mail.ru.';
}

if (!$consent) {
    $errors[] = 'Без согласия на обработку персональных данных мы не вправе принять заявку.';
}

if ($errors) {
    respond(false, implode(' ', $errors), $isAjax);
}

// --- ограничение частоты -----------------------------------------------------

if (!empty($CONFIG['per_hour'])) {
    $ip = $_SERVER['REMOTE_ADDR'] ?? 'unknown';
    $file = sys_get_temp_dir() . '/master-leads-' . md5($ip) . '.txt';
    $now = time();
    $hits = [];

    if (is_readable($file)) {
        $raw = @file_get_contents($file);
        foreach (explode("\n", (string) $raw) as $line) {
            $line = (int) trim($line);
            if ($line > $now - 3600) {
                $hits[] = $line;
            }
        }
    }

    if (count($hits) >= (int) $CONFIG['per_hour']) {
        respond(false, 'С этого адреса уже отправлено несколько заявок. Попробуйте позже или позвоните нам.', $isAjax);
    }

    $hits[] = $now;
    @file_put_contents($file, implode("\n", $hits), LOCK_EX);
}

// --- сборка текста -----------------------------------------------------------

$when = date('d.m.Y H:i');
$ip = $_SERVER['REMOTE_ADDR'] ?? '-';
$page = oneLine($_SERVER['HTTP_REFERER'] ?? '-', 300);

$lines = [
    'Заявка с сайта ООО «МАСТЕР»',
    '',
    'Имя: ' . $name,
    'Телефон: ' . $phone,
];
if ($email !== '')   { $lines[] = 'Почта: ' . $email; }
if ($message !== '') { $lines[] = 'Комментарий: ' . $message; }
$lines[] = '';
$lines[] = 'Отправлено: ' . $when;
$lines[] = 'Страница: ' . $page;
$lines[] = 'IP: ' . $ip;

$text = implode("\n", $lines);

// --- отправка ----------------------------------------------------------------

/** Кодирует тему письма, чтобы кириллица не превратилась в вопросительные знаки. */
function encodeHeader($value)
{
    return '=?UTF-8?B?' . base64_encode($value) . '?=';
}

function sendByMail(array $c, $text, $name, $phone, $replyTo)
{
    $subject = encodeHeader($c['subject'] . ' - ' . $name . ', ' . $phone);
    $from = encodeHeader($c['from_name']) . ' <' . $c['from'] . '>';

    $headers = [
        'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=UTF-8',
        'Content-Transfer-Encoding: 8bit',
        'From: ' . $from,
    ];
    if ($replyTo !== '') {
        $headers[] = 'Reply-To: ' . $replyTo;
    }

    if ($c['mail_transport'] === 'smtp') {
        return sendBySmtp($c, $subject, $headers, $text);
    }

    return @mail($c['to'], $subject, $text, implode("\r\n", $headers), '-f' . $c['from']);
}

/** Небольшой SMTP-клиент: нужен, когда хостинг не отправляет письма сам. */
function sendBySmtp(array $c, $subject, array $headers, $text)
{
    $s = $c['smtp'];
    $host = ($s['secure'] === 'ssl' ? 'ssl://' : '') . $s['host'];
    $socket = @fsockopen($host, (int) $s['port'], $errno, $errstr, 15);
    if (!$socket) {
        return false;
    }
    stream_set_timeout($socket, 15);

    $read = function () use ($socket) {
        $data = '';
        while (($line = fgets($socket, 1024)) !== false) {
            $data .= $line;
            if (strlen($line) < 4 || $line[3] === ' ') {
                break;
            }
        }
        return $data;
    };

    $say = function ($command, $expect) use ($socket, $read) {
        if ($command !== null) {
            fwrite($socket, $command . "\r\n");
        }
        $answer = $read();
        return substr($answer, 0, 3) === (string) $expect;
    };

    $ok = $say(null, 220)
        && $say('EHLO ' . $s['host'], 250);

    if ($ok && $s['secure'] === 'tls') {
        $ok = $say('STARTTLS', 220)
            && stream_socket_enable_crypto($socket, true, STREAM_CRYPTO_METHOD_TLS_CLIENT)
            && $say('EHLO ' . $s['host'], 250);
    }

    $ok = $ok
        && $say('AUTH LOGIN', 334)
        && $say(base64_encode($s['user']), 334)
        && $say(base64_encode($s['pass']), 235)
        && $say('MAIL FROM:<' . $c['from'] . '>', 250);

    foreach (array_map('trim', explode(',', $c['to'])) as $recipient) {
        if ($recipient === '') {
            continue;
        }
        $ok = $ok && $say('RCPT TO:<' . $recipient . '>', 250);
    }

    if ($ok && $say('DATA', 354)) {
        $body = implode("\r\n", array_merge($headers, [
            'To: ' . $c['to'],
            'Subject: ' . $subject,
            'Date: ' . date('r'),
            '',
            // точка в начале строки экранируется, иначе письмо оборвётся
            preg_replace('/^\./m', '..', str_replace("\n", "\r\n", $text)),
        ]));
        fwrite($socket, $body . "\r\n.\r\n");
        $ok = $say(null, 250);
    } else {
        $ok = false;
    }

    $say('QUIT', 221);
    fclose($socket);

    return $ok;
}

function sendByTelegram(array $c, $text)
{
    $t = $c['telegram'];
    if ($t['token'] === '' || $t['chat_id'] === '') {
        return false;
    }

    $payload = http_build_query([
        'chat_id' => $t['chat_id'],
        'text' => $text,
        'disable_web_page_preview' => 'true',
    ]);
    $url = 'https://api.telegram.org/bot' . $t['token'] . '/sendMessage';

    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $payload,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 15,
        ]);
        $answer = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        return $code === 200 && $answer !== false;
    }

    $answer = @file_get_contents($url, false, stream_context_create([
        'http' => [
            'method' => 'POST',
            'header' => "Content-Type: application/x-www-form-urlencoded\r\n",
            'content' => $payload,
            'timeout' => 15,
            'ignore_errors' => true,
        ],
    ]));

    return $answer !== false && strpos($answer, '"ok":true') !== false;
}

$mode = $CONFIG['mode'];
$sent = false;

if ($mode === 'mail' || $mode === 'both') {
    $sent = sendByMail($CONFIG, $text, $name, $phone, $email) || $sent;
}

if ($mode === 'telegram' || $mode === 'both') {
    $sent = sendByTelegram($CONFIG, $text) || $sent;
}

if (!$sent) {
    // Заявку всё равно сохраняем рядом со скриптом, чтобы она не потерялась.
    @file_put_contents(__DIR__ . '/leads.log', $text . "\n\n---\n\n", FILE_APPEND | LOCK_EX);

    respond(
        false,
        'Не получилось отправить заявку. Позвоните нам: +7 (929) 555-50-00 или напишите на ooomaster2022@mail.ru.',
        $isAjax
    );
}

respond(true, 'Спасибо, заявка отправлена. Мы свяжемся с вами по указанному телефону.', $isAjax);
