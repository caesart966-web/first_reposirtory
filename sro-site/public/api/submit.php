<?php
/**
 * Приём заявок с сайта на своей же площадке.
 *
 * Зачем: раньше форма уходила в Web3Forms — зарубежный сервис, который из
 * России без VPN не открывается, и заявки просто не доходили бы. Этот файл
 * лежит на том же домене, что и сайт, поэтому блокировки его не касаются:
 * браузер посетителя никуда наружу не ходит.
 *
 * Формат запроса и ответа намеренно повторяет Web3Forms — фронтенд менять
 * не пришлось, в сборке меняется только адрес: VITE_LEAD_ENDPOINT.
 *
 * Требуется обычный хостинг с PHP (Beget, Timeweb, REG.RU и подобные).
 * На объектном хранилище без PHP и на GitHub Pages этот способ не работает.
 *
 * Два способа отправить письмо, оба здесь:
 *
 *   1. SMTP через ящик получателя (рекомендуется). Письмо кладётся прямо на
 *      сервер mail.ru от имени того же ящика, куда идёт заявка. Доходит за
 *      секунды и не попадает в спам: отправитель и получатель — один ящик,
 *      проверять SPF и DKIM почте не у кого. Домен для почты покупать не надо.
 *   2. Функция mail() хостинга — если SMTP не заполнен. Работает без настроек,
 *      но письма с чужого домена mail.ru нередко кладёт в спам.
 *
 * Проверка после заливки — открыть в браузере:
 *   https://ваш-домен/api/submit.php?selftest=<FORM_TOKEN>
 * Страница покажет, ушло письмо или нет, и что именно ответил сервер почты.
 *
 * ЧТО НУЖНО ЗАПОЛНИТЬ ПЕРЕД ЗАЛИВКОЙ — блок настроек ниже.
 */

// --- настройки ------------------------------------------------------------

// Куда приходят заявки. Можно несколько адресов через запятую.
const MAIL_TO = '9001330219@mail.ru';

// Ящик и пароль для отправки по SMTP. Пустой SMTP_USER выключает SMTP, и
// письма уходят функцией mail() хостинга.
//
// Пароль — НЕ пароль от почты. В mail.ru обычный пароль для внешних программ
// не работает: в настройках ящика есть раздел паролей для внешних приложений,
// там создаётся отдельный пароль, его и вставляем. Он даёт доступ только к
// отправке и почте, и его можно отозвать одной кнопкой, не меняя основной.
//
// Хост и порт для mail.ru указаны в том же разделе настроек ящика — сверьте
// их там перед заливкой, если mail.ru что-то поменяет.
const SMTP_HOST = 'smtp.mail.ru';
const SMTP_PORT = 465; // 465 — сразу шифрованное соединение, 587 — STARTTLS
const SMTP_USER = '9001330219@mail.ru';
const SMTP_PASS = '';

// От кого уходит письмо. Пустая строка — правильное значение: тогда берётся
// SMTP_USER, то есть ящик отправляет сам себе. Заполнять нужно только при
// отправке через mail(), и обязательно адресом на домене сайта: с чужого
// домена почта получателя сочтёт письмо подделкой, потому что не сойдётся SPF.
const MAIL_FROM = '';

// Тот же токен, что в VITE_LEAD_ACCESS_KEY при сборке сайта. Секретом он не
// является — лежит в коде страницы, — но отсекает ботов, которые долбят
// формы наугад, не читая разметку.
const FORM_TOKEN = 'sro-mn3gi1r1iambpw0ljb25fzcdqwm1';

// Домен сайта. Запросы с других адресов не принимаем: так чужая страница
// не сможет слать заявки от вашего имени. Пустая строка отключает проверку.
const ALLOWED_HOST = '';

// Не больше стольких заявок с одного адреса за час.
const RATE_LIMIT = 10;

// --- дальше править не нужно ---------------------------------------------

const MAX_FIELD = 200;
const MAX_MESSAGE = 4000;
const SMTP_TIMEOUT = 20;

function fail(int $code, string $message): never
{
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['success' => false, 'message' => $message], JSON_UNESCAPED_UNICODE);
    exit;
}

/** Убирает переводы строк: без этого в заголовки письма можно дописать чужие. */
function header_safe(string $value, int $limit = MAX_FIELD): string
{
    $value = str_replace(["\r", "\n", "\0"], ' ', $value);
    return mb_substr(trim($value), 0, $limit);
}

/** Тема письма по-русски: без кодирования почтовые клиенты покажут кракозябры. */
function encode_subject(string $subject): string
{
    return '=?UTF-8?B?' . base64_encode($subject) . '?=';
}

function client_ip(): string
{
    return (string) ($_SERVER['REMOTE_ADDR'] ?? 'unknown');
}

/** Адрес в конверте письма: SMTP_USER, если включён SMTP, иначе MAIL_FROM. */
function sender(): string
{
    return SMTP_USER !== '' ? SMTP_USER : MAIL_FROM;
}

/** Простое ограничение частоты: счётчик на час в файле во временной папке. */
function rate_limited(): bool
{
    $file = sys_get_temp_dir() . '/sro-leads-' . date('YmdH') . '-' . md5(client_ip()) . '.count';
    $count = is_file($file) ? (int) file_get_contents($file) : 0;
    if ($count >= RATE_LIMIT) {
        return true;
    }
    file_put_contents($file, (string) ($count + 1), LOCK_EX);
    return false;
}

/**
 * Отправка письма напрямую через SMTP.
 *
 * Готовой библиотеки здесь намеренно нет: на дешёвом хостинге composer часто
 * недоступен, а весь нужный разговор с сервером — шесть команд. Тело письма
 * кодируется base64: 8bit проходит не на каждом сервере, base64 — на любом.
 *
 * $error заполняется дословным ответом сервера — по нему сразу видно, что
 * не так: неверный пароль, закрытый порт, отказ принимать адрес.
 */
function smtp_send(array $to, string $subject, string $body, array $headers, ?string &$error): bool
{
    $transport = SMTP_PORT === 465 ? 'ssl://' : 'tcp://';
    $socket = @stream_socket_client(
        $transport . SMTP_HOST . ':' . SMTP_PORT,
        $errno,
        $errstr,
        SMTP_TIMEOUT,
        STREAM_CLIENT_CONNECT,
    );
    if (!$socket) {
        $error = "не удалось соединиться с " . SMTP_HOST . ':' . SMTP_PORT . " — $errstr ($errno)";
        return false;
    }
    stream_set_timeout($socket, SMTP_TIMEOUT);

    // Ответ сервера бывает в несколько строк: у всех, кроме последней,
    // на четвёртом месте дефис вместо пробела.
    $read = static function () use ($socket): array {
        $lines = [];
        while (($line = fgets($socket, 2048)) !== false) {
            $lines[] = rtrim($line, "\r\n");
            if (strlen($line) < 4 || $line[3] !== '-') {
                break;
            }
        }
        $text = implode(' / ', $lines);
        return [(int) substr((string) end($lines), 0, 3), $text];
    };

    $say = static function (?string $line, array $expect, string $what) use (
        $socket,
        $read,
        &$error,
    ): bool {
        if ($line !== null) {
            fwrite($socket, $line . "\r\n");
        }
        [$code, $text] = $read();
        if (!in_array($code, $expect, true)) {
            $error = "{$what}: сервер ответил «{$text}»";
            return false;
        }
        return true;
    };

    try {
        $me = 'sro-site';
        if (!$say(null, [220], 'приветствие')) {
            return false;
        }
        if (!$say("EHLO $me", [250], 'EHLO')) {
            return false;
        }
        // На 587 соединение открывается открытым и шифруется отдельной командой.
        if (SMTP_PORT !== 465) {
            if (!$say('STARTTLS', [220], 'STARTTLS')) {
                return false;
            }
            if (!@stream_socket_enable_crypto($socket, true, STREAM_CRYPTO_METHOD_TLS_CLIENT)) {
                $error = 'не удалось включить шифрование (STARTTLS)';
                return false;
            }
            if (!$say("EHLO $me", [250], 'EHLO после STARTTLS')) {
                return false;
            }
        }
        if (!$say('AUTH LOGIN', [334], 'AUTH LOGIN')) {
            return false;
        }
        if (!$say(base64_encode(SMTP_USER), [334], 'имя пользователя')) {
            return false;
        }
        if (!$say(base64_encode(SMTP_PASS), [235], 'пароль (нужен пароль для внешнего приложения)')) {
            return false;
        }
        if (!$say('MAIL FROM:<' . sender() . '>', [250], 'адрес отправителя')) {
            return false;
        }
        foreach ($to as $address) {
            if (!$say("RCPT TO:<$address>", [250, 251], "адрес получателя $address")) {
                return false;
            }
        }
        if (!$say('DATA', [354], 'DATA')) {
            return false;
        }

        $head = array_merge(
            [
                'To: ' . implode(', ', $to),
                'Subject: ' . $subject,
                'Date: ' . date('r'),
                'Message-ID: <' . bin2hex(random_bytes(12)) . '@' . SMTP_HOST . '>',
            ],
            $headers,
            ['Content-Transfer-Encoding: base64'],
        );
        // Точка в начале строки завершила бы письмо — по правилам SMTP её удваивают.
        $payload = chunk_split(base64_encode($body), 76, "\r\n");
        $letter = implode("\r\n", $head) . "\r\n\r\n" . str_replace("\r\n.", "\r\n..", $payload);
        fwrite($socket, $letter . "\r\n.\r\n");

        return $say(null, [250], 'приём письма');
    } finally {
        @fwrite($socket, "QUIT\r\n");
        @fclose($socket);
    }
}

/**
 * Отправка. В режиме проверки письмо не уходит, а пишется в файл — так можно
 * убедиться, что обработчик собирает письмо правильно, не рассылая почту.
 */
function deliver(array $to, string $subject, string $body, array $headers, ?string &$error): bool
{
    $dry = getenv('SRO_MAIL_DRY_RUN');
    if ($dry) {
        $dump = 'To: ' . implode(', ', $to) . "\n" . implode("\n", $headers) . "\nSubject: $subject\n\n$body\n";
        return (bool) file_put_contents($dry, $dump);
    }

    if (SMTP_USER !== '') {
        return smtp_send($to, $subject, $body, $headers, $error);
    }

    if (sender() === '') {
        $error = 'не заполнен ни SMTP_USER, ни MAIL_FROM';
        return false;
    }

    // Пятый параметр задаёт конверт отправителя — по нему принимающая сторона
    // проверяет SPF. Без него письма чаще уходят в спам.
    $sent = mail(
        implode(', ', $to),
        $subject,
        $body,
        implode("\r\n", array_merge($headers, ['Content-Transfer-Encoding: 8bit'])),
        '-f' . sender(),
    );
    if (!$sent) {
        $error = 'функция mail() хостинга вернула отказ';
    }
    return $sent;
}

/** Список получателей из MAIL_TO. */
function recipients(): array
{
    $list = array_filter(array_map('trim', explode(',', MAIL_TO)), static fn($a) => $a !== '');
    return array_values($list);
}

function letter_headers(string $fromName, string $replyTo): array
{
    $headers = [
        'From: ' . encode_subject($fromName) . ' <' . sender() . '>',
        'Content-Type: text/plain; charset=UTF-8',
        'MIME-Version: 1.0',
    ];
    if ($replyTo !== '') {
        $headers[] = 'Reply-To: ' . $replyTo;
    }
    return $headers;
}

// --- проверка настроек ----------------------------------------------------

// Открывается в браузере после заливки на хостинг и отвечает на единственный
// вопрос: дойдёт письмо или нет. Без такой проверки о неверном пароле узнают
// от посетителя, который не дождался ответа на заявку.
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'GET' && isset($_GET['selftest'])) {
    header('Content-Type: text/plain; charset=utf-8');
    if (!hash_equals(FORM_TOKEN, (string) $_GET['selftest'])) {
        http_response_code(403);
        echo "Неверный токен. Нужен тот же, что в FORM_TOKEN.\n";
        exit;
    }
    if (rate_limited()) {
        http_response_code(429);
        echo "Слишком много проверок подряд, попробуйте через час.\n";
        exit;
    }

    $way = SMTP_USER !== '' ? 'SMTP через ' . SMTP_HOST . ':' . SMTP_PORT : 'функция mail() хостинга';
    echo "Способ отправки: $way\n";
    echo 'Отправитель: ' . (sender() ?: '— не задан —') . "\n";
    echo 'Получатель:  ' . implode(', ', recipients()) . "\n\n";

    $error = null;
    $ok = deliver(
        recipients(),
        encode_subject('Проверка формы сайта СРО'),
        "Это проверочное письмо с формы сайта.\nЕсли оно пришло — заявки будут приходить сюда же.\n\n"
            . 'Отправлено: ' . date('d.m.Y H:i:s') . "\n",
        letter_headers('Проверка формы', ''),
        $error,
    );
    if ($ok) {
        echo "РЕЗУЛЬТАТ: письмо отправлено. Проверьте ящик, в том числе папку «Спам».\n";
    } else {
        http_response_code(500);
        echo "РЕЗУЛЬТАТ: отправить не удалось.\n";
        echo "Причина: $error\n";
    }
    exit;
}

// --- приём заявки ---------------------------------------------------------

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    fail(405, 'Метод не поддерживается');
}

if (ALLOWED_HOST !== '') {
    $origin = $_SERVER['HTTP_ORIGIN'] ?? $_SERVER['HTTP_REFERER'] ?? '';
    $host = $origin === '' ? '' : (string) parse_url($origin, PHP_URL_HOST);
    if ($host !== ALLOWED_HOST) {
        fail(403, 'Запрос не с сайта');
    }
}

$raw = file_get_contents('php://input');
if ($raw === false || strlen($raw) > 16384) {
    fail(400, 'Пустой или слишком большой запрос');
}

$data = json_decode($raw, true);
if (!is_array($data)) {
    fail(400, 'Ожидается JSON');
}

if (!hash_equals(FORM_TOKEN, (string) ($data['access_key'] ?? ''))) {
    fail(403, 'Неверный ключ формы');
}

$message = trim((string) ($data['message'] ?? ''));
if ($message === '') {
    fail(400, 'Пустая заявка');
}
$message = mb_substr($message, 0, MAX_MESSAGE);

$subject = header_safe((string) ($data['subject'] ?? 'Заявка с сайта'));
$fromName = header_safe((string) ($data['from_name'] ?? 'Заявка с сайта'), 100);
$replyTo = header_safe((string) ($data['replyto'] ?? ''), 254);

if ($replyTo !== '' && !filter_var($replyTo, FILTER_VALIDATE_EMAIL)) {
    $replyTo = '';
}

if (rate_limited()) {
    fail(429, 'Слишком много заявок подряд, попробуйте позже');
}

// В письмо добавляем время и адрес — пригодится, если заявка спорная.
$body = $message . "\n\n---\nПолучено: " . date('d.m.Y H:i:s') . "\nIP: " . client_ip();

$error = null;
if (!deliver(recipients(), encode_subject($subject), $body, letter_headers($fromName, $replyTo), $error)) {
    // Молчаливого «успеха» быть не должно: посетитель увидит экран ошибки
    // с прямыми контактами и позвонит, вместо того чтобы ждать ответа.
    error_log('sro-site: заявка не отправлена — ' . (string) $error);
    fail(500, 'Письмо не удалось отправить');
}

header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');
echo json_encode(['success' => true], JSON_UNESCAPED_UNICODE);
